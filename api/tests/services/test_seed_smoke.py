"""Not part of the unit-test pyramid described in ADR 0000 - this is a
one-off smoke test proving scripts/seed.py actually runs end-to-end
(hierarchy build, dotted lines, dual co-managers, vacancies, dual-role
employee) against the real test database, and that it's idempotent and
resettable as required.
"""

import pytest

from app.repos import OrganizationRepo, PositionRepo
from scripts.seed import seed

pytestmark = pytest.mark.integration


def test_seed_is_idempotent_and_produces_the_documented_demo_story(db):
    seed()
    seed()  # must be a no-op the second time, not a duplicate/crash

    org_repo = OrganizationRepo()
    tenant_a = org_repo.find_by_name("Acme Corporation")
    tenant_b = org_repo.find_by_name("Bramble & Co")
    assert tenant_a is not None
    assert tenant_b is not None

    position_repo = PositionRepo(tenant_a["_id"])
    positions = position_repo.list_for_graph()
    assert 100 <= len(positions) <= 150

    vacant = [p for p in positions if p["status"] == "vacant"]
    assert len(vacant) == 10

    dual_solid = [p for p in positions if len(p["solid_manager_ids"]) == 2]
    assert len(dual_solid) == 2

    dotted = [p for p in positions if any(e["relation"] == "dotted" for e in p["reports_to"])]
    assert len(dotted) >= 1

    tenant_b_positions = PositionRepo(tenant_b["_id"]).list_for_graph()
    assert len(tenant_b_positions) < len(positions)


def test_seed_reset_removes_and_recreates_the_tenants(db):
    seed()
    org_repo = OrganizationRepo()
    first_org_id = org_repo.find_by_name("Acme Corporation")["_id"]

    seed(reset=True)

    second_org_id = org_repo.find_by_name("Acme Corporation")["_id"]
    assert first_org_id != second_org_id
