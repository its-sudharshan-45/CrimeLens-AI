from app.db.base import Base
from .mixins import UUIDMixin, TimestampMixin, SoftDeleteMixin

class BaseModel(Base, UUIDMixin, TimestampMixin, SoftDeleteMixin):
    """
    Abstract base model that composes Base with all standard mixins.
    All business models should inherit from this class.
    """
    __abstract__ = True
