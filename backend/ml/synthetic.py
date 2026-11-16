"""Synthetic lead generator for the conversion-prediction model.

Offline tooling, not imported by the API. All data is fake: names and contact
details are never generated, only the features the model needs. The conversion
label comes from a hand-written logistic rule plus noise, so a model trained on
it can recover known relationships (useful for validating the pipeline), but its
scores say nothing about real customers.

Run: uv run python -m ml.synthetic --n 3000 --seed 42
"""

import argparse
import csv
from pathlib import Path

import numpy as np

EVENT_TYPES = ["wedding", "corporate", "birthday", "bar_mitzvah", "private", "other"]
SOURCES = ["referral", "website", "social", "phone", "ads", "returning"]

# Log-odds contribution per category (hand-picked, documented assumptions).
EVENT_EFFECT = {
    "wedding": 0.4,
    "corporate": 0.5,
    "birthday": 0.0,
    "bar_mitzvah": 0.3,
    "private": -0.1,
    "other": -0.5,
}
SOURCE_EFFECT = {
    "returning": 1.4,
    "referral": 0.9,
    "phone": 0.4,
    "website": 0.0,
    "social": -0.3,
    "ads": -0.6,
}
SOURCE_PROBS = [0.18, 0.12, 0.10, 0.28, 0.14, 0.18]

FIELDS = [
    "event_type",
    "source",
    "guest_count",
    "budget_estimate",
    "days_to_event",
    "first_response_minutes",
    "interaction_count",
    "has_email",
    "converted",
]


def generate(n: int, seed: int = 42) -> list[dict]:
    rng = np.random.default_rng(seed)

    event_type = rng.choice(EVENT_TYPES, size=n, p=[0.22, 0.15, 0.2, 0.13, 0.2, 0.1])
    source = rng.choice(SOURCES, size=n, p=SOURCE_PROBS)
    guests = np.clip(rng.lognormal(mean=4.2, sigma=0.7, size=n), 5, 1500).astype(int)
    per_guest = rng.normal(190, 60, size=n).clip(60, 600)
    budget = (guests * per_guest).round(-2).astype(int)
    days_to_event = np.clip(rng.gamma(shape=2.2, scale=35, size=n), 2, 540).astype(int)
    first_response = np.clip(rng.lognormal(mean=4.0, sigma=1.3, size=n), 1, 4320).astype(int)
    interactions = rng.poisson(lam=2.5, size=n)
    has_email = rng.random(n) < 0.75

    logit = (
        -1.9
        + np.array([EVENT_EFFECT[e] for e in event_type])
        + np.array([SOURCE_EFFECT[s] for s in source])
        - 0.6 * np.log1p(first_response / 60)  # slow answers lose leads
        + 0.35 * np.minimum(interactions, 8)  # engagement helps, with diminishing returns
        + 0.5 * has_email
        - 0.9 * (days_to_event < 10)  # too short notice
        - 0.4 * (days_to_event > 300)  # too far ahead, likely just browsing
        + 0.3 * np.log(budget / (guests * 190))  # budget fit per guest
        + rng.normal(0, 0.6, size=n)  # unexplained noise
    )
    converted = rng.random(n) < 1 / (1 + np.exp(-logit))

    return [
        {
            "event_type": str(event_type[i]),
            "source": str(source[i]),
            "guest_count": int(guests[i]),
            "budget_estimate": int(budget[i]),
            "days_to_event": int(days_to_event[i]),
            "first_response_minutes": int(first_response[i]),
            "interaction_count": int(interactions[i]),
            "has_email": int(has_email[i]),
            "converted": int(converted[i]),
        }
        for i in range(n)
    ]


def write_csv(rows: list[dict], path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=FIELDS)
        writer.writeheader()
        writer.writerows(rows)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--n", type=int, default=3000)
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument("--out", type=Path, default=Path("ml/data/leads_synthetic.csv"))
    args = parser.parse_args()
    rows = generate(args.n, args.seed)
    write_csv(rows, args.out)
    rate = sum(r["converted"] for r in rows) / len(rows)
    print(f"wrote {len(rows)} rows to {args.out} (conversion rate {rate:.1%})")  # noqa: T201


if __name__ == "__main__":
    main()
