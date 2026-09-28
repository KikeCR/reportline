"""Not a ``ScopedRepo``: ``organizations._id`` *is* the org id, so there's no
separate tenant field to scope queries by.
"""

from __future__ import annotations

from datetime import UTC, datetime
from typing import cast

from bson import ObjectId
from pymongo.client_session import ClientSession
from pymongo.collection import Collection

from app.db import Document, get_database


class OrganizationRepo:
    collection_name = "organizations"

    @property
    def _collection(self) -> Collection[Document]:
        return get_database()[self.collection_name]

    def create(self, name: str, *, session: ClientSession | None = None) -> ObjectId:
        now = datetime.now(UTC)
        document: Document = {
            "_id": ObjectId(),
            "name": name,
            "graph_version": 0,
            "schema_version": 1,
            "created_at": now,
            "updated_at": now,
        }
        self._collection.insert_one(document, session=session)
        return cast(ObjectId, document["_id"])

    def get_by_id(
        self, org_id: ObjectId, *, session: ClientSession | None = None
    ) -> Document | None:
        return self._collection.find_one({"_id": org_id}, session=session)

    def find_by_name(self, name: str, *, session: ClientSession | None = None) -> Document | None:
        return self._collection.find_one({"name": name}, session=session)

    def delete(self, org_id: ObjectId, *, session: ClientSession | None = None) -> None:
        self._collection.delete_one({"_id": org_id}, session=session)

    def bump_graph_version(
        self, org_id: ObjectId, expected_version: int, *, session: ClientSession | None = None
    ) -> bool:
        """Atomically increment ``graph_version`` iff it still equals ``expected_version``.

        Returns ``True`` on success, ``False`` if another writer changed the
        graph first - the caller (``org_graph``) treats that as a conflict
        to retry or fail cleanly, per the brief's optimistic-concurrency
        requirement.
        """
        result = self._collection.update_one(
            {"_id": org_id, "graph_version": expected_version},
            {"$inc": {"graph_version": 1}, "$set": {"updated_at": datetime.now(UTC)}},
            session=session,
        )
        return result.modified_count == 1
