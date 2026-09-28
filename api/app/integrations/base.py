"""Adapter protocol for HRIS sources. Each adapter fetches raw records from
its source and normalizes them into ``CanonicalWorker`` - the only shape
``services/sync.py`` deals with.
"""

from __future__ import annotations

from decimal import Decimal
from typing import Protocol

from pydantic import BaseModel, Field


class CanonicalWorker(BaseModel):
    source_system: str
    source_id: str = Field(min_length=1)
    name: str = Field(min_length=1)
    email: str = Field(min_length=1)
    title: str = Field(min_length=1)
    department: str = Field(min_length=1)
    manager_source_id: str | None = None
    compensation_amount: Decimal = Decimal("0")
    compensation_currency: str = "USD"


class Adapter(Protocol):
    source_name: str

    def fetch(self) -> list[dict[str, object]]:
        """Return raw records from this source (a fixture, in this project)."""
        ...

    def to_canonical(self, raw: dict[str, object]) -> CanonicalWorker:
        """Raise ``pydantic.ValidationError`` for a record that can't be
        normalized - ``sync.py`` quarantines it rather than failing the run.
        """
        ...
