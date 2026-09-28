from decimal import Decimal

import pytest
from bson import ObjectId

from app.integrations.bamboo_like import BambooLikeAdapter
from app.integrations.workday_like import WorkdayLikeAdapter
from app.repos import EmployeeRepo, PositionRepo, QuarantineRepo, SyncRunRepo
from app.services import org_graph
from app.services.sync import run_sync
from tests.factories import build_organization

pytestmark = pytest.mark.integration


def _seed_org(db) -> ObjectId:
    organization = build_organization()
    db["organizations"].insert_one(organization)
    return organization["_id"]


def test_workday_sync_creates_positions_employees_and_reporting_lines(db):
    org_id = _seed_org(db)

    result = run_sync(org_id, WorkdayLikeAdapter())

    position_repo = PositionRepo(org_id)
    ceo = position_repo.find_by_source_ref("workday_like", "W-001")
    vp = position_repo.find_by_source_ref("workday_like", "W-002")
    assert ceo is not None
    assert vp is not None
    assert vp["reports_to"] == [
        {"position_id": ceo["_id"], "relation": "solid", "is_primary": True}
    ]
    # W-003 (missing email) and W-004 (unresolved manager) are quarantined;
    # W-003 never even reaches pass 2, W-004 fails there.
    assert result.quarantined == 2
    assert result.created == 3  # W-001, W-002, W-004 (W-003 never got created)


def test_workday_sync_quarantines_invalid_records_without_failing_the_run(db):
    org_id = _seed_org(db)

    run_sync(org_id, WorkdayLikeAdapter())

    quarantined = QuarantineRepo(org_id).list_for_org()
    reasons = [q["errors"] for q in quarantined]
    assert any("email" in str(r) for r in reasons)
    assert any("unresolved manager reference" in r for r in reasons)


def test_sync_is_idempotent(db):
    org_id = _seed_org(db)

    run_sync(org_id, WorkdayLikeAdapter())
    positions_after_first = list(db["positions"].find({"org_id": org_id}))
    employees_after_first = list(db["employees"].find({"org_id": org_id}))

    second = run_sync(org_id, WorkdayLikeAdapter())

    positions_after_second = list(db["positions"].find({"org_id": org_id}))
    employees_after_second = list(db["employees"].find({"org_id": org_id}))
    assert len(positions_after_second) == len(positions_after_first)
    assert len(employees_after_second) == len(employees_after_first)
    assert second.created == 0
    assert second.unchanged == 3


def test_bamboo_sync_resolves_manager_by_email(db):
    org_id = _seed_org(db)

    run_sync(org_id, BambooLikeAdapter())

    position_repo = PositionRepo(org_id)
    carol = position_repo.find_by_source_ref("bamboo_like", "B-001")
    dave = position_repo.find_by_source_ref("bamboo_like", "B-002")
    assert dave["reports_to"] == [
        {"position_id": carol["_id"], "relation": "solid", "is_primary": True}
    ]


def test_bamboo_sync_quarantines_one_side_of_a_manager_cycle(db):
    org_id = _seed_org(db)

    result = run_sync(org_id, BambooLikeAdapter())

    position_repo = PositionRepo(org_id)
    cycle_a = position_repo.find_by_source_ref("bamboo_like", "B-004")
    cycle_b = position_repo.find_by_source_ref("bamboo_like", "B-005")
    # exactly one direction of the cycle resolved, the other was rejected.
    assert (len(cycle_a["reports_to"]) == 1) != (len(cycle_b["reports_to"]) == 1)
    assert result.quarantined >= 1


def test_quarantine_entries_do_not_duplicate_across_repeated_sync_runs(db):
    org_id = _seed_org(db)

    first = run_sync(org_id, WorkdayLikeAdapter())
    first_quarantine_count = len(QuarantineRepo(org_id).list_for_org())

    second = run_sync(org_id, WorkdayLikeAdapter())

    # Same still-broken fixture records every run: each is still reported as
    # quarantined, but re-syncing an unfixed record must not pile up a
    # duplicate quarantine document for the same underlying problem.
    assert second.quarantined == first.quarantined
    assert len(QuarantineRepo(org_id).list_for_org()) == first_quarantine_count


def test_sync_records_a_sync_run(db):
    org_id = _seed_org(db)

    run_sync(org_id, WorkdayLikeAdapter())

    runs = SyncRunRepo(org_id).list_for_org()
    assert len(runs) == 1
    assert runs[0]["source"] == "workday_like"
    assert runs[0]["created_count"] == 3


def test_sync_is_tenant_isolated(db):
    org_a = _seed_org(db)
    org_b = _seed_org(db)

    run_sync(org_a, WorkdayLikeAdapter())

    assert PositionRepo(org_b).find_by_source_ref("workday_like", "W-001") is None


def test_conflict_rule_last_synced_source_wins_the_primary_manager(db):
    """Two sources disagreeing about a manager: re-running a sync that
    resolves a different manager for an existing position replaces the old
    primary edge rather than adding a second one."""
    org_id = _seed_org(db)
    ceo = PositionRepo(org_id).create(
        "CEO", "Executive", source_refs=[{"system": "manual", "id": "ceo"}]
    )
    other_manager = PositionRepo(org_id).create("Other Manager", "Engineering")
    report = PositionRepo(org_id).create(
        "VP Engineering", "Engineering", source_refs=[{"system": "workday_like", "id": "W-002"}]
    )
    org_graph.add_reporting_line(org_id, other_manager, report, "solid", True)
    EmployeeRepo(org_id).create(
        "Priya Shah", "priya.shah@example.com", compensation_amount=Decimal("1")
    )
    # give the workday CEO worker's position a matching source ref so pass 2 resolves to it
    PositionRepo(org_id).update_fields(
        ceo,
        title="CEO",
        department="Executive",
        source_refs=[{"system": "workday_like", "id": "W-001"}],
    )

    run_sync(org_id, WorkdayLikeAdapter())

    updated_report = PositionRepo(org_id).get_by_id(report)
    assert len(updated_report["reports_to"]) == 1
    assert updated_report["reports_to"][0]["position_id"] == ceo
