"""Create the assignments collection, its validator, and its indexes."""

from pymongo.database import Database

from app.db import Document
from app.repos.validators import ASSIGNMENTS_VALIDATOR

VERSION = "0004"
NAME = "create_assignments"


def up(db: Database[Document]) -> None:
    if "assignments" not in db.list_collection_names():
        db.create_collection(
            "assignments",
            validator=ASSIGNMENTS_VALIDATOR,
            validationLevel="strict",
            validationAction="error",
        )

    assignments = db["assignments"]
    assignments.create_index(
        [("org_id", 1), ("position_id", 1), ("start_date", 1)],
        name="ix_assignments_org_position_start",
    )
    assignments.create_index(
        [("org_id", 1), ("employee_id", 1), ("end_date", 1)],
        name="ix_assignments_org_employee_current",
    )
