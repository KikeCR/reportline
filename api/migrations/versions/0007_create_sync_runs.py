from pymongo.database import Database

from app.db import Document
from app.repos.validators import SYNC_RUNS_VALIDATOR

VERSION = "0007"
NAME = "create_sync_runs"


def up(db: Database[Document]) -> None:
    if "sync_runs" not in db.list_collection_names():
        db.create_collection(
            "sync_runs",
            validator=SYNC_RUNS_VALIDATOR,
            validationLevel="strict",
            validationAction="error",
        )
    db["sync_runs"].create_index(
        [("org_id", 1), ("started_at", -1)], name="ix_sync_runs_org_started"
    )
