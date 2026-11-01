"""Run with:  python test_agent_journal.py   (needs your MySQL running; uses a throw-away pair named SELFTEST and cleans up)"""
import pandas as pd

from agent import journal as J

PAIR = "SELFTEST"


class FakeSource:
    """Returns hand-made bars so we know exactly what the outcome must be."""
    def __init__(self, bars): self.bars_df = bars
    def bars(self, pair, tf, now): return self.bars_df


def _bars(start, prices):
    idx = pd.date_range(start, periods=len(prices), freq="15min", tz="UTC")
    return pd.DataFrame({"Open": prices, "High": [p + 0.0002 for p in prices], "Low": [p - 0.0002 for p in prices], "Close": prices}, index=idx)


def _setup(t, direction="BUY"):
    sl, tp = (1.0990, 1.1020) if direction == "BUY" else (1.1010, 1.0980)
    return ({"pair": PAIR, "tf": 15, "signal_time": pd.Timestamp(t, tz="UTC"), "direction": direction, "entry": 1.1000, "sl": sl, "tp": tp, "rr": 2.0},
            {"p_win": 0.4123, "quality": "higher", "factors": [{"factor": "12h momentum with the trade", "effect": "helps", "strength": 0.1}]})


def _cleanup():
    J._run("DELETE FROM agent_journal WHERE pair=%s", (PAIR,))
    J._run("DELETE FROM agent_log WHERE pair=%s", (PAIR,))


def test_journal_end_to_end():
    J.init_journal()
    _cleanup()
    try:
        t_win, t_loss, t_open = "2025-03-04 10:00", "2025-03-04 14:00", "2025-03-04 23:00"
        # 1) logging, and the same setup can never be journaled twice
        i1, new1 = J.log_setup(*_setup(t_win))
        i1b, new1b = J.log_setup(*_setup(t_win))
        assert new1 and not new1b and i1 == i1b
        i2, _ = J.log_setup(*_setup(t_loss))
        i3, _ = J.log_setup(*_setup(t_open))
        # 2) the restart-safety set
        assert (PAIR, 15, pd.Timestamp(t_win, tz="UTC")) in J.load_seen(days=36500)
        # 3) the price path: after t_win it rises to the take-profit; after t_loss it falls through the stop
        bars = pd.concat([_bars("2025-03-04 10:15", [1.1005, 1.1015, 1.1030, 1.1030]),
                          _bars("2025-03-04 14:15", [1.0995, 1.0985, 1.0970, 1.0970]),
                          _bars("2025-03-04 23:15", [1.1001, 1.1002, 1.1001, 1.1001])])
        now = pd.Timestamp("2025-03-04 23:45", tz="UTC")
        done = {d["id"]: d for d in J.resolve_pending(FakeSource(bars), now)}
        assert done[i1]["outcome"] == "PROFIT" and done[i1]["r"] == 2.0
        assert done[i2]["outcome"] == "LOSS" and done[i2]["r"] == -1.0
        assert i3 not in done                                         # neither level hit yet, and 24h not over: stays PENDING
        # 4) 24h later with still no hit: EXPIRED, and expired setups are not counted in the statistics
        done2 = J.resolve_pending(FakeSource(bars), pd.Timestamp("2025-03-05 23:30", tz="UTC"))
        assert [d["outcome"] for d in done2 if d["id"] == i3] == ["EXPIRED"]
        s = J.stats()
        mine = [r for r in J.recent(500) if r["pair"] == PAIR]
        assert len(mine) == 3 and s["all"]["n"] >= 2
        # 5) alert bookkeeping and the log
        J.set_explanation(i1, "test"); J.mark_alerted(i1); J.log_event(PAIR, 15, "ALERT", {"id": i1})
        row = [r for r in J.recent(500) if r["id"] == i1][0]
        assert row["alerted"] == 1 and row["explanation"] == "test"
        assert any(r["event"] == "ALERT" and r["pair"] == PAIR for r in J.recent_log(200))
    finally:
        _cleanup()


if __name__ == "__main__":
    test_journal_end_to_end()
    print("PASS test_journal_end_to_end")
