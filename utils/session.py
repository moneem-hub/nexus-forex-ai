"""
Keep users signed in across a browser refresh, with an INACTIVITY timeout.

How it works
  - At login, the server creates a random session token and stores only its SHA-256 hash in MySQL (table user_sessions).
  - The token is kept in the page URL as ?sid=...; a browser refresh keeps the URL, so the user is recognised again.
  - Every page run refreshes the session's last_seen (sliding timeout). After IDLE_MINUTES without any interaction, or
    MAX_HOURS after login, the session is rejected and the user must sign in again.
  - Sign Out deletes the session, so the old URL stops working.

Trade-off, stated honestly: a token in the URL is simpler to build and test than a cookie, but anyone who copies the URL
can use that session until it expires. Fine for a local demo; a cookie is the production-grade choice.
"""
import hashlib
import os
import secrets

import streamlit as st

from utils.db import _get_conn, init_db

IDLE_MINUTES = int(os.getenv("SESSION_IDLE_MINUTES", "30"))
MAX_HOURS = int(os.getenv("SESSION_MAX_HOURS", "12"))
PARAM = "sid"


def _hash(token: str) -> str:
    return hashlib.sha256(token.encode("utf-8")).hexdigest()


def _run(sql: str, params: tuple = ()):
    conn = _get_conn()
    try:
        cur = conn.cursor()
        cur.execute(sql, params)
        conn.commit()
        cur.close()
    finally:
        conn.close()


def _fetch(sql: str, params: tuple = ()):
    conn = _get_conn()
    try:
        cur = conn.cursor()
        cur.execute(sql, params)
        rows = cur.fetchall()
        cur.close()
        return rows
    finally:
        conn.close()


def init_sessions() -> None:
    init_db()                                    # makes sure the database exists (the app already does this at start-up)
    _run("""CREATE TABLE IF NOT EXISTS user_sessions (
              token_hash CHAR(64)    PRIMARY KEY,
              username   VARCHAR(50) NOT NULL,
              created_at DATETIME    NOT NULL,
              last_seen  DATETIME    NOT NULL,
              INDEX idx_user (username)
            )""")


def create_session(username: str) -> str:
    token = secrets.token_urlsafe(32)
    _run("DELETE FROM user_sessions WHERE last_seen < UTC_TIMESTAMP() - INTERVAL 1 DAY")          # tidy up old rows
    _run("INSERT INTO user_sessions (token_hash, username, created_at, last_seen) VALUES (%s,%s,UTC_TIMESTAMP(),UTC_TIMESTAMP())",
         (_hash(token), username))
    return token


def validate_session(token: str) -> str | None:
    """Return the username if the session is alive (and extend it), otherwise None (and remove it)."""
    if not token:
        return None
    h = _hash(token)
    rows = _fetch("SELECT username FROM user_sessions WHERE token_hash=%s "
                  "AND last_seen >= UTC_TIMESTAMP() - INTERVAL %s MINUTE AND created_at >= UTC_TIMESTAMP() - INTERVAL %s HOUR",
                  (h, IDLE_MINUTES, MAX_HOURS))
    if not rows:
        _run("DELETE FROM user_sessions WHERE token_hash=%s", (h,))
        return None
    _run("UPDATE user_sessions SET last_seen=UTC_TIMESTAMP() WHERE token_hash=%s", (h,))
    return rows[0][0]


def destroy_session(token: str) -> None:
    if token:
        _run("DELETE FROM user_sessions WHERE token_hash=%s", (_hash(token),))


# ── Streamlit glue ────────────────────────────────────────────────────────────────────
def start_session(username: str) -> None:
    token = create_session(username)
    st.session_state["sid"] = token
    st.query_params[PARAM] = token


def end_session() -> None:
    destroy_session(st.session_state.get("sid") or st.query_params.get(PARAM, ""))
    if PARAM in st.query_params:
        del st.query_params[PARAM]


def _logged_out(message: str) -> None:
    st.session_state["logged_in"] = False
    st.session_state["username"] = ""
    st.session_state.pop("sid", None)
    st.session_state.pop("history", None)
    if PARAM in st.query_params:
        del st.query_params[PARAM]
    st.session_state["flash"] = message


def restore_login() -> None:
    """Call at the top of every script run, after the session defaults."""
    expired = f"Your session ended after {IDLE_MINUTES} minutes of inactivity. Please sign in again."
    if st.session_state.get("logged_in"):
        sid = st.session_state.get("sid")
        if sid and validate_session(sid) is None:                 # sliding timeout: every run extends it; stale ones end here
            _logged_out(expired)
        return
    token = st.query_params.get(PARAM)
    if not token:
        return
    user = validate_session(token)
    if user:
        st.session_state["logged_in"], st.session_state["username"], st.session_state["sid"] = True, user, token
    else:
        _logged_out(expired)
