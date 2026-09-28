"""Repo for the ``positions`` collection - see docs/access-patterns.md (P1-P10)
and docs/adr/0001-org-as-dag.md for why the graph traversal is shaped this
way (the ``restrictSearchWithMatch`` pitfall, solid-only descendants vs.
all-edge-type ancestors).
"""

from __future__ import annotations

from collections.abc import Iterable, Mapping, Sequence
from datetime import UTC, datetime

from bson import ObjectId
from pymongo import UpdateOne
from pymongo.client_session import ClientSession
from pymongo.results import UpdateResult

from app.db import Document
from app.repos.base import ScopedRepo


class PositionRepo(ScopedRepo):
    collection_name = "positions"

    def create(
        self,
        title: str,
        department: str,
        *,
        status: str = "active",
        created_by: ObjectId | None = None,
        session: ClientSession | None = None,
    ) -> ObjectId:
        """A newly created position always starts edgeless - it's wired into
        the graph afterward via ``services.org_graph.add_reporting_line``.
        """
        now = datetime.now(UTC)
        return self.insert_one(
            {
                "title": title,
                "department": department,
                "status": status,
                "reports_to": [],
                "solid_manager_ids": [],
                "ancestor_ids": [],
                "schema_version": 1,
                "created_at": now,
                "updated_at": now,
                "created_by": created_by,
                "updated_by": created_by,
            },
            session=session,
        )

    def get_by_id(
        self, position_id: ObjectId, *, session: ClientSession | None = None
    ) -> Document | None:
        return self.find_one({"_id": position_id}, session=session)

    def get_many_by_ids(
        self, position_ids: Iterable[ObjectId], *, session: ClientSession | None = None
    ) -> list[Document]:
        ids = list(position_ids)
        if not ids:
            return []
        return list(self.find({"_id": {"$in": ids}}, session=session))

    def direct_reports(
        self, position_id: ObjectId, *, session: ClientSession | None = None
    ) -> list[Document]:
        """P4: who currently reports to this position, across all edge types."""
        return list(
            self.find(
                {"reports_to.position_id": position_id},
                sort=[("title", 1)],
                session=session,
            )
        )

    def get_descendants(
        self, position_id: ObjectId, *, max_depth: int, session: ClientSession | None = None
    ) -> list[Document]:
        """P2: solid-line subtree below ``position_id``, via ``$graphLookup``
        over ``solid_manager_ids``. See ADR 0001 for why the traversal edge
        is the denormalized ``solid_manager_ids`` array rather than
        ``reports_to`` directly.
        """
        pipeline: list[Mapping[str, object]] = [
            {"$match": {"_id": position_id, "org_id": self.org_id}},
            {
                "$graphLookup": {
                    "from": self.collection_name,
                    "startWith": "$_id",
                    "connectFromField": "_id",
                    "connectToField": "solid_manager_ids",
                    "as": "subtree",
                    "maxDepth": max_depth,
                    "depthField": "depth",
                    "restrictSearchWithMatch": {"org_id": self.org_id},
                }
            },
            {"$unwind": "$subtree"},
            {"$replaceRoot": {"newRoot": "$subtree"}},
        ]
        return list(self.aggregate(pipeline, session=session))

    def get_ancestors(
        self, position_id: ObjectId, *, session: ClientSession | None = None
    ) -> list[Document]:
        """P3: ``ancestor_ids`` is precomputed, so this is one indexed fetch,
        not a second ``$graphLookup``.
        """
        position = self.get_by_id(position_id, session=session)
        if position is None:
            return []
        ancestor_ids: list[ObjectId] = position.get("ancestor_ids", [])
        return self.get_many_by_ids(ancestor_ids, session=session)

    def in_subtree_of(
        self, position_id: ObjectId, *, session: ClientSession | None = None
    ) -> list[Document]:
        """P6: permission scoping - every position whose ancestor_ids
        contains this manager's position, via the load-bearing
        ``ix_positions_org_ancestor_ids`` index.
        """
        return list(self.find({"ancestor_ids": position_id}, session=session))

    def root_ids(self, *, session: ClientSession | None = None) -> list[ObjectId]:
        """P8: positions with no reports_to edges at all."""
        cursor = self.find({"reports_to": {"$size": 0}}, projection={"_id": 1}, session=session)
        return [doc["_id"] for doc in cursor]

    def list_for_graph(self, *, session: ClientSession | None = None) -> list[Document]:
        """P7: the full tenant graph, excluding closed positions."""
        return list(self.find({"status": {"$ne": "closed"}}, session=session))

    def update_edges_and_ancestors(
        self,
        position_id: ObjectId,
        *,
        reports_to: Sequence[Mapping[str, object]],
        solid_manager_ids: list[ObjectId],
        ancestor_ids: list[ObjectId],
        updated_at: datetime,
        updated_by: ObjectId | None,
        session: ClientSession | None = None,
    ) -> UpdateResult:
        return self.update_one(
            {"_id": position_id},
            {
                "$set": {
                    "reports_to": reports_to,
                    "solid_manager_ids": solid_manager_ids,
                    "ancestor_ids": ancestor_ids,
                    "updated_at": updated_at,
                    "updated_by": updated_by,
                }
            },
            session=session,
        )

    def bulk_update_ancestor_ids(
        self,
        updates: Mapping[ObjectId, list[ObjectId]],
        *,
        updated_at: datetime,
        session: ClientSession | None = None,
    ) -> None:
        if not updates:
            return
        requests = [
            UpdateOne(
                {"_id": position_id, "org_id": self.org_id},
                {"$set": {"ancestor_ids": ancestor_ids, "updated_at": updated_at}},
            )
            for position_id, ancestor_ids in updates.items()
        ]
        self.bulk_write(requests, session=session)
