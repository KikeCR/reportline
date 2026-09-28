"""$jsonSchema validator for the employees collection. See docs/data-model.md
- kept in sync with app.models.employee.Employee by
tests/repos/test_validators_match_models.py.
"""

from typing import Any

EMPLOYEES_VALIDATOR: dict[str, Any] = {
    "$jsonSchema": {
        "bsonType": "object",
        "required": [
            "org_id",
            "name",
            "email",
            "source_refs",
            "compensation",
            "schema_version",
            "created_at",
            "updated_at",
        ],
        "additionalProperties": False,
        "properties": {
            "_id": {"bsonType": "objectId"},
            "org_id": {"bsonType": "objectId"},
            "name": {"bsonType": "string", "minLength": 1, "maxLength": 200},
            "email": {"bsonType": "string"},
            "source_refs": {
                "bsonType": "array",
                "items": {
                    "bsonType": "object",
                    "required": ["system", "id"],
                    "additionalProperties": False,
                    "properties": {
                        "system": {"bsonType": "string", "minLength": 1},
                        "id": {"bsonType": "string", "minLength": 1},
                    },
                },
            },
            "compensation": {
                "bsonType": "object",
                "required": ["amount", "currency"],
                "additionalProperties": False,
                "properties": {
                    "amount": {"bsonType": "decimal"},
                    "currency": {"bsonType": "string", "minLength": 3, "maxLength": 3},
                },
            },
            "schema_version": {"bsonType": "int"},
            "created_at": {"bsonType": "date"},
            "updated_at": {"bsonType": "date"},
            "created_by": {"bsonType": ["objectId", "null"]},
            "updated_by": {"bsonType": ["objectId", "null"]},
        },
    }
}
