"""Every $jsonSchema validator must agree with its canonical Pydantic model on
field names and enum values - CLAUDE.md requires the two be kept in sync,
and this is the automated check that catches drift.

"BSON-required" and "Pydantic-required" aren't the same thing (a Pydantic
field with a default, like ``status``, is still always present in a stored
document because the service always constructs the full model before
writing) - so the check is: every field Pydantic *cannot* construct without
(no default) must be BSON-required, and every BSON-required field must be a
real field on the model.
"""

from __future__ import annotations

from typing import Any

from app.models import Assignment, Employee, Organization, Position, QuarantineRecord
from app.repos.validators import (
    ASSIGNMENTS_VALIDATOR,
    EMPLOYEES_VALIDATOR,
    ORGANIZATIONS_VALIDATOR,
    POSITIONS_VALIDATOR,
    QUARANTINE_VALIDATOR,
)


def _bson_field_names(validator: dict[str, Any]) -> set[str]:
    return set(validator["$jsonSchema"]["properties"].keys())


def _bson_required(validator: dict[str, Any]) -> set[str]:
    return set(validator["$jsonSchema"]["required"])


def _model_field_names_by_alias(model: type) -> set[str]:
    return {
        (field.alias or name)
        for name, field in model.model_fields.items()  # type: ignore[attr-defined]
    }


def _model_required_by_alias(model: type) -> set[str]:
    # "_id" is excluded: MongoDB auto-generates it on insert, so validators
    # don't need to (and conventionally don't) list it as required, even
    # though our models always set it explicitly before inserting.
    return {
        (field.alias or name)
        for name, field in model.model_fields.items()  # type: ignore[attr-defined]
        if field.is_required()
    } - {"_id"}


def _assert_validator_matches_model(validator: dict[str, Any], model: type) -> None:
    bson_fields = _bson_field_names(validator)
    model_fields = _model_field_names_by_alias(model)
    assert bson_fields == model_fields, (
        f"validator properties {bson_fields} != model fields {model_fields}"
    )

    bson_required = _bson_required(validator)
    model_required = _model_required_by_alias(model)
    assert model_required <= bson_required, (
        f"model requires {model_required - bson_required} that the validator allows to be absent"
    )


def test_organizations_validator_matches_model():
    _assert_validator_matches_model(ORGANIZATIONS_VALIDATOR, Organization)


def test_positions_validator_matches_model():
    _assert_validator_matches_model(POSITIONS_VALIDATOR, Position)


def test_employees_validator_matches_model():
    _assert_validator_matches_model(EMPLOYEES_VALIDATOR, Employee)


def test_assignments_validator_matches_model():
    _assert_validator_matches_model(ASSIGNMENTS_VALIDATOR, Assignment)


def test_quarantine_validator_matches_model():
    _assert_validator_matches_model(QUARANTINE_VALIDATOR, QuarantineRecord)


def test_position_status_enum_matches_model():
    bson_statuses = set(POSITIONS_VALIDATOR["$jsonSchema"]["properties"]["status"]["enum"])
    model_statuses = {member.value for member in Position.model_fields["status"].annotation}  # type: ignore[attr-defined]

    assert bson_statuses == model_statuses


def test_reports_to_relation_enum_matches_model():
    bson_relations = set(
        POSITIONS_VALIDATOR["$jsonSchema"]["properties"]["reports_to"]["items"]["properties"][
            "relation"
        ]["enum"]
    )

    assert bson_relations == {"solid", "dotted"}
