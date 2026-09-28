from typing import Any

SYNC_RUNS_VALIDATOR: dict[str, Any] = {
    "$jsonSchema": {
        "bsonType": "object",
        "required": [
            "org_id",
            "source",
            "created_count",
            "updated_count",
            "unchanged_count",
            "quarantined_count",
            "duration_ms",
            "started_at",
        ],
        "additionalProperties": False,
        "properties": {
            "_id": {"bsonType": "objectId"},
            "org_id": {"bsonType": "objectId"},
            "source": {"bsonType": "string", "minLength": 1},
            "created_count": {"bsonType": "int"},
            "updated_count": {"bsonType": "int"},
            "unchanged_count": {"bsonType": "int"},
            "quarantined_count": {"bsonType": "int"},
            "duration_ms": {"bsonType": "int"},
            "started_at": {"bsonType": "date"},
        },
    }
}
