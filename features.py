"""
Shared feature engineering for TRAINING and LIVE SERVING.

Rule: every feature at row t may only use data up to and including row t.
All features are scale-free (returns, ratios, z-scores), so one model can
serve EUR/USD (~1.1) and USD/JPY (~150) alike.

By default only the Close price is used. High/Low-based features are behind
`include_range_features=True` because, on the Yahoo daily FX data, the
High/Low window is not aligned with the Close and leaks information about the
next day. train.py uses that flag to *detect* this leak, never in production.

Live use: pass only COMPLETED bars (drop today's unfinished candle).
"""
import numpy as np
import pandas as pd

BASE_FEATURES = [
    "ret_1", "ret_2", "ret_3", "ret_5", "ret_10",
    "vol_5", "vol_10", "vol_20",
    "rsi_14", "macd_norm", "macd_hist_norm",
    "zscore_20", "dist_sma_10", "dist_sma_50", "move_z",
]
RANGE_FEATURES = ["range_pct", "close_pos", "atr_pct"]


def build_features(df: pd.DataFrame, include_range_features: bool = False) -> pd.DataFrame:
    """df needs columns Open, High, Low, Close. Returns features (NaN during warm-up)."""
    close = df["Close"].astype(float)
    out = pd.DataFrame(index=df.index)

    ret = close.pct_change()
    for n in (1, 2, 3, 5, 10):
        out[f"ret_{n}"] = close.pct_change(n)
    for n in (5, 10, 20):
        out[f"vol_{n}"] = ret.rolling(n).std()

    # RSI with Wilder smoothing
    delta = close.diff()
    gain = delta.clip(lower=0).ewm(alpha=1 / 14, adjust=False, min_periods=14).mean()
    loss = (-delta.clip(upper=0)).ewm(alpha=1 / 14, adjust=False, min_periods=14).mean()
    out["rsi_14"] = 100 - 100 / (1 + gain / (loss + 1e-12))

    # MACD, normalised by price so it is scale-free
    macd = close.ewm(span=12, adjust=False, min_periods=12).mean() - \
           close.ewm(span=26, adjust=False, min_periods=26).mean()
    signal = macd.ewm(span=9, adjust=False, min_periods=9).mean()
    out["macd_norm"] = macd / close
    out["macd_hist_norm"] = (macd - signal) / close

    sma20 = close.rolling(20).mean()
    out["zscore_20"] = (close - sma20) / (close.rolling(20).std() + 1e-12)
    out["dist_sma_10"] = close / close.rolling(10).mean() - 1
    out["dist_sma_50"] = close / close.rolling(50).mean() - 1
    out["move_z"] = ret / (out["vol_20"] + 1e-12)

    if include_range_features:
        hi, lo = df["High"].astype(float), df["Low"].astype(float)
        out["range_pct"] = (hi - lo) / close
        out["close_pos"] = (close - lo) / (hi - lo + 1e-12)
        tr = pd.concat([hi - lo, (hi - close.shift()).abs(), (lo - close.shift()).abs()], axis=1).max(axis=1)
        out["atr_pct"] = tr.rolling(14).mean() / close

    cols = BASE_FEATURES + (RANGE_FEATURES if include_range_features else [])
    return out[cols].replace([np.inf, -np.inf], np.nan)


def latest_features(df: pd.DataFrame) -> pd.DataFrame:
    """Feature row for the most recent completed bar (for live prediction)."""
    return build_features(df).dropna().tail(1)
