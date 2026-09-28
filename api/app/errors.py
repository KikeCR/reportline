"""The single domain error taxonomy, mapped to HTTP responses in routes/.

Every service and repo raises one of these (never a raw ``pymongo`` or
``ValueError`` exception) so a route never has to guess what status code a
failure deserves. Routes register one Flask error handler per taxonomy
member (Phase 2) - this module has no Flask dependency itself.
"""

from __future__ import annotations

from typing import Any


class ReportlineError(Exception):
    """Base class for every domain error. Never raised directly."""

    http_status: int = 500
    code: str = "internal_error"

    def __init__(self, message: str, **details: Any) -> None:
        super().__init__(message)
        self.message = message
        self.details = details


class NotFoundError(ReportlineError):
    http_status = 404
    code = "not_found"


class ForbiddenError(ReportlineError):
    http_status = 403
    code = "forbidden"


class ConflictError(ReportlineError):
    http_status = 409
    code = "conflict"


class CycleError(ConflictError):
    """A graph edit would introduce a cycle across any edge type."""

    code = "cycle_detected"


class ConcurrentGraphEditError(ConflictError):
    """The org's graph_version changed between read and write; caller may retry."""

    code = "concurrent_graph_edit"


class DomainValidationError(ReportlineError):
    """A business-rule violation caught outside Pydantic field validation."""

    http_status = 422
    code = "validation_error"
