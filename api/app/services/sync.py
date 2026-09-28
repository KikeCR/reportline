"""Two-pass HRIS sync: upsert people + positions first, then resolve
reporting lines. A bad or unresolvable record is quarantined, never fails
the whole run.

Conflict rule (two sources disagreeing about a manager): last-synced source
wins - if a position's current primary manager differs from what this run
resolves, the old primary edge is removed and the new one added, atomically
per edge via ``org_graph``.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Any

from bson import ObjectId
from pydantic import ValidationError

from app.db import Document
from app.errors import ReportlineError
from app.integrations.base import Adapter, CanonicalWorker
from app.repos import AssignmentRepo, EmployeeRepo, PositionRepo, QuarantineRepo, SyncRunRepo
from app.services import org_graph


@dataclass(frozen=True)
class SyncResult:
    created: int
    updated: int
    unchanged: int
    quarantined: int
    duration_ms: int
    started_at: datetime


def _resolve_manager_position(
    position_repo: PositionRepo,
    employee_repo: EmployeeRepo,
    assignment_repo: AssignmentRepo,
    source_system: str,
    manager_source_id: str,
) -> dict[str, Any] | None:
    manager_position = position_repo.find_by_source_ref(source_system, manager_source_id)
    if manager_position is not None:
        return manager_position

    # bamboo_like references managers by email, not by its own source id.
    manager_employee = employee_repo.find_by_email(manager_source_id)
    if manager_employee is None:
        return None
    current = assignment_repo.current_for_employee(manager_employee["_id"])
    if not current:
        return None
    return position_repo.get_by_id(current[0]["position_id"])


def run_sync(org_id: ObjectId, adapter: Adapter) -> SyncResult:
    started = datetime.now(UTC)
    quarantine_repo = QuarantineRepo(org_id)
    employee_repo = EmployeeRepo(org_id)
    position_repo = PositionRepo(org_id)
    assignment_repo = AssignmentRepo(org_id)

    canonical_workers: list[CanonicalWorker] = []
    quarantined = 0
    for raw in adapter.fetch():
        try:
            canonical_workers.append(adapter.to_canonical(raw))
        except ValidationError as exc:
            if not quarantine_repo.exists_for_raw(adapter.source_name, raw):
                quarantine_repo.create(adapter.source_name, raw, [str(e) for e in exc.errors()])
            quarantined += 1

    created = updated = unchanged = 0
    position_id_by_source_id: dict[str, ObjectId] = {}

    # Pass 1: upsert positions and employees, and a current assignment
    # linking them - all keyed by (source_system, source_id) for idempotency.
    for worker in canonical_workers:
        ref = {"system": worker.source_system, "id": worker.source_id}

        existing_position = position_repo.find_by_source_ref(worker.source_system, worker.source_id)
        if existing_position is None:
            position_id = position_repo.create(worker.title, worker.department, source_refs=[ref])
            created += 1
        else:
            position_id = existing_position["_id"]
            if (
                existing_position["title"] == worker.title
                and existing_position["department"] == worker.department
            ):
                unchanged += 1
            else:
                position_repo.update_fields(
                    position_id,
                    title=worker.title,
                    department=worker.department,
                    source_refs=existing_position["source_refs"],
                )
                updated += 1
        position_id_by_source_id[worker.source_id] = position_id

        existing_employee = employee_repo.find_by_source_ref(worker.source_system, worker.source_id)
        if existing_employee is None:
            employee_id = employee_repo.create(
                worker.name,
                worker.email,
                compensation_amount=worker.compensation_amount,
                compensation_currency=worker.compensation_currency,
                source_refs=[ref],
            )
        else:
            employee_id = existing_employee["_id"]
            same = (
                existing_employee["name"] == worker.name
                and existing_employee["compensation"]["amount"].to_decimal()
                == worker.compensation_amount
            )
            if not same:
                employee_repo.update_fields(
                    employee_id,
                    name=worker.name,
                    compensation_amount=worker.compensation_amount,
                    compensation_currency=worker.compensation_currency,
                    source_refs=existing_employee["source_refs"],
                )

        current_assignments = assignment_repo.current_for_position(position_id)
        if not any(a["employee_id"] == employee_id for a in current_assignments):
            assignment_repo.create(employee_id, position_id, start_date=datetime.now(UTC))

    # Pass 2: resolve reporting lines now that every position from this run exists.
    for worker in canonical_workers:
        if worker.manager_source_id is None:
            continue
        report_position_id = position_id_by_source_id[worker.source_id]

        manager_position = _resolve_manager_position(
            position_repo,
            employee_repo,
            assignment_repo,
            worker.source_system,
            worker.manager_source_id,
        )
        if manager_position is None:
            raw = {"source_id": worker.source_id, "manager_source_id": worker.manager_source_id}
            if not quarantine_repo.exists_for_raw(worker.source_system, raw):
                quarantine_repo.create(worker.source_system, raw, ["unresolved manager reference"])
            quarantined += 1
            continue

        report_position = position_repo.get_by_id(report_position_id)
        assert report_position is not None
        current_primary = next(
            (
                e
                for e in report_position["reports_to"]
                if e["relation"] == "solid" and e["is_primary"]
            ),
            None,
        )
        if current_primary and current_primary["position_id"] == manager_position["_id"]:
            continue

        try:
            # move_subtree replaces the old primary edge (if any) with the new
            # one inside a single transaction - add_reporting_line +
            # remove_reporting_line as two separate calls would let a
            # rejected add leave the position with no manager at all.
            org_graph.move_subtree(org_id, report_position_id, manager_position["_id"])
        except ReportlineError as exc:
            raw = {"source_id": worker.source_id, "manager_source_id": worker.manager_source_id}
            if not quarantine_repo.exists_for_raw(worker.source_system, raw):
                quarantine_repo.create(worker.source_system, raw, [str(exc)])
            quarantined += 1

    duration_ms = int((datetime.now(UTC) - started).total_seconds() * 1000)
    SyncRunRepo(org_id).create(
        adapter.source_name,
        created_count=created,
        updated_count=updated,
        unchanged_count=unchanged,
        quarantined_count=quarantined,
        duration_ms=duration_ms,
        started_at=started,
    )

    return SyncResult(
        created=created,
        updated=updated,
        unchanged=unchanged,
        quarantined=quarantined,
        duration_ms=duration_ms,
        started_at=started,
    )


def list_sync_runs(org_id: ObjectId) -> list[Document]:
    return SyncRunRepo(org_id).list_for_org()


def list_quarantine(org_id: ObjectId) -> list[Document]:
    return QuarantineRepo(org_id).list_for_org()
