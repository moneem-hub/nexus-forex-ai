"""
Run with:  python test_session.py     (needs MySQL running; uses the throw-away database nexus_forex_test)
Tests: staying signed in across a refresh, inactivity timeout (sliding), maximum lifetime, sign-out, tampered tokens,
and the New Prediction page restoring the latest saved signal.
"""
import utils.db as D

D.DB_NAME = "nexus_forex_test"

from streamlit.testing.v1 import AppTest

from utils import session as S

HARNESS = """
import utils.db as D
D.DB_NAME = "nexus_forex_test"
import streamlit as st
from utils.session import init_sessions, restore_login
st.session_state.setdefault('logged_in', False)
st.session_state.setdefault('username', '')
init_sessions()
restore_login()
st.write('STATE:' + ('IN:' + st.session_state.username if st.session_state.logged_in else 'OUT'))
"""

START_END = """
import utils.db as D
D.DB_NAME = "nexus_forex_test"
import streamlit as st
from utils.session import init_sessions, start_session, end_session
init_sessions()
if st.session_state.get('mode') == 'end':
    end_session()
else:
    start_session('admin')
"""


def state(at):
    return next(m.value for m in at.markdown if "STATE:" in m.value)


def run_with(token=None, at=None):
    at = at or AppTest.from_string(HARNESS)
    if token is not None:
        at.query_params["sid"] = token
    return at.run(timeout=120)


def age(token, last_seen_minutes=None, created_hours=None):
    h = S._hash(token)
    if last_seen_minutes is not None:
        S._run("UPDATE user_sessions SET last_seen = UTC_TIMESTAMP() - INTERVAL %s MINUTE WHERE token_hash=%s", (last_seen_minutes, h))
    if created_hours is not None:
        S._run("UPDATE user_sessions SET created_at = UTC_TIMESTAMP() - INTERVAL %s HOUR WHERE token_hash=%s", (created_hours, h))


def reset():
    S.init_sessions()
    S._run("DELETE FROM user_sessions")


def test_token_is_stored_hashed_never_in_plain_text():
    reset()
    token = S.create_session("admin")
    rows = S._fetch("SELECT token_hash, username FROM user_sessions")
    assert rows == [(S._hash(token), "admin")] and token not in rows[0][0] and len(token) >= 40


def test_refresh_with_a_valid_token_keeps_the_user_signed_in():
    reset(); token = S.create_session("admin")
    assert state(run_with(token)) == "STATE:IN:admin"
    assert state(run_with()) == "STATE:OUT"                                   # no token (e.g. a brand-new visit) = login required


def test_wrong_or_tampered_token_is_rejected_and_removed_from_the_url():
    reset(); token = S.create_session("admin")
    at = run_with(token[:-3] + "xyz")
    assert state(at) == "STATE:OUT" and "sid" not in at.query_params


def test_inactivity_timeout_ends_the_session_with_a_message():
    reset(); token = S.create_session("admin")
    age(token, last_seen_minutes=S.IDLE_MINUTES + 1)
    at = run_with(token)
    assert state(at) == "STATE:OUT" and "inactivity" in at.session_state["flash"]
    assert S._fetch("SELECT COUNT(*) FROM user_sessions")[0][0] == 0           # the dead session is removed


def test_activity_extends_the_session_sliding_timeout():
    reset(); token = S.create_session("admin")
    age(token, last_seen_minutes=S.IDLE_MINUTES - 5)                           # nearly expired...
    assert state(run_with(token)) == "STATE:IN:admin"                          # ...but still valid, and this visit extends it
    secs = S._fetch("SELECT TIMESTAMPDIFF(SECOND, last_seen, UTC_TIMESTAMP()) FROM user_sessions")[0][0]
    assert secs < 60


def test_session_has_a_maximum_lifetime_even_if_always_active():
    reset(); token = S.create_session("admin")
    age(token, created_hours=S.MAX_HOURS + 1)
    assert state(run_with(token)) == "STATE:OUT"


def test_signing_out_destroys_the_session():
    reset(); token = S.create_session("admin")
    S.destroy_session(token)
    assert state(run_with(token)) == "STATE:OUT"


def test_an_open_page_is_signed_out_at_its_next_interaction_after_going_idle():
    reset(); token = S.create_session("admin")
    at = run_with(token)
    assert state(at) == "STATE:IN:admin"
    age(token, last_seen_minutes=S.IDLE_MINUTES + 1)                           # the user walks away...
    at = run_with(at=at)                                                       # ...and comes back to click something
    assert state(at) == "STATE:OUT" and "inactivity" in at.session_state["flash"]


def test_start_and_end_session_manage_the_url_token():
    reset()
    at = AppTest.from_string(START_END).run(timeout=120)
    token = at.query_params["sid"][0] if isinstance(at.query_params["sid"], list) else at.query_params["sid"]
    assert token and S._fetch("SELECT COUNT(*) FROM user_sessions")[0][0] == 1
    at.session_state["mode"] = "end"
    at.run(timeout=120)
    assert "sid" not in at.query_params and S._fetch("SELECT COUNT(*) FROM user_sessions")[0][0] == 0


def test_new_prediction_page_restores_the_latest_saved_signal_for_the_pair():
    script = """
import streamlit as st
st.session_state['history'] = [
  {"Timestamp": "2026-11-18 08:00", "Pair": "EURUSD", "Signal": "BUY",  "Entry": 1.10000, "Stop Loss": 1.09900, "Take Profit": 1.10200, "R:R": "1:2.0", "Outcome": "LOSS"},
  {"Timestamp": "2026-11-19 09:25", "Pair": "EURUSD", "Signal": "SELL", "Entry": 1.11111, "Stop Loss": 1.11211, "Take Profit": 1.10911, "R:R": "1:2.0", "Outcome": "PENDING"},
  {"Timestamp": "2026-11-19 10:00", "Pair": "GBPUSD", "Signal": "BUY",  "Entry": 1.31313, "Stop Loss": 1.31213, "Take Profit": 1.31513, "R:R": "1:2.0", "Outcome": "PENDING"},
]
from tabs.prediction import render_prediction_tab
render_prediction_tab("EURUSD=X", "EURUSD")
"""
    at = AppTest.from_string(script).run(timeout=120)
    html = " ".join(m.value for m in at.markdown)
    assert "restored from history" in html and "1.11111" in html              # the NEWEST EURUSD signal
    assert "1.10000" not in html and "1.31313" not in html                    # not the older one, not another pair
    assert "1.10961" in html                                                  # TP1 (1.5R below a SELL at 1.11111 with a 0.001 stop)


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
