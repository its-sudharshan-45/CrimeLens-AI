"""
CrimeLocation Pydantic Schemas
==============================
All schemas are Pydantic v2.

Indian geographic bounds used for validation
--------------------------------------------
Latitude  :  6.0°N  – 38.0°N
Longitude : 68.0°E  – 98.0°E
ZIP code  : 6-digit numeric Indian PIN code
"""
import re
from datetime import datetime
from typing import Optional
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, field_validator

from app.core.enums.indian_state import IndianState


class CrimeLocationCreate(BaseModel):
    """
    Validated payload for creating a new crime location.

    Validation rules
    ----------------
    latitude    6.0 – 38.0 (India's geographic extent, °N).
    longitude  68.0 – 98.0 (India's geographic extent, °E).
    city        Required, 1–100 characters.
    district    Required, 1–100 characters, free-form text.
    state       Must be a valid IndianState enum value.
    zip_code    Optional 6-digit Indian PIN code.
    address     Optional, max 512 characters.
    landmark    Optional, max 255 characters.
    """

    latitude: float = Field(..., description="Decimal degrees — India: 6.0°N – 38.0°N")
    longitude: float = Field(
        ..., description="Decimal degrees — India: 68.0°E – 98.0°E"
    )
    address: Optional[str] = Field(None, max_length=512)
    landmark: Optional[str] = Field(None, max_length=255)
    city: str = Field(..., description="City name")
    district: str = Field(..., description="District name (free-form)")
    state: IndianState = Field(..., description="Valid Indian State or Union Territory")
    zip_code: Optional[str] = Field(None, description="6-digit Indian PIN code")

    @field_validator("latitude", mode="after")
    @classmethod
    def validate_latitude(cls, v: float) -> float:
        if not (6.0 <= v <= 38.0):
            raise ValueError(
                f"Latitude {v}° is outside Indian territory. "
                "Valid range: 6.0°N – 38.0°N"
            )
        return v

    @field_validator("longitude", mode="after")
    @classmethod
    def validate_longitude(cls, v: float) -> float:
        if not (68.0 <= v <= 98.0):
            raise ValueError(
                f"Longitude {v}° is outside Indian territory. "
                "Valid range: 68.0°E – 98.0°E"
            )
        return v

    @field_validator("zip_code", mode="before")
    @classmethod
    def validate_zip_code(cls, v: Optional[str]) -> Optional[str]:
        if v is not None:
            v = v.strip()
            if not re.match(r"^\d{6}$", v):
                raise ValueError(
                    "zip_code must be a 6-digit Indian PIN code (e.g. 400001)"
                )
        return v

    @field_validator("city", "district", mode="before")
    @classmethod
    def strip_string_fields(cls, v: str) -> str:
        v = v.strip()
        if not v:
            raise ValueError("Field cannot be blank")
        return v


class CrimeLocationUpdate(BaseModel):
    """
    Validated payload for partially updating an existing crime location.
    All fields are optional — only supplied fields are written.
    """

    latitude: Optional[float] = None
    longitude: Optional[float] = None
    address: Optional[str] = Field(None, max_length=512)
    landmark: Optional[str] = Field(None, max_length=255)
    city: Optional[str] = Field(None)
    district: Optional[str] = Field(None)
    state: Optional[IndianState] = None
    zip_code: Optional[str] = None

    @field_validator("latitude", mode="after")
    @classmethod
    def validate_latitude(cls, v: Optional[float]) -> Optional[float]:
        if v is not None and not (6.0 <= v <= 38.0):
            raise ValueError(
                f"Latitude {v}° is outside Indian territory (6.0°N – 38.0°N)"
            )
        return v

    @field_validator("longitude", mode="after")
    @classmethod
    def validate_longitude(cls, v: Optional[float]) -> Optional[float]:
        if v is not None and not (68.0 <= v <= 98.0):
            raise ValueError(
                f"Longitude {v}° is outside Indian territory (68.0°E – 98.0°E)"
            )
        return v

    @field_validator("zip_code", mode="before")
    @classmethod
    def validate_zip_code(cls, v: Optional[str]) -> Optional[str]:
        if v is not None:
            v = v.strip()
            if not re.match(r"^\d{6}$", v):
                raise ValueError("zip_code must be a 6-digit Indian PIN code")
        return v


class CrimeLocationResponse(BaseModel):
    """Outbound DTO for a single crime location."""

    id: UUID
    latitude: float
    longitude: float
    address: Optional[str] = None
    landmark: Optional[str] = None
    city: str
    district: str
    state: str  # Stored as plain string in DB
    zip_code: Optional[str] = None
    created_at: datetime
    updated_at: datetime
    is_deleted: bool

    model_config = ConfigDict(from_attributes=True)
