"""Structured JSON logging with a request id on every line.

``configure_logging`` is called once, from ``create_app`` and from every
standalone script (``scripts/seed.py``, ``scripts/explain_queries.py``, the
migration runner CLI) so log output is consistent everywhere, not just
inside a Flask request.
"""

from __future__ import annotations

import logging
import uuid

import structlog


def configure_logging(level: str = "INFO") -> None:
    logging.basicConfig(format="%(message)s", level=level)
    structlog.configure(
        processors=[
            structlog.contextvars.merge_contextvars,
            structlog.processors.add_log_level,
            structlog.processors.TimeStamper(fmt="iso", utc=True),
            structlog.processors.StackInfoRenderer(),
            structlog.processors.format_exc_info,
            structlog.processors.JSONRenderer(),
        ],
        wrapper_class=structlog.make_filtering_bound_logger(logging.getLevelNamesMapping()[level]),
        logger_factory=structlog.PrintLoggerFactory(),
        cache_logger_on_first_use=True,
    )


def new_request_id() -> str:
    return uuid.uuid4().hex


def bind_request_id(request_id: str | None = None) -> str:
    """Bind a request id to the current context, generating one if absent."""
    request_id = request_id or new_request_id()
    structlog.contextvars.bind_contextvars(request_id=request_id)
    return request_id


get_logger = structlog.get_logger
