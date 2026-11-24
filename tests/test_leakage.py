"""The tests that make the agent honest.

test_no_forbidden_features is the single most valuable test in this repo:
casual + registered == cnt exactly, so any model handed those columns
scores R^2 = 1.0 and looks brilliant while having learned nothing.
"""
import pandas as pd
import pytest

from src.config import FORBIDDEN, TARGET
from src.features import build_features, feature_columns
from src.ingest import load_raw


@pytest.fixture(scope="module")
def feats():
    return build_features(load_raw())


def test_leakage_identity_holds(feats):
    """Documents *why* casual and registered are forbidden."""
    assert (feats.casual + feats.registered == feats[TARGET]).all()


def test_no_forbidden_features(feats):
    """Guards the gate, not the data: feature_columns() excludes FORBIDDEN by
    construction, so this cannot discover a *new* leaky column. What it
    catches is someone editing feature_columns() or FORBIDDEN -- which is
    exactly the fault the Step 7 hook demonstrates."""
    cols = set(feature_columns(feats))
    assert not (cols & FORBIDDEN), f"forbidden columns in feature set: {cols & FORBIDDEN}"


def test_lags_are_true_calendar_lags(feats):
    """cnt_lag_1 for date d must equal cnt on d-1, in calendar days."""
    by_date = feats.set_index("dteday")[TARGET]
    checked = 0
    for date, lag in feats.set_index("dteday").cnt_lag_1.items():
        prev = date - pd.Timedelta(days=1)
        if prev in by_date.index:
            assert lag == pytest.approx(by_date[prev]), f"bad lag at {date.date()}"
            checked += 1
    assert checked > 600, "too few rows actually verified"


def test_lag_is_not_the_target(feats):
    assert not (feats.cnt_lag_1 == feats[TARGET]).all()


def test_rolling_mean_excludes_today(feats):
    """cnt_roll_7 must be the mean of the 7 calendar days *before* today."""
    by_date = feats.set_index("dteday")[TARGET]
    date = feats.dteday.iloc[200]
    window = [date - pd.Timedelta(days=k) for k in range(1, 8)]
    if all(d in by_date.index for d in window):
        expected = sum(by_date[d] for d in window) / 7
        assert feats.set_index("dteday").cnt_roll_7[date] == pytest.approx(expected)


def test_lag_7_is_a_true_seven_day_lag(feats):
    """cnt_lag_7 on d must equal cnt on d-7 in calendar days. Guards against
    cnt_lag_7 being built from LAG_WARMUP: raising LAG_WARMUP for a longer
    feature would otherwise silently turn it into a longer lag."""
    by_date = feats.set_index("dteday")[TARGET]
    checked = 0
    for date, lag in feats.set_index("dteday").cnt_lag_7.items():
        prev = date - pd.Timedelta(days=7)
        if prev in by_date.index:
            assert lag == pytest.approx(by_date[prev]), f"bad 7-day lag at {date.date()}"
            checked += 1
    assert checked > 600, "too few rows actually verified"


def test_roll_28_is_mean_of_28_strictly_earlier_days():
    """cnt_roll_28 on 2011-06-15 must equal the mean of cnt over the 28
    calendar days 2011-05-18 .. 2011-06-14, computed by hand from the raw
    file, never including 2011-06-15 itself."""
    raw = load_raw().set_index("dteday")[TARGET]
    feats = build_features(load_raw()).set_index("dteday")
    day = pd.Timestamp("2011-06-15")
    window = pd.date_range(day - pd.Timedelta(days=28), day - pd.Timedelta(days=1))
    assert len(window) == 28 and window.max() < day
    assert all(d in raw.index for d in window), "window crosses a missing day"
    expected = raw.loc[window].mean()
    assert feats.loc[day, "cnt_roll_28"] == pytest.approx(expected)


def test_no_missing_values(feats):
    assert feats[feature_columns(feats)].isna().sum().sum() == 0


def test_dates_are_sorted_and_unique(feats):
    assert feats.dteday.is_monotonic_increasing
    assert feats.dteday.is_unique
