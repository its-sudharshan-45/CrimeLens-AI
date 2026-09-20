from datetime import datetime
from typing import Optional
from sqlalchemy import Boolean, DateTime
from sqlalchemy.orm import Mapped, mapped_column

class SoftDeleteMixin:
    """Provides is_deleted and deleted_at for soft deletion."""
    is_deleted: Mapped[bool] = mapped_column(
        Boolean, default=False, nullable=False, index=True
    )
    deleted_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
