"""
The monitoring loop: what turns the agent from "a script you run" into "something that watches the market for you".

  python -m agent.monitor                                    # LIVE: all pairs, 5m and 15m, until you press Ctrl+C
  python -m agent.monitor --pairs EURUSD XAUUSD --tfs 15
  python -m agent.monitor --replay --from "2020-01-13 06:00" --to "2020-01-13 12:00" --pairs EURUSD --tfs 5 --fresh
        DEMO MODE: the same loop, run over history on a fast simulated clock (no waiting, no live market needed)

How it works
  - wakes up shortly after every bar closes (xx:00:45, xx:05:45 ...), Monday-Friday, only inside the kill-zone windows
  - cheap deterministic check first; the LLM agent is woken ONLY when a new setup exists (saves tokens and API limits)
  - every hour it settles earlier setups (PROFIT / LOSS / EXPIRED) in the journal
  - a failing job never stops the loop; repeated failures send you a warning
"""
import argparse
import time
from pathlib import Path

import pandas as pd

import utils.db as D
from agent import journal as J
from agent.agent import run_agent
from agent.alerts import send_alert
from agent.config import load_env
from agent.data_sources import LiveSource, ReplaySource
from agent.detect import detect_new_setup
from agent.llm import FakeLLM, GroqLLM, LLMError
from agent.scoring import load_scorer
from agent.tools import ToolBox
from collect_setups import find_file, load_ohlc

ACTIVE_WINDOWS = [(7 * 60, 10 * 60 + 30), (13 * 60, 16 * 60 + 30)]   # UTC minutes of the day: London and New York kill zones + 30 min margin
TICK_DELAY_S = 45                                                      # wait for the bar to be published
WARN_AFTER_FAILURES = 5


def is_active(now: pd.Timestamp) -> bool:
    minute = now.hour * 60 + now.minute
    return now.dayofweek < 5 and any(a <= minute < b for a, b in ACTIVE_WINDOWS)


def next_tick(now: pd.Timestamp, base_tf: int = 5, delay: int = TICK_DELAY_S) -> pd.Timestamp:
    t = now.floor(f"{base_tf}min") + pd.Timedelta(seconds=delay)
    while t <= now:
        t += pd.Timedelta(minutes=base_tf)
    return t


class RealClock:
    def now(self): return pd.Timestamp.now(tz="UTC")

    def sleep_until(self, t):
        while (d := (t - self.now()).total_seconds()) > 0:
            time.sleep(min(d, 30))


class SimClock:
    def __init__(self, start): self.t = start
    def now(self): return self.t
    def sleep_until(self, t): self.t = max(self.t, t)


class _OnceSource:
    """Within one tick, download each (pair, timeframe) only once, however many steps ask for it."""
    def __init__(self, src): self.src, self.cache = src, {}

    def bars(self, pair, tf, now):
        key = (pair, tf, now)
        if key not in self.cache:
            self.cache[key] = self.src.bars(pair, tf, now)
        return self.cache[key]


class Monitor:
    def __init__(self, source, bundle, jobs, llm, clock, seen, alert_fn=send_alert, max_age_minutes=45, verbose=True, verbose_scans=False):
        self.source, self.bundle, self.jobs, self.llm, self.clock = source, bundle, jobs, llm, clock
        self.seen, self.alert_fn, self.max_age, self.verbose = seen, alert_fn, max_age_minutes, verbose
        self.verbose_scans = verbose_scans
        self.base_tf = min(tf for _, tf in jobs)
        self.stats = {"ticks": 0, "jobs": 0, "setups": 0, "alerts": 0, "errors": 0}
        self.failures: dict = {}

    def _say(self, msg):
        if self.verbose:
            print(msg, flush=True)

    def tick(self, now: pd.Timestamp) -> None:
        self.stats["ticks"] += 1
        src = _OnceSource(self.source)
        if self.stats["ticks"] == 1 or now.minute == 0:                    # settle earlier setups: at start-up and hourly
            try:
                for r in J.resolve_pending(src, now):
                    self._say(f"[{now:%Y-%m-%d %H:%M}] outcome: setup {r['id']} {r['pair']} -> {r['outcome']}")
            except Exception as e:
                self._on_error("-", 0, e)
        ran = 0
        for pair, tf in self.jobs:
            if now.minute % tf or not is_active(now):
                continue
            ran += 1
            try:
                self._run_job(src, pair, tf, now)
                self.failures[(pair, tf)] = 0
            except Exception as e:
                self._on_error(pair, tf, e)
        self.stats["jobs"] += ran
        if ran and (self.verbose_scans or now.minute == 0):                 # heartbeat once an hour (or every tick with --verbose-scans)
            self._say(f"[{now:%Y-%m-%d %H:%M}] watching: scanned {ran} job(s) this tick")

    def _run_job(self, src, pair, tf, now):
        window = src.bars(pair, tf, now)
        if detect_new_setup(window, pair, tf, now, set(self.seen), self.max_age) is None:    # copy of seen: a pre-check, no side effects
            return
        box = ToolBox(src, self.bundle, now, self.seen, self.alert_fn, self.max_age)
        out = run_agent(self.llm, box, pair, tf)
        self.stats["setups"] += out["found"]
        self.stats["alerts"] += out["alerted"]
        self._say(f"[{now:%Y-%m-%d %H:%M}] {pair} {tf}m -> {out}")

    def _on_error(self, pair, tf, e):
        self.stats["errors"] += 1
        n = self.failures[(pair, tf)] = self.failures.get((pair, tf), 0) + 1
        try:
            J.log_event(pair, tf, "ERROR", str(e))
        except Exception:
            pass
        self._say(f"  error in {pair} {tf}m ({n} in a row): {e}")
        if n == WARN_AFTER_FAILURES:
            self.alert_fn(f"Agent warning: {pair} {tf}m has failed {n} times in a row ({e}). Check the data source.")

    def run(self, until: pd.Timestamp | None = None) -> dict:
        try:
            while True:
                t = next_tick(self.clock.now(), self.base_tf)
                if until is not None and t > until:
                    break
                self.clock.sleep_until(t)
                self.tick(self.clock.now())
        except KeyboardInterrupt:
            self._say("stopped by user")
        return self.stats


def main():
    load_env()
    ap = argparse.ArgumentParser()
    ap.add_argument("--pairs", nargs="*", default=["EURUSD", "GBPUSD", "USDJPY", "XAUUSD"])
    ap.add_argument("--tfs", nargs="*", type=int, default=[5, 15], choices=[5, 15])
    ap.add_argument("--model", default="setup_model.pkl")
    ap.add_argument("--no-llm", action="store_true", help="skip the LLM: templated alerts only")
    ap.add_argument("--max-age-minutes", type=int, default=45)
    ap.add_argument("--replay", action="store_true", help="demo mode: run over history on a simulated clock")
    ap.add_argument("--data-dir", default="data/raw")
    ap.add_argument("--from", dest="start", help='replay start, UTC, e.g. "2020-01-13 06:00"')
    ap.add_argument("--to", dest="end", help="replay end, UTC")
    ap.add_argument("--verbose-scans", action="store_true", help="print a line at every scan, not just hourly")
    ap.add_argument("--fresh", action="store_true", help="replay only: clear the replay journal first")
    a = ap.parse_args()

    jobs = [(p, tf) for p in a.pairs for tf in a.tfs]
    if a.replay:
        if not (a.start and a.end):
            raise SystemExit("--replay needs --from and --to")
        D.DB_NAME = D.DB_NAME + "_replay"                                 # demos never mix with the live track record
        frames = {}
        for p, tf in jobs:
            f = find_file(Path(a.data_dir), p, tf)
            if f is None:
                raise SystemExit(f"no {p} {tf}m file in {a.data_dir}")
            frames[(p, tf)] = load_ohlc(f)
        source, clock, until, seen_days = ReplaySource(frames), SimClock(pd.Timestamp(a.start, tz="UTC")), pd.Timestamp(a.end, tz="UTC"), 36500
    else:
        source, clock, until, seen_days = LiveSource(), RealClock(), None, 3

    J.init_journal()
    if a.replay and a.fresh:
        J._run("DELETE FROM agent_journal")
        J._run("DELETE FROM agent_log")
    llm = FakeLLM(lambda m: LLMError("LLM disabled (--no-llm)")) if a.no_llm else GroqLLM()
    mon = Monitor(source, load_scorer(a.model), jobs, llm, clock, J.load_seen(seen_days), max_age_minutes=a.max_age_minutes, verbose_scans=a.verbose_scans)
    print(f"Monitoring {len(jobs)} job(s): {', '.join(f'{p} {tf}m' for p, tf in jobs)}. {'Replay' if a.replay else 'Live'}. Ctrl+C to stop.")
    print("Final:", mon.run(until))


if __name__ == "__main__":
    main()
