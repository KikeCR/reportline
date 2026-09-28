"""Create the positions collection, its validator, and its indexes.

Index names and the query each serves are documented in
docs/data-model.md's "positions" section (ix_positions_org_reports_to,
ix_positions_org_solid_manager_ids, ix_positions_org_ancestor_ids,
ix_positions_org_status).
"""

from pymongo.database import Database

from app.db import Document
from app.repos.validators import POSITIONS_VALIDATOR

VERSION = "0002"
NAME = "create_positions"


def up(db: Database[Document]) -> None:
    if "positions" not in db.list_collection_names():
        db.create_collection(
            "positions",
            validator=POSITIONS_VALIDATOR,
            validationLevel="strict",
            validationAction="error",
        )

    positions = db["positions"]
    positions.create_index(
        [("org_id", 1), ("reports_to.position_id", 1)], name="ix_positions_org_reports_to"
    )
    positions.create_index(
        [("org_id", 1), ("solid_manager_ids", 1)], name="ix_positions_org_solid_manager_ids"
    )
    positions.create_index(
        [("org_id", 1), ("ancestor_ids", 1)], name="ix_positions_org_ancestor_ids"
    )
    positions.create_index([("org_id", 1), ("status", 1)], name="ix_positions_org_status")
