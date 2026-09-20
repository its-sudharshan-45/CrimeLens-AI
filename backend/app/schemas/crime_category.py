"""
CrimeCategory Pydantic Schemas
==============================
All schemas are Pydantic v2.  Validators use @field_validator.

CrimeCategoryCreate   — inbound payload for POST
CrimeCategoryUpdate   — inbound payload for PATCH (all fields optional)
CrimeCategoryResponse — outbound DTO (single item)
"""
import re
from datetime import datetime
from typing import Optional
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, field_validator


class CrimeCategoryCreate(BaseModel):
    """
    Validated payload for creating a new crime category.

    Validation rules
    ----------------
    name           1–100 characters, stripped of whitespace.
    description    Optional, maximum 255 characters.
    severity_level Integer in the range [1, 10].
    color_code     Optional #RRGGBB hex colour string.
    """

    name: str = Field(..., description="Category name (1–100 characters)")
    description: Optional[str] = Field(None, max_length=255)
    severity_level: int = Field(1, description="Severity level 1 (minor) – 10 (critical)")
    color_code: Optional[str] = Field(None, description="#RRGGBB hex colour")

    @field_validator("name", mode="before")
    @classmethod
    def strip_name(cls, v: str) -> str:
        v = v.strip()
        if not v:
            raise ValueError("name cannot be blank or only whitespace")
        if len(v) > 100:
            raise ValueError("name must be at most 100 characters")
        return v

    @field_validator("severity_level")
    @classmethod
    def validate_severity_level(cls, v: int) -> int:
        if not (1 <= v <= 10):
            raise ValueError("severity_level must be between 1 and 10")
        return v

    @field_validator("color_code", mode="before")
    @classmethod
    def validate_color_code(cls, v: Optional[str]) -> Optional[str]:
        if v is not None:
            v = v.strip()
            if not re.match(r"^#[0-9A-Fa-f]{6}$", v):
                raise ValueError(
                    "color_code must be a valid #RRGGBB hex colour (e.g. #FF5733)"
                )
        return v


class CrimeCategoryUpdate(BaseModel):
    """
    Validated payload for partially updating an existing crime category.
    All fields are optional — only supplied fields are written.
    """

    name: Optional[str] = Field(None, description="New name (1–100 characters)")
    description: Optional[str] = Field(None, max_length=255)
    severity_level: Optional[int] = Field(None, description="Severity level 1–10")
    color_code: Optional[str] = None

    @field_validator("name", mode="before")
    @classmethod
    def strip_name(cls, v: Optional[str]) -> Optional[str]:
        if v is not None:
            v = v.strip()
            if not v:
                raise ValueError("name cannot be blank")
            if len(v) > 100:
                raise ValueError("name must be at most 100 characters")
        return v

    @field_validator("severity_level")
    @classmethod
    def validate_severity_level(cls, v: Optional[int]) -> Optional[int]:
        if v is not None and not (1 <= v <= 10):
            raise ValueError("severity_level must be between 1 and 10")
        return v

    @field_validator("color_code", mode="before")
    @classmethod
    def validate_color_code(cls, v: Optional[str]) -> Optional[str]:
        if v is not None:
            v = v.strip()
            if not re.match(r"^#[0-9A-Fa-f]{6}$", v):
                raise ValueError(
                    "color_code must be a valid #RRGGBB hex colour (e.g. #FF5733)"
                )
        return v


class CrimeCategoryResponse(BaseModel):
    """Outbound DTO for a single crime category."""

    id: UUID
    name: str
    description: Optional[str]
    severity_level: int
    color_code: Optional[str]
    created_at: datetime
    updated_at: datetime
    is_deleted: bool

    model_config = ConfigDict(from_attributes=True)
