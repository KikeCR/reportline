"""$jsonSchema validator for the assignments collection. See
docs/data-model.md - kept in sync with app.models.assignment.Assignment by
tests/repos/test_validators_match_models.py.
"""

from typing import Any

ASSIGNMENTS_VALIDATOR: dict[str, Any] = {
    "$jsonSchema": {
        "bsonType": "object",
        "required": [
            "org_id",
            "employee_id",
            "position_id",
            "start_date",
            "fte",
            "is_primary",
            "schema_version",
            "created_at",
            "updated_at",
        ],
        "additionalProperties": False,
        "properties": {
            "_id": {"bsonType": "objectId"},
            "org_id": {"bsonType": "objectId"},
            "employee_id": {"bsonType": "objectId"},
            "position_id": {"bsonType": "objectId"},
            "start_date": {"bsonType": "date"},
            "end_date": {"bsonType": ["date", "null"]},
            "fte": {"bsonType": "double", "minimum": 0, "exclusiveMinimum": True, "maximum": 1},
            "is_primary": {"bsonType": "bool"},
            "schema_version": {"bsonType": "int"},
            "created_at": {"bsonType": "date"},
            "updated_at": {"bsonType": "date"},
            "created_by": {"bsonType": ["objectId", "null"]},
            "updated_by": {"bsonType": ["objectId", "null"]},
        },
    }
}
