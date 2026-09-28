from datetime import UTC, datetime

import pytest
from bson import ObjectId
from pydantic import ValidationError

from app.models import MAX_REPORTS_TO, Position, PositionStatus, ReportsToEdge


def _base_kwargs(**overrides):
    now = datetime.now(UTC)
    kwargs = {
        "_id": ObjectId(),
        "org_id": ObjectId(),
        "title": "VP Engineering",
        "department": "Engineering",
        "created_at": now,
        "updated_at": now,
    }
    kwargs.update(overrides)
    return kwargs


def test_position_defaults_to_active_with_no_edges():
    position = Position(**_base_kwargs())

    assert position.status == PositionStatus.ACTIVE
    assert position.reports_to == []
    assert position.solid_manager_ids == []
    assert position.ancestor_ids == []


def test_solid_manager_ids_must_match_solid_edges_in_reports_to():
    manager_id = ObjectId()

    with pytest.raises(ValidationError, match="solid_manager_ids must exactly match"):
        Position(
            **_base_kwargs(
                reports_to=[{"position_id": manager_id, "relation": "solid", "is_primary": True}],
                solid_manager_ids=[],
            )
        )


def test_dotted_edges_are_excluded_from_solid_manager_ids():
    manager_id = ObjectId()

    position = Position(
        **_base_kwargs(
            reports_to=[{"position_id": manager_id, "relation": "dotted", "is_primary": False}],
            solid_manager_ids=[],
        )
    )

    assert position.solid_manager_ids == []


def test_rejects_more_than_one_primary_solid_edge():
    with pytest.raises(ValidationError, match="at most one primary solid"):
        Position(
            **_base_kwargs(
                reports_to=[
                    {"position_id": ObjectId(), "relation": "solid", "is_primary": True},
                    {"position_id": ObjectId(), "relation": "solid", "is_primary": True},
                ],
                solid_manager_ids=[ObjectId(), ObjectId()],
            )
        )


def test_allows_two_co_managers_when_only_one_is_primary():
    manager_a, manager_b = ObjectId(), ObjectId()

    position = Position(
        **_base_kwargs(
            reports_to=[
                {"position_id": manager_a, "relation": "solid", "is_primary": True},
                {"position_id": manager_b, "relation": "solid", "is_primary": False},
            ],
            solid_manager_ids=[manager_a, manager_b],
        )
    )

    assert len(position.solid_manager_ids) == 2


def test_reports_to_is_capped():
    edges = [
        {"position_id": ObjectId(), "relation": "dotted", "is_primary": False}
        for _ in range(MAX_REPORTS_TO + 1)
    ]

    with pytest.raises(ValidationError, match="at most"):
        Position(**_base_kwargs(reports_to=edges, solid_manager_ids=[]))


def test_reports_to_edge_rejects_unknown_relation():
    with pytest.raises(ValidationError):
        ReportsToEdge(position_id=ObjectId(), relation="loose", is_primary=False)
