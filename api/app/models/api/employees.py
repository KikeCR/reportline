"""``EmployeePublicOut`` (no compensation) vs ``EmployeeHROut``. Auth/roles
are descoped for now (see README "Descoped") so the route always returns
``EmployeeHROut``; ``EmployeePublicOut`` stays defined for when a permission
model is added back.
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
