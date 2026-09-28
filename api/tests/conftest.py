"""Shared fixtures. Mirrors SaveState's pattern: a session-scoped real
database (never mongomock - $graphLookup and transactions don't work
against it), migrations applied once via the real runner (so the suite also
proves the migrations work), and an autouse per-test cleanup that only
truncates collections for tests marked ``integration``.

Uses ``MongoDBAtlasLocalContainer`` rather than a hand-rolled
``mongod --replSet`` container: that image runs as a single-node replica
set out of the box, which is exactly what transactions and ``$graphLookup``
need, without scripting ``rs.initiate()`` in test setup. This is a
deliberate divergence from docker-compose's local-dev Mongo, which uses a
hand-rolled ``rs0`` + keyfile setup instead, to demonstrate the production
security model - see ADR 0001.
"""

from __future__ import annotations

from collections.abc import Iterator

import pytest
from pymongo.database import Database
from testcontainers.community.mongodb import MongoDBAtlasLocalContainer

from app.config import get_settings
from app.db import Document, get_database, get_mongo_client
from migrations.runner import run_migrations


@pytest.fixture(scope="session")
def monkeysession() -> Iterator[pytest.MonkeyPatch]:
    mp = pytest.MonkeyPatch()
    yield mp
    mp.undo()


@pytest.fixture(scope="session")
def mongo_container() -> Iterator[MongoDBAtlasLocalContainer]:
    with MongoDBAtlasLocalContainer() as container:
        yield container


@pytest.fixture(scope="session", autouse=True)
def _test_database(
    mongo_container: MongoDBAtlasLocalContainer, monkeysession: pytest.MonkeyPatch
) -> Iterator[Database[Document]]:
    monkeysession.setenv("SECRET_KEY", "test-secret")
    monkeysession.setenv("MONGODB_URI", mongo_container.get_connection_url())
    monkeysession.setenv("MONGODB_DB_NAME", "reportline_test")
    get_settings.cache_clear()
    get_mongo_client.cache_clear()

    database = get_database()
    run_migrations(database)

    yield database

    get_mongo_client().close()
    get_settings.cache_clear()
    get_mongo_client.cache_clear()


@pytest.fixture
def db(request: pytest.FixtureRequest, _test_database: Database[Document]) -> Database[Document]:
    if request.node.get_closest_marker("integration") is not None:
        for name in _test_database.list_collection_names():
            if name != "schema_migrations":
                _test_database[name].delete_many({})
    return _test_database
