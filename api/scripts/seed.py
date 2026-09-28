"""Deterministic, idempotent, resettable demo data.

Everything here goes through the same repos and services (``org_graph``,
``PositionRepo.create``, ``EmployeeRepo.create``, ``AssignmentRepo.create``)
that the running app uses - never a raw ``pymongo`` insert - so the seeded
graph respects every invariant (cycle-free, at most one primary solid edge,
capped fan-out) the same way a real edit would.

Usage (see ``make seed``)::

    python -m scripts.seed
    python -m scripts.seed --reset   # drop and recreate the two demo tenants
"""

from __future__ import annotations

import argparse
import random
import re
from dataclasses import dataclass, field
from datetime import UTC, datetime, timedelta
from decimal import Decimal

from bson import ObjectId

from app.config import get_settings
from app.db import get_database
from app.errors import CycleError
from app.logging import configure_logging, get_logger
from app.repos import AssignmentRepo, EmployeeRepo, OrganizationRepo, PositionRepo
from app.services import org_graph
from migrations.runner import run_migrations

logger = get_logger(__name__)

SEED = 20260101  # fixed, so every run produces byte-for-byte the same graph shape

_DEPARTMENTS = ["Engineering", "Sales", "Marketing", "Finance", "People"]

_IC_TITLES = {
    "Engineering": ["Software Engineer", "Senior Software Engineer", "Staff Engineer"],
    "Sales": ["Account Executive", "Senior Account Executive", "Sales Development Rep"],
    "Marketing": ["Marketing Specialist", "Content Strategist", "Growth Marketer"],
    "Finance": ["Financial Analyst", "Senior Financial Analyst", "Accountant"],
    "People": ["People Partner", "Recruiter", "People Operations Specialist"],
}

# A real (if fictional) name pool, not "VP Employee 482910" - readable demo
# data is the point. 30x30 combinations is comfortably more than either
# tenant needs, so every seeded person gets a distinct name.
_FIRST_NAMES = [
    "Priya",
    "Tomas",
    "Carol",
    "Dave",
    "Elena",
    "Marcus",
    "Sofia",
    "James",
    "Amara",
    "Liam",
    "Nadia",
    "Ethan",
    "Yuki",
    "Omar",
    "Grace",
    "Noah",
    "Mei",
    "Lucas",
    "Fatima",
    "Daniel",
    "Ingrid",
    "Rafael",
    "Chloe",
    "Kwame",
    "Anika",
    "Felix",
    "Zara",
    "Hiro",
    "Isla",
    "Mateo",
]
_LAST_NAMES = [
    "Shah",
    "Rivera",
    "Nakamura",
    "Okafor",
    "Petrov",
    "Alvarez",
    "Chen",
    "Kowalski",
    "Silva",
    "Novak",
    "Andersen",
    "Haddad",
    "Fischer",
    "Dubois",
    "Kimura",
    "Osei",
    "Lindqvist",
    "Moreau",
    "Santos",
    "Bakker",
    "Costa",
    "Weber",
    "Ibrahim",
    "Larsen",
    "Tanaka",
    "Reyes",
    "Berg",
    "Adeyemi",
    "Fontaine",
    "Volkov",
]


def _slugify(name: str) -> str:
    return re.sub(r"-+", "-", re.sub(r"[^a-z0-9]+", "-", name.lower())).strip("-")


def _build_name_pool(rng: random.Random, count: int) -> list[str]:
    pairs = [(first, last) for first in _FIRST_NAMES for last in _LAST_NAMES]
    rng.shuffle(pairs)
    if count > len(pairs):
        raise ValueError(f"name pool too small: need {count}, have {len(pairs)}")
    return [f"{first} {last}" for first, last in pairs[:count]]


_BASE_COMPENSATION = {
    "ceo": Decimal("420000"),
    "vp": Decimal("260000"),
    "director": Decimal("190000"),
    "manager": Decimal("145000"),
    "ic": Decimal("98000"),
}


@dataclass
class _SeededPosition:
    id: ObjectId
    title: str
    department: str
    level: str  # "ceo" | "vp" | "director" | "manager" | "ic"


@dataclass
class _Tenant:
    org_id: ObjectId
    positions: list[_SeededPosition] = field(default_factory=list)


def _compensation_for(level: str, rng: random.Random) -> Decimal:
    base = _BASE_COMPENSATION[level]
    jitter = Decimal(rng.randint(-8, 8)) / Decimal(100)  # +/-8%
    return (base * (Decimal(1) + jitter)).quantize(Decimal("1.00"))


def _create_position(
    position_repo: PositionRepo, title: str, department: str, level: str
) -> _SeededPosition:
    position_id = position_repo.create(title, department)
    return _SeededPosition(id=position_id, title=title, department=department, level=level)


def _build_hierarchy(org_id: ObjectId, rng: random.Random, *, ic_range: tuple[int, int]) -> _Tenant:
    position_repo = PositionRepo(org_id)
    tenant = _Tenant(org_id=org_id)

    ceo = _create_position(position_repo, "CEO", "Executive", "ceo")
    tenant.positions.append(ceo)

    for department in _DEPARTMENTS:
        vp = _create_position(position_repo, f"VP of {department}", department, "vp")
        tenant.positions.append(vp)
        org_graph.add_reporting_line(org_id, ceo.id, vp.id, "solid", True)

        for _ in range(3):
            director = _create_position(
                position_repo, f"Director of {department}", department, "director"
            )
            tenant.positions.append(director)
            org_graph.add_reporting_line(org_id, vp.id, director.id, "solid", True)

            for _ in range(2):
                manager = _create_position(
                    position_repo,
                    f"{department} Manager",
                    department,
                    "manager",
                )
                tenant.positions.append(manager)
                org_graph.add_reporting_line(org_id, director.id, manager.id, "solid", True)

                for _ in range(rng.randint(*ic_range)):
                    title = rng.choice(_IC_TITLES[department])
                    ic = _create_position(position_repo, title, department, "ic")
                    tenant.positions.append(ic)
                    org_graph.add_reporting_line(org_id, manager.id, ic.id, "solid", True)

    return tenant


def _add_dotted_lines(org_id: ObjectId, tenant: _Tenant, rng: random.Random, count: int) -> None:
    ics = [p for p in tenant.positions if p.level == "ic"]
    managers = [p for p in tenant.positions if p.level in ("manager", "director")]
    added = 0
    attempts = 0
    while added < count and attempts < count * 10:
        attempts += 1
        report = rng.choice(ics)
        manager = rng.choice(managers)
        if manager.department == report.department:
            continue
        try:
            org_graph.add_reporting_line(org_id, manager.id, report.id, "dotted", False)
        except CycleError:
            continue
        added += 1


def _add_dual_solid_co_managers(org_id: ObjectId, tenant: _Tenant, rng: random.Random) -> None:
    """Two positions each gain a second solid manager, non-primary - the
    "two positions with two solid-line co-managers" demo story.
    """
    ics = [p for p in tenant.positions if p.level == "ic"]
    managers = [p for p in tenant.positions if p.level == "manager"]
    for report in rng.sample(ics, 2):
        candidate_managers = [m for m in managers if m.department != report.department]
        second_manager = rng.choice(candidate_managers)
        try:
            org_graph.add_reporting_line(org_id, second_manager.id, report.id, "solid", False)
        except CycleError:
            continue


def _email_for(name: str, domain: str) -> str:
    first, last = name.lower().split(" ", 1)
    return f"{first}.{last.replace(' ', '-')}@{domain}"


def _populate_people(
    org_id: ObjectId,
    tenant: _Tenant,
    rng: random.Random,
    *,
    email_domain: str,
    vacant_count: int,
    dual_role_employee_positions: tuple[ObjectId, ObjectId] | None,
) -> None:
    employee_repo = EmployeeRepo(org_id)
    assignment_repo = AssignmentRepo(org_id)
    position_repo = PositionRepo(org_id)
    now = datetime.now(UTC)

    fillable = [p for p in tenant.positions if p.level != "ceo"]
    vacant_ids = {p.id for p in rng.sample(fillable, min(vacant_count, len(fillable)))}
    if dual_role_employee_positions:
        vacant_ids -= set(dual_role_employee_positions)

    names = iter(_build_name_pool(rng, len(tenant.positions) + 1))

    for position in tenant.positions:
        if position.id in vacant_ids:
            position_repo.update_one({"_id": position.id}, {"$set": {"status": "vacant"}})
            continue

        if dual_role_employee_positions and position.id in dual_role_employee_positions:
            continue  # both handled once, below, by the single dual-role employee

        name = next(names)
        email = _email_for(name, email_domain)
        employee_id = employee_repo.create(
            name, email, compensation_amount=_compensation_for(position.level, rng)
        )
        assignment_repo.create(employee_id, position.id, start_date=now - timedelta(days=365))

    if dual_role_employee_positions:
        position_a_id, position_b_id = dual_role_employee_positions
        dual_role_name = next(names)
        employee_id = employee_repo.create(
            dual_role_name,
            _email_for(dual_role_name, email_domain),
            compensation_amount=_compensation_for("ic", rng),
        )
        assignment_repo.create(
            employee_id,
            position_a_id,
            start_date=now - timedelta(days=200),
            fte=0.5,
            is_primary=True,
        )
        assignment_repo.create(
            employee_id,
            position_b_id,
            start_date=now - timedelta(days=200),
            fte=0.5,
            is_primary=False,
        )


def _seed_tenant(
    name: str,
    *,
    ic_range: tuple[int, int],
    dotted_lines: int,
    dual_solid_co_managers: bool,
    vacant_count: int,
    dual_role_employee: bool,
) -> ObjectId:
    org_repo = OrganizationRepo()
    org_id = org_repo.create(name)
    rng = random.Random(f"{SEED}:{name}")

    tenant = _build_hierarchy(org_id, rng, ic_range=ic_range)
    _add_dotted_lines(org_id, tenant, rng, dotted_lines)

    dual_role_positions: tuple[ObjectId, ObjectId] | None = None
    if dual_solid_co_managers:
        _add_dual_solid_co_managers(org_id, tenant, rng)
    if dual_role_employee:
        ics = [p for p in tenant.positions if p.level == "ic"]
        chosen = rng.sample(ics, 2)
        dual_role_positions = (chosen[0].id, chosen[1].id)

    _populate_people(
        org_id,
        tenant,
        rng,
        email_domain=f"{_slugify(name)}.example",
        vacant_count=vacant_count,
        dual_role_employee_positions=dual_role_positions,
    )

    logger.info("tenant_seeded", org_id=str(org_id), name=name, positions=len(tenant.positions))
    return org_id


def _reset_tenant(name: str) -> None:
    org_repo = OrganizationRepo()
    existing = org_repo.find_by_name(name)
    if existing is None:
        return
    org_id = existing["_id"]
    PositionRepo(org_id).delete_all()
    EmployeeRepo(org_id).delete_all()
    AssignmentRepo(org_id).delete_all()
    org_repo.delete(org_id)
    logger.info("tenant_reset", org_id=str(org_id), name=name)


def seed(*, reset: bool = False) -> None:
    settings = get_settings()
    configure_logging(settings.log_level)
    run_migrations(get_database())

    tenant_a_name = "Acme Corporation"
    tenant_b_name = "Bramble & Co"

    if reset:
        _reset_tenant(tenant_a_name)
        _reset_tenant(tenant_b_name)

    org_repo = OrganizationRepo()
    if org_repo.find_by_name(tenant_a_name) is not None:
        logger.info("seed_skipped_already_present", name=tenant_a_name)
    else:
        _seed_tenant(
            tenant_a_name,
            ic_range=(2, 3),
            dotted_lines=8,
            dual_solid_co_managers=True,
            vacant_count=10,
            dual_role_employee=True,
        )

    if org_repo.find_by_name(tenant_b_name) is not None:
        logger.info("seed_skipped_already_present", name=tenant_b_name)
    else:
        _seed_tenant(
            tenant_b_name,
            ic_range=(1, 2),
            dotted_lines=2,
            dual_solid_co_managers=False,
            vacant_count=2,
            dual_role_employee=False,
        )


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--reset", action="store_true", help="drop and recreate the two demo tenants"
    )
    args = parser.parse_args()
    seed(reset=args.reset)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
