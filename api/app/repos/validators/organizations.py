"""$jsonSchema validator for the organizations collection. See
docs/data-model.md - kept in sync with app.models.organization.Organization
by tests/repos/test_validators_match_models.py.
"""

from typing import Any

ORGANIZATIONS_VALIDATOR: dict[str, Any] = {
    "$jsonSchema": {
        "bsonType": "object",
        "required": ["name", "graph_version", "schema_version", "created_at", "updated_at"],
        "additionalProperties": False,
        "properties": {
            "_id": {"bsonType": "objectId"},
            "name": {"bsonType": "string", "minLength": 1},
            "graph_version": {"bsonType": "int"},
            "schema_version": {"bsonType": "int"},
            "created_at": {"bsonType": "date"},
            "updated_at": {"bsonType": "date"},
        },
    }
}
