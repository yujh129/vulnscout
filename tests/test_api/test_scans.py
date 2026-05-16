import pytest
from httpx import AsyncClient, ASGITransport

from vulnscout.main import app
from vulnscout.models.db import init_db


@pytest.fixture(autouse=True)
def setup_db():
    """Initialize database tables before each test."""
    init_db()


@pytest.fixture
def client():
    transport = ASGITransport(app=app)
    return AsyncClient(transport=transport, base_url="http://test")


@pytest.mark.asyncio
async def test_health(client):
    resp = await client.get("/health")
    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "ok"


@pytest.mark.asyncio
async def test_list_scans_empty(client):
    resp = await client.get("/api/v1/scans")
    assert resp.status_code == 200
    assert isinstance(resp.json(), list)
