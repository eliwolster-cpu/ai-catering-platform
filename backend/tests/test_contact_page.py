import re

from fastapi.testclient import TestClient

from app.main import app
from app.schemas.lead import EventType

client = TestClient(app)


def test_contact_page_is_hebrew_rtl_with_required_markers():
    html = client.get("/contact/").text
    assert 'lang="he"' in html
    assert 'dir="rtl"' in html
    assert "/js/contact.js" in html
    for field in ("name", "phone", "event_type"):
        assert re.search(rf'id="{field}"[^>]*aria-required="true"', html)
    assert html.count("(חובה)") == 3


def test_event_type_options_match_backend_enum():
    html = client.get("/contact/").text
    select = re.search(r'<select[^>]*id="event_type".*?</select>', html, re.S).group(0)
    values = {v for v in re.findall(r'<option value="([^"]*)"', select) if v}
    assert values == {e.value for e in EventType}


def test_contact_page_does_not_promise_a_booking_or_collect_source():
    html = client.get("/contact/").text
    assert "לא הזמנה" in html  # an inquiry is never presented as a confirmed booking
    assert 'name="source"' not in html  # source is set by the script, not chosen by the visitor


def test_script_sends_website_source_and_never_uses_innerhtml():
    script = client.get("/js/contact.js").text
    assert 'source: "website"' in script
    assert "innerHTML" not in script


def test_landing_links_to_contact_page():
    assert "/contact/" in client.get("/").text
