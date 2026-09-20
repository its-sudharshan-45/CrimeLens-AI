import uuid
from sqlalchemy import Uuid
from sqlalchemy.orm import Mapped, mapped_column

class UUIDMixin:
    """Provides a UUID primary key."""
    id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
        index=True
    )
