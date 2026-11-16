import pandas as pd
import pytest
from fastapi.testclient import TestClient

from app.api.leads import get_lead_repository
from app.core.config import get_settings
from app.main import app
from app.repositories.lead_repository import InMemoryLeadRepository
from ml.demo_seed import assert_local, seed
from ml.synthetic import generate
from ml.train import FEATURES, train_and_evaluate


@pytest.fixture
def client(monkeypatch):
    monkeypatch.setenv("ADMIN_API_KEY", "k")
    get_settings.cache_clear()
    repo = InMemoryLeadRepository()
    app.dependency_overrides[get_lead_repository] = lambda: repo
    yield TestClient(app, headers={"X-Admin-Key": "k"})
    app.dependency_overrides.clear()
    get_settings.cache_clear()


def test_seed_creates_scored_leads_ranked_by_score(client):
    _, models = train_and_evaluate(pd.DataFrame(generate(2000, seed=5)), seed=5)
    bundle = {"model": models["logistic_regression"], "features": FEATURES}
    ranked = seed(client, bundle, n=15)
    assert len(ranked) == 15
    scores = [lead["conversion_score"] for lead in ranked]
    assert all(s is not None for s in scores)
    assert scores == sorted(scores, reverse=True)


def test_seed_refuses_non_local_servers():
    assert_local("http://127.0.0.1:8000")
    assert_local("http://localhost:8000")
    for url in ("https://yummai.example.com", "https://abc.supabase.co", "http://10.0.0.5:8000"):
        with pytest.raises(SystemExit):
            assert_local(url)
