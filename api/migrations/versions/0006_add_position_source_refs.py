"""Adds source_refs to positions (Phase 5 sync needs to upsert positions
idempotently, keyed by source system+id, same as employees already are).
"""

from pymongo.database import Database

from app.db import Document
from app.repos.validators import POSITIONS_VALIDATOR

VERSION = "0006"
NAME = "add_position_source_refs"


def up(db: Database[Document]) -> None:
    db.command(
        {
            "collMod": "positions",
            "validator": POSITIONS_VALIDATOR,
            "validationLevel": "strict",
            "validationAction": "error",
        }
    )
    db["positions"].update_many({"source_refs": {"$exists": False}}, {"$set": {"source_refs": []}})
    db["positions"].create_index(
        [("org_id", 1), ("source_refs.system", 1), ("source_refs.id", 1)],
        name="ux_positions_org_source_ref",
        unique=True,
        partialFilterExpression={"source_refs.0": {"$exists": True}},
    )
