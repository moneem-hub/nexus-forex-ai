"""Run with:  python test_kronos_pipeline.py     (no model download needed: the Kronos call is replaced by a stand-in)
Checks the parts that decide whether the comparison is TRUSTWORTHY: no future data reaches the model, features are computed
correctly, runs resume, and the comparison finds real information when it exists and none when it does not."""
import glob
import tempfile
from pathlib import Path
import numpy as np
import pandas as pd

from collect_setups import load_ohlc
from compare_pretrained import compare
from kronos_features import HORIZON_HOURS, KR_COLS, LOOKBACK_BARS, forecast_features, run
from train_setup_model import FEATURES, add_direction_features


def _pred(highs, lows, closes):
    return pd.DataFrame({"high": highs, "low": lows, "close": closes})


def test_forecast_features_hit_logic_and_direction():
    buy_tp = forecast_features(_pred([1.001, 1.0021], [0.9995, 1.0], [1.001, 1.002]), 1.0, "BUY", sl=0.999, tp=1.002)
    buy_sl = forecast_features(_pred([1.001, 1.0021], [0.9985, 1.0], [1.0, 1.002]), 1.0, "BUY", sl=0.999, tp=1.002)
    same_bar = forecast_features(_pred([1.0025], [0.9985], [1.0]), 1.0, "BUY", sl=0.999, tp=1.002)       # both inside one bar: conservative = SL
    neither = forecast_features(_pred([1.0005], [0.9995], [1.0]), 1.0, "BUY", sl=0.999, tp=1.002)
    sell_tp = forecast_features(_pred([1.0004, 1.0], [0.9995, 0.9975], [0.999, 0.998]), 1.0, "SELL", sl=1.001, tp=0.998)
    assert (buy_tp["kr_hit"], buy_sl["kr_hit"], same_bar["kr_hit"], neither["kr_hit"], sell_tp["kr_hit"]) == (1, -1, -1, 0, 1)
    assert buy_tp["kr_ret_dir"] > 0 and sell_tp["kr_ret_dir"] > 0                # a falling forecast is 'with the trade' for a SELL
    assert "eval_real_ret_dir" not in KR_COLS and not any(c.startswith("eval") for c in KR_COLS)


class StandIn:
    """Pretends to be Kronos, and checks that nothing from the future is ever handed to it."""
    def __init__(self, signal_times): self.calls, self.times = 0, signal_times
    def predict_batch(self, df_list, x_timestamp_list, y_timestamp_list, pred_len, **kw):
        self.calls += 1
        out = []
        for df, x_ts, y_ts in zip(df_list, x_timestamp_list, y_timestamp_list):
            assert len(df) == LOOKBACK_BARS and len(x_ts) == LOOKBACK_BARS and len(y_ts) == pred_len
            assert x_ts.iloc[-1] < y_ts.iloc[0], "forecast window must start AFTER the last bar the model saw"
            assert x_ts.is_monotonic_increasing
            last = df["close"].iloc[-1]
            out.append(pd.DataFrame({"open": last, "high": last * 1.0005, "low": last * 0.9995, "close": last * 1.0002}, index=y_ts))
        return out


def test_run_gives_the_model_only_the_past_and_resumes_cleanly():
    raw = sorted(glob.glob("data/raw/eurusd-m5-*.csv"))[0]
    bars = load_ohlc(raw)
    setups = pd.read_csv("data/setups_5m.csv", parse_dates=["time"])
    setups = setups[(setups.pair == "EURUSD") & setups.outcome.isin(["PROFIT", "LOSS"])].assign(tf_min=5)
    with tempfile.TemporaryDirectory() as d:
        out = Path(d) / "kr.csv"
        model = StandIn(setups.time)
        n = run(model, setups, {("EURUSD", 5): bars}, out, batch=4, log=lambda *_: None)
        df = pd.read_csv(out, parse_dates=["time"])
        enough = [t for t in setups.time if len(bars.loc[:t]) >= LOOKBACK_BARS]
        assert n == len(df) == len(enough) > 0
        assert not df[KR_COLS].isna().any().any() and set(df.kr_hit) <= {-1, 0, 1}
        assert run(model, setups, {("EURUSD", 5): bars}, out, batch=4, log=lambda *_: None) == 0      # second run: nothing left to do
        assert len(pd.read_csv(out)) == n
        out2 = Path(d) / "kr2.csv"
        assert run(model, setups, {("EURUSD", 5): bars}, out2, batch=4, limit=3, log=lambda *_: None) == 3


def _synthetic(planted, n=700, seed=5):
    rng = np.random.default_rng(seed)
    t = pd.Timestamp("2020-03-01", tz="UTC") + pd.to_timedelta(np.sort(rng.uniform(0, 6 * 365 * 24, n)), unit="h")
    raw = pd.DataFrame({"time": t, "pair": "EURUSD", "tf_min": 5, "is_buy": rng.integers(0, 2, n), "is_ny": rng.integers(0, 2, n),
                        "hour": rng.integers(7, 16, n), "dow": rng.integers(0, 5, n), "risk_pct": rng.uniform(.0005, .003, n),
                        "atr_pct": rng.uniform(.0005, .002, n), "risk_atr": rng.uniform(.5, 3, n), "asian_range_pct": rng.uniform(.001, .006, n),
                        "asian_pos": rng.uniform(-.2, 1.2, n), "ret_4h": rng.normal(0, .003, n), "ret_12h": rng.normal(0, .004, n),
                        "ret_24h": rng.normal(0, .005, n), "dist_sma_24h": rng.normal(0, .002, n)})
    df = add_direction_features(raw)
    kr = rng.normal(0, 1, n)
    logit = -0.7 + (1.0 * kr if planted else 0.0)
    df["y"] = (rng.uniform(size=n) < 1 / (1 + np.exp(-logit))).astype(int)
    df["r"] = np.where(df.y == 1, 2.0, -1.0)
    df["kr_ret_risk"], df["kr_ret_dir"], df["kr_range"], df["kr_hit"] = kr, kr * .001, rng.uniform(.001, .004, n), rng.integers(-1, 2, n)
    return df


def test_comparison_finds_information_when_it_exists_and_not_when_it_does_not():
    quiet = lambda *_: None
    real = compare(_synthetic(planted=True), model_names=("Logistic Regression",), show=quiet)["Logistic Regression"]["B_vs_A"]
    null = compare(_synthetic(planted=False), model_names=("Logistic Regression",), show=quiet)["Logistic Regression"]["B_vs_A"]
    assert real["d_auc_ci"][0] > 0, real                                         # planted signal is detected
    assert null["d_auc_ci"][0] <= 0 <= null["d_auc_ci"][1] or abs(null["d_auc"]) < 0.03, null   # pure noise is NOT called a gain


if __name__ == "__main__":
    for name, fn in list(globals().items()):
        if name.startswith("test_"):
            fn()
            print("PASS", name)
