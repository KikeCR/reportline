"""Prints ``.explain("executionStats")``-equivalent summaries for the key
queries in docs/access-patterns.md, so index usage can be verified by eye
(IXSCAN vs COLLSCAN, docs examined vs returned) rather than assumed.

This is a diagnostics script, not application logic - like ``migrations/``,
it talks to Mongo directly via ``app.db.get_database()`` rather than through
``repos/``, because its whole job is inspecting raw query plans, which
``ScopedRepo``'s query methods don't (and shouldn't) expose.

Usage: run ``make seed`` first, then ``python -m scripts.explain_queries``.
"""

from __future__ import annotations

from typing import Any

from pymongo.database import Database

from app.config import get_settings
from app.db import Document, get_database
from app.logging import configure_logging, get_logger

logger = get_logger(__name__)


def _summarize(label: str, explain_output: dict[str, Any]) -> None:
    stats = explain_output.get("executionStats", explain_output)
    winning_plan = explain_output.get("queryPlanner", {}).get("winningPlan", {})
    stage = _find_stage(winning_plan)
    print(f"\n=== {label} ===")
    print(f"  stage:          {stage}")
    print(f"  docs examined:  {stats.get('totalDocsExamined', 'n/a')}")
    print(f"  keys examined:  {stats.get('totalKeysExamined', 'n/a')}")
    print(f"  docs returned:  {stats.get('nReturned', 'n/a')}")
    print(f"  execution ms:   {stats.get('executionTimeMillis', 'n/a')}")


def _find_stage(plan: dict[str, Any]) -> str:
    if "inputStage" in plan:
        return f"{plan.get('stage')} -> {_find_stage(plan['inputStage'])}"
    return str(plan.get("stage", "UNKNOWN"))


def _explain_find(
    db: Database[Document], collection: str, filter_: dict[str, Any], label: str
) -> None:
    explain_output = db[collection].find(filter_).explain()
    _summarize(label, explain_output)


def _explain_aggregate(
    db: Database[Document], collection: str, pipeline: list[dict[str, Any]], label: str
) -> None:
    explain_output = db.command(
        {"explain": {"aggregate": collection, "pipeline": pipeline, "cursor": {}}}
    )
    stats = explain_output.get("executionStats", {})
    print(f"\n=== {label} ===")
    print(f"  docs examined:  {stats.get('totalDocsExamined', 'n/a')}")
    print(f"  docs returned:  {stats.get('nReturned', 'n/a')}")
    print(f"  execution ms:   {stats.get('executionTimeMillis', 'n/a')}")


def main() -> int:
    settings = get_settings()
    configure_logging(settings.log_level)
    db = get_database()

    org = db["organizations"].find_one({"name": "Acme Corporation"})
    if org is None:
        logger.error("no_seed_data_found", hint="run `make seed` first")
        return 1
    org_id = org["_id"]

    root = db["positions"].find_one({"org_id": org_id, "reports_to": {"$size": 0}})
    if root is None:
        logger.error("no_root_position_found")
        return 1
    root_id = root["_id"]

    any_manager = db["positions"].find_one({"org_id": org_id, "solid_manager_ids": {"$ne": []}})

    _explain_find(
        db, "positions", {"org_id": org_id, "status": {"$ne": "closed"}}, "P7: full graph read"
    )
    if any_manager is not None:
        _explain_find(
            db,
            "positions",
            {"org_id": org_id, "ancestor_ids": any_manager["_id"]},
            "P6: manager permission-scope subtree",
        )
    _explain_aggregate(
        db,
        "positions",
        [
            {"$match": {"_id": root_id, "org_id": org_id}},
            {
                "$graphLookup": {
                    "from": "positions",
                    "startWith": "$_id",
                    "connectFromField": "_id",
                    "connectToField": "solid_manager_ids",
                    "as": "subtree",
                    "restrictSearchWithMatch": {"org_id": org_id},
                }
            },
        ],
        "P2: get_descendants via $graphLookup",
    )
    _explain_find(
        db,
        "employees",
        {"org_id": org_id, "source_refs": {"$elemMatch": {"system": "workday_like", "id": "x"}}},
        "E2: dedup by source ref",
    )

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
