"""Not a ``ScopedRepo``: a connectivity check has no tenant to scope by."""

from __future__ import annotations

from pymongo.errors import PyMongoError

from app.db import get_database


def ping() -> bool:
    try:
        get_database().command("ping")
    except PyMongoError:
        return False
    return True
