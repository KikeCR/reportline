"""``ScopedRepo`` - the only way anything in this codebase queries Mongo.

CLAUDE.md: "Every repo query MUST include org_id (tenant scope) via
ScopedRepo. No exceptions." Every method here folds ``org_id`` into the
filter itself, so a repo subclass has no way to issue an unscoped query
through these methods. A pipeline passed to :meth:`aggregate` is the one
exception - aggregation stages aren't scoped automatically, so a repo
method that builds one must embed ``org_id`` in every stage itself (see
``PositionRepo.get_descendants`` for the pattern).
"""

from __future__ import annotations

from collections.abc import Iterable, Mapping
from typing import Any, cast

from bson import ObjectId
from pymongo import UpdateOne
from pymongo.client_session import ClientSession
from pymongo.collection import Collection
from pymongo.command_cursor import CommandCursor
from pymongo.cursor import Cursor
from pymongo.errors import BulkWriteError, DuplicateKeyError
from pymongo.results import BulkWriteResult, UpdateResult

from app.db import Document, get_database
from app.errors import ConflictError


class ScopedRepo:
    collection_name: str

    def __init__(self, org_id: ObjectId) -> None:
        self.org_id = org_id

    @property
    def _collection(self) -> Collection[Document]:
        return get_database()[self.collection_name]

    def _scoped(self, filter_: Mapping[str, Any]) -> dict[str, Any]:
        return {**filter_, "org_id": self.org_id}

    def find_one(
        self,
        filter_: Mapping[str, Any],
        *,
        projection: Mapping[str, Any] | None = None,
        session: ClientSession | None = None,
    ) -> Document | None:
        return self._collection.find_one(self._scoped(filter_), projection, session=session)

    def find(
        self,
        filter_: Mapping[str, Any],
        *,
        projection: Mapping[str, Any] | None = None,
        sort: list[tuple[str, int]] | None = None,
        session: ClientSession | None = None,
    ) -> Cursor[Document]:
        cursor = self._collection.find(self._scoped(filter_), projection, session=session)
        if sort:
            cursor = cursor.sort(sort)
        return cursor

    def aggregate(
        self, pipeline: list[Mapping[str, Any]], *, session: ClientSession | None = None
    ) -> CommandCursor[Document]:
        """Run a pipeline as-is. The caller MUST scope every stage by org_id."""
        return self._collection.aggregate(pipeline, session=session)

    def insert_one(
        self, document: Mapping[str, Any], *, session: ClientSession | None = None
    ) -> ObjectId:
        scoped_document = {**document, "org_id": self.org_id}
        try:
            result = self._collection.insert_one(scoped_document, session=session)
        except DuplicateKeyError as exc:
            raise ConflictError("a document with this unique key already exists") from exc
        return cast(ObjectId, result.inserted_id)

    def update_one(
        self,
        filter_: Mapping[str, Any],
        update: Mapping[str, Any],
        *,
        session: ClientSession | None = None,
        upsert: bool = False,
    ) -> UpdateResult:
        try:
            return self._collection.update_one(
                self._scoped(filter_), update, session=session, upsert=upsert
            )
        except DuplicateKeyError as exc:
            raise ConflictError("a document with this unique key already exists") from exc

    def delete_all(self, *, session: ClientSession | None = None) -> int:
        """Delete every document for this tenant in this collection. Used by
        ``scripts/seed.py --reset``, never by application request code.
        """
        result = self._collection.delete_many({"org_id": self.org_id}, session=session)
        return result.deleted_count

    def bulk_write(
        self, requests: Iterable[UpdateOne], *, session: ClientSession | None = None
    ) -> BulkWriteResult:
        """Each request's filter MUST already be scoped by the caller."""
        try:
            return self._collection.bulk_write(list(requests), ordered=False, session=session)
        except BulkWriteError as exc:
            raise ConflictError(
                "one or more documents in this bulk operation could not be written",
                write_errors=exc.details.get("writeErrors", []),
            ) from exc
