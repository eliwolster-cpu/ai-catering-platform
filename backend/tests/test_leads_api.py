import pytest
from fastapi.testclient import TestClient

from app.api.leads import get_lead_repository
from app.core.config import get_settings
from app.main import app
from app.repositories.lead_repository import InMemoryLeadRepository

KEY = "test-admin-key"
PAYLOAD = {
    "name": "דנה כהן",
    "phone": "050-1234567",
    "email": "dana@example.com",
    "event_type": "wedding",
    "source": "referral",
}
AUTH = {"X-Admin-Key": KEY}
MISSING = "00000000-0000-0000-0000-000000000000"


@pytest.fixture
def client(monkeypatch):
    monkeypatch.setenv("ADMIN_API_KEY", KEY)
    get_settings.cache_clear()
    repo = InMemoryLeadRepository()
    app.dependency_overrides[get_lead_repository] = lambda: repo
    yield TestClient(app)
    app.dependency_overrides.clear()
    get_settings.cache_clear()


def test_public_create_returns_only_id(client):
    response = client.post("/api/leads", json=PAYLOAD)
    assert response.status_code == 201
    assert list(response.json()) == ["id"]


def test_create_rejects_invalid_and_status_injection(client):
    assert client.post("/api/leads", json={**PAYLOAD, "phone": "x"}).status_code == 422
    assert client.post("/api/leads", json={**PAYLOAD, "status": "won"}).status_code == 422


def test_admin_routes_require_key(client):
    assert client.get("/api/admin/leads").status_code == 401
    assert client.get("/api/admin/leads", headers={"X-Admin-Key": "wrong"}).status_code == 401


def test_non_ascii_key_is_401_not_500(client):
    response = client.get("/api/admin/leads", headers={"X-Admin-Key": "é".encode("latin-1")})
    assert response.status_code == 401


def test_admin_routes_fail_closed_when_key_unset(client, monkeypatch):
    monkeypatch.delenv("ADMIN_API_KEY")
    get_settings.cache_clear()
    assert client.get("/api/admin/leads", headers={"X-Admin-Key": ""}).status_code == 401
    assert client.get("/api/admin/leads", headers=AUTH).status_code == 401


def test_list_filter_get_and_update(client):
    lead_id = client.post("/api/leads", json=PAYLOAD).json()["id"]
    client.post("/api/leads", json={**PAYLOAD, "name": "שני"})

    assert len(client.get("/api/admin/leads", headers=AUTH).json()) == 2
    assert client.get("/api/admin/leads?lead_status=won", headers=AUTH).json() == []

    got = client.get(f"/api/admin/leads/{lead_id}", headers=AUTH)
    assert got.status_code == 200
    assert got.json()["status"] == "new"

    patched = client.patch(
        f"/api/admin/leads/{lead_id}", headers=AUTH, json={"status": "contacted"}
    )
    assert patched.status_code == 200
    assert patched.json()["status"] == "contacted"
    assert patched.json()["name"] == "דנה כהן"
    assert len(client.get("/api/admin/leads?lead_status=contacted", headers=AUTH).json()) == 1


def test_unknown_lead_is_404_and_bad_patch_is_422(client):
    assert client.get(f"/api/admin/leads/{MISSING}", headers=AUTH).status_code == 404
    assert client.patch(f"/api/admin/leads/{MISSING}", headers=AUTH, json={}).status_code == 404
    assert (
        client.patch(f"/api/admin/leads/{MISSING}", headers=AUTH, json={"x": 1}).status_code == 422
    )
