import secrets
from functools import lru_cache
from typing import Annotated, Literal
from uuid import UUID

from fastapi import APIRouter, Depends, Header, HTTPException, status
from pydantic import BaseModel

from app.core.config import get_settings
from app.repositories.lead_repository import InMemoryLeadRepository
from app.repositories.supabase_lead_repository import SupabaseLeadRepository
from app.schemas.lead import Lead, LeadCreate, LeadStatus, LeadUpdate
from app.services import lead_service
from app.services.lead_service import LeadRepository

router = APIRouter(prefix="/api")


@lru_cache
def get_lead_repository() -> LeadRepository:
    settings = get_settings()
    if settings.supabase_url and settings.supabase_service_role_key:
        return SupabaseLeadRepository(settings.supabase_url, settings.supabase_service_role_key)
    if settings.app_env == "production":
        # Never fall back to memory in production: leads would silently disappear on restart.
        raise HTTPException(status.HTTP_503_SERVICE_UNAVAILABLE, detail="storage not configured")
    return InMemoryLeadRepository()


def require_admin(x_admin_key: Annotated[str | None, Header()] = None) -> None:
    """Owner-only access. Fails closed when no key is configured."""
    expected = get_settings().admin_api_key
    if (
        not expected
        or not x_admin_key
        or not secrets.compare_digest(x_admin_key.encode(), expected.encode())
    ):
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, detail="unauthorized")


Repo = Annotated[LeadRepository, Depends(get_lead_repository)]


class LeadCreated(BaseModel):
    id: UUID


@router.post("/leads", status_code=status.HTTP_201_CREATED)
def create_lead(data: LeadCreate, repo: Repo) -> LeadCreated:
    # Public endpoint: returns only the id, never echoes personal data.
    return LeadCreated(id=lead_service.create_lead(repo, data).id)


admin = APIRouter(prefix="/admin/leads", dependencies=[Depends(require_admin)])


@admin.get("")
def list_leads(
    repo: Repo,
    lead_status: LeadStatus | None = None,
    sort: Literal["created", "score"] = "created",
) -> list[Lead]:
    return lead_service.list_leads(repo, lead_status, sort)


@admin.get("/{lead_id}")
def get_lead(lead_id: UUID, repo: Repo) -> Lead:
    lead = lead_service.get_lead(repo, lead_id)
    if lead is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail="lead not found")
    return lead


@admin.patch("/{lead_id}")
def update_lead(lead_id: UUID, changes: LeadUpdate, repo: Repo) -> Lead:
    lead = lead_service.update_lead(repo, lead_id, changes)
    if lead is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail="lead not found")
    return lead


router.include_router(admin)
