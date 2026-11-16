"""Run with:  python test_agent_tab.py   (needs MySQL running and Streamlit installed; uses the throw-away database nexus_forex_test)
Renders the Agent tab headlessly with Streamlit's test runner and checks it shows the journal, honest statistics and the alert detail."""
import pandas as pd
from streamlit.testing.v1 import AppTest

import utils.db as D

D.DB_NAME = "nexus_forex_test"

from agent import journal as J

SCRIPT = """
import utils.db as D
D.DB_NAME = "nexus_forex_test"
from tabs.agent_tab import render_agent_tab
render_agent_tab()
"""


def _setup(t, direction="BUY"):
    sl, tp = (1.0990, 1.1020) if direction == "BUY" else (1.1010, 1.0980)
    return ({"pair": "EURUSD", "tf": 5, "signal_time": pd.Timestamp(t, tz="UTC"), "direction": direction, "entry": 1.1000, "sl": sl, "tp": tp, "rr": 2.0},
            {"p_win": 0.41, "quality": "higher" if direction == "BUY" else "lower", "factors": [{"factor": "12h momentum with the trade", "effect": "helps", "strength": 0.1}]})


def test_tab_renders_empty_then_with_data():
    J.init_journal()
    J._run("DELETE FROM agent_journal"); J._run("DELETE FROM agent_log")
    at = AppTest.from_string(SCRIPT).run(timeout=30)
    assert not at.exception, at.exception
    assert any("No agent activity" in m.value for m in at.markdown), "empty state missing"

    ids = []
    for t, d in (("2025-03-04 08:00", "BUY"), ("2025-03-04 09:00", "SELL"), ("2025-03-04 14:00", "BUY")):
        i, _ = J.log_setup(*_setup(t, d)); ids.append(i)
        J.set_explanation(i, f"EURUSD {d} setup at 1.1000, quality note"); J.mark_alerted(i)
    J._run("UPDATE agent_journal SET outcome='PROFIT', r_result=2.0 WHERE id=%s", (ids[0],))
    J._run("UPDATE agent_journal SET outcome='LOSS', r_result=-1.0 WHERE id=%s", (ids[1],))
    J.log_event(None, None, "HEARTBEAT", {"active": True})

    at = AppTest.from_string(SCRIPT).run(timeout=30)
    assert not at.exception, at.exception
    html = " ".join(m.value for m in at.markdown)
    for text in ("Setups seen", "Alerts sent", "Resolved", "Pending", "All setups", "Model: higher quality", "Model: lower quality"):
        assert text in html, text
    assert "<div class='ag-val'>3</div>" in html                              # 3 setups seen
    assert ">2</div>" in html                                                 # 2 resolved
    assert "too few to judge" in html                                         # small samples are flagged, not celebrated
    assert any("Monitor running" in s.value for s in at.success), "heartbeat status missing"
    assert any("quality note" in i.value for i in at.info), "alert detail missing"
    assert len(at.dataframe) >= 2                                             # journal table + activity log
    assert "1.10000" in at.dataframe[0].value.to_string()                     # prices keep their 5 decimals (not rounded to 1.1)
    assert "weak evidence" in html                                            # honesty note is always shown


def test_replay_mode_reads_the_separate_database_and_restores_the_name():
    J.init_journal()
    at = AppTest.from_string(SCRIPT).run(timeout=30)
    at.radio[0].set_value("Replay demo").run(timeout=30)
    assert not at.exception, at.exception
    assert D.DB_NAME == "nexus_forex_test"                                 # never left pointing at the replay database


if __name__ == "__main__":
    try:
        for name, fn in list(globals().items()):
            if name.startswith("test_"):
                fn(); print("PASS", name)
    finally:
        import mysql.connector
        from db_config import DB_HOST, DB_PASSWORD, DB_PORT, DB_USER
        c = mysql.connector.connect(host=DB_HOST, user=DB_USER, password=DB_PASSWORD, port=DB_PORT)
        cur = c.cursor(); cur.execute("DROP DATABASE IF EXISTS nexus_forex_test"); cur.execute("DROP DATABASE IF EXISTS nexus_forex_test_replay"); c.close()
