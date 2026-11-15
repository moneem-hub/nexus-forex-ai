"""
Run with:  python test_agent_monitor.py   (needs MySQL running; uses the throw-away database nexus_forex_test)
Runs the REAL monitoring loop over history on a simulated clock and checks scheduling, coverage, error handling and cost control.
"""
import glob

import pandas as pd

import utils.db as D

D.DB_NAME = "nexus_forex_test"                        # safety: never touch the real journal

from agent import journal as J
from agent.data_sources import ReplaySource
from agent.llm import FakeLLM, LLMError
from agent.monitor import Monitor, SimClock, is_active, next_tick
from collect_setups import load_ohlc
from test_agent_loop import BUNDLE, reset

RAW = sorted(glob.glob("data/raw/eurusd-m5-*.csv"))[0]
BARS = load_ohlc(RAW)
SETUPS = pd.read_csv("data/setups_5m.csv", parse_dates=["time"]).query("pair == 'EURUSD'")
T0 = SETUPS.time.iloc[3]                                                   # a known setup from the backtest
START, UNTIL = T0.floor("h") - pd.Timedelta(hours=3), T0.floor("h") + pd.Timedelta(hours=2)


def _utc(s): return pd.Timestamp(s, tz="UTC")


def test_next_tick_and_active_windows():
    assert next_tick(_utc("2025-03-04 10:00:10")) == _utc("2025-03-04 10:00:45")
    assert next_tick(_utc("2025-03-04 10:00:45")) == _utc("2025-03-04 10:05:45")
    assert next_tick(_utc("2025-03-04 10:03:00")) == _utc("2025-03-04 10:05:45")
    assert next_tick(_utc("2025-03-04 10:14:00"), base_tf=15) == _utc("2025-03-04 10:15:45")
    assert is_active(_utc("2025-03-04 08:00")) and is_active(_utc("2025-03-04 15:59")) and is_active(_utc("2025-03-04 10:29"))
    assert not is_active(_utc("2025-03-04 11:00")) and not is_active(_utc("2025-03-04 06:59")) and not is_active(_utc("2025-03-04 12:30"))
    assert not is_active(_utc("2025-03-08 08:00")) and not is_active(_utc("2025-03-09 14:00"))      # Saturday, Sunday


def test_monitor_finds_every_backtest_setup_once_and_wakes_the_llm_only_when_needed():
    reset()
    sent = []
    llm = FakeLLM(lambda m: LLMError("no LLM in this test"))             # every setup goes through the fallback alert
    mon = Monitor(ReplaySource({("EURUSD", 5): BARS}), BUNDLE, [("EURUSD", 5)], llm, SimClock(START), set(),
                  alert_fn=lambda t: sent.append(t) or {"sent": True, "channel": "test"}, max_age_minutes=45, verbose=False)
    stats = mon.run(until=UNTIL)
    got = sorted(pd.Timestamp(r["signal_time"], tz="UTC") for r in J.recent(500))
    expected = sorted(SETUPS[(SETUPS.time >= START) & (SETUPS.time < UNTIL - pd.Timedelta(hours=1))].time)
    assert expected, "pick another day: the backtest has no setup in this window"
    assert set(expected) <= set(got), (expected, got)                    # the live loop misses nothing the backtest found
    assert len(got) == len(set(got)) == len(sent) == stats["alerts"]     # each exactly once, each alerted
    assert llm.calls == stats["setups"] == len(got)                      # the LLM was woken once per setup, never for quiet scans
    assert stats["ticks"] > 40 and stats["errors"] == 0
    print(f"   {len(got)} setup(s), {stats['jobs']} scans, {llm.calls} LLM wake-up(s)")


def test_weekend_runs_no_jobs_at_all():
    reset()
    sat = _utc("2025-03-08 07:00")
    mon = Monitor(ReplaySource({("EURUSD", 5): BARS}), BUNDLE, [("EURUSD", 5)], FakeLLM(lambda m: LLMError("x")), SimClock(sat), set(), verbose=False)
    stats = mon.run(until=sat + pd.Timedelta(hours=8))
    assert stats["jobs"] == 0 and stats["ticks"] > 0


def test_a_failing_job_never_stops_the_loop_and_warns_once():
    reset()
    class Broken:
        def bars(self, pair, tf, now): raise RuntimeError("data source down")
    warnings = []
    mon = Monitor(Broken(), BUNDLE, [("EURUSD", 5)], FakeLLM(lambda m: LLMError("x")), SimClock(_utc("2025-03-04 08:00")), set(),
                  alert_fn=lambda t: warnings.append(t) or {"sent": True}, verbose=False)
    stats = mon.run(until=_utc("2025-03-04 08:50"))
    assert stats["errors"] >= 9 and len(warnings) == 1 and "failed 5 times" in warnings[0], (stats, warnings)
    assert any(r["event"] == "ERROR" for r in J.recent_log(50))


if __name__ == "__main__":
    try:
        for name, fn in list(globals().items()):
            if name.startswith("test_"):
                fn(); print("PASS", name)
    finally:
        import mysql.connector
        from db_config import DB_HOST, DB_PASSWORD, DB_PORT, DB_USER
        c = mysql.connector.connect(host=DB_HOST, user=DB_USER, password=DB_PASSWORD, port=DB_PORT)
        c.cursor().execute("DROP DATABASE IF EXISTS nexus_forex_test"); c.close()
