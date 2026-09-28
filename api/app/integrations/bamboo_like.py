"""Adapter for a BambooHR-like export: flat CSV, managers referenced by
supervisor email rather than an id - ``manager_source_id`` here is an email,
resolved by ``services/sync.py`` with an email fallback lookup (see there).
"""

from __future__ import annotations

import csv
from pathlib import Path
from typing import Any

from app.integrations.base import CanonicalWorker

_FIXTURE_PATH = Path(__file__).parent / "fixtures" / "bamboo_like.csv"


class BambooLikeAdapter:
    source_name = "bamboo_like"

    def fetch(self) -> list[dict[str, Any]]:
        with _FIXTURE_PATH.open(newline="") as f:
            return list(csv.DictReader(f))

    def to_canonical(self, raw: dict[str, Any]) -> CanonicalWorker:
        supervisor_email: str = raw.get("supervisor_email", "")
        salary: Any = raw.get("annual_salary") or 0
        return CanonicalWorker(
            source_system=self.source_name,
            source_id=raw.get("employee_id", ""),
            name=raw.get("full_name", ""),
            email=raw.get("work_email", ""),
            title=raw.get("job_title", ""),
            department=raw.get("department", ""),
            manager_source_id=supervisor_email or None,
            compensation_amount=salary,
        )
