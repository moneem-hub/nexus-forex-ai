"""
One scan: fetch bars -> detect a new setup -> score it. Prints what the agent would see. No alerts yet.

  python -m agent.run_once --pair EURUSD --tf 15                                   # live, right now
  python -m agent.run_once --pair EURUSD --tf 5 --replay data/raw/eurusd-m5-....csv --at "2025-03-04 10:00"
"""
import argparse

import pandas as pd

from agent.data_sources import LiveSource, ReplaySource
from agent.detect import detect_new_setup
from agent.scoring import load_scorer, score_signal
from collect_setups import load_ohlc


def scan(source, pair, tf, now, bundle, seen, max_age_minutes):
    window = source.bars(pair, tf, now)
    last = window.index[-1] if len(window) else None
    print(f"[{now:%Y-%m-%d %H:%M} UTC] {pair} {tf}m: {len(window)} completed bars, last bar opened {last}")
    sig = detect_new_setup(window, pair, tf, now, seen, max_age_minutes)
    if sig is None:
        print("  no new setup")
        return None
    scored = score_signal(bundle, window.loc[:sig["signal_time"]], sig, tf)
    print(f"  NEW SETUP {sig['direction']} at {sig['entry']:.5f}  SL {sig['sl']:.5f}  TP {sig['tp']:.5f}  RR {sig['rr']}")
    print(f"  model: P(win) {scored['p_win']:.1%}, quality {scored['quality']}")
    for f in scored["factors"]:
        print(f"    - {f['factor']} {f['effect']} ({f['strength']})")
    return {**sig, **scored}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--pair", default="EURUSD")
    ap.add_argument("--tf", type=int, default=15, choices=[5, 15])
    ap.add_argument("--model", default="setup_model.pkl")
    ap.add_argument("--replay", help="path to a Dukascopy CSV: replay history instead of the live market")
    ap.add_argument("--at", help='replay moment in UTC, e.g. "2025-03-04 10:00"')
    ap.add_argument("--max-age-minutes", type=int, default=45, help="how fresh a setup must be to count as new")
    a = ap.parse_args()

    bundle = load_scorer(a.model)
    if a.replay:
        if not a.at:
            raise SystemExit("--replay needs --at")
        source, now = ReplaySource({(a.pair, a.tf): load_ohlc(a.replay)}), pd.Timestamp(a.at, tz="UTC")
    else:
        source, now = LiveSource(), pd.Timestamp.now(tz="UTC")
    scan(source, a.pair, a.tf, now, bundle, set(), a.max_age_minutes)


if __name__ == "__main__":
    main()
