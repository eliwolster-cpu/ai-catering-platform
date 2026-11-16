from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


def test_admin_page_is_hebrew_rtl_and_loads_lead_board():
    html = client.get("/admin/").text
    assert 'lang="he"' in html
    assert 'dir="rtl"' in html
    assert "/js/admin/leads.js" in html
    assert "/css/admin.css" in html
    assert 'type="password"' in html  # the access key must not be shown on screen
    assert 'aria-live="polite"' in html


def test_admin_assets_are_served():
    for path in ("/js/admin/leads.js", "/css/admin.css", "/js/lib/dom.js"):
        assert client.get(path).status_code == 200


def test_admin_script_never_uses_innerhtml():
    # Lead names and phones come from the public form: they must only reach the DOM as text.
    script = client.get("/js/admin/leads.js").text
    assert "innerHTML" not in script
    assert "insertAdjacentHTML" not in script
