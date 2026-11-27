"""
Run a PRE-TRAINED market model (Kronos, MIT licence) on every historical setup and save forecast-based features.

For each setup: the 400 candles up to and including the signal bar go in; Kronos forecasts the next 2 hours; a few
direction-aware features come out (does the forecast move with the trade, how wide is the forecast range, does the forecast
path reach take-profit or stop-loss first). Nothing is trained: the pretrained model is used as it is, zero-shot.

  python kronos_features.py --kronos-dir C:\\path\\to\\Kronos            # all setups (slow on CPU: run it once, it resumes)
  python kronos_features.py --kronos-dir C:\\path\\to\\Kronos --limit 20 # quick trial

Needs: git clone https://github.com/shiyu-coder/Kronos  and  pip install torch einops huggingface_hub safetensors
Output: data/kronos_features.csv  (pair, time, tf_min, kr_* features, and eval_real_ret_dir = realised outcome, EVALUATION ONLY)
"""
import argparse
import sys
import time
from pathlib import Path

import numpy as np
import pandas as pd

from collect_setups import find_file, load_ohlc

LOOKBACK_BARS = 400            # context given to the model (its limit is 512)
HORIZON_HOURS = 2              # how far ahead it forecasts
KR_COLS = ["kr_ret_dir", "kr_range", "kr_hit", "kr_ret_risk"]   # the ONLY columns used as features; eval_* is never a feature


def forecast_features(pred: pd.DataFrame, last_close: float, direction: str, sl: float, tp: float) -> dict:
    """Turn a forecast (open/high/low/close per future bar) into direction-aware, scale-free features."""
    sgn = 1.0 if direction == "BUY" else -1.0
    ret_dir = sgn * (float(pred["close"].iloc[-1]) - last_close) / last_close
    rng = (float(pred["high"].max()) - float(pred["low"].min())) / last_close
    hit = 0                                                        # +1: forecast reaches TP first, -1: SL first (or same bar), 0: neither
    for hi, lo in zip(pred["high"].values, pred["low"].values):
        if direction == "BUY":
            if lo <= sl:
                hit = -1; break
            if hi >= tp:
                hit = 1; break
        else:
            if hi >= sl:
                hit = -1; break
            if lo <= tp:
                hit = 1; break
    risk = abs(last_close - sl) / last_close
    return {"kr_ret_dir": ret_dir, "kr_range": rng, "kr_hit": hit, "kr_ret_risk": ret_dir / (risk + 1e-12)}


def build_job(bars: pd.DataFrame, row, tf: int, lookback: int, horizon_bars: int):
    """Inputs for one setup. Uses ONLY bars up to and including the signal bar. Returns None if there is not enough history."""
    ctx = bars.loc[:row.time].tail(lookback)
    if len(ctx) < lookback or ctx.index[-1] != row.time:
        return None
    x_ts = pd.Series(ctx.index.tz_convert("UTC").tz_localize(None))
    y_ts = pd.Series(pd.date_range(x_ts.iloc[-1] + pd.Timedelta(minutes=tf), periods=horizon_bars, freq=f"{tf}min"))
    last_close = float(ctx["Close"].iloc[-1])
    fut = bars.loc[row.time:].iloc[1:horizon_bars + 1]             # realised future: for EVALUATION only
    sgn = 1.0 if row.direction == "BUY" else -1.0
    real = sgn * (float(fut["Close"].iloc[-1]) - last_close) / last_close if len(fut) == horizon_bars else np.nan
    df = ctx[["Open", "High", "Low", "Close"]].rename(columns=str.lower).reset_index(drop=True)
    return {"key": (row.pair, row.time, tf), "df": df, "x_ts": x_ts, "y_ts": y_ts, "last_close": last_close,
            "direction": row.direction, "sl": float(row.sl), "tp": float(row.tp), "real": real}


def run(predictor, setups: pd.DataFrame, frames: dict, out_path: Path, lookback=LOOKBACK_BARS, horizon_hours=HORIZON_HOURS,
        batch=8, samples=3, limit=None, log=print) -> int:
    done = set()
    if out_path.exists():
        old = pd.read_csv(out_path, parse_dates=["time"])
        done = set(zip(old.pair, old.time, old.tf_min))
    written = 0
    for tf in sorted(setups.tf_min.unique()):
        H = int(horizon_hours * 60 / tf)
        todo = []
        for row in setups[setups.tf_min == tf].itertuples():
            if (row.pair, row.time, tf) in done or (row.pair, tf) not in frames:
                continue
            job = build_job(frames[(row.pair, tf)], row, tf, lookback, H)
            if job:
                todo.append(job)
        if limit is not None:
            todo = todo[:max(0, limit - written)]
        log(f"{tf}-minute setups to process: {len(todo)} (already done: {sum(1 for k in done if k[2] == tf)})")
        t0 = time.time()
        for i in range(0, len(todo), batch):
            chunk = todo[i:i + batch]
            preds = predictor.predict_batch(df_list=[j["df"] for j in chunk], x_timestamp_list=[j["x_ts"] for j in chunk],
                                            y_timestamp_list=[j["y_ts"] for j in chunk], pred_len=H, T=1.0, top_p=0.9,
                                            sample_count=samples, verbose=False)
            rows = []
            for j, p in zip(chunk, preds):
                f = forecast_features(p, j["last_close"], j["direction"], j["sl"], j["tp"])
                rows.append({"pair": j["key"][0], "time": j["key"][1], "tf_min": tf, **f, "eval_real_ret_dir": j["real"]})
            pd.DataFrame(rows).to_csv(out_path, mode="a", header=not out_path.exists(), index=False)   # checkpoint after every batch
            written += len(rows)
            n_done = i + len(chunk)
            eta = (time.time() - t0) / n_done * (len(todo) - n_done) / 60
            log(f"  {tf}m: {n_done}/{len(todo)} done, about {eta:.0f} min left")
    return written


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--kronos-dir", required=True, help="folder where you cloned https://github.com/shiyu-coder/Kronos")
    ap.add_argument("--data-dir", default="data/raw")
    ap.add_argument("--setups", default="data/setups*.csv")
    ap.add_argument("--out", default="data/kronos_features.csv")
    ap.add_argument("--model", default="NeoQuasar/Kronos-small")
    ap.add_argument("--tokenizer", default="NeoQuasar/Kronos-Tokenizer-base")
    ap.add_argument("--device", default="cpu", help="cpu, or cuda:0 if you have an NVIDIA GPU")
    ap.add_argument("--batch", type=int, default=8)
    ap.add_argument("--samples", type=int, default=3, help="forecast paths averaged per setup")
    ap.add_argument("--limit", type=int, default=None, help="process only this many setups (quick trial)")
    a = ap.parse_args()

    sys.path.insert(0, str(Path(a.kronos_dir).resolve()))
    import torch
    from model import Kronos, KronosPredictor, KronosTokenizer          # from the cloned Kronos repository
    from train_setup_model import load_setups

    torch.manual_seed(0)
    print("Loading the pretrained model (first run downloads it from Hugging Face)...")
    predictor = KronosPredictor(Kronos.from_pretrained(a.model), KronosTokenizer.from_pretrained(a.tokenizer), device=a.device, max_context=512)
    setups = load_setups(a.setups)
    frames = {}
    for pair in setups.pair.unique():
        for tf in setups.tf_min.unique():
            f = find_file(Path(a.data_dir), pair, int(tf))
            if f is not None:
                frames[(pair, int(tf))] = load_ohlc(f)
    n = run(predictor, setups, frames, Path(a.out), batch=a.batch, samples=a.samples, limit=a.limit)
    print(f"Done: {n} new rows written to {a.out}. Next: python compare_pretrained.py")


if __name__ == "__main__":
    main()
