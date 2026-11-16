"""Step 6: offline lead scoring.

Maps leads (the admin API shape) to model features, predicts the probability of
conversion, and writes {lead_id: score}. The API only stores and sorts the score;
the production image does not ship scikit-learn. Scores are advisory and never
feed prices or quotations.

Run: uv run python -m ml.score --leads leads.json --out scores.json
(leads.json is the output of GET /api/admin/leads; only load models made by ml.train.)
"""

import argparse
import json
from datetime import date, datetime
from pathlib import Path

import joblib
import pandas as pd

from ml.train import FEATURES, add_features

# Fallbacks for fields a fresh lead may not have yet (documented assumptions).
DEFAULT_GUESTS = 80
DEFAULT_PER_GUEST = 190
DEFAULT_DAYS_TO_EVENT = 60
DEFAULT_RESPONSE_MINUTES = 1440  # unanswered leads are treated as a day old


def lead_to_features(lead: dict) -> dict:
    created = datetime.fromisoformat(lead["created_at"]).date()
    event_date = lead.get("event_date")
    days = (date.fromisoformat(event_date) - created).days if event_date else DEFAULT_DAYS_TO_EVENT
    guests = lead.get("guest_count") or DEFAULT_GUESTS
    response = lead.get("first_response_minutes")
    return {
        "event_type": lead["event_type"],
        "source": lead["source"],
        "guest_count": guests,
        "budget_estimate": lead.get("budget_estimate") or guests * DEFAULT_PER_GUEST,
        "days_to_event": max(days, 0),
        "first_response_minutes": DEFAULT_RESPONSE_MINUTES if response is None else response,
        "interaction_count": lead.get("interaction_count", 0),
        "has_email": int(bool(lead.get("email"))),
    }


def score_leads(bundle: dict, leads: list[dict]) -> dict[str, float]:
    if not leads:
        return {}
    frame = add_features(pd.DataFrame([lead_to_features(lead) for lead in leads]))
    proba = bundle["model"].predict_proba(frame[bundle["features"]])[:, 1]
    return {lead["id"]: round(float(p), 4) for lead, p in zip(leads, proba, strict=True)}


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--leads", type=Path, required=True)
    parser.add_argument("--out", type=Path, required=True)
    parser.add_argument("--model", type=Path, default=Path("ml/models/lead_model.joblib"))
    args = parser.parse_args()

    bundle = joblib.load(args.model)  # noqa: S301 - trusted file produced by ml.train
    if bundle["features"] != FEATURES:
        raise SystemExit("model was trained with a different feature set; retrain it")
    leads = json.loads(args.leads.read_text(encoding="utf-8"))
    scores = score_leads(bundle, leads)
    args.out.write_text(json.dumps(scores, indent=2), encoding="utf-8")
    print(f"scored {len(scores)} leads -> {args.out}")


if __name__ == "__main__":
    main()
