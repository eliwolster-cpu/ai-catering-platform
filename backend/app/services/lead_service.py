from typing import Protocol
from uuid import UUID

from app.schemas.lead import Lead, LeadCreate, LeadStatus, LeadUpdate


class LeadRepository(Protocol):
    def add(self, data: LeadCreate) -> Lead: ...
    def get(self, lead_id: UUID) -> Lead | None: ...
    def list(self, status: LeadStatus | None = None, sort: str = "created") -> list[Lead]: ...
    def update(self, lead_id: UUID, changes: LeadUpdate) -> Lead | None: ...


def create_lead(repo: LeadRepository, data: LeadCreate) -> Lead:
    return repo.add(data)


def list_leads(
    repo: LeadRepository, status: LeadStatus | None = None, sort: str = "created"
) -> list[Lead]:
    return repo.list(status, sort)


def get_lead(repo: LeadRepository, lead_id: UUID) -> Lead | None:
    return repo.get(lead_id)


def update_lead(repo: LeadRepository, lead_id: UUID, changes: LeadUpdate) -> Lead | None:
    return repo.update(lead_id, changes)
