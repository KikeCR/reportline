"""The one process-wide MongoClient.

Only ``app.repos`` imports this module. Nothing outside ``repos/`` should
ever hold a reference to a ``Database`` or ``Collection`` - see
CLAUDE.md's "Only repos/ may import pymongo collections" rule.
"""

from __future__ import annotations

from functools import lru_cache
from typing import Any

import pymongo.monitoring as monitoring
from pymongo import MongoClient
from pymongo.database import Database

from app.config import get_settings
from app.logging import get_logger

logger = get_logger(__name__)

Document = dict[str, Any]


class _SlowQueryLogger(monitoring.CommandListener):
    """Logs any command that takes longer than the configured threshold."""

    def __init__(self, threshold_ms: int) -> None:
        self._threshold_ms = threshold_ms

    def started(self, event: monitoring.CommandStartedEvent) -> None:
        pass

    def failed(self, event: monitoring.CommandFailedEvent) -> None:
        logger.warning(
            "mongo_command_failed",
            command=event.command_name,
            database=event.database_name,
            duration_ms=round(event.duration_micros / 1000, 1),
            request_id=event.request_id,
        )

    def succeeded(self, event: monitoring.CommandSucceededEvent) -> None:
        duration_ms = event.duration_micros / 1000
        if duration_ms >= self._threshold_ms:
            logger.warning(
                "slow_query",
                command=event.command_name,
                database=event.database_name,
                duration_ms=round(duration_ms, 1),
                request_id=event.request_id,
            )


@lru_cache
def get_mongo_client() -> MongoClient[Document]:
    settings = get_settings()
    return MongoClient(
        settings.mongodb_uri,
        maxPoolSize=settings.mongodb_max_pool_size,
        minPoolSize=settings.mongodb_min_pool_size,
        serverSelectionTimeoutMS=settings.mongodb_server_selection_timeout_ms,
        socketTimeoutMS=settings.mongodb_socket_timeout_ms,
        retryWrites=True,
        tz_aware=True,
        appname="reportline-api",
        event_listeners=[_SlowQueryLogger(settings.mongodb_slow_query_threshold_ms)],
    )


def get_database() -> Database[Document]:
    settings = get_settings()
    return get_mongo_client()[settings.mongodb_db_name]
