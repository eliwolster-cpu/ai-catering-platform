"""Lead storage. In-memory for now; the Supabase implementation replaces it in Phase 2."""

from datetime import UTC, datetime
from threading import Lock
from uuid import UUID, uuid4

from app.schemas.lead import Lead, LeadCreate, LeadStatus, LeadUpdate


class InMemoryLeadRepository:
    def __init__(self) -> None:
        self._leads: dict[UUID, Lead] = {}
        self._lock = Lock()

    def add(self, data: LeadCreate) -> Lead:
        now = datetime.now(UTC)
        lead = Lead(id=uuid4(), created_at=now, updated_at=now, **data.model_dump())
        with self._lock:
            self._leads[lead.id] = lead
        return lead

    def get(self, lead_id: UUID) -> Lead | None:
        return self._leads.get(lead_id)

    def list(self, status: LeadStatus | None = None, sort: str = "created") -> list[Lead]:
        leads = [lead for lead in self._leads.values() if status in (None, lead.status)]
        if sort == "score":  # highest score first, unscored last
            return sorted(
                leads,
                key=lambda lead: (lead.conversion_score is not None, lead.conversion_score or 0),
                reverse=True,
            )
        return sorted(leads, key=lambda lead: lead.created_at, reverse=True)

    def update(self, lead_id: UUID, changes: LeadUpdate) -> Lead | None:
        with self._lock:
            lead = self._leads.get(lead_id)
            if lead is None:
                return None
            now = datetime.now(UTC)
            fields = changes.model_dump(exclude_unset=True)
            if fields.get("conversion_score") is not None:
                fields["scored_at"] = now
            updated = lead.model_copy(update={**fields, "updated_at": now})
            self._leads[lead_id] = updated
            return updated
