import json
from datetime import UTC, datetime
from uuid import uuid4

import httpx
import pytest
from fastapi import HTTPException

from app.api.leads import get_lead_repository
from app.core.config import get_settings
from app.repositories.lead_repository import InMemoryLeadRepository
from app.repositories.supabase_lead_repository import SupabaseLeadRepository
from app.schemas.lead import LeadCreate, LeadStatus, LeadUpdate

URL = "https://example.supabase.co"
KEY = "service-key"
NOW = datetime.now(UTC).isoformat()


def row(**over):
    return {
        "id": str(uuid4()),
        "name": "דנה",
        "phone": "050-1234567",
        "email": None,
        "event_type": "wedding",
        "event_date": None,
        "guest_count": None,
        "budget_estimate": None,
        "source": "website",
        "status": "new",
        "first_response_minutes": None,
        "interaction_count": 0,
        "conversion_score": None,
        "scored_at": None,
        "created_at": NOW,
        "updated_at": NOW,
        **over,
    }


def make(handler):
    client = httpx.Client(transport=httpx.MockTransport(handler))
    return SupabaseLeadRepository(URL, KEY, client)


def test_add_posts_json_with_service_key_and_parses_row():
    seen = {}

    def handler(request: httpx.Request):
        seen["req"] = request
        return httpx.Response(201, json=[row()])

    lead = make(handler).add(
        LeadCreate(name="דנה", phone="050-1234567", event_type="wedding", source="website")
    )
    req = seen["req"]
    assert req.method == "POST"
    assert str(req.url) == f"{URL}/rest/v1/leads"
    assert req.headers["apikey"] == KEY
    assert req.headers["authorization"] == f"Bearer {KEY}"
    assert json.loads(req.content)["event_type"] == "wedding"
    assert lead.status is LeadStatus.NEW


def test_get_filters_by_id_and_returns_none_when_missing():
    lead_id = uuid4()
    seen = {}

    def handler(request):
        seen["url"] = request.url
        return httpx.Response(200, json=[])

    assert make(handler).get(lead_id) is None
    assert seen["url"].params["id"] == f"eq.{lead_id}"


@pytest.mark.parametrize(
    ("sort", "order"),
    [("score", "conversion_score.desc.nullslast"), ("created", "created_at.desc")],
)
def test_list_orders_and_filters_by_status(sort, order):
    seen = {}

    def handler(request):
        seen["params"] = request.url.params
        return httpx.Response(200, json=[row(), row()])

    leads = make(handler).list(LeadStatus.WON, sort)
    assert len(leads) == 2
    assert seen["params"]["order"] == order
    assert seen["params"]["status"] == "eq.won"


def test_update_sets_scored_at_only_with_a_score():
    bodies = []

    def handler(request):
        bodies.append(json.loads(request.content))
        return httpx.Response(200, json=[row(conversion_score=0.7, scored_at=NOW)])

    repo = make(handler)
    lead = repo.update(uuid4(), LeadUpdate(conversion_score=0.7))
    assert lead.conversion_score == 0.7
    assert "scored_at" in bodies[0]
    repo.update(uuid4(), LeadUpdate(status=LeadStatus.CONTACTED))
    assert bodies[1]["status"] == "contacted"
    assert "scored_at" not in bodies[1]
    assert "conversion_score" not in bodies[1]


def test_update_unknown_lead_returns_none_and_server_errors_propagate():
    assert make(lambda r: httpx.Response(200, json=[])).update(uuid4(), LeadUpdate()) is None
    with pytest.raises(httpx.HTTPStatusError):
        make(lambda r: httpx.Response(500, json={})).list()


def test_repository_selection_follows_settings(monkeypatch):
    for name in ("SUPABASE_URL", "SUPABASE_SERVICE_ROLE_KEY", "APP_ENV"):
        monkeypatch.delenv(name, raising=False)

    def pick():
        get_settings.cache_clear()
        get_lead_repository.cache_clear()
        return get_lead_repository()

    try:
        assert isinstance(pick(), InMemoryLeadRepository)

        monkeypatch.setenv("SUPABASE_URL", URL)
        monkeypatch.setenv("SUPABASE_SERVICE_ROLE_KEY", KEY)
        assert isinstance(pick(), SupabaseLeadRepository)

        monkeypatch.delenv("SUPABASE_URL")
        monkeypatch.setenv("APP_ENV", "production")
        with pytest.raises(HTTPException) as exc:
            pick()
        assert exc.value.status_code == 503
    finally:
        monkeypatch.undo()
        get_settings.cache_clear()
        get_lead_repository.cache_clear()
