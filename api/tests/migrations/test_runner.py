import pytest
from bson import ObjectId
from pymongo.errors import DuplicateKeyError, WriteError

from migrations.runner import migration_status, run_migrations
from tests.factories import build_employee, build_position

pytestmark = pytest.mark.integration


def test_applying_from_empty_creates_every_collection(db):
    for name in (
        "organizations",
        "positions",
        "employees",
        "assignments",
        "quarantine",
        "sync_runs",
    ):
        assert name in db.list_collection_names()


def test_re_running_migrations_is_a_no_op(db):
    applied = run_migrations(db)

    assert applied == []


def test_migration_status_reports_every_migration_as_applied(db):
    status = migration_status(db)

    assert len(status) == 7
    assert all(entry["applied"] for entry in status)


def test_schema_migrations_are_recorded_with_version_name_checksum(db):
    records = list(db["schema_migrations"].find({}))

    assert {r["version"] for r in records} == {
        "0001",
        "0002",
        "0003",
        "0004",
        "0005",
        "0006",
        "0007",
    }
    for record in records:
        assert record["checksum"]
        assert record["applied_at"] is not None


def test_positions_validator_rejects_an_invalid_status(db):
    org_id = ObjectId()
    bad_position = build_position(org_id, status="on_leave")

    with pytest.raises(WriteError):
        db["positions"].insert_one(bad_position)


def test_positions_validator_rejects_more_than_the_capped_reports_to(db):
    org_id = ObjectId()
    too_many_edges = [
        {"position_id": ObjectId(), "relation": "dotted", "is_primary": False} for _ in range(9)
    ]
    bad_position = build_position(org_id, reports_to=too_many_edges)

    with pytest.raises(WriteError):
        db["positions"].insert_one(bad_position)


def test_employees_unique_source_ref_index_rejects_duplicates(db):
    org_id = ObjectId()
    ref = {"system": "workday_like", "id": "W-1"}
    db["employees"].insert_one(build_employee(org_id, source_refs=[ref]))

    with pytest.raises(DuplicateKeyError):
        db["employees"].insert_one(build_employee(org_id, source_refs=[ref]))


def test_employees_without_any_source_ref_do_not_collide(db):
    org_id = ObjectId()
    db["employees"].insert_one(build_employee(org_id, source_refs=[]))
    db["employees"].insert_one(build_employee(org_id, source_refs=[]))  # must not raise


@pytest.mark.parametrize(
    ("collection", "expected_index_names"),
    [
        (
            "positions",
            {
                "ix_positions_org_reports_to",
                "ix_positions_org_solid_manager_ids",
                "ix_positions_org_ancestor_ids",
                "ix_positions_org_status",
                "ux_positions_org_source_ref",
            },
        ),
        ("employees", {"ux_employees_org_source_ref"}),
        (
            "assignments",
            {"ix_assignments_org_position_start", "ix_assignments_org_employee_current"},
        ),
        ("quarantine", {"ix_quarantine_org_created"}),
        ("sync_runs", {"ix_sync_runs_org_started"}),
    ],
)
def test_expected_indexes_exist(db, collection, expected_index_names):
    index_names = set(db[collection].index_information().keys())

    assert expected_index_names <= index_names
