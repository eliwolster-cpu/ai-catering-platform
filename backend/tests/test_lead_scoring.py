import pandas as pd
import pytest
from fastapi.testclient import TestClient

from app.api.leads import get_lead_repository
from app.core.config import get_settings
from app.main import app
from app.repositories.lead_repository import InMemoryLeadRepository
from ml.score import lead_to_features, score_leads
from ml.synthetic import generate
from ml.train import FEATURES, train_and_evaluate

AUTH = {"X-Admin-Key": "k"}
BASE = {
    "name": "x",
    "phone": "050-1234567",
    "event_type": "wedding",
    "source": "returning",
}


def api_lead(**over):
    return {
        "id": "a",
        "event_type": "wedding",
        "source": "returning",
        "created_at": "2026-11-01T10:00:00+00:00",
        "interaction_count": 0,
        **over,
    }


def test_features_use_defaults_for_missing_fields():
    f = lead_to_features(api_lead())
    assert f["days_to_event"] == 60
    assert f["guest_count"] == 80
    assert f["budget_estimate"] == 80 * 190
    assert f["first_response_minutes"] == 1440
    assert f["has_email"] == 0


def test_features_compute_days_and_clamp_past_events():
    assert lead_to_features(api_lead(event_date="2026-12-01"))["days_to_event"] == 30
    assert lead_to_features(api_lead(event_date="2026-10-01"))["days_to_event"] == 0
    assert lead_to_features(api_lead(email="a@b.co"))["has_email"] == 1


def test_good_lead_scores_higher_than_poor_lead():
    _, models = train_and_evaluate(pd.DataFrame(generate(3000, seed=3)), seed=3)
    bundle = {"model": models["logistic_regression"], "features": FEATURES}
    good = api_lead(id="good", first_response_minutes=5, interaction_count=6, email="a@b.co")
    poor = api_lead(id="poor", source="ads", event_type="other", first_response_minutes=3000)
    scores = score_leads(bundle, [good, poor])
    assert all(0 <= s <= 1 for s in scores.values())
    assert scores["good"] > scores["poor"]
    assert score_leads(bundle, []) == {}


@pytest.fixture
def client(monkeypatch):
    monkeypatch.setenv("ADMIN_API_KEY", "k")
    get_settings.cache_clear()
    repo = InMemoryLeadRepository()
    app.dependency_overrides[get_lead_repository] = lambda: repo
    yield TestClient(app)
    app.dependency_overrides.clear()
    get_settings.cache_clear()


def test_score_is_stored_validated_and_sorts_list(client):
    ids = [client.post("/api/leads", json={**BASE, "name": n}).json()["id"] for n in "abc"]
    client.patch(f"/api/admin/leads/{ids[0]}", headers=AUTH, json={"conversion_score": 0.2})
    patched = client.patch(
        f"/api/admin/leads/{ids[1]}", headers=AUTH, json={"conversion_score": 0.9}
    )
    assert patched.json()["scored_at"] is not None

    ranked = client.get("/api/admin/leads?sort=score", headers=AUTH).json()
    assert [lead["id"] for lead in ranked[:2]] == [ids[1], ids[0]]
    assert ranked[2]["conversion_score"] is None  # unscored last

    bad = client.patch(f"/api/admin/leads/{ids[2]}", headers=AUTH, json={"conversion_score": 1.5})
    assert bad.status_code == 422
    assert client.get("/api/admin/leads?sort=nope", headers=AUTH).status_code == 422


def test_public_intake_cannot_set_score(client):
    response = client.post("/api/leads", json={**BASE, "conversion_score": 0.99})
    assert response.status_code == 422
