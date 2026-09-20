from typing import TYPE_CHECKING, List, Optional

from sqlalchemy import Float, Index, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .base import BaseModel

if TYPE_CHECKING:
    from .crime_report import CrimeReport

class CrimeLocation(BaseModel):
    __tablename__ = "crime_locations"

    latitude: Mapped[float] = mapped_column(Float, nullable=False)
    longitude: Mapped[float] = mapped_column(Float, nullable=False)
    address: Mapped[Optional[str]] = mapped_column(String(512), nullable=True)
    landmark: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    city: Mapped[str] = mapped_column(String(100), nullable=False)
    district: Mapped[str] = mapped_column(String(100), nullable=False)
    state: Mapped[str] = mapped_column(String(100), nullable=False)
    zip_code: Mapped[Optional[str]] = mapped_column(String(20), nullable=True)

    reports: Mapped[List["CrimeReport"]] = relationship(
        "CrimeReport", back_populates="location"
    )

    __table_args__ = (
        Index("ix_crime_locations_lat_lon", "latitude", "longitude"),
    )
