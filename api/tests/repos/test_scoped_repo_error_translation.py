"""CLAUDE.md's Mongo standards require driver errors to be translated at the
repo layer so services/routes never see a raw PyMongo exception. These
exercise that translation directly on ScopedRepo, via EmployeeRepo (whose
unique source-ref index is the natural way to trigger a real conflict).
"""

import pytest
from bson import ObjectId
from pymongo import UpdateOne

from app.errors import ConflictError
from app.repos import EmployeeRepo
from tests.factories import build_employee

pytestmark = pytest.mark.integration


def test_insert_one_translates_duplicate_key_error(db):
    org_id = ObjectId()
    repo = EmployeeRepo(org_id)
    ref = {"system": "workday_like", "id": "W-1"}
    repo.insert_one(build_employee(org_id, source_refs=[ref]))

    with pytest.raises(ConflictError):
        repo.insert_one(build_employee(org_id, source_refs=[ref]))


def test_update_one_translates_duplicate_key_error(db):
    org_id = ObjectId()
    repo = EmployeeRepo(org_id)
    ref = {"system": "workday_like", "id": "W-1"}
    repo.insert_one(build_employee(org_id, source_refs=[ref]))
    other_id = repo.insert_one(build_employee(org_id, source_refs=[]))

    with pytest.raises(ConflictError):
        repo.update_one({"_id": other_id}, {"$set": {"source_refs": [ref]}})


def test_bulk_write_translates_bulk_write_error(db):
    org_id = ObjectId()
    repo = EmployeeRepo(org_id)
    ref = {"system": "workday_like", "id": "W-1"}
    repo.insert_one(build_employee(org_id, source_refs=[ref]))
    other_id = repo.insert_one(build_employee(org_id, source_refs=[]))

    with pytest.raises(ConflictError):
        repo.bulk_write(
            [UpdateOne({"_id": other_id, "org_id": org_id}, {"$set": {"source_refs": [ref]}})]
        )
