"""Run with:  python test_agent_detect.py   (from the project root; uses your own data; takes about a minute)"""
import glob

import pandas as pd

from agent.data_sources import ReplaySource
from agent.detect import detect_new_setup
from collect_setups import EVAL_HOURS, load_ohlc

RAW = sorted(glob.glob("data/raw/eurusd-m5-*.csv"))
TF, DAYS = 5, 60                                   # replay the first 60 days of the file


def _replay_agent(df):
    """Drive the agent's detection hour by hour exactly like the live loop would, on history."""
    src, seen, found = ReplaySource({("EURUSD", TF): df}), set(), []
    day0 = df.index[0].normalize()
    for d in range(DAYS):
        for h in EVAL_HOURS:
            now = day0 + pd.Timedelta(days=d, hours=h)
            window = src.bars("EURUSD", TF, now)
            sig = detect_new_setup(window, "EURUSD", TF, now, seen, max_age_minutes=60)
            if sig:
                found.append(sig["signal_time"])
    return found, seen


def test_agent_finds_the_same_setups_as_the_backtest():
    """The live detection path must reproduce the setups stored in the training data for the same period."""
    df = load_ohlc(RAW[0])
    found, _ = _replay_agent(df)
    s = pd.read_csv("data/setups_5m.csv", parse_dates=["time"])
    end = df.index[0].normalize() + pd.Timedelta(days=DAYS)
    expected = sorted(s[(s.pair == "EURUSD") & (s.time < end)].time)
    assert sorted(found) == expected, (len(found), len(expected))
    print(f"   {len(found)} setups, identical to the backtest")


def test_each_setup_fires_only_once():
    df = load_ohlc(RAW[0])
    found, seen = _replay_agent(df)
    assert len(found) == len(set(found)) == len(seen)


def test_replay_never_shows_unfinished_bars():
    df = load_ohlc(RAW[0])
    src = ReplaySource({("EURUSD", TF): df})
    now = df.index[5000] + pd.Timedelta(minutes=2)             # 2 minutes into a bar
    w = src.bars("EURUSD", TF, now)
    assert (w.index + pd.Timedelta(minutes=TF) <= now).all() and w.index[-1] < df.index[5000]


if __name__ == "__main__":
    if not RAW:
        raise SystemExit("Put eurusd-m5-*.csv in data/raw first.")
    for name, fn in list(globals().items()):
        if name.startswith("test_"):
            fn()
            print("PASS", name)
