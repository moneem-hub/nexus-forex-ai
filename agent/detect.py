"""
Detect a NEW ICT setup with the same engine and the same acceptance rule used to build the training data
(collect_setups.replay_pair), so live behaviour and the backtest describe the same thing.
"""
import pandas as pd

from utils.ict_strategy import run_ict_strategy


def detect_new_setup(window: pd.DataFrame, pair: str, tf: int, now: pd.Timestamp, seen: set,
                     max_age_minutes: int = 3 * 15, rr: float = 2.0):
    """
    window : completed bars (UTC) up to `now`
    seen   : set of (pair, tf, signal_time) already handled; updated in place so a setup fires only once
    Returns the setup dict (engine fields + pair, tf, signal_time) or None.
    """
    if len(window) < 60:
        return None
    sig, _status = run_ict_strategy(window.copy(), pair, rr)      # copy: the engine edits the index in place
    if sig is None:
        return None
    sig_ts = pd.Timestamp(sig["timestamp"]).tz_localize("UTC")
    if not (now - pd.Timedelta(minutes=max_age_minutes) <= sig_ts < now):   # only freshly formed setups
        return None
    key = (pair, tf, sig_ts)
    if key in seen:
        return None
    seen.add(key)
    return {**sig, "pair": pair, "tf": tf, "signal_time": sig_ts}
