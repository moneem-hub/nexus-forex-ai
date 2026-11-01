"""
The agent's trade journal and activity log, in the SAME MySQL database the app already uses.
Two NEW tables; your existing tables are never touched.

  agent_journal : one row per setup the agent saw (score, quality, reasons, alert status, outcome, result in R)
  agent_log     : what the agent did and when (scans, setups, alerts, outcome checks, errors)

A UNIQUE key on (pair, timeframe, signal time) means a setup can never be journaled twice, even after a restart.
Times are stored as UTC. Outcome labels follow the training data: PROFIT / LOSS within 24 hours of the signal,
otherwise EXPIRED. Only PROFIT and LOSS count in the statistics.
"""
import json
from datetime import timedelta

import pandas as pd
from mysql.connector import Error, errorcode

from utils.db import _get_conn, init_db
from utils.ict_strategy import check_outcome

HORIZON = timedelta(hours=24)


def _utc_naive(ts) -> "datetime":
    return pd.Timestamp(ts).tz_convert("UTC").tz_localize(None).to_pydatetime()


def _fetch(sql: str, params: tuple = ()) -> list[dict]:
    conn = _get_conn()
    try:
        cur = conn.cursor(dictionary=True)
        cur.execute(sql, params)
        rows = cur.fetchall()
        cur.close()
        return rows
    finally:
        conn.close()


def _run(sql: str, params: tuple = ()) -> None:
    conn = _get_conn()
    try:
        cur = conn.cursor()
        cur.execute(sql, params)
        conn.commit()
        cur.close()
    finally:
        conn.close()


def init_journal() -> None:
    init_db()                                       # makes sure the database exists (what the app does at start-up)
    _run("""CREATE TABLE IF NOT EXISTS agent_journal (
              id            INT AUTO_INCREMENT PRIMARY KEY,
              pair          VARCHAR(10)  NOT NULL,
              tf_min        INT          NOT NULL,
              signal_time   DATETIME     NOT NULL,
              direction     VARCHAR(4)   NOT NULL,
              entry         DECIMAL(14,5), sl DECIMAL(14,5), tp DECIMAL(14,5),
              rr            DECIMAL(6,2),
              p_win         DECIMAL(6,4),
              quality       VARCHAR(8),
              factors       TEXT,
              explanation   TEXT,
              alerted       TINYINT      NOT NULL DEFAULT 0,
              alert_time    DATETIME     NULL,
              outcome       VARCHAR(10)  NOT NULL DEFAULT 'PENDING',
              resolved_time DATETIME     NULL,
              r_result      DECIMAL(6,2) NULL,
              created_at    DATETIME     NOT NULL DEFAULT CURRENT_TIMESTAMP,
              UNIQUE KEY uq_setup (pair, tf_min, signal_time),
              INDEX idx_outcome (outcome)
            )""")
    _run("""CREATE TABLE IF NOT EXISTS agent_log (
              id      INT AUTO_INCREMENT PRIMARY KEY,
              ts      DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
              pair    VARCHAR(10), tf_min INT,
              event   VARCHAR(20) NOT NULL,
              details TEXT
            )""")


# ── writing ───────────────────────────────────────────────────────────────────────────
def log_setup(setup: dict, scored: dict) -> tuple[int, bool]:
    """Journal a new setup. Returns (journal_id, is_new). A repeat of the same setup returns (existing_id, False)."""
    row = (setup["pair"], setup["tf"], _utc_naive(setup["signal_time"]), setup["direction"], setup["entry"], setup["sl"],
           setup["tp"], setup["rr"], scored["p_win"], scored.get("quality"), json.dumps(scored.get("factors", [])))
    conn = _get_conn()
    try:
        cur = conn.cursor()
        try:
            cur.execute("""INSERT INTO agent_journal (pair, tf_min, signal_time, direction, entry, sl, tp, rr, p_win, quality, factors)
                           VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)""", row)
            conn.commit()
            return cur.lastrowid, True
        except Error as e:
            if e.errno != errorcode.ER_DUP_ENTRY:
                raise
            cur.execute("SELECT id FROM agent_journal WHERE pair=%s AND tf_min=%s AND signal_time=%s", row[:3])
            return cur.fetchone()[0], False
    finally:
        conn.close()


def set_explanation(journal_id: int, text: str) -> None:
    _run("UPDATE agent_journal SET explanation=%s WHERE id=%s", (text, journal_id))


def mark_alerted(journal_id: int) -> None:
    _run("UPDATE agent_journal SET alerted=1, alert_time=UTC_TIMESTAMP() WHERE id=%s", (journal_id,))


def log_event(pair: str | None, tf: int | None, event: str, details="") -> None:
    if not isinstance(details, str):
        details = json.dumps(details, default=str)
    _run("INSERT INTO agent_log (pair, tf_min, event, details) VALUES (%s,%s,%s,%s)", (pair, tf, event, details[:4000]))


# ── reading ───────────────────────────────────────────────────────────────────────────
def load_seen(days: int = 3) -> set:
    """Setups already journaled recently, to seed the detector after a restart."""
    rows = _fetch("SELECT pair, tf_min, signal_time FROM agent_journal WHERE signal_time >= UTC_TIMESTAMP() - INTERVAL %s DAY", (days,))
    return {(r["pair"], r["tf_min"], pd.Timestamp(r["signal_time"], tz="UTC")) for r in rows}


def pending() -> list[dict]:
    return _fetch("SELECT * FROM agent_journal WHERE outcome='PENDING' ORDER BY signal_time")


def recent(limit: int = 20) -> list[dict]:
    return _fetch("SELECT * FROM agent_journal ORDER BY signal_time DESC LIMIT %s", (limit,))


def recent_log(limit: int = 50) -> list[dict]:
    return _fetch("SELECT * FROM agent_log ORDER BY id DESC LIMIT %s", (limit,))


def stats(exclude_pairs: tuple = ()) -> dict:
    """Win rate and mean result (in R) for resolved setups: overall and by model quality label."""
    rows = [r for r in _fetch("SELECT pair, quality, outcome, r_result FROM agent_journal WHERE outcome IN ('PROFIT','LOSS')")
            if r["pair"] not in exclude_pairs]
    def agg(rs):
        n = len(rs)
        return {"n": n, "win_rate": (sum(r["outcome"] == "PROFIT" for r in rs) / n) if n else None,
                "mean_r": (sum(float(r["r_result"]) for r in rs) / n) if n else None}
    return {"all": agg(rows), "higher": agg([r for r in rows if r["quality"] == "higher"]),
            "lower": agg([r for r in rows if r["quality"] == "lower"])}


# ── resolving outcomes ────────────────────────────────────────────────────────────────
def resolve_pending(source, now: pd.Timestamp) -> list[dict]:
    """
    Check every PENDING setup against the bars that followed it, using the engine's own check_outcome().
    PROFIT/LOSS if take-profit or stop-loss was hit within 24h; EXPIRED if neither was (or the data is too old to check).
    """
    done = []
    for row in pending():
        sig_ts = pd.Timestamp(row["signal_time"], tz="UTC")
        outcome = None
        if now - sig_ts > pd.Timedelta(days=6):                       # older than the 7-day data window: cannot be checked
            outcome = "EXPIRED"
        else:
            bars = source.bars(row["pair"], row["tf_min"], now)
            future = bars[(bars.index > sig_ts) & (bars.index <= sig_ts + HORIZON)].copy()
            res = check_outcome(future, sig_ts.strftime("%Y-%m-%d %H:%M"), row["direction"],
                                float(row["entry"]), float(row["sl"]), float(row["tp"]))
            if res in ("PROFIT", "LOSS"):
                outcome = res
            elif now >= sig_ts + HORIZON:
                outcome = "EXPIRED"
        if outcome:
            r = {"PROFIT": float(row["rr"]), "LOSS": -1.0}.get(outcome)
            _run("UPDATE agent_journal SET outcome=%s, resolved_time=UTC_TIMESTAMP(), r_result=%s WHERE id=%s", (outcome, r, row["id"]))
            log_event(row["pair"], row["tf_min"], "OUTCOME", {"id": row["id"], "outcome": outcome})
            done.append({"id": row["id"], "pair": row["pair"], "outcome": outcome, "r": r})
    return done
