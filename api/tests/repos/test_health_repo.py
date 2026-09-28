from unittest.mock import MagicMock

import pytest
from pymongo.errors import PyMongoError

from app.repos import health

pytestmark = pytest.mark.integration


def test_ping_returns_true_when_mongo_is_reachable(db):
    assert health.ping() is True


def test_ping_returns_false_when_mongo_is_unreachable(monkeypatch, db):
    broken_db = MagicMock()
    broken_db.command.side_effect = PyMongoError("connection refused")
    monkeypatch.setattr(health, "get_database", lambda: broken_db)

    assert health.ping() is False
