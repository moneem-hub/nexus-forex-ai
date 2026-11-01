"""Run with:  python test_agent_scoring.py    (from the project root; uses your own data files)"""
import glob

import numpy as np
import pandas as pd

from agent.scoring import score_signal
from collect_setups import load_ohlc, setup_features
from train_setup_model import FEATURES, add_direction_features, load_setups, models

RAW_5M = sorted(glob.glob("data/raw/eurusd-m5-*.csv"))
SETUPS_5M = "data/setups_5m.csv"


def _window(bars, t):
    return bars[(bars.index >= t - pd.Timedelta(days=7)) & (bars.index <= t)]


def test_feature_parity_with_training_data():
    """Features recomputed from raw bars (as the live agent will) must equal the ones stored in the training CSV."""
    bars = load_ohlc(RAW_5M[0])
    s = pd.read_csv(SETUPS_5M, parse_dates=["time"])
    s = s[s.pair == "EURUSD"].head(15)
    for _, r in s.iterrows():
        f = setup_features(_window(bars, r.time), r.direction, r.entry, r.sl, 5)
        for k in ("risk_pct", "atr_pct", "risk_atr", "ret_4h", "ret_12h", "ret_24h", "dist_sma_24h", "asian_pos", "asian_range_pct"):
            assert np.isclose(f[k], r[k], equal_nan=True), (r.time, k, f[k], r[k])


def test_score_output_shape():
    df = load_setups("data/setups*.csv")
    m = models()["Logistic Regression"]().fit(df[FEATURES], df.y)
    bundle = {"model": m, "features": FEATURES, "meta": {"score_median": float(np.median(m.predict_proba(df[FEATURES])[:, 1]))}}
    bars = load_ohlc(RAW_5M[0])
    r = pd.read_csv(SETUPS_5M, parse_dates=["time"]).query("pair == 'EURUSD'").iloc[0]
    out = score_signal(bundle, _window(bars, r.time), {"direction": r.direction, "entry": r.entry, "sl": r.sl}, 5)
    assert 0 <= out["p_win"] <= 1 and out["quality"] in ("higher", "lower") and 1 <= len(out["factors"]) <= 3
    print("   example:", out["p_win"], out["quality"], out["factors"])


def test_direction_symmetry():
    """Self-contained: when trend-with-the-trade matters, the same upward move must HELP a BUY and HURT a SELL."""
    rng = np.random.default_rng(0)
    n = 600
    raw = pd.DataFrame({"tf_min": 15, "is_ny": rng.integers(0, 2, n), "hour": 9, "dow": 2, "risk_pct": .002, "atr_pct": .001,
                        "risk_atr": 1.5, "asian_range_pct": .003, "asian_pos": rng.uniform(0, 1, n),
                        "ret_4h": rng.normal(0, .003, n), "ret_12h": rng.normal(0, .004, n), "ret_24h": rng.normal(0, .005, n),
                        "dist_sma_24h": rng.normal(0, .002, n), "is_buy": rng.integers(0, 2, n)})
    d = add_direction_features(raw)
    y = (rng.uniform(size=n) < 1 / (1 + np.exp(-(-0.5 + 300 * d.ret_12h_dir)))).astype(int)
    model = models()["Logistic Regression"]().fit(d[FEATURES], y)
    base = {**raw.iloc[0].to_dict(), "ret_12h": 0.006}
    p = {k: model.predict_proba(add_direction_features(pd.DataFrame([{**base, "is_buy": v}]))[FEATURES])[:, 1][0]
         for k, v in (("BUY", 1), ("SELL", 0))}
    assert p["BUY"] > p["SELL"], p


if __name__ == "__main__":
    if not RAW_5M:
        raise SystemExit("Put eurusd-m5-*.csv in data/raw first.")
    for name, fn in list(globals().items()):
        if name.startswith("test_"):
            fn()
            print("PASS", name)
