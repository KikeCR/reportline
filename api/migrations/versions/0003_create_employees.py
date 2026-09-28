"""Create the employees collection, its validator, and its unique
source-ref index. See docs/data-model.md's "employees" section for why the
index is partial and why lookups against it must use $elemMatch.
"""

from pymongo.database import Database

from app.db import Document
from app.repos.validators import EMPLOYEES_VALIDATOR

VERSION = "0003"
NAME = "create_employees"


def up(db: Database[Document]) -> None:
    if "employees" not in db.list_collection_names():
        db.create_collection(
            "employees",
            validator=EMPLOYEES_VALIDATOR,
            validationLevel="strict",
            validationAction="error",
        )

    db["employees"].create_index(
        [("org_id", 1), ("source_refs.system", 1), ("source_refs.id", 1)],
        name="ux_employees_org_source_ref",
        unique=True,
        partialFilterExpression={"source_refs.0": {"$exists": True}},
    )
