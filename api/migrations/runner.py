"""The migration runner.

CLAUDE.md: "Schema, validators, and indexes change ONLY through a new
migration in api/migrations/. Never call create_index or collMod from
application startup or request code." This module is the only place that
does either.

Each migration is a Python file in ``migrations/versions/`` named
``<4-digit-version>_<name>.py``, exporting a module-level ``VERSION``,
``NAME``, and an ``up(db)`` function. Applied migrations are recorded in the
``schema_migrations`` collection (version, name, checksum, applied_at) -
re-running an already-applied migration is a no-op, and editing a migration
after it's been applied is treated as an error (write a new migration
instead, per the expand/migrate/contract process).
"""

from __future__ import annotations

import hashlib
import importlib.util
from collections.abc import Callable
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path

from pymongo.database import Database

from app.db import Document

SCHEMA_MIGRATIONS_COLLECTION = "schema_migrations"
DEFAULT_VERSIONS_DIR = Path(__file__).parent / "versions"


@dataclass(frozen=True)
class LoadedMigration:
    version: str
    name: str
    checksum: str
    up: Callable[[Database[Document]], None]


class MigrationChecksumMismatchError(RuntimeError):
    """An already-applied migration file was edited after being applied."""


def _discover(versions_dir: Path) -> list[LoadedMigration]:
    migrations = []
    for path in sorted(versions_dir.glob("[0-9]*.py")):
        spec = importlib.util.spec_from_file_location(f"migrations.versions.{path.stem}", path)
        if spec is None or spec.loader is None:  # pragma: no cover - defensive
            raise RuntimeError(f"could not load migration module at {path}")
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        checksum = hashlib.sha256(path.read_bytes()).hexdigest()
        migrations.append(
            LoadedMigration(
                version=module.VERSION, name=module.NAME, checksum=checksum, up=module.up
            )
        )
    versions = [m.version for m in migrations]
    if len(versions) != len(set(versions)):
        raise RuntimeError(f"duplicate migration version numbers found: {versions}")
    return migrations


def _applied_by_version(db: Database[Document]) -> dict[str, str]:
    return {doc["version"]: doc["checksum"] for doc in db[SCHEMA_MIGRATIONS_COLLECTION].find({})}


def run_migrations(
    db: Database[Document], *, versions_dir: Path = DEFAULT_VERSIONS_DIR
) -> list[LoadedMigration]:
    """Apply every pending migration, in order. Returns the ones just applied."""
    migrations = _discover(versions_dir)
    applied = _applied_by_version(db)
    newly_applied: list[LoadedMigration] = []

    for migration in migrations:
        previous_checksum = applied.get(migration.version)
        if previous_checksum is not None:
            if previous_checksum != migration.checksum:
                raise MigrationChecksumMismatchError(
                    f"migration {migration.version} ({migration.name}) was edited after "
                    "being applied - never edit an applied migration, write a new one"
                )
            continue

        migration.up(db)
        db[SCHEMA_MIGRATIONS_COLLECTION].insert_one(
            {
                "version": migration.version,
                "name": migration.name,
                "checksum": migration.checksum,
                "applied_at": datetime.now(UTC),
            }
        )
        newly_applied.append(migration)

    return newly_applied


def migration_status(
    db: Database[Document], *, versions_dir: Path = DEFAULT_VERSIONS_DIR
) -> list[dict[str, str | bool]]:
    migrations = _discover(versions_dir)
    applied = _applied_by_version(db)
    return [
        {"version": m.version, "name": m.name, "applied": m.version in applied} for m in migrations
    ]
