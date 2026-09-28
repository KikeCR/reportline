"""Repo for the ``employees`` collection - see docs/access-patterns.md (E1-E2)."""

from __future__ import annotations

from datetime import UTC, datetime
from decimal import Decimal

from bson import Decimal128, ObjectId
from pymongo.client_session import ClientSession

from app.db import Document
from app.repos.base import ScopedRepo


class EmployeeRepo(ScopedRepo):
    collection_name = "employees"

    def create(
        self,
        name: str,
        email: str,
        *,
        compensation_amount: Decimal,
        compensation_currency: str = "USD",
        source_refs: list[dict[str, str]] | None = None,
        created_by: ObjectId | None = None,
        session: ClientSession | None = None,
    ) -> ObjectId:
        now = datetime.now(UTC)
        return self.insert_one(
            {
                "name": name,
                "email": email,
                "source_refs": source_refs or [],
                "compensation": {
                    "amount": Decimal128(compensation_amount),
                    "currency": compensation_currency,
                },
                "schema_version": 1,
                "created_at": now,
                "updated_at": now,
                "created_by": created_by,
                "updated_by": created_by,
            },
            session=session,
        )

    def get_by_id(
        self, employee_id: ObjectId, *, session: ClientSession | None = None
    ) -> Document | None:
        return self.find_one({"_id": employee_id}, session=session)

    def find_by_source_ref(
        self, system: str, ref_id: str, *, session: ClientSession | None = None
    ) -> Document | None:
        """E2: ``$elemMatch`` is required here, not two dotted-path
        conditions - see docs/access-patterns.md for why the naive form is
        a correctness bug, not just a style choice.
        """
        return self.find_one(
            {"source_refs": {"$elemMatch": {"system": system, "id": ref_id}}}, session=session
        )
