from __future__ import annotations

from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict, field_validator

from src.utils.text import repair_data


class SchemaBase(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    @field_validator("*", mode="before", check_fields=False)
    @classmethod
    def _repair_text_fields(cls, value: Any) -> Any:
        return repair_data(value)


class IDSchema(SchemaBase):
    id: str


class TimestampSchema(SchemaBase):
    created_at: datetime
    updated_at: datetime
