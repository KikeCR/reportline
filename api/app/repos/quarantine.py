from __future__ import annotations

from datetime import UTC, datetime
from typing import Any

from bson import ObjectId
from pymongo.client_session import ClientSession

from app.db import Document
from app.repos.base import ScopedRepo


class QuarantineRepo(ScopedRepo):
    collection_name = "quarantine"

    def create(
        self,
        source: str,
        raw: dict[str, Any],
        errors: list[str],
        *,
        session: ClientSession | None = None,
    ) -> ObjectId:
        return self.insert_one(
            {"source": source, "raw": raw, "errors": errors, "created_at": datetime.now(UTC)},
            session=session,
        )

    def list_for_org(self, *, session: ClientSession | None = None) -> list[Document]:
        return list(self.find({}, sort=[("created_at", -1)], session=session))

    def exists_for_raw(
        self, source: str, raw: dict[str, Any], *, session: ClientSession | None = None
    ) -> bool:
        """True if this exact raw record is already quarantined for this
        source. A re-run against a still-broken record shouldn't pile up a
        fresh quarantine entry every time - ``services/sync.py`` checks this
        before creating one."""
        return self.find_one({"source": source, "raw": raw}, session=session) is not None
