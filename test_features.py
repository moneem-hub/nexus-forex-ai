"""Run with:  python test_features.py   (or: pytest)"""
import numpy as np
import pandas as pd
from features import build_features, BASE_FEATURES, RANGE_FEATURES


def _fake_prices(n=400, seed=0, start=1.1):
    rng = np.random.default_rng(seed)
    close = start * np.exp(np.cumsum(rng.normal(0, 0.005, n)))
    high = close * (1 + rng.uniform(0, 0.003, n))
    low = close * (1 - rng.uniform(0, 0.003, n))
    open_ = np.r_[close[0], close[:-1]]
    idx = pd.bdate_range("2020-01-01", periods=n)
    return pd.DataFrame({"Open": open_, "High": high, "Low": low, "Close": close}, index=idx)


def test_no_lookahead():
    """Row t computed from data[:t+1] must equal row t computed from the full data."""
    df = _fake_prices()
    for flag in (False, True):
        full = build_features(df, include_range_features=flag)
        for t in (150, 250, 399):
            part = build_features(df.iloc[: t + 1], include_range_features=flag)
            pd.testing.assert_series_equal(full.iloc[t], part.iloc[t], check_names=False)


def test_columns():
    df = _fake_prices()
    assert list(build_features(df).columns) == BASE_FEATURES
    assert list(build_features(df, True).columns) == BASE_FEATURES + RANGE_FEATURES


def test_scale_free():
    """Multiplying prices by 100 (EURUSD -> USDJPY-like scale) must not change features."""
    df = _fake_prices()
    big = df * 100
    a, b = build_features(df, True).dropna(), build_features(big, True).dropna()
    np.testing.assert_allclose(a.values, b.values, rtol=1e-6, atol=1e-9)


if __name__ == "__main__":
    for name, fn in list(globals().items()):
        if name.startswith("test_"):
            fn()
            print("PASS", name)
