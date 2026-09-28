from datetime import UTC, datetime
from decimal import Decimal

import pytest
from bson import Decimal128, ObjectId
from pydantic import ValidationError

from app.models import Employee


def _base_kwargs(**overrides):
    now = datetime.now(UTC)
    kwargs = {
        "_id": ObjectId(),
        "org_id": ObjectId(),
        "name": "Ada Lovelace",
        "email": "ada@example.com",
        "compensation": {"amount": "150000.00", "currency": "USD"},
        "created_at": now,
        "updated_at": now,
    }
    kwargs.update(overrides)
    return kwargs


def test_employee_compensation_round_trips_as_decimal():
    employee = Employee(**_base_kwargs())

    assert isinstance(employee.compensation.amount, Decimal128)
    assert employee.compensation.amount.to_decimal() == Decimal("150000.00")


def test_employee_rejects_invalid_email():
    with pytest.raises(ValidationError, match="not a valid email"):
        Employee(**_base_kwargs(email="not-an-email"))


def test_employee_defaults_to_no_source_refs():
    employee = Employee(**_base_kwargs())

    assert employee.source_refs == []


def test_employee_serializes_compensation_as_decimal_string_for_json():
    employee = Employee(**_base_kwargs())

    dumped = employee.model_dump(mode="json")

    assert dumped["compensation"]["amount"] == "150000.00"
    assert dumped["id"] == str(employee.id)
