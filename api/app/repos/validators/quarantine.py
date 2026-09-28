"""$jsonSchema validator for the quarantine collection. See
docs/data-model.md - kept in sync with app.models.quarantine.QuarantineRecord
by tests/repos/test_validators_match_models.py.
"""

from typing import Any

QUARANTINE_VALIDATOR: dict[str, Any] = {
    "$jsonSchema": {
        "bsonType": "object",
        "required": ["org_id", "source", "raw", "errors", "created_at"],
        "additionalProperties": False,
        "properties": {
            "_id": {"bsonType": "objectId"},
            "org_id": {"bsonType": "objectId"},
            "source": {"bsonType": "string", "minLength": 1},
            "raw": {"bsonType": "object"},
            "errors": {"bsonType": "array", "items": {"bsonType": "string"}},
            "created_at": {"bsonType": "date"},
        },
    }
}
