from typing import TYPE_CHECKING, List, Optional

from sqlalchemy import Integer, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .base import BaseModel

if TYPE_CHECKING:
    from .crime_report import CrimeReport

class CrimeCategory(BaseModel):
    __tablename__ = "crime_categories"

    name: Mapped[str] = mapped_column(
        String(100), unique=True, index=True, nullable=False
    )
    description: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    severity_level: Mapped[int] = mapped_column(Integer, default=1, nullable=False)
    color_code: Mapped[Optional[str]] = mapped_column(String(20), nullable=True)

    reports: Mapped[List["CrimeReport"]] = relationship(
        "CrimeReport", back_populates="category"
    )
