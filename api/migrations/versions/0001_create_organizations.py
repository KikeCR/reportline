"""Create the organizations collection and its validator.

See docs/data-model.md's "Addition beyond the brief's Phase 1 list" note for
why this collection exists.
"""

from pymongo.database import Database

from app.db import Document
from app.repos.validators import ORGANIZATIONS_VALIDATOR

VERSION = "0001"
NAME = "create_organizations"


def up(db: Database[Document]) -> None:
    if "organizations" not in db.list_collection_names():
        db.create_collection(
            "organizations",
            validator=ORGANIZATIONS_VALIDATOR,
            validationLevel="strict",
            validationAction="error",
        )
