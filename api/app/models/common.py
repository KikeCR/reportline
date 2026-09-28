"""Shared Pydantic building blocks: the ObjectId/Decimal128 bridge types and
the base class every canonical (Mongo-shaped) model inherits from.
"""

from __future__ import annotations

from datetime import datetime
from decimal import Decimal
from typing import Annotated, Any

from bson import Decimal128, ObjectId
from pydantic import (
    BaseModel,
    ConfigDict,
    Field,
    GetCoreSchemaHandler,
    GetJsonSchemaHandler,
)
from pydantic.json_schema import JsonSchemaValue
from pydantic_core import core_schema


class _ObjectIdPydanticAnnotation:
    """Lets ``ObjectId`` be used as a Pydantic field type.

    Accepts an ``ObjectId`` or a valid hex string on input; serializes to a
    plain string for JSON output, which is how every id crosses the API
    boundary (it stays an ``ObjectId`` in the database and in memory).
    """

    @classmethod
    def __get_pydantic_core_schema__(
        cls, source_type: Any, handler: GetCoreSchemaHandler
    ) -> core_schema.CoreSchema:
        def validate(value: Any) -> ObjectId:
            if isinstance(value, ObjectId):
                return value
            if isinstance(value, str) and ObjectId.is_valid(value):
                return ObjectId(value)
            raise ValueError(f"{value!r} is not a valid ObjectId")

        return core_schema.no_info_plain_validator_function(
            validate,
            serialization=core_schema.plain_serializer_function_ser_schema(str, when_used="json"),
        )

    @classmethod
    def __get_pydantic_json_schema__(
        cls, schema: core_schema.CoreSchema, handler: GetJsonSchemaHandler
    ) -> JsonSchemaValue:
        return {"type": "string", "format": "objectid", "example": "507f1f77bcf86cd799439011"}


PyObjectId = Annotated[ObjectId, _ObjectIdPydanticAnnotation]


class _Decimal128PydanticAnnotation:
    """Lets ``bson.Decimal128`` be used as a Pydantic field type.

    Money is stored as ``Decimal128`` (never ``float``, per the MongoDB
    standards); this accepts a ``Decimal``/``int``/``str`` on input and
    serializes to a decimal string for JSON output.
    """

    @classmethod
    def __get_pydantic_core_schema__(
        cls, source_type: Any, handler: GetCoreSchemaHandler
    ) -> core_schema.CoreSchema:
        def validate(value: Any) -> Decimal128:
            if isinstance(value, Decimal128):
                return value
            if isinstance(value, Decimal | int | str):
                return Decimal128(str(value))
            raise ValueError(f"{value!r} is not a valid decimal amount")

        def serialize(value: Decimal128) -> str:
            return str(value.to_decimal())

        return core_schema.no_info_plain_validator_function(
            validate,
            serialization=core_schema.plain_serializer_function_ser_schema(
                serialize, when_used="json"
            ),
        )

    @classmethod
    def __get_pydantic_json_schema__(
        cls, schema: core_schema.CoreSchema, handler: GetJsonSchemaHandler
    ) -> JsonSchemaValue:
        return {"type": "string", "format": "decimal"}


PyDecimal128 = Annotated[Decimal128, _Decimal128PydanticAnnotation]


class MongoBaseModel(BaseModel):
    """Base for canonical models mapped 1:1 to a tenant-scoped document."""

    model_config = ConfigDict(populate_by_name=True)

    id: PyObjectId = Field(alias="_id")
    org_id: PyObjectId
    schema_version: int = 1
    created_at: datetime
    updated_at: datetime
    created_by: PyObjectId | None = None
    updated_by: PyObjectId | None = None
