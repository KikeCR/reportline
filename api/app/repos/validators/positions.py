"""$jsonSchema validator for the positions collection. See docs/data-model.md
- kept in sync with app.models.position.Position by
tests/repos/test_validators_match_models.py.
"""

from typing import Any

from app.models.position import MAX_REPORTS_TO

_REPORTS_TO_EDGE_SCHEMA: dict[str, Any] = {
    "bsonType": "object",
    "required": ["position_id", "relation", "is_primary"],
    "additionalProperties": False,
    "properties": {
        "position_id": {"bsonType": "objectId"},
        "relation": {"enum": ["solid", "dotted"]},
        "is_primary": {"bsonType": "bool"},
    },
}

POSITIONS_VALIDATOR: dict[str, Any] = {
    "$jsonSchema": {
        "bsonType": "object",
        "required": [
            "org_id",
            "title",
            "department",
            "status",
            "reports_to",
            "solid_manager_ids",
            "ancestor_ids",
            "source_refs",
            "schema_version",
            "created_at",
            "updated_at",
        ],
        "additionalProperties": False,
        "properties": {
            "_id": {"bsonType": "objectId"},
            "org_id": {"bsonType": "objectId"},
            "title": {"bsonType": "string", "minLength": 1, "maxLength": 200},
            "department": {"bsonType": "string", "minLength": 1, "maxLength": 200},
            "status": {"enum": ["active", "vacant", "closed"]},
            "reports_to": {
                "bsonType": "array",
                "maxItems": MAX_REPORTS_TO,
                "items": _REPORTS_TO_EDGE_SCHEMA,
            },
            "solid_manager_ids": {
                "bsonType": "array",
                "maxItems": MAX_REPORTS_TO,
                "items": {"bsonType": "objectId"},
            },
            "ancestor_ids": {"bsonType": "array", "items": {"bsonType": "objectId"}},
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
            "schema_version": {"bsonType": "int"},
            "created_at": {"bsonType": "date"},
            "updated_at": {"bsonType": "date"},
            "created_by": {"bsonType": ["objectId", "null"]},
            "updated_by": {"bsonType": ["objectId", "null"]},
        },
    }
}
