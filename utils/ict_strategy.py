"""
ICT Kill Zone Strategy — Python port of the Pine Script indicator.
Sessions in UTC/GMT. Designed for 5-min and 15-min charts.
Pairs: EURUSD=X, GBPUSD=X, USDJPY=X
"""
import numpy as np
import pandas as pd


# ── Session Helpers ────────────────────────────────────────────────────────────

def _session(hour: int) -> str:
    if 0 <= hour < 7:   return "asian"
    if 7 <= hour < 10:  return "london"
    if 10 <= hour < 13: return "pre_ny"
    if 13 <= hour < 16: return "ny"
    return "dead"


def _in_kz(hour: int) -> bool:
    return (7 <= hour < 10) or (13 <= hour < 16)


SESSION_LABELS = {
    "asian":  "Asian Range  ·  00:00 – 07:00 GMT",
    "london": "London Kill Zone  ·  07:00 – 10:00 GMT",
    "pre_ny": "Dead Zone  ·  10:00 – 13:00 GMT",
    "ny":     "NY Kill Zone  ·  13:00 – 16:00 GMT",
    "dead":   "Dead Zone  ·  16:00 – 00:00 GMT",
}

NEXT_KZ_LABEL = {
    "asian":  "London Kill Zone  ·  07:00 GMT",
    "london": "NY Kill Zone  ·  13:00 GMT",
    "pre_ny": "NY Kill Zone  ·  13:00 GMT",
    "ny":     "London Kill Zone (tomorrow)  ·  07:00 GMT",
    "dead":   "London Kill Zone (tomorrow)  ·  07:00 GMT",
}


# ── ATR ────────────────────────────────────────────────────────────────────────

def _atr(df: pd.DataFrame, period: int = 14) -> pd.Series:
    h, l, c = df["High"], df["Low"], df["Close"]
    tr = pd.concat(
        [h - l, (h - c.shift()).abs(), (l - c.shift()).abs()], axis=1
    ).max(axis=1)
    return tr.rolling(period).mean()


# ── Pivot High / Low ───────────────────────────────────────────────────────────

def _pivot_high(series: pd.Series, lb: int = 5) -> pd.Series:
    vals = series.values
    out  = np.full(len(vals), np.nan)
    for i in range(lb, len(vals) - lb):
        window = vals[i - lb : i + lb + 1]
        if vals[i] >= np.nanmax(window):
            out[i] = vals[i]
    return pd.Series(out, index=series.index)


def _pivot_low(series: pd.Series, lb: int = 5) -> pd.Series:
    vals = series.values
    out  = np.full(len(vals), np.nan)
    for i in range(lb, len(vals) - lb):
        window = vals[i - lb : i + lb + 1]
        if vals[i] <= np.nanmin(window):
            out[i] = vals[i]
    return pd.Series(out, index=series.index)


# ── Asian Range (per day, broadcast to every bar of that day) ──────────────────

def _asian_range(df: pd.DataFrame):
    mask     = df.index.hour < 7
    dates    = df.index.normalize()
    asian_h  = df["High"].where(mask).groupby(dates).transform("max")
    asian_l  = df["Low"].where(mask).groupby(dates).transform("min")
    return asian_h, asian_l


# ── Core ICT Strategy ──────────────────────────────────────────────────────────

def run_ict_strategy(df: pd.DataFrame, pair_label: str, rr_target: float = 2.0):
    """
    Run ICT Kill Zone strategy on OHLCV DataFrame (5m or 15m).

    Returns
    -------
    signal : dict or None
        Signal dict if a setup was found; None otherwise.
    status : dict
        Current session info and condition flags for the UI.
    """
    if len(df) < 60:
        return None, {"error": "Not enough data"}

    # ── Timezone normalise to UTC
    if df.index.tz is None:
        df.index = df.index.tz_localize("UTC")
    else:
        df.index = df.index.tz_convert("UTC")
    df = df.copy()

    # ── Session labels
    df["hour"]    = df.index.hour
    df["in_kz"]   = df["hour"].apply(_in_kz)
    df["session"] = df["hour"].apply(_session)

    # ── ATR
    df["atr"] = _atr(df)

    # ── Asian Range
    df["asian_h"], df["asian_l"] = _asian_range(df)

    # ── Fair Value Gaps (only inside Kill Zones)
    #    Bullish FVG : low > high[2]  AND  close[1] > open[1]
    #    Bearish FVG : high < low[2]  AND  close[1] < open[1]
    df["bull_fvg"] = (
        df["in_kz"]
        & (df["Low"] > df["High"].shift(2))
        & (df["Close"].shift(1) > df["Open"].shift(1))
    )
    df["bear_fvg"] = (
        df["in_kz"]
        & (df["High"] < df["Low"].shift(2))
        & (df["Close"].shift(1) < df["Open"].shift(1))
    )

    # ── Swing pivot points (lookback = 5 bars each side)
    LB = 5
    df["ph"] = _pivot_high(df["High"], LB)
    df["pl"] = _pivot_low(df["Low"],  LB)

    # Forward-fill most-recent pivot values to every bar
    df["recent_sh"] = df["ph"].ffill()
    df["recent_sl"] = df["pl"].ffill()

    # ── Liquidity Sweeps
    ph_shifted = df["ph"].shift(LB)
    pl_shifted = df["pl"].shift(LB)

    df["bear_sweep"] = (
        ph_shifted.notna()
        & (df["High"] > ph_shifted)
        & (df["Close"] < ph_shifted)
    )
    df["bull_sweep"] = (
        pl_shifted.notna()
        & (df["Low"] < pl_shifted)
        & (df["Close"] > pl_shifted)
    )
    df["ash_sweep"] = (
        df["asian_h"].notna()
        & (df["High"] > df["asian_h"])
        & (df["Close"] < df["asian_h"])
    )
    df["asl_sweep"] = (
        df["asian_l"].notna()
        & (df["Low"] < df["asian_l"])
        & (df["Close"] > df["asian_l"])
    )

    df["any_bull_sweep"] = df["bull_sweep"] | df["asl_sweep"]
    df["any_bear_sweep"] = df["bear_sweep"] | df["ash_sweep"]

    # ── Market Structure Shift (MSS) — within 20 bars of a sweep
    bull_on = False
    bear_on = False
    sw_idx  = -999
    bull_st, bear_st = [], []

    for i in range(len(df)):
        row = df.iloc[i]
        if row["any_bull_sweep"]:
            bull_on, bear_on, sw_idx = True, False, i
        if row["any_bear_sweep"]:
            bear_on, bull_on, sw_idx = True, False, i
        if i - sw_idx > 20:
            bull_on = bear_on = False
        bull_st.append(bull_on)
        bear_st.append(bear_on)

    df["rbull"] = bull_st
    df["rbear"] = bear_st

    df["bull_mss"] = (
        df["rbull"]
        & (df["Close"] > df["recent_sh"])
        & (df["Close"].shift(1) <= df["recent_sh"])
    )
    df["bear_mss"] = (
        df["rbear"]
        & (df["Close"] < df["recent_sl"])
        & (df["Close"].shift(1) >= df["recent_sl"])
    )

    # ── Full Setup  =  in_kz + MSS + FVG on previous bar
    df["long_setup"]  = (
        df["in_kz"] & df["bull_mss"] & df["bull_fvg"].shift(1).fillna(False).astype(bool)
    )
    df["short_setup"] = (
        df["in_kz"] & df["bear_mss"] & df["bear_fvg"].shift(1).fillna(False).astype(bool)
    )

    # ── Build status info for UI
    last_ts  = df.index[-1]
    cur_sess = _session(last_ts.hour)
    last     = df.iloc[-1]

    status = {
        "session":      cur_sess,
        "session_label": SESSION_LABELS[cur_sess],
        "in_kz":        bool(last["in_kz"]),
        "next_kz":      NEXT_KZ_LABEL[cur_sess],
        "asian_high":   (float(last["asian_h"]) if pd.notna(last["asian_h"]) else None),
        "asian_low":    (float(last["asian_l"]) if pd.notna(last["asian_l"]) else None),
        "bull_fvg":     bool(df["bull_fvg"].tail(15).any()),
        "bear_fvg":     bool(df["bear_fvg"].tail(15).any()),
        "bull_sweep":   bool(df["any_bull_sweep"].tail(10).any()),
        "bear_sweep":   bool(df["any_bear_sweep"].tail(10).any()),
        "bull_mss":     bool(df["bull_mss"].tail(10).any()),
        "bear_mss":     bool(df["bear_mss"].tail(10).any()),
    }

    # ── Collect all detected setups, pick the most recent
    setups = []
    for ts, row in df[df["long_setup"]].iterrows():
        setups.append(("BUY", ts, row))
    for ts, row in df[df["short_setup"]].iterrows():
        setups.append(("SELL", ts, row))

    if not setups:
        return None, status

    setups.sort(key=lambda x: x[1])
    direction, sig_ts, row = setups[-1]

    entry   = float(row["Close"])
    atr_val = float(row["atr"]) if pd.notna(row["atr"]) else entry * 0.001

    idx = df.index.get_loc(sig_ts)
    prev_low  = float(df["Low"].iloc[idx - 1])  if idx > 0 else float(row["Low"])
    prev_high = float(df["High"].iloc[idx - 1]) if idx > 0 else float(row["High"])

    if direction == "BUY":
        sl   = prev_low  - atr_val * 0.1
        risk = abs(entry - sl)
        tp1  = entry + risk * 1.5
        tp   = entry + risk * rr_target
    else:
        sl   = prev_high + atr_val * 0.1
        risk = abs(sl - entry)
        tp1  = entry - risk * 1.5
        tp   = entry - risk * rr_target

    rr = abs(tp - entry) / risk if risk > 0 else 0

    signal = {
        "timestamp":    sig_ts.strftime("%Y-%m-%d %H:%M"),
        "pair":         pair_label,
        "direction":    direction,
        "entry":        entry,
        "sl":           sl,
        "tp":           tp,
        "tp1":          tp1,
        "rr":           rr,
        "session_label": SESSION_LABELS.get(str(row["session"]), str(row["session"])),
    }

    return signal, status


# ── Outcome Checker ────────────────────────────────────────────────────────────

def check_outcome(
    df: pd.DataFrame,
    signal_time: str,
    direction: str,
    entry: float,
    sl: float,
    tp: float,
) -> str:
    """
    Check whether a historical signal hit TP (PROFIT) or SL (LOSS).
    Returns 'PROFIT', 'LOSS', or 'PENDING'.
    """
    try:
        if df.index.tz is None:
            df.index = df.index.tz_localize("UTC")
        else:
            df.index = df.index.tz_convert("UTC")

        sig_dt = pd.Timestamp(signal_time).tz_localize("UTC")
        after  = df[df.index > sig_dt]

        if after.empty:
            return "PENDING"

        for _, row in after.iterrows():
            if direction == "BUY":
                if float(row["Low"])  <= sl:  return "LOSS"
                if float(row["High"]) >= tp:  return "PROFIT"
            else:
                if float(row["High"]) >= sl:  return "LOSS"
                if float(row["Low"])  <= tp:  return "PROFIT"

        return "PENDING"
    except Exception:
        return "PENDING"
