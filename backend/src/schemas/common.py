from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, ConfigDict


class SchemaBase(BaseModel):
    model_config = ConfigDict(from_attributes=True)


class IDSchema(SchemaBase):
    id: str


class TimestampSchema(SchemaBase):
    created_at: datetime
    updated_at: datetime

