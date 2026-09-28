from __future__ import annotations

from app.db import Document
from app.repos import OrganizationRepo


def list_organizations() -> list[Document]:
    return OrganizationRepo().list_all()
