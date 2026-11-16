import pandas as pd
import pytest

from ml.explore import summarize
from ml.synthetic import generate
from ml.train import FEATURES, add_features, train_and_evaluate


@pytest.fixture(scope="module")
def df():
    return pd.DataFrame(generate(3000, seed=7))


def test_summary_reports_balance_and_groups(df):
    text = summarize(df)
    assert "Conversion rate" in text
    assert "Conversion by source" in text
    assert "first_response_minutes" in text


def test_add_features_derives_columns(df):
    out = add_features(df)
    assert (out["budget_per_guest"] > 0).all()
    assert set(FEATURES) <= set(out.columns)


def test_models_beat_chance_and_baseline(df):
    report, models = train_and_evaluate(df, seed=7)
    assert set(models) == {"logistic_regression", "gradient_boosting"}
    for metrics in report["models"].values():
        assert metrics["auc"] > 0.65
        assert metrics["brier"] < report["baseline_brier"]
    assert report["best"] in models


def test_predictions_are_probabilities_and_ignore_unknown_category(df):
    _, models = train_and_evaluate(df, seed=7)
    row = add_features(df.head(3))[FEATURES].copy()
    row.loc[row.index[0], "source"] = "never_seen"
    proba = models["logistic_regression"].predict_proba(row)[:, 1]
    assert ((proba >= 0) & (proba <= 1)).all()
