"""Step 5: train and evaluate the lead-conversion model.

Compares a logistic-regression baseline with gradient boosting on a held-out split,
reports AUC / Brier / calibration, and saves the better model (by AUC).

The saved file is a joblib pickle: only ever load files this script produced.

Run: uv run python -m ml.train --data ml/data/leads_synthetic.csv
"""

import argparse
import json
from pathlib import Path

import joblib
import numpy as np
import pandas as pd
from sklearn.calibration import calibration_curve
from sklearn.compose import ColumnTransformer
from sklearn.ensemble import HistGradientBoostingClassifier
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import brier_score_loss, roc_auc_score
from sklearn.model_selection import train_test_split
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import OneHotEncoder, StandardScaler

from ml.explore import CATEGORICAL, NUMERIC

TARGET = "converted"
# Features the scorer needs at prediction time (order matters for the saved model).
FEATURES = [*CATEGORICAL, *NUMERIC, "budget_per_guest", "log_response_minutes"]


def add_features(df: pd.DataFrame) -> pd.DataFrame:
    out = df.copy()
    out["budget_per_guest"] = out["budget_estimate"] / out["guest_count"].clip(lower=1)
    out["log_response_minutes"] = np.log1p(out["first_response_minutes"])
    return out


def _preprocessor(scale: bool) -> ColumnTransformer:
    numeric = [c for c in FEATURES if c not in CATEGORICAL]
    return ColumnTransformer(
        [
            ("cat", OneHotEncoder(handle_unknown="ignore"), CATEGORICAL),
            ("num", StandardScaler() if scale else "passthrough", numeric),
        ]
    )


def build_models(seed: int) -> dict[str, Pipeline]:
    return {
        "logistic_regression": Pipeline(
            [
                ("prep", _preprocessor(scale=True)),
                ("clf", LogisticRegression(max_iter=1000, random_state=seed)),
            ]
        ),
        "gradient_boosting": Pipeline(
            [
                ("prep", _preprocessor(scale=False)),
                ("clf", HistGradientBoostingClassifier(max_depth=4, random_state=seed)),
            ]
        ),
    }


def evaluate(model: Pipeline, x_test: pd.DataFrame, y_test: pd.Series) -> dict:
    proba = model.predict_proba(x_test)[:, 1]
    frac_pos, mean_pred = calibration_curve(y_test, proba, n_bins=5, strategy="quantile")
    return {
        "auc": round(float(roc_auc_score(y_test, proba)), 4),
        "brier": round(float(brier_score_loss(y_test, proba)), 4),
        "calibration_max_gap": round(float(np.max(np.abs(frac_pos - mean_pred))), 4),
    }


def train_and_evaluate(df: pd.DataFrame, seed: int = 42) -> tuple[dict, dict[str, Pipeline]]:
    data = add_features(df)
    x_train, x_test, y_train, y_test = train_test_split(
        data[FEATURES], data[TARGET], test_size=0.25, stratify=data[TARGET], random_state=seed
    )
    models = build_models(seed)
    results = {}
    for name, model in models.items():
        model.fit(x_train, y_train)
        results[name] = evaluate(model, x_test, y_test)
    base_rate = float(y_train.mean())
    report = {
        "rows": len(df),
        "train_rows": len(x_train),
        "test_rows": len(x_test),
        "base_rate": round(base_rate, 4),
        "baseline_brier": round(
            float(brier_score_loss(y_test, np.full(len(y_test), base_rate))), 4
        ),
        "models": results,
        "best": max(results, key=lambda n: results[n]["auc"]),
    }
    return report, models


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--data", type=Path, default=Path("ml/data/leads_synthetic.csv"))
    parser.add_argument("--out-dir", type=Path, default=Path("ml/models"))
    parser.add_argument("--seed", type=int, default=42)
    args = parser.parse_args()

    report, models = train_and_evaluate(pd.read_csv(args.data), args.seed)
    args.out_dir.mkdir(parents=True, exist_ok=True)
    joblib.dump(
        {"model": models[report["best"]], "features": FEATURES}, args.out_dir / "lead_model.joblib"
    )
    (args.out_dir / "metrics.json").write_text(json.dumps(report, indent=2), encoding="utf-8")
    print(json.dumps(report, indent=2))


if __name__ == "__main__":
    main()
