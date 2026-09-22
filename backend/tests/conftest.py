"""
Shared pytest fixtures for CrimeLens AI backend integration tests.
"""

from __future__ import annotations

import uuid
from collections.abc import AsyncGenerator
from datetime import datetime, timedelta, timezone

import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy import JSON, select
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.api.dependencies import get_current_active_user, get_current_user
from app.core.enums.crime_status import CrimeStatus
from app.core.enums.priority import Priority
from app.db.base import Base
from app.db.session import get_db
from app.main import app
from app.models import (  # noqa: F401 - register all models on Base.metadata
    AuditLog,
    CrimeCategory,
    CrimeLocation,
    CrimeReport,
    Evidence,
    Investigation,
    InvestigationAssignment,
    InvestigationNote,
    InvestigationTimeline,
    Prediction,
    User,
)
from app.models.crime_category import CrimeCategory
from app.models.crime_location import CrimeLocation
from app.models.crime_report import CrimeReport
from app.models.user import User

TEST_DATABASE_URL = "sqlite+aiosqlite:///:memory:"

# Stable UUIDs for deterministic DB seeding across test runs
TEST_ADMIN_ID = uuid.UUID("11111111-1111-4111-8111-111111111111")
TEST_OFFICER_ID = uuid.UUID("22222222-2222-4222-8222-222222222222")
TEST_ANALYST_ID = uuid.UUID("33333333-3333-4333-8333-333333333333")
TEST_INVESTIGATOR_ID = uuid.UUID("44444444-4444-4444-8444-444444444444")
TEST_NEW_INVESTIGATOR_ID = uuid.UUID("55555555-5555-4555-8555-555555555555")
TEST_REPORT_ID = uuid.UUID("66666666-6666-4666-8666-666666666666")

mock_admin_user = User(
    id=TEST_ADMIN_ID,
    email="admin@test.com",
    full_name="Admin",
    supabase_user_id=uuid.UUID("aaaaaaaa-aaaa-4aaa-8aaa-aaaaaaaaaaaa"),
    is_active=True,
)

mock_officer_user = User(
    id=TEST_OFFICER_ID,
    email="officer@test.com",
    full_name="Officer",
    supabase_user_id=uuid.UUID("bbbbbbbb-bbbb-4bbb-8bbb-bbbbbbbbbbbb"),
    is_active=True,
)

mock_analyst_user = User(
    id=TEST_ANALYST_ID,
    email="analyst@test.com",
    full_name="Analyst",
    supabase_user_id=uuid.UUID("cccccccc-cccc-4ccc-8ccc-cccccccccccc"),
    is_active=True,
)

mock_investigator_user = User(
    id=TEST_INVESTIGATOR_ID,
    email="investigator@test.com",
    full_name="Investigator",
    supabase_user_id=uuid.UUID("dddddddd-dddd-4ddd-8ddd-dddddddddddd"),
    is_active=True,
)


def _set_auth_user(user: User) -> None:
    async def _override() -> User:
        return user

    app.dependency_overrides[get_current_user] = _override
    app.dependency_overrides[get_current_active_user] = _override


def _clear_auth_overrides() -> None:
    app.dependency_overrides.pop(get_current_user, None)
    app.dependency_overrides.pop(get_current_active_user, None)


async def _seed_test_data(session: AsyncSession) -> None:
    """Ensure users and a crime report exist for FK-backed tests."""
    user_specs = [
        (TEST_ADMIN_ID, "admin@test.com", uuid.UUID("aaaaaaaa-aaaa-4aaa-8aaa-aaaaaaaaaaaa")),
        (TEST_OFFICER_ID, "officer@test.com", uuid.UUID("bbbbbbbb-bbbb-4bbb-8bbb-bbbbbbbbbbbb")),
        (TEST_ANALYST_ID, "analyst@test.com", uuid.UUID("cccccccc-cccc-4ccc-8ccc-cccccccccccc")),
        (TEST_INVESTIGATOR_ID, "investigator@test.com", uuid.UUID("dddddddd-dddd-4ddd-8ddd-dddddddddddd")),
        (TEST_NEW_INVESTIGATOR_ID, "investigator2@test.com", uuid.UUID("eeeeeeee-eeee-4eee-8eee-eeeeeeeeeeee")),
    ]
    for user_id, email, supabase_id in user_specs:
        result = await session.execute(select(User).where(User.id == user_id))
        if result.scalar_one_or_none() is None:
            session.add(
                User(
                    id=user_id,
                    email=email,
                    supabase_user_id=supabase_id,
                    full_name=email.split("@")[0].title(),
                    is_active=True,
                )
            )
    await session.flush()

    result = await session.execute(select(CrimeReport).where(CrimeReport.id == TEST_REPORT_ID))
    if result.scalar_one_or_none() is None:
        category = CrimeCategory(name="Test Category", severity_level=3, color_code="#FF0000")
        session.add(category)
        await session.flush()

        location = CrimeLocation(
            latitude=12.97,
            longitude=77.59,
            city="Test City",
            district="Test District",
            state="Karnataka",
        )
        session.add(location)
        await session.flush()

        session.add(
            CrimeReport(
                id=TEST_REPORT_ID,
                crime_number=f"CR-{datetime.now(timezone.utc).year}-TEST001",
                title="Test Crime Report",
                description="Seeded report for integration tests",
                incident_date=datetime.now(timezone.utc) - timedelta(days=1),
                status=CrimeStatus.OPEN,
                priority=Priority.MEDIUM,
                reporter_id=TEST_OFFICER_ID,
                category_id=category.id,
                location_id=location.id,
            )
        )
    await session.commit()


def _prepare_sqlite_schema() -> None:
    """Replace PostgreSQL-only column types so metadata works on SQLite."""
    for table in Base.metadata.tables.values():
        for column in table.columns:
            if isinstance(column.type, JSONB):
                column.type = JSON()
            if getattr(column.type, "native_enum", None) is True:
                setattr(column.type, "native_enum", False)


@pytest.fixture
async def db_session() -> AsyncGenerator[AsyncSession, None]:
    engine = create_async_engine(TEST_DATABASE_URL, future=True)
    session_factory = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

    _prepare_sqlite_schema()
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    async with session_factory() as session:
        await _seed_test_data(session)
        yield session

    await engine.dispose()


@pytest.fixture
async def client(db_session: AsyncSession) -> AsyncGenerator[AsyncClient, None]:
    async def override_get_db() -> AsyncGenerator[AsyncSession, None]:
        yield db_session

    app.dependency_overrides[get_db] = override_get_db
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        yield ac
    app.dependency_overrides.pop(get_db, None)


@pytest.fixture
def auth_admin():
    _set_auth_user(mock_admin_user)
    yield
    _clear_auth_overrides()


@pytest.fixture
def auth_officer():
    _set_auth_user(mock_officer_user)
    yield
    _clear_auth_overrides()


@pytest.fixture
def auth_analyst():
    _set_auth_user(mock_analyst_user)
    yield
    _clear_auth_overrides()


@pytest.fixture
def admin_token_headers(auth_admin):
    return {"Authorization": "Bearer test-admin-token"}


@pytest.fixture
def officer_token_headers(auth_officer):
    return {"Authorization": "Bearer test-officer-token"}


@pytest.fixture
def analyst_token_headers(auth_analyst):
    return {"Authorization": "Bearer test-analyst-token"}


@pytest.fixture
def report_id() -> uuid.UUID:
    return TEST_REPORT_ID


@pytest.fixture
def investigator_id() -> uuid.UUID:
    return TEST_INVESTIGATOR_ID


@pytest.fixture
def new_investigator_id() -> uuid.UUID:
    return TEST_NEW_INVESTIGATOR_ID
