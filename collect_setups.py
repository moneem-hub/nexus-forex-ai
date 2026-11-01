"""
STEP 1 of the setup-quality model: replay history through YOUR ICT engine and label every setup.

Nothing in your existing code is changed. This script only IMPORTS utils/ict_strategy.py and
calls it exactly as the live app does, then asks the engine's own check_outcome() whether each
setup would have hit take-profit or stop-loss.

    python collect_setups.py --data-dir data/raw --out data/setups.csv

Input : 5- or 15-minute OHLC CSV files in --data-dir (the timeframes your engine is designed for).
        The file name must contain the pair (EURUSD, GBPUSD, USDJPY, XAUUSD) and, when you keep several
        timeframes in one folder, the dukascopy-node tag m5 or m15, e.g. eurusd-m5-bid-2022-01-01-2026-10-30.csv
        Use --timeframe-min 5 (or 15) to say which timeframe to process, and a different --out per timeframe.
        Timestamps MUST be UTC (the engine's kill zones are UTC). If your data is in broker time
        (e.g. MT5 server time UTC+2/+3), pass --utc-offset-hours 2 (or 3).
Output: one row per setup: when, pair, direction, entry/SL/TP, outcome (PROFIT/LOSS/PENDING),
        plus context features computed ONLY from bars up to the signal bar.
"""
import argparse
import re
from pathlib import Path

import numpy as np
import pandas as pd

from utils.ict_strategy import check_outcome, run_ict_strategy

KNOWN_PAIRS = ["EURUSD", "GBPUSD", "USDJPY", "XAUUSD"]
EVAL_HOURS = [8, 9, 10, 14, 15, 16]   # end of every hour inside the London (07-10) and NY (13-16) kill zones
LOOKBACK = pd.Timedelta(days=7)       # the live app feeds the engine about 7 days of bars
HORIZON_HOURS = 24                    # judge each setup over the next 24 hours
HOUR = pd.Timedelta(hours=1)


# ── Loading ────────────────────────────────────────────────────────────────────────────
def load_ohlc(path, utc_offset_hours: float = 0.0, resample: str | None = None) -> pd.DataFrame:
    """Read a CSV from dukascopy-node, Dukascopy's export, or MetaTrader. Returns a UTC-indexed OHLC frame."""
    df = pd.read_csv(path, sep=None, engine="python")
    df.columns = [re.sub(r"[<>\s]", "", str(c)).lower() for c in df.columns]

    if "date" in df.columns and "time" in df.columns:                  # MetaTrader: <DATE> <TIME>
        ts = pd.to_datetime(df["date"].astype(str) + " " + df["time"].astype(str), utc=True)
    else:
        tcol = next((c for c in ("timestamp", "gmttime", "datetime", "time", "date") if c in df.columns), None)
        if tcol is None:
            raise ValueError(f"{path}: no time column found. Columns: {list(df.columns)}")
        raw = df[tcol]
        if pd.api.types.is_numeric_dtype(raw):                         # epoch milliseconds or seconds
            ts = pd.to_datetime(raw, unit="ms" if raw.iloc[0] > 1e11 else "s", utc=True)
        else:
            dayfirst = bool(re.match(r"^\d{2}\.\d{2}\.\d{4}", str(raw.iloc[0])))   # 01.01.2023 00:00:00.000
            ts = pd.to_datetime(raw, utc=True, dayfirst=dayfirst)

    need = ["open", "high", "low", "close"]
    if not all(c in df.columns for c in need):
        raise ValueError(f"{path}: need open/high/low/close columns. Columns: {list(df.columns)}")
    out = pd.DataFrame({c.capitalize(): pd.to_numeric(df[c], errors="coerce") for c in need})
    out.index = ts - pd.Timedelta(hours=utc_offset_hours)       # broker time -> UTC
    out = out[~out.index.duplicated()].sort_index().dropna()

    if resample:                                                  # e.g. 5-minute or 1-minute data -> 15-minute bars
        out = out.resample(resample).agg({"Open": "first", "High": "max", "Low": "min", "Close": "last"}).dropna()
    return out


def sanity_report(df: pd.DataFrame, name: str, tf: int = 15):
    step = df.index.to_series().diff().median()
    valid = ((df.High >= df[["Open", "Close"]].max(axis=1)) & (df.Low <= df[["Open", "Close"]].min(axis=1))).mean()
    print(f"  {name}: {len(df)} bars, {df.index[0].date()} -> {df.index[-1].date()}, "
          f"median spacing {step}, valid OHLC {valid:.1%}")
    if step != pd.Timedelta(minutes=tf):
        print(f"  WARNING: bars are not {tf} minutes apart (median {step}). Check --timeframe-min, use --resample {tf}min, or re-download.")
    if valid < 0.99:
        print("  WARNING: many bars break OHLC rules. Check the file and its column order.")


# ── Features (use ONLY bars up to and including the signal bar) ────────────────────────
def setup_features(w: pd.DataFrame, direction: str, entry: float, sl: float, tf: int = 15) -> dict:
    close, ts = w["Close"], w.index[-1]
    tr = pd.concat([w.High - w.Low, (w.High - close.shift()).abs(), (w.Low - close.shift()).abs()], axis=1).max(axis=1)
    atr = tr.rolling(14).mean().iloc[-1]
    risk = abs(entry - sl)

    day = w[w.index.normalize() == ts.normalize()]
    asia = day[day.index.hour < 7]
    if len(asia):
        ah, al = asia.High.max(), asia.Low.min()
        asia_rng, asia_pos = (ah - al) / entry, (entry - al) / (ah - al + 1e-12)
    else:
        asia_rng = asia_pos = np.nan

    def ret(hours):                                    # return over the last N HOURS (same meaning on 5m and 15m)
        n = int(hours * 60 / tf)
        return close.iloc[-1] / close.iloc[-1 - n] - 1 if len(close) > n else np.nan

    return {
        "tf_min": tf,
        "is_buy": int(direction == "BUY"),
        "is_ny": int(ts.hour >= 13),
        "hour": ts.hour,
        "dow": ts.dayofweek,
        "risk_pct": risk / entry,
        "atr_pct": atr / entry,
        "risk_atr": risk / (atr + 1e-12),
        "asian_range_pct": asia_rng,
        "asian_pos": asia_pos,
        "ret_4h": ret(4), "ret_12h": ret(12), "ret_24h": ret(24),
        "dist_sma_24h": close.iloc[-1] / close.tail(int(24 * 60 / tf)).mean() - 1,
    }


# ── Replay ─────────────────────────────────────────────────────────────────────────────
def replay_pair(df: pd.DataFrame, pair: str, tf: int = 15, rr_target: float = 2.0, verbose: bool = True) -> pd.DataFrame:
    horizon = int(HORIZON_HOURS * 60 / tf)
    idx, rows, seen = df.index, [], set()
    days = idx.normalize().unique()
    for n, day in enumerate(days):
        if verbose and n % 100 == 0:
            print(f"    {pair}: day {n}/{len(days)}  setups so far: {len(rows)}", flush=True)
        for h in EVAL_HOURS:
            T = day + pd.Timedelta(hours=h)
            lo, hi = idx.searchsorted(T - HOUR), idx.searchsorted(T)
            if hi == lo:                       # no new bars in the last hour (weekend / gap)
                continue
            start = idx.searchsorted(T - LOOKBACK)
            window = df.iloc[start:hi]
            if len(window) < 60:
                continue
            sig, _ = run_ict_strategy(window.copy(), pair, rr_target)
            if sig is None:
                continue
            sig_ts = pd.Timestamp(sig["timestamp"]).tz_localize("UTC")
            if not (T - HOUR <= sig_ts < T) or (pair, sig_ts) in seen:   # only setups formed in this hour
                continue
            seen.add((pair, sig_ts))

            pos = idx.get_loc(sig_ts)
            future = df.iloc[pos + 1: pos + 1 + horizon].copy()
            outcome = check_outcome(future, sig["timestamp"], sig["direction"], sig["entry"], sig["sl"], sig["tp"])
            feats = setup_features(window.loc[:sig_ts], sig["direction"], sig["entry"], sig["sl"], tf)
            rows.append({"time": sig_ts, "pair": pair, "direction": sig["direction"], "entry": sig["entry"],
                         "sl": sig["sl"], "tp": sig["tp"], "rr": sig["rr"], "outcome": outcome, **feats})
    return pd.DataFrame(rows)


def find_file(data_dir: Path, pair: str, tf: int):
    hits = sorted(p for p in data_dir.glob("*.csv") if pair.lower() in p.name.lower())
    tagged = [p for p in hits if re.search(rf"m{tf}(?!\d)", p.name.lower())]   # e.g. ...-m5-bid-... vs ...-m15-bid-...
    return (tagged or hits or [None])[0]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--data-dir", default="data/raw")
    ap.add_argument("--out", default="data/setups.csv")
    ap.add_argument("--pairs", nargs="*", default=KNOWN_PAIRS)
    ap.add_argument("--utc-offset-hours", type=float, default=0.0, help="broker time minus UTC, e.g. 2 or 3 for MT5")
    ap.add_argument("--resample", default=None, help="e.g. 15min if your files are 1- or 5-minute bars")
    ap.add_argument("--rr", type=float, default=2.0)
    ap.add_argument("--timeframe-min", type=int, default=15, choices=[5, 15], help="bar size of the files to process")
    a = ap.parse_args()

    frames = []
    for pair in a.pairs:
        f = find_file(Path(a.data_dir), pair, a.timeframe_min)
        if f is None:
            print(f"- {pair}: no file found in {a.data_dir}, skipping")
            continue
        print(f"- {pair}: {f.name}")
        df = load_ohlc(f, a.utc_offset_hours, a.resample)
        sanity_report(df, pair, a.timeframe_min)
        frames.append(replay_pair(df, pair, a.timeframe_min, a.rr))
    if not frames or all(x.empty for x in frames):
        raise SystemExit("No setups found. Check the data files, timezone and timeframe.")

    res = pd.concat(frames).sort_values("time").reset_index(drop=True)
    Path(a.out).parent.mkdir(parents=True, exist_ok=True)
    res.to_csv(a.out, index=False)

    done = res[res.outcome != "PENDING"]
    wins = (done.outcome == "PROFIT").mean() if len(done) else float("nan")
    print(f"\nSaved {len(res)} setups -> {a.out}")
    print(res.groupby(["pair", "outcome"]).size().unstack(fill_value=0).to_string())
    be = 1 / (1 + a.rr)
    print(f"\nResolved setups: {len(done)} | win rate {wins:.1%} | break-even win rate at 1:{a.rr:g} is {be:.1%}")
    print(f"Average result per setup: {wins * a.rr - (1 - wins):+.2f} R   (positive = this rule-set made money on this data)")
    print("Training needs a few hundred resolved setups at least; more is better.")


if __name__ == "__main__":
    main()
