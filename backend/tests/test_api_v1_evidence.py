from unittest.mock import patch

import pytest
from httpx import AsyncClient

FAKE_FILE_CONTENT = b"fake image content"


@pytest.fixture
def mock_storage():
    with patch(
        "app.services.evidence_service.storage_service.upload_file",
        return_value="66666666-6666-4666-8666-666666666666/test.jpg",
    ) as upload_mock, patch(
        "app.services.evidence_service.storage_service.generate_signed_url",
        return_value="https://fake-signed-url.com",
    ) as signed_mock:
        yield {"upload": upload_mock, "signed": signed_mock}


@pytest.mark.asyncio
async def test_upload_evidence_success(
    client: AsyncClient, admin_token_headers, mock_storage, report_id
):
    """Test successful upload by an authorized user."""
    files = {"file": ("test.jpg", FAKE_FILE_CONTENT, "image/jpeg")}
    data = {"report_id": str(report_id), "description": "Test evidence"}

    response = await client.post(
        "/api/v1/evidence/upload",
        files=files,
        data=data,
        headers=admin_token_headers,
    )

    assert response.status_code == 200
    res_data = response.json()
    assert res_data["file_name"] == "test.jpg"
    assert res_data["mime_type"] == "image/jpeg"
    assert res_data["file_extension"] == "jpg"
    assert "checksum" in res_data

    mock_storage["upload"].assert_called_once()


@pytest.mark.asyncio
async def test_upload_evidence_invalid_mime(
    client: AsyncClient, admin_token_headers, report_id
):
    """Test validation rejection for unknown/invalid MIME types."""
    files = {"file": ("test.exe", b"executable bytes", "application/x-msdownload")}
    data = {"report_id": str(report_id)}

    response = await client.post(
        "/api/v1/evidence/upload", files=files, data=data, headers=admin_token_headers
    )
    assert response.status_code == 415


@pytest.mark.asyncio
async def test_upload_evidence_archive_rejected(
    client: AsyncClient, admin_token_headers, report_id
):
    """Test strict rejection of archives."""
    files = {"file": ("archive.zip", b"zip bytes", "application/zip")}
    data = {"report_id": str(report_id)}

    response = await client.post(
        "/api/v1/evidence/upload", files=files, data=data, headers=admin_token_headers
    )
    assert response.status_code in [400, 415]


@pytest.mark.asyncio
async def test_unauthenticated_cannot_upload(
    client: AsyncClient, report_id
):
    """Test unauthenticated upload is rejected."""
    files = {"file": ("test.jpg", b"data", "image/jpeg")}
    data = {"report_id": str(report_id)}

    response = await client.post(
        "/api/v1/evidence/upload", files=files, data=data
    )
    assert response.status_code in [401, 403]


@pytest.mark.asyncio
async def test_download_signed_url(
    client: AsyncClient, admin_token_headers, mock_storage, report_id
):
    """Test generation of a secure signed URL."""
    files = {"file": ("test.jpg", FAKE_FILE_CONTENT, "image/jpeg")}
    data = {"report_id": str(report_id), "description": "Test evidence"}

    upload_res = await client.post(
        "/api/v1/evidence/upload",
        files=files,
        data=data,
        headers=admin_token_headers,
    )

    assert upload_res.status_code == 200
    evidence_id = upload_res.json()["id"]

    response = await client.get(
        f"/api/v1/evidence/{evidence_id}/download",
        headers=admin_token_headers,
    )
    assert response.status_code == 200
    assert "download_url" in response.json()
    assert response.json()["download_url"] == "https://fake-signed-url.com"
