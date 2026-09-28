"""``EmployeePublicOut`` vs ``EmployeeHROut``: CLAUDE.md requires
compensation to exist only on the HR-level model. Phase 4 will branch on
role to choose between them; until then, GET /employees/{id} always returns
the public shape - never expose compensation ahead of having a permission
model to gate it.
"""

from __future__ import annotations

from pydantic import BaseModel

from app.models.common import PyDecimal128, PyObjectId


class EmployeePath(BaseModel):
    employee_id: PyObjectId


class CompensationOut(BaseModel):
    amount: PyDecimal128
    currency: str


class EmployeePublicOut(BaseModel):
    id: PyObjectId
    name: str
    title: str | None


class EmployeeHROut(EmployeePublicOut):
    compensation: CompensationOut
