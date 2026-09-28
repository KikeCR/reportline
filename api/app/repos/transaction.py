"""Multi-document transaction helper.

This is the one place ``services/`` is allowed to reach past a plain repo
method: a service needs a live ``ClientSession`` handle to pass into several
repo calls that must all commit or abort together (see
``services/org_graph.py``). The session is an opaque handle here - the
service never calls a collection method on it directly, so the
"only repos/ touches pymongo collections" rule still holds (see ADR 0001).
"""

from __future__ import annotations

from collections.abc import Callable

from pymongo.client_session import ClientSession
from pymongo.read_concern import ReadConcern
from pymongo.write_concern import WriteConcern

from app.db import get_mongo_client


def run_in_transaction[T](callback: Callable[[ClientSession], T]) -> T:
    """Run ``callback`` inside a majority read/write multi-document transaction.

    ``callback`` may be invoked more than once if the driver retries a
    transient transaction error - it must not have side effects outside the
    database (see ``ClientSession.with_transaction``'s docstring).
    """
    client = get_mongo_client()
    with client.start_session() as session:
        return session.with_transaction(
            callback,
            read_concern=ReadConcern("majority"),
            write_concern=WriteConcern("majority"),
        )
