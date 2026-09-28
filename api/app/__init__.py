"""The application factory."""

from __future__ import annotations

import json

from flask import Response, make_response
from flask_openapi3.models.info import Info
from flask_openapi3.openapi import OpenAPI
from pydantic import ValidationError

from app.config import Settings, get_settings
from app.errors import ReportlineError
from app.logging import bind_request_id, configure_logging, get_logger
from app.models.api.common import ErrorOut
from app.routes.admin import bp as admin_bp
from app.routes.employees import bp as employees_bp
from app.routes.graph import bp as graph_bp
from app.routes.health import bp as health_bp
from app.routes.organizations import bp as organizations_bp
from app.routes.positions import bp as positions_bp
from app.routes.reporting_lines import bp as reporting_lines_bp

logger = get_logger(__name__)


def _handle_reportline_error(err: ReportlineError) -> tuple[dict[str, object], int]:
    logger.warning("request_failed", code=err.code, message=err.message, status=err.http_status)
    body = ErrorOut(error=err.code, message=err.message, details=err.details)
    return body.model_dump(mode="json"), err.http_status


def _handle_validation_error(err: ValidationError) -> Response:
    """Must return a single ``Response``, not a tuple - flask-openapi3 passes
    this callback's return value straight into ``werkzeug.abort()``, which
    only special-cases a bare ``Response`` (see its own
    ``make_validation_error_response`` for the pattern this mirrors).
    """
    errors = json.loads(err.json())
    message = errors[0]["msg"] if errors else "invalid request"
    body = ErrorOut(error="validation_error", message=message, details={"errors": errors})
    response = make_response(body.model_dump_json())
    response.headers["Content-Type"] = "application/json"
    response.status_code = 422
    return response


def create_app(settings: Settings | None = None) -> OpenAPI:
    settings = settings or get_settings()
    configure_logging(settings.log_level)

    app = OpenAPI(
        __name__,
        info=Info(title="Reportline API", version="1.0.0"),
        validation_error_status=422,
        validation_error_callback=_handle_validation_error,
        doc_prefix="/api/v1/openapi",
    )
    app.config["SETTINGS"] = settings

    @app.before_request
    def _bind_request_id() -> None:
        bind_request_id()

    app.register_error_handler(ReportlineError, _handle_reportline_error)

    app.register_api(health_bp)
    app.register_api(positions_bp)
    app.register_api(employees_bp)
    app.register_api(graph_bp)
    app.register_api(reporting_lines_bp)
    app.register_api(admin_bp)
    app.register_api(organizations_bp)

    return app
