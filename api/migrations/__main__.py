"""``python -m migrations`` applies pending migrations; ``--status`` lists them.

This is what ``make migrate`` / ``make migrate-status`` run, and what
``docker compose run --rm seed`` runs before seeding - see docs/runbook.md
for the operational procedures (recovering from a checksum mismatch,
resetting the local environment).
"""

from __future__ import annotations

import sys

from app.config import get_settings
from app.db import get_database
from app.logging import configure_logging, get_logger
from migrations.runner import migration_status, run_migrations

logger = get_logger(__name__)


def main(argv: list[str]) -> int:
    settings = get_settings()
    configure_logging(settings.log_level)
    db = get_database()

    if "--status" in argv:
        for entry in migration_status(db):
            marker = "[x]" if entry["applied"] else "[ ]"
            print(f"{marker} {entry['version']} {entry['name']}")
        return 0

    applied = run_migrations(db)
    for migration in applied:
        logger.info("migration_applied", version=migration.version, name=migration.name)
    if not applied:
        logger.info("no_pending_migrations")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
