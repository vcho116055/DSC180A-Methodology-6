"""Stage 3: temporal split, fit, evaluate, write metrics.

Two baselines and two models, on purpose.

  baseline_mean         predict the 2011 average for every day
  baseline_persistence  predict yesterday's count (cnt_lag_1)
  ridge                 standardised linear model on the audited features
  hgb                   gradient-boosted trees on the same features

The mean baseline shows what "the distribution moved" costs. Persistence
is the baseline that actually matters: ridge's features are dominated by
lagged demand, so if it cannot beat "yesterday again" it has learned
nothing worth reporting. The booster is there because it fails, and the
reason it fails is the headline result.

Run: python -m src.train
"""
import json

import numpy as np
import pandas as pd
from sklearn.base import BaseEstimator, RegressorMixin
from sklearn.dummy import DummyRegressor
from sklearn.ensemble import HistGradientBoostingRegressor
from sklearn.linear_model import Ridge
from sklearn.metrics import mean_absolute_error, r2_score
from sklearn.pipeline import make_pipeline
from sklearn.preprocessing import StandardScaler

from src.config import METRICS, PROCESSED, TARGET, TRAIN_END, VALID_END
from src.features import feature_columns


class PersistenceBaseline(BaseEstimator, RegressorMixin):
    """Predict a single lagged column unchanged. Nothing is fit."""

    def __init__(self, column: str = "cnt_lag_1"):
        self.column = column

    def fit(self, X, y=None):
        if self.column not in X.columns:
            raise ValueError(f"persistence baseline needs column {self.column!r}")
        return self

    def predict(self, X):
        return X[self.column].to_numpy(dtype=float)


MODELS = {
    "baseline_mean": DummyRegressor(strategy="mean"),
    "baseline_persistence": PersistenceBaseline("cnt_lag_1"),
    "ridge": make_pipeline(StandardScaler(), Ridge(alpha=1.0)),
    "hgb": HistGradientBoostingRegressor(random_state=0, max_iter=300),
}


class RelativeTarget(BaseEstimator, RegressorMixin):
    """Exercise 4: fit `estimator` on cnt relative to a lagged level column,
    then map predictions back to rides. A tree cannot predict above the
    largest target it saw in 2011; a ratio or difference to recent demand
    stays inside the training range even as the level grows.

      mode="ratio": fit y / X[base],  predict est(X) * X[base]
      mode="diff":  fit y - X[base],  predict est(X) + X[base]
    """

    def __init__(self, estimator, base: str = "cnt_roll_28", mode: str = "ratio"):
        self.estimator = estimator
        self.base = base
        self.mode = mode

    def _to_rel(self, X, y):
        b = X[self.base].to_numpy(dtype=float)
        return y / b if self.mode == "ratio" else y - b

    def fit(self, X, y):
        from sklearn.base import clone
        self.est_ = clone(self.estimator).fit(X, self._to_rel(X, np.asarray(y, dtype=float)))
        return self

    def predict(self, X):
        b = X[self.base].to_numpy(dtype=float)
        p = self.est_.predict(X)
        return p * b if self.mode == "ratio" else p + b


def transformed_models(mode: str, base: str) -> dict:
    return {
        f"{name}_{mode}_{base}": RelativeTarget(MODELS[name], base=base, mode=mode)
        for name in ("ridge", "hgb")
    }


def temporal_split(df: pd.DataFrame):
    """Split by date, never at random. A random split on a time series
    puts tomorrow in train and today in test."""
    train = df[df.dteday <= TRAIN_END]
    valid = df[(df.dteday > TRAIN_END) & (df.dteday <= VALID_END)]
    test = df[df.dteday > VALID_END]
    return train, valid, test


def fit_and_score(models: dict | None = None, use_test: bool = True) -> dict:
    df = pd.read_parquet(PROCESSED)
    cols = feature_columns(df)
    train, valid, test = temporal_split(df)

    results = {
        "n_features": len(cols),
        "features": cols,
        "n_train": len(train),
        "n_valid": len(valid),
        "n_test": len(test),
    }
    splits = [("valid", valid)] + ([("test", test)] if use_test else [])
    for name, model in (models or MODELS).items():
        model.fit(train[cols], train[TARGET])
        results[name] = {
            split: {
                "r2": round(float(r2_score(part[TARGET], model.predict(part[cols]))), 4),
                "mae": round(float(mean_absolute_error(part[TARGET], model.predict(part[cols]))), 1),
            }
            for split, part in splits
        }
    return results


if __name__ == "__main__":
    import argparse

    ap = argparse.ArgumentParser()
    ap.add_argument("--target-transform", choices=["ratio", "diff"],
                    help="Exercise 4 only. Writes reports/metrics_<mode>_<base>.json, "
                         "never reports/metrics.json. Validation only unless --final.")
    ap.add_argument("--base", default="cnt_roll_28", help="lagged level column")
    ap.add_argument("--final", action="store_true",
                    help="also score the test set. Run once, after choosing.")
    args = ap.parse_args()

    if args.target_transform:
        res = fit_and_score(transformed_models(args.target_transform, args.base),
                            use_test=args.final)
        out = METRICS.with_name(f"metrics_{args.target_transform}_{args.base}.json")
    else:
        res = fit_and_score()
        out = METRICS
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(res, indent=2))
    print(json.dumps({k: v for k, v in res.items() if k != "features"}, indent=2))
