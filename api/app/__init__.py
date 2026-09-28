"""The application factory. Blueprints are registered starting Phase 2."""

from __future__ import annotations

from flask import Flask

from app.config import Settings, get_settings
from app.logging import configure_logging


def create_app(settings: Settings | None = None) -> Flask:
    settings = settings or get_settings()
    configure_logging(settings.log_level)

    app = Flask(__name__)
    app.config["SETTINGS"] = settings

    return app
