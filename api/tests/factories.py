"""Plain builder functions for test data - mirrors SaveState's
``tests/factories.py`` convention (plain functions, ``**overrides``,
``itertools.count()`` for uniqueness) rather than a factory-library.

``build_graph_from_spec`` is Reportline-specific: SaveState has no
graph-shaped domain to build fixtures for. It parses a compact spec like
``"CEO>VP1, CEO>VP2, VP1>Dir1, Dir1..VP2"`` (``>`` = solid line, ``..`` =
dotted line, left side is the manager) into fully-wired position documents
(``reports_to``, ``solid_manager_ids``, and ``ancestor_ids`` all computed),
so graph read-path tests stay readable without calling
``org_graph.add_reporting_line`` once per edge.
"""

from __future__ import annotations

import itertools
from datetime import UTC, datetime
from typing import Any

from bson import Decimal128, ObjectId

_counter = itertools.count(1)


def build_organization(**overrides: Any) -> dict[str, Any]:
    now = datetime.now(UTC)
    n = next(_counter)
    doc: dict[str, Any] = {
        "_id": ObjectId(),
        "name": f"Org {n}",
        "graph_version": 0,
        "schema_version": 1,
        "created_at": now,
        "updated_at": now,
    }
    doc.update(overrides)
    return doc


def build_position(org_id: ObjectId, **overrides: Any) -> dict[str, Any]:
    now = datetime.now(UTC)
    n = next(_counter)
    doc: dict[str, Any] = {
        "_id": ObjectId(),
        "org_id": org_id,
        "title": f"Position {n}",
        "department": "Engineering",
        "status": "active",
        "reports_to": [],
        "solid_manager_ids": [],
        "ancestor_ids": [],
        "schema_version": 1,
        "created_at": now,
        "updated_at": now,
        "created_by": None,
        "updated_by": None,
    }
    doc.update(overrides)
    return doc


def build_employee(org_id: ObjectId, **overrides: Any) -> dict[str, Any]:
    now = datetime.now(UTC)
    n = next(_counter)
    doc: dict[str, Any] = {
        "_id": ObjectId(),
        "org_id": org_id,
        "name": f"Employee {n}",
        "email": f"employee{n}@example.com",
        "source_refs": [],
        "compensation": {"amount": Decimal128("100000.00"), "currency": "USD"},
        "schema_version": 1,
        "created_at": now,
        "updated_at": now,
        "created_by": None,
        "updated_by": None,
    }
    doc.update(overrides)
    return doc


def build_assignment(
    org_id: ObjectId, employee_id: ObjectId, position_id: ObjectId, **overrides: Any
) -> dict[str, Any]:
    now = datetime.now(UTC)
    doc: dict[str, Any] = {
        "_id": ObjectId(),
        "org_id": org_id,
        "employee_id": employee_id,
        "position_id": position_id,
        "start_date": now,
        "end_date": None,
        "fte": 1.0,
        "is_primary": True,
        "schema_version": 1,
        "created_at": now,
        "updated_at": now,
        "created_by": None,
        "updated_by": None,
    }
    doc.update(overrides)
    return doc


def _parse_edge(raw_edge: str) -> tuple[str, str, str]:
    if ".." in raw_edge:
        manager_label, report_label = raw_edge.split("..", 1)
        relation = "dotted"
    else:
        manager_label, report_label = raw_edge.split(">", 1)
        relation = "solid"
    return manager_label.strip(), report_label.strip(), relation


def build_graph_from_spec(org_id: ObjectId, spec: str) -> dict[str, dict[str, Any]]:
    edges = [_parse_edge(raw) for raw in spec.split(",") if raw.strip()]
    labels = {label for edge in edges for label in (edge[0], edge[1])}
    ids = {label: ObjectId() for label in labels}

    reports_to: dict[str, list[dict[str, Any]]] = {label: [] for label in labels}
    solid_manager_ids: dict[str, list[ObjectId]] = {label: [] for label in labels}
    has_primary: dict[str, bool] = dict.fromkeys(labels, False)

    for manager_label, report_label, relation in edges:
        is_primary = relation == "solid" and not has_primary[report_label]
        if is_primary:
            has_primary[report_label] = True
        reports_to[report_label].append(
            {"position_id": ids[manager_label], "relation": relation, "is_primary": is_primary}
        )
        if relation == "solid":
            solid_manager_ids[report_label].append(ids[manager_label])

    label_by_id = {oid: label for label, oid in ids.items()}

    def ancestors_of(label: str, seen: frozenset[str] = frozenset()) -> set[str]:
        result: set[str] = set()
        for edge in reports_to[label]:
            manager_label = label_by_id[edge["position_id"]]
            if manager_label in seen:
                continue
            result.add(manager_label)
            result |= ancestors_of(manager_label, seen | {manager_label})
        return result

    return {
        label: build_position(
            org_id,
            _id=ids[label],
            title=label,
            reports_to=reports_to[label],
            solid_manager_ids=solid_manager_ids[label],
            ancestor_ids=[ids[ancestor] for ancestor in ancestors_of(label)],
        )
        for label in labels
    }
