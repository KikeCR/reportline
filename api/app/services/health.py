from __future__ import annotations

from app.repos import health as health_repo


def check_database() -> bool:
    return health_repo.ping()
