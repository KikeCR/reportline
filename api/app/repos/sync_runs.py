from __future__ import annotations

from datetime import datetime

from bson import ObjectId
from pymongo.client_session import ClientSession

from app.db import Document
from app.repos.base import ScopedRepo


class SyncRunRepo(ScopedRepo):
    collection_name = "sync_runs"

    def create(
        self,
        source: str,
        *,
        created_count: int,
        updated_count: int,
        unchanged_count: int,
        quarantined_count: int,
        duration_ms: int,
        started_at: datetime,
        session: ClientSession | None = None,
    ) -> ObjectId:
        return self.insert_one(
            {
                "source": source,
                "created_count": created_count,
                "updated_count": updated_count,
                "unchanged_count": unchanged_count,
                "quarantined_count": quarantined_count,
                "duration_ms": duration_ms,
                "started_at": started_at,
            },
            session=session,
        )

    def list_for_org(self, *, session: ClientSession | None = None) -> list[Document]:
        return list(self.find({}, sort=[("started_at", -1)], session=session))
