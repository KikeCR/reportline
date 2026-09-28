"""Repo for the ``assignments`` collection - see docs/access-patterns.md (A1-A4)."""

from __future__ import annotations

from collections.abc import Iterable
from datetime import UTC, datetime

from bson import ObjectId
from pymongo.client_session import ClientSession

from app.db import Document
from app.repos.base import ScopedRepo


class AssignmentRepo(ScopedRepo):
    collection_name = "assignments"

    def create(
        self,
        employee_id: ObjectId,
        position_id: ObjectId,
        *,
        start_date: datetime,
        fte: float = 1.0,
        is_primary: bool = True,
        end_date: datetime | None = None,
        created_by: ObjectId | None = None,
        session: ClientSession | None = None,
    ) -> ObjectId:
        now = datetime.now(UTC)
        return self.insert_one(
            {
                "employee_id": employee_id,
                "position_id": position_id,
                "start_date": start_date,
                "end_date": end_date,
                "fte": fte,
                "is_primary": is_primary,
                "schema_version": 1,
                "created_at": now,
                "updated_at": now,
                "created_by": created_by,
                "updated_by": created_by,
            },
            session=session,
        )

    def current_for_position(
        self, position_id: ObjectId, *, session: ClientSession | None = None
    ) -> list[Document]:
        """A1: current occupant(s) of a position."""
        return list(self.find({"position_id": position_id, "end_date": None}, session=session))

    def as_of_for_position(
        self, position_id: ObjectId, as_of: datetime, *, session: ClientSession | None = None
    ) -> list[Document]:
        """A2: occupant(s) as of a given date."""
        return list(
            self.find(
                {
                    "position_id": position_id,
                    "start_date": {"$lte": as_of},
                    "$or": [{"end_date": None}, {"end_date": {"$gte": as_of}}],
                },
                session=session,
            )
        )

    def current_for_positions(
        self, position_ids: Iterable[ObjectId], *, session: ClientSession | None = None
    ) -> list[Document]:
        """A1b: current occupant(s) of many positions in one query - the
        graph's "people" view batches through this instead of A1 per node,
        to keep the whole-graph read at a small constant number of queries
        regardless of headcount (see ADR 0002)."""
        return list(
            self.find(
                {"position_id": {"$in": list(position_ids)}, "end_date": None}, session=session
            )
        )

    def as_of_for_positions(
        self,
        position_ids: Iterable[ObjectId],
        as_of: datetime,
        *,
        session: ClientSession | None = None,
    ) -> list[Document]:
        """A2b: batched form of A2, for the same reason as A1b."""
        return list(
            self.find(
                {
                    "position_id": {"$in": list(position_ids)},
                    "start_date": {"$lte": as_of},
                    "$or": [{"end_date": None}, {"end_date": {"$gte": as_of}}],
                },
                session=session,
            )
        )

    def current_for_employee(
        self, employee_id: ObjectId, *, session: ClientSession | None = None
    ) -> list[Document]:
        """A3: an employee's current assignment(s), including the dual-role case."""
        return list(self.find({"employee_id": employee_id, "end_date": None}, session=session))
