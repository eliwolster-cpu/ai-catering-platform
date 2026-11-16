"""Leads in Supabase via PostgREST, using the server-side service-role key.

The key bypasses RLS, so it must never leave the backend. ids and enum values are
typed (UUID / StrEnum) before they reach a URL, so nothing user-supplied is interpolated raw.
"""

from datetime import UTC, datetime
from uuid import UUID

import httpx

from app.schemas.lead import Lead, LeadCreate, LeadStatus, LeadUpdate

TABLE = "leads"


class SupabaseLeadRepository:
    def __init__(self, url: str, service_role_key: str, client: httpx.Client | None = None):
        self._client = client or httpx.Client(timeout=10)
        self._endpoint = f"{url.rstrip('/')}/rest/v1/{TABLE}"
        self._headers = {
            "apikey": service_role_key,
            "Authorization": f"Bearer {service_role_key}",
            "Content-Type": "application/json",
        }

    def _request(self, method: str, params: dict | None = None, json: dict | None = None):
        headers = {**self._headers, "Prefer": "return=representation"}
        response = self._client.request(
            method, self._endpoint, params=params, json=json, headers=headers
        )
        response.raise_for_status()
        return response.json()

    def add(self, data: LeadCreate) -> Lead:
        rows = self._request("POST", json=data.model_dump(mode="json"))
        return Lead.model_validate(rows[0])

    def get(self, lead_id: UUID) -> Lead | None:
        rows = self._request("GET", params={"select": "*", "id": f"eq.{lead_id}"})
        return Lead.model_validate(rows[0]) if rows else None

    def list(self, status: LeadStatus | None = None, sort: str = "created") -> list[Lead]:
        params = {
            "select": "*",
            "order": "conversion_score.desc.nullslast" if sort == "score" else "created_at.desc",
        }
        if status is not None:
            params["status"] = f"eq.{status.value}"
        return [Lead.model_validate(row) for row in self._request("GET", params=params)]

    def update(self, lead_id: UUID, changes: LeadUpdate) -> Lead | None:
        now = datetime.now(UTC).isoformat()
        fields = changes.model_dump(mode="json", exclude_unset=True)
        if fields.get("conversion_score") is not None:
            fields["scored_at"] = now
        rows = self._request(
            "PATCH", params={"id": f"eq.{lead_id}"}, json={**fields, "updated_at": now}
        )
        return Lead.model_validate(rows[0]) if rows else None
