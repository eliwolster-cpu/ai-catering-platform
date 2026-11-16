import numpy as np

from app.schemas.lead import EventType, LeadSource
from ml.synthetic import EVENT_TYPES, FIELDS, SOURCES, generate, write_csv


def test_vocabularies_match_lead_schema():
    assert set(EVENT_TYPES) == {e.value for e in EventType}
    assert set(SOURCES) == {s.value for s in LeadSource}


def test_same_seed_is_reproducible_and_different_seed_differs():
    assert generate(200, seed=1) == generate(200, seed=1)
    assert generate(200, seed=1) != generate(200, seed=2)


def test_rows_have_valid_ranges():
    rows = generate(1000)
    assert len(rows) == 1000
    for r in rows:
        assert set(r) == set(FIELDS)
        assert 5 <= r["guest_count"] <= 1500
        assert r["budget_estimate"] > 0
        assert 2 <= r["days_to_event"] <= 540
        assert r["first_response_minutes"] >= 1
        assert r["interaction_count"] >= 0
        assert r["has_email"] in (0, 1)
        assert r["converted"] in (0, 1)


def test_conversion_rate_is_plausible_and_signal_is_learnable():
    rows = generate(5000)
    rate = np.mean([r["converted"] for r in rows])
    assert 0.2 < rate < 0.6

    def rate_for(source):
        group = [r["converted"] for r in rows if r["source"] == source]
        return np.mean(group)

    assert rate_for("returning") > rate_for("ads")
    fast = [r["converted"] for r in rows if r["first_response_minutes"] <= 30]
    slow = [r["converted"] for r in rows if r["first_response_minutes"] >= 600]
    assert np.mean(fast) > np.mean(slow)


def test_write_csv_roundtrip(tmp_path):
    out = tmp_path / "nested" / "leads.csv"
    write_csv(generate(50), out)
    lines = out.read_text(encoding="utf-8").splitlines()
    assert lines[0] == ",".join(FIELDS)
    assert len(lines) == 51
