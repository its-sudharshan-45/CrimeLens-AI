from sqlalchemy import MetaData
from sqlalchemy.orm import DeclarativeBase

# Naming convention for Alembic migrations to automatically name constraints
# This prevents issues when migrating databases where constraints need to be altered/dropped.
POSTGRES_NAMING_CONVENTION = {
    "ix": "ix_%(column_0_label)s",
    "uq": "uq_%(table_name)s_%(column_0_name)s",
    "ck": "ck_%(table_name)s_%(constraint_name)s",
    "fk": "fk_%(table_name)s_%(column_0_name)s_%(referred_table_name)s",
    "pk": "pk_%(table_name)s"
}

metadata = MetaData(naming_convention=POSTGRES_NAMING_CONVENTION)

class Base(DeclarativeBase):
    """
    Base class for all SQLAlchemy 2.0 models.
    All models will inherit from this class, and they will share the same metadata.
    """
    metadata = metadata
