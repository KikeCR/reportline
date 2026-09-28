from datetime import UTC, datetime, timedelta

import pytest
from bson import ObjectId

from app.repos import AssignmentRepo
from tests.factories import build_assignment

pytestmark = pytest.mark.integration


def test_create_defaults_to_current_full_time_primary_assignment(db):
    org_id = ObjectId()
    repo = AssignmentRepo(org_id)
    start = datetime.now(UTC)

    assignment_id = repo.create(ObjectId(), ObjectId(), start_date=start)

    current = repo.current_for_position(
        db["assignments"].find_one({"_id": assignment_id})["position_id"]
    )
    assert current[0]["fte"] == 1.0
    assert current[0]["is_primary"] is True
    assert current[0]["end_date"] is None


def test_tenant_isolation_on_current_for_position(db):
    org_a, org_b = ObjectId(), ObjectId()
    position_id = ObjectId()
    db["assignments"].insert_one(build_assignment(org_b, ObjectId(), position_id))

    repo_a = AssignmentRepo(org_a)

    assert repo_a.current_for_position(position_id) == []


def test_current_for_position_excludes_ended_assignments(db):
    org_id = ObjectId()
    position_id = ObjectId()
    now = datetime.now(UTC)
    db["assignments"].insert_one(
        build_assignment(org_id, ObjectId(), position_id, end_date=now - timedelta(days=1))
    )
    current = build_assignment(org_id, ObjectId(), position_id, end_date=None)
    db["assignments"].insert_one(current)
    repo = AssignmentRepo(org_id)

    result = repo.current_for_position(position_id)

    assert [r["_id"] for r in result] == [current["_id"]]


def test_as_of_for_position_finds_assignment_active_on_that_date(db):
    org_id = ObjectId()
    position_id = ObjectId()
    start = datetime(2024, 1, 1, tzinfo=UTC)
    end = datetime(2024, 6, 1, tzinfo=UTC)
    past_assignment = build_assignment(
        org_id, ObjectId(), position_id, start_date=start, end_date=end
    )
    db["assignments"].insert_one(past_assignment)
    repo = AssignmentRepo(org_id)

    as_of_during = repo.as_of_for_position(position_id, datetime(2024, 3, 1, tzinfo=UTC))
    as_of_after = repo.as_of_for_position(position_id, datetime(2025, 1, 1, tzinfo=UTC))

    assert [r["_id"] for r in as_of_during] == [past_assignment["_id"]]
    assert as_of_after == []


def test_current_for_employee_supports_dual_role_holding_two_positions(db):
    org_id = ObjectId()
    employee_id = ObjectId()
    assignment_a = build_assignment(org_id, employee_id, ObjectId(), fte=0.5, is_primary=True)
    assignment_b = build_assignment(org_id, employee_id, ObjectId(), fte=0.5, is_primary=False)
    db["assignments"].insert_many([assignment_a, assignment_b])
    repo = AssignmentRepo(org_id)

    result = repo.current_for_employee(employee_id)

    assert {r["_id"] for r in result} == {assignment_a["_id"], assignment_b["_id"]}
