"""Create the quarantine collection, its validator, and its index.

Written to and read starting Phase 5; created now because it's part of the
core Phase 1 data model (see docs/data-model.md).
"""

from pymongo.database import Database

from app.db import Document
from app.repos.validators import QUARANTINE_VALIDATOR

VERSION = "0005"
NAME = "create_quarantine"


def up(db: Database[Document]) -> None:
    if "quarantine" not in db.list_collection_names():
        db.create_collection(
            "quarantine",
            validator=QUARANTINE_VALIDATOR,
            validationLevel="strict",
            validationAction="error",
        )

    db["quarantine"].create_index(
        [("org_id", 1), ("created_at", -1)], name="ix_quarantine_org_created"
    )
