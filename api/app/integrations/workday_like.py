"""Adapter for a Workday-like export: nested JSON, managers referenced by
worker id.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from app.integrations.base import CanonicalWorker

_FIXTURE_PATH = Path(__file__).parent / "fixtures" / "workday_like.json"


class WorkdayLikeAdapter:
    source_name = "workday_like"

    def fetch(self) -> list[dict[str, Any]]:
        data = json.loads(_FIXTURE_PATH.read_text())
        workers: list[dict[str, Any]] = data["workers"]
        return workers

    def to_canonical(self, raw: dict[str, Any]) -> CanonicalWorker:
        personal: dict[str, Any] = raw.get("personal_info") or {}
        position: dict[str, Any] = raw.get("position") or {}
        compensation: dict[str, Any] = raw.get("compensation") or {}
        return CanonicalWorker(
            source_system=self.source_name,
            source_id=raw.get("worker_id", ""),
            name=personal.get("name", ""),
            email=personal.get("email", ""),
            title=position.get("title", ""),
            department=position.get("department", ""),
            manager_source_id=raw.get("manager_worker_id"),
            compensation_amount=compensation.get("base_salary", 0),
            compensation_currency=compensation.get("currency", "USD"),
        )
