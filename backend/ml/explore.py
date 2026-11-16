"""Step 4: quick data exploration. Prints and writes a markdown summary.

Run: uv run python -m ml.explore --data ml/data/leads_synthetic.csv
"""

import argparse
from pathlib import Path

import pandas as pd

CATEGORICAL = ["event_type", "source"]
NUMERIC = [
    "guest_count",
    "budget_estimate",
    "days_to_event",
    "first_response_minutes",
    "interaction_count",
    "has_email",
]


def load(path: Path) -> pd.DataFrame:
    return pd.read_csv(path)


def summarize(df: pd.DataFrame) -> str:
    rate = df["converted"].mean()
    lines = [
        "# Lead data summary",
        "",
        f"- Rows: {len(df)}",
        f"- Conversion rate: {rate:.1%} ({int(df['converted'].sum())} converted)",
        f"- Missing values: {int(df.isna().sum().sum())}",
        "",
    ]
    for col in CATEGORICAL:
        table = df.groupby(col)["converted"].agg(["count", "mean"]).sort_values("mean")
        lines += [f"## Conversion by {col}", "", "| value | leads | conversion |", "|---|---|---|"]
        lines += [
            f"| {idx} | {row['count']:.0f} | {row['mean']:.1%} |" for idx, row in table.iterrows()
        ]
        lines.append("")
    corr = df[[*NUMERIC, "converted"]].corr(method="spearman")["converted"].drop("converted")
    lines += ["## Spearman correlation with conversion", "", "| feature | corr |", "|---|---|"]
    lines += [f"| {k} | {v:+.2f} |" for k, v in corr.sort_values().items()]
    lines.append("")
    return "\n".join(lines)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--data", type=Path, default=Path("ml/data/leads_synthetic.csv"))
    parser.add_argument("--out", type=Path, default=Path("ml/reports/data_summary.md"))
    args = parser.parse_args()
    report = summarize(load(args.data))
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(report, encoding="utf-8")
    print(report)


if __name__ == "__main__":
    main()
