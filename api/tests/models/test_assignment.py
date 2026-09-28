from datetime import UTC, datetime, timedelta

import pytest
from bson import ObjectId
from pydantic import ValidationError

from app.models import Assignment


def _base_kwargs(**overrides):
    now = datetime.now(UTC)
    kwargs = {
        "_id": ObjectId(),
        "org_id": ObjectId(),
        "employee_id": ObjectId(),
        "position_id": ObjectId(),
        "start_date": now,
        "fte": 1.0,
        "created_at": now,
        "updated_at": now,
    }
    kwargs.update(overrides)
    return kwargs


def test_end_date_none_means_current():
    assignment = Assignment(**_base_kwargs())

    assert assignment.end_date is None


def test_rejects_end_date_before_start_date():
    start = datetime.now(UTC)

    with pytest.raises(ValidationError, match="end_date must not be before start_date"):
        Assignment(**_base_kwargs(start_date=start, end_date=start - timedelta(days=1)))


@pytest.mark.parametrize("fte", [0, -0.5, 1.1])
def test_rejects_fte_outside_valid_range(fte):
    with pytest.raises(ValidationError):
        Assignment(**_base_kwargs(fte=fte))


def test_allows_part_time_fte():
    assignment = Assignment(**_base_kwargs(fte=0.5))

    assert assignment.fte == 0.5
