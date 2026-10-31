import hashlib
import json
import os
from datetime import datetime

import mysql.connector
from mysql.connector import Error

from db_config import DB_HOST, DB_USER, DB_PASSWORD, DB_NAME, DB_PORT


def _hash(password: str) -> str:
    return hashlib.sha256(password.encode()).hexdigest()


def _get_conn():
    return mysql.connector.connect(
        host=DB_HOST,
        user=DB_USER,
        password=DB_PASSWORD,
        database=DB_NAME,
        port=DB_PORT,
    )


def init_db():
    """Database aur tables create karo agar exist nahi karte."""
    conn = mysql.connector.connect(
        host=DB_HOST, user=DB_USER, password=DB_PASSWORD, port=DB_PORT
    )
    cur = conn.cursor()
    cur.execute(f"CREATE DATABASE IF NOT EXISTS `{DB_NAME}`")
    cur.execute(f"USE `{DB_NAME}`")

    cur.execute("""
        CREATE TABLE IF NOT EXISTS users (
            username      VARCHAR(50)  PRIMARY KEY,
            password_hash VARCHAR(64)  NOT NULL,
            full_name     VARCHAR(100) DEFAULT '',
            email         VARCHAR(100) DEFAULT '',
            created_at    VARCHAR(20)
        )
    """)

    cur.execute("""
        CREATE TABLE IF NOT EXISTS prediction_history (
            id          INT AUTO_INCREMENT PRIMARY KEY,
            username    VARCHAR(50)  NOT NULL,
            timestamp   VARCHAR(20)  NOT NULL,
            pair        VARCHAR(10)  NOT NULL,
            `signal`    VARCHAR(10)  NOT NULL,
            entry       DECIMAL(12,5),
            stop_loss   DECIMAL(12,5),
            take_profit DECIMAL(12,5),
            rr          VARCHAR(10),
            outcome     VARCHAR(10)  DEFAULT 'PENDING',
            INDEX idx_user (username)
        )
    """)

    # outcome column add karo agar purani table mein nahi hai
    try:
        cur.execute(
            "ALTER TABLE prediction_history ADD COLUMN outcome VARCHAR(10) DEFAULT 'PENDING'"
        )
        conn.commit()
    except Error:
        pass  # Already exists

    # Default admin
    cur.execute("SELECT username FROM users WHERE username='admin'")
    if not cur.fetchone():
        cur.execute(
            "INSERT INTO users (username,password_hash,full_name,email,created_at)"
            " VALUES (%s,%s,%s,%s,%s)",
            ("admin", _hash("admin123"), "Administrator", "admin@nexusfx.com", "2024-01-01"),
        )

    _migrate_users_json(cur)

    conn.commit()
    cur.close()
    conn.close()


def _migrate_users_json(cur):
    users_file = "users.json"
    if not os.path.exists(users_file):
        return
    with open(users_file, "r", encoding="utf-8") as f:
        users = json.load(f)
    for uname, data in users.items():
        cur.execute("SELECT username FROM users WHERE username=%s", (uname,))
        if not cur.fetchone():
            cur.execute(
                "INSERT INTO users (username,password_hash,full_name,email,created_at)"
                " VALUES (%s,%s,%s,%s,%s)",
                (
                    uname,
                    data.get("password_hash", ""),
                    data.get("full_name", ""),
                    data.get("email", ""),
                    data.get("created_at", datetime.now().strftime("%Y-%m-%d")),
                ),
            )


# ── Auth ────────────────────────────────────────────────────────────────────────

def db_verify_login(username: str, password: str) -> bool:
    try:
        conn = _get_conn()
        cur  = conn.cursor()
        cur.execute("SELECT password_hash FROM users WHERE username=%s", (username,))
        row = cur.fetchone()
        cur.close(); conn.close()
        return bool(row) and row[0] == _hash(password)
    except Error:
        return False


def db_create_user(username, password, confirm, full_name="", email=""):
    username = username.strip()
    if not username or not password:
        return False, "Username and password are required."
    if len(username) < 3:
        return False, "Username must be at least 3 characters."
    if len(password) < 6:
        return False, "Password must be at least 6 characters."
    if password != confirm:
        return False, "Passwords do not match."
    try:
        conn = _get_conn()
        cur  = conn.cursor()
        cur.execute("SELECT username FROM users WHERE username=%s", (username,))
        if cur.fetchone():
            cur.close(); conn.close()
            return False, "Username already taken — please choose another."
        cur.execute(
            "INSERT INTO users (username,password_hash,full_name,email,created_at)"
            " VALUES (%s,%s,%s,%s,%s)",
            (username, _hash(password), full_name.strip(), email.strip(),
             datetime.now().strftime("%Y-%m-%d")),
        )
        conn.commit()
        cur.close(); conn.close()
        return True, "Account created successfully! You can now sign in."
    except Error as e:
        return False, f"Database error: {e}"


# ── History ──────────────────────────────────────────────────────────────────────

def db_save_history(username: str, record: dict) -> bool:
    """Prediction record save karo. Returns True on success, False on failure."""
    try:
        conn = _get_conn()
        cur  = conn.cursor()
        cur.execute(
            """INSERT INTO prediction_history
               (username, timestamp, pair, `signal`, entry, stop_loss, take_profit, rr, outcome)
               VALUES (%s,%s,%s,%s,%s,%s,%s,%s,'PENDING')""",
            (
                username,
                record["Timestamp"],
                record["Pair"],
                record["Signal"],
                record["Entry"],
                record["Stop Loss"],
                record["Take Profit"],
                record["R:R"],
            ),
        )
        conn.commit()
        cur.close(); conn.close()
        return True
    except Error as e:
        raise RuntimeError(f"DB save failed: {e}") from e


def db_load_history(username: str) -> list:
    """Is user ki puri history load karo (id aur outcome ke saath)."""
    try:
        conn = _get_conn()
        cur  = conn.cursor(dictionary=True)
        cur.execute(
            """SELECT
                   id,
                   timestamp   AS `Timestamp`,
                   pair        AS `Pair`,
                   `signal`    AS `Signal`,
                   entry       AS `Entry`,
                   stop_loss   AS `Stop Loss`,
                   take_profit AS `Take Profit`,
                   rr          AS `R:R`,
                   outcome     AS `Outcome`
               FROM prediction_history
               WHERE username=%s
               ORDER BY id ASC""",
            (username,),
        )
        rows = cur.fetchall()
        cur.close(); conn.close()
        for r in rows:
            for k in ("Entry", "Stop Loss", "Take Profit"):
                if r[k] is not None:
                    r[k] = float(r[k])
        return rows
    except Error:
        return []


def db_clear_history(username: str):
    try:
        conn = _get_conn()
        cur  = conn.cursor()
        cur.execute("DELETE FROM prediction_history WHERE username=%s", (username,))
        conn.commit()
        cur.close(); conn.close()
    except Error:
        pass


def db_update_outcome(record_id: int, outcome: str):
    """Signal ka outcome update karo — PROFIT, LOSS, ya PENDING."""
    try:
        conn = _get_conn()
        cur  = conn.cursor()
        cur.execute(
            "UPDATE prediction_history SET outcome=%s WHERE id=%s",
            (outcome, record_id),
        )
        conn.commit()
        cur.close(); conn.close()
    except Error:
        pass


def db_get_pending_signals(username: str) -> list:
    """Un signals ko fetch karo jinki outcome abhi PENDING hai."""
    try:
        conn = _get_conn()
        cur  = conn.cursor(dictionary=True)
        cur.execute(
            """SELECT id,
                      timestamp   AS `Timestamp`,
                      pair        AS `Pair`,
                      `signal`    AS `Signal`,
                      entry       AS `Entry`,
                      stop_loss   AS `Stop Loss`,
                      take_profit AS `Take Profit`
               FROM prediction_history
               WHERE username=%s AND (outcome='PENDING' OR outcome IS NULL)
               ORDER BY id ASC""",
            (username,),
        )
        rows = cur.fetchall()
        cur.close(); conn.close()
        for r in rows:
            for k in ("Entry", "Stop Loss", "Take Profit"):
                if r[k] is not None:
                    r[k] = float(r[k])
        return rows
    except Error:
        return []
