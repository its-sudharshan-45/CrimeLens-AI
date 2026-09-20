import uuid
from datetime import datetime, timezone, timedelta
import pytest
from httpx import AsyncClient

from app.api.dependencies import get_current_active_user
from app.core.enums.crime_status import CrimeStatus
from app.core.enums.priority import Priority
from app.main import app
from tests.conftest import mock_admin_user, mock_officer_user, mock_analyst_user


def override_auth_admin():
    return mock_admin_user

def override_auth_officer():
    return mock_officer_user

def override_auth_analyst():
    return mock_analyst_user

@pytest.fixture
def auth_admin(monkeypatch):
    app.dependency_overrides[get_current_active_user] = override_auth_admin
    yield
    app.dependency_overrides.pop(get_current_active_user, None)

@pytest.fixture
def auth_officer(monkeypatch):
    app.dependency_overrides[get_current_active_user] = override_auth_officer
    yield
    app.dependency_overrides.pop(get_current_active_user, None)

@pytest.fixture
def auth_analyst(monkeypatch):
    app.dependency_overrides[get_current_active_user] = override_auth_analyst
    yield
    app.dependency_overrides.pop(get_current_active_user, None)


# ---------------------------------------------------------------------------
# Crime Categories
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_create_category_admin(client: AsyncClient, auth_admin):
    payload = {
        "name": f"Theft-{uuid.uuid4().hex[:6]}",
        "severity_level": 3,
        "color_code": "#FF5733"
    }
    response = await client.post("/api/v1/crime-categories", json=payload)
    assert response.status_code == 201
    data = response.json()
    assert data["name"] == payload["name"]
    assert data["severity_level"] == 3

@pytest.mark.asyncio
async def test_create_category_unauthenticated(client: AsyncClient):
    payload = {"name": "Homicide", "severity_level": 10}
    response = await client.post("/api/v1/crime-categories", json=payload)
    assert response.status_code in [401, 403]

@pytest.mark.asyncio
async def test_list_categories(client: AsyncClient, auth_analyst):
    response = await client.get("/api/v1/crime-categories")
    assert response.status_code == 200
    data = response.json()
    assert "items" in data
    assert "total" in data

# ---------------------------------------------------------------------------
# Crime Locations
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_create_location_officer(client: AsyncClient, auth_officer):
    payload = {
        "latitude": 13.08,
        "longitude": 80.27,
        "city": "Chennai",
        "district": "Chennai",
        "state": "Tamil Nadu"
    }
    response = await client.post("/api/v1/crime-locations", json=payload)
    assert response.status_code == 201
    data = response.json()
    assert data["city"] == "Chennai"
    assert data["state"] == "Tamil Nadu"

@pytest.mark.asyncio
async def test_create_location_unauthenticated(client: AsyncClient):
    payload = {
        "latitude": 13.08,
        "longitude": 80.27,
        "city": "Chennai",
        "district": "Chennai",
        "state": "Tamil Nadu"
    }
    response = await client.post("/api/v1/crime-locations", json=payload)
    assert response.status_code in [401, 403]

# ---------------------------------------------------------------------------
# Crime Reports
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_create_report_officer(client: AsyncClient, auth_officer):
    app.dependency_overrides[get_current_active_user] = override_auth_admin
    
    cat_payload = {"name": f"Robbery-{uuid.uuid4().hex[:6]}", "severity_level": 7}
    cat_res = await client.post("/api/v1/crime-categories", json=cat_payload)
    assert cat_res.status_code == 201
    cat_id = cat_res.json()["id"]

    loc_payload = {
        "latitude": 28.7, "longitude": 77.1,
        "city": "Delhi", "district": "New Delhi", "state": "Delhi"
    }
    loc_res = await client.post("/api/v1/crime-locations", json=loc_payload)
    assert loc_res.status_code == 201
    loc_id = loc_res.json()["id"]
    
    app.dependency_overrides[get_current_active_user] = override_auth_officer

    incident_date = (datetime.now(timezone.utc) - timedelta(days=1)).isoformat()
    
    rep_payload = {
        "title": "Bank Robbery",
        "description": "Armed robbery at local bank",
        "incident_date": incident_date,
        "category_id": cat_id,
        "location_id": loc_id,
        "priority": Priority.HIGH.value
    }
    response = await client.post("/api/v1/crime-reports", json=rep_payload)
    assert response.status_code == 201
    data = response.json()
    
    assert data["title"] == "Bank Robbery"
    assert data["status"] == CrimeStatus.OPEN.value
    assert data["reporter_id"] == str(mock_officer_user.id)
    assert data["crime_number"].startswith(f"CR-{datetime.now(timezone.utc).year}-")

    app.dependency_overrides[get_current_active_user] = override_auth_analyst
    patch_response = await client.patch(f"/api/v1/crime-reports/{data['id']}", json={"title": "Updated Title"})
    assert patch_response.status_code == 200
    assert patch_response.json()["title"] == "Updated Title"

    app.dependency_overrides[get_current_active_user] = override_auth_admin
    patch_response = await client.patch(
        f"/api/v1/crime-reports/{data['id']}", 
        json={"status": CrimeStatus.UNDER_INVESTIGATION.value}
    )
    assert patch_response.status_code == 200
    assert patch_response.json()["status"] == CrimeStatus.UNDER_INVESTIGATION.value
