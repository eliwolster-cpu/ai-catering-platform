import pytest
from pydantic import ValidationError

from app.schemas.lead import EventType, LeadCreate, LeadSource, LeadStatus, LeadUpdate

VALID = {
    "name": "דנה כהן",
    "phone": "050-1234567",
    "event_type": "wedding",
    "source": "referral",
}


def test_create_minimal_lead():
    lead = LeadCreate(**VALID)
    assert lead.event_type is EventType.WEDDING
    assert lead.source is LeadSource.REFERRAL
    assert lead.email is None


@pytest.mark.parametrize(
    "override",
    [
        {"phone": "abc"},
        {"name": ""},
        {"guest_count": 0},
        {"guest_count": 99999},
        {"budget_estimate": -1},
        {"event_type": "party"},
        {"source": "unknown"},
        {"email": "not-an-email"},
        {"status": "won"},  # status is not settable on create
    ],
)
def test_create_rejects_invalid_values(override):
    with pytest.raises(ValidationError):
        LeadCreate(**{**VALID, **override})


def test_update_accepts_status_and_rejects_unknown_fields():
    assert LeadUpdate(status="contacted").status is LeadStatus.CONTACTED
    with pytest.raises(ValidationError):
        LeadUpdate(name="x")
