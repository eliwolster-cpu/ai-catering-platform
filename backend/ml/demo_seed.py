"""Fill a LOCAL running server with fake, scored leads for demos.

Creates leads through the public API, sets their activity and status through the admin API,
scores them with the trained model and stores the scores. Refuses non-local URLs so fake
data can never land in a real environment.

Run (server started with ADMIN_API_KEY=demo-key-123):
  uv run python -m ml.demo_seed --key demo-key-123 --n 40
"""

import argparse
import random
from datetime import date, timedelta
from pathlib import Path
from urllib.parse import urlparse

import httpx
import joblib

from ml.score import score_leads
from ml.synthetic import generate

FIRST = ["דנה", "רון", "מיכל", "יוסי", "נועה", "אבי", "שירה", "אורי", "תמר", "גיל", "ליאור", "מאיה"]
LAST = ["כהן", "לוי", "מזרחי", "אברהם", "פרץ", "ביטון", "דהן", "שלום", "אזולאי", "גולן"]
STATUSES = ["new", "new", "new", "contacted", "contacted", "quote_sent", "won", "lost"]
LOCAL_HOSTS = {"127.0.0.1", "localhost", "::1", "testserver"}


def assert_local(url: str) -> None:
    if urlparse(url).hostname not in LOCAL_HOSTS:
        raise SystemExit(f"refusing to seed fake data into non-local server: {url}")


def seed(http: httpx.Client, bundle: dict, n: int = 40, seed_value: int = 11) -> list[dict]:
    """Seed through `http` (admin key already in its headers); returns leads ranked by score."""
    rng = random.Random(seed_value)  # noqa: S311 - fake demo names, not security-sensitive
    for i, row in enumerate(generate(n, seed=seed_value)):
        body = {
            "name": f"{rng.choice(FIRST)} {rng.choice(LAST)}",
            "phone": f"050-{rng.randint(1000000, 9999999)}",
            "event_type": row["event_type"],
            "source": row["source"],
            "guest_count": min(row["guest_count"], 5000),
            "budget_estimate": row["budget_estimate"],
            "event_date": str(date.today() + timedelta(days=row["days_to_event"])),
        }
        if row["has_email"]:
            body["email"] = f"demo{i}@example.com"
        lead_id = http.post("/api/leads", json=body).raise_for_status().json()["id"]
        http.patch(
            f"/api/admin/leads/{lead_id}",
            json={
                "first_response_minutes": row["first_response_minutes"],
                "interaction_count": row["interaction_count"],
                "status": rng.choice(STATUSES),
            },
        ).raise_for_status()

    leads = http.get("/api/admin/leads").raise_for_status().json()
    for lead_id, score in score_leads(bundle, leads).items():
        http.patch(
            f"/api/admin/leads/{lead_id}", json={"conversion_score": score}
        ).raise_for_status()
    return http.get("/api/admin/leads", params={"sort": "score"}).raise_for_status().json()


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--url", default="http://127.0.0.1:8000")
    parser.add_argument("--key", required=True, help="the server's ADMIN_API_KEY")
    parser.add_argument("--n", type=int, default=40)
    parser.add_argument("--model", type=Path, default=Path("ml/models/lead_model.joblib"))
    args = parser.parse_args()
    assert_local(args.url)
    bundle = joblib.load(args.model)  # trusted file produced by ml.train
    with httpx.Client(base_url=args.url, headers={"X-Admin-Key": args.key}, timeout=10) as http:
        ranked = seed(http, bundle, args.n)
    print(f"seeded {len(ranked)} fake leads; open {args.url}/admin/")


if __name__ == "__main__":
    main()
