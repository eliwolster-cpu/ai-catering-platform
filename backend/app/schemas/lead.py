"""Lead DTOs. Enum values mirror the CHECK constraints in the leads migration."""

from datetime import date, datetime
from enum import StrEnum
from uuid import UUID

from pydantic import BaseModel, ConfigDict, EmailStr, Field


class LeadStatus(StrEnum):
    NEW = "new"
    CONTACTED = "contacted"
    QUOTE_SENT = "quote_sent"
    WON = "won"
    LOST = "lost"


class LeadSource(StrEnum):
    REFERRAL = "referral"
    WEBSITE = "website"
    SOCIAL = "social"
    PHONE = "phone"
    ADS = "ads"
    RETURNING = "returning"


class EventType(StrEnum):
    WEDDING = "wedding"
    CORPORATE = "corporate"
    BIRTHDAY = "birthday"
    BAR_MITZVAH = "bar_mitzvah"
    PRIVATE = "private"
    OTHER = "other"


class LeadCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    name: str = Field(min_length=1, max_length=120)
    phone: str = Field(pattern=r"^\+?[0-9\-\s]{7,20}$")
    email: EmailStr | None = None
    event_type: EventType
    event_date: date | None = None
    guest_count: int | None = Field(default=None, ge=1, le=5000)
    budget_estimate: int | None = Field(default=None, ge=0, le=10_000_000)
    source: LeadSource


class LeadUpdate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    status: LeadStatus | None = None
    first_response_minutes: int | None = Field(default=None, ge=0)
    interaction_count: int | None = Field(default=None, ge=0)


class Lead(LeadCreate):
    id: UUID
    status: LeadStatus = LeadStatus.NEW
    first_response_minutes: int | None = None
    interaction_count: int = 0
    created_at: datetime
    updated_at: datetime
