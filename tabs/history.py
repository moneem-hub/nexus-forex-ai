import streamlit as st
import pandas as pd
import yfinance as yf

from utils.db import (
    db_save_history, db_load_history, db_clear_history,
    db_update_outcome, db_get_pending_signals,
)
from utils.ict_strategy import check_outcome


PAIR_TICKER = {
    "EURUSD": "EURUSD=X",
    "GBPUSD": "GBPUSD=X",
    "USDJPY": "USDJPY=X",
}


def load_history():
    username = st.session_state.get("username", "")
    if not username:
        return []
    return db_load_history(username)


def save_history(record: dict) -> bool:
    """MySQL mein save karo. True = success, False = failure (shown in UI)."""
    username = st.session_state.get("username", "")
    if not username:
        return False
    db_save_history(username, record)
    return True


def _outcome_badge(outcome: str) -> str:
    if outcome == "PROFIT":
        return (
            "<span style='background:#065F46;color:#6EE7B7;padding:2px 10px;"
            "border-radius:20px;font-size:.68rem;font-weight:700;'>✓ PROFIT</span>"
        )
    if outcome == "LOSS":
        return (
            "<span style='background:#7F1D1D;color:#FCA5A5;padding:2px 10px;"
            "border-radius:20px;font-size:.68rem;font-weight:700;'>✗ LOSS</span>"
        )
    return (
        "<span style='background:#374151;color:#9CA3AF;padding:2px 10px;"
        "border-radius:20px;font-size:.68rem;font-weight:700;'>⏳ PENDING</span>"
    )


def _refresh_outcomes():
    """PENDING sinyallerin TP/SL durumunu kontrol et ve DB'yi güncelle."""
    username = st.session_state.get("username", "")
    if not username:
        return

    pending = db_get_pending_signals(username)
    if not pending:
        return

    # Unique pairs ke liye price data download karo (60 din)
    pair_data = {}
    for pair_label in {r["Pair"] for r in pending}:
        ticker = PAIR_TICKER.get(pair_label, pair_label + "=X")
        try:
            df = yf.download(
                ticker,
                period="60d",
                interval="5m",
                auto_adjust=True,
                progress=False,
            )
            if not df.empty:
                if isinstance(df.columns, pd.MultiIndex):
                    df.columns = df.columns.get_level_values(0)
                df.columns = [str(c).strip() for c in df.columns]
                col_map = {}
                for c in df.columns:
                    cl = c.lower()
                    if cl == "high":   col_map[c] = "High"
                    elif cl == "low":  col_map[c] = "Low"
                    elif cl in ("close", "adj close"): col_map[c] = "Close"
                df = df.rename(columns=col_map)
                pair_data[pair_label] = df
        except Exception:
            pass

    # Her pending signal ke liye outcome check karo
    updated = 0
    for rec in pending:
        df = pair_data.get(rec["Pair"])
        if df is None:
            continue
        outcome = check_outcome(
            df,
            rec["Timestamp"],
            rec["Signal"],
            rec["Entry"],
            rec["Stop Loss"],
            rec["Take Profit"],
        )
        if outcome != "PENDING":
            db_update_outcome(rec["id"], outcome)
            updated += 1

    # Session state refresh
    st.session_state["history"] = load_history()
    return updated


def _sec(text: str) -> str:
    return f"""<div class='sec-hdr'>
        <div class='sec-bar'></div>
        <span class='sec-txt'>{text}</span>
        <span class='sec-line'></span>
    </div>"""


def render_history_tab():
    st.markdown("<br>", unsafe_allow_html=True)
    st.markdown(_sec("Prediction History — All Pairs"), unsafe_allow_html=True)

    # ── Outcome refresh button ─────────────────────────────────────────────────
    col_ref, _ = st.columns([1, 3])
    with col_ref:
        if st.button("🔄  Check Outcomes", use_container_width=True):
            with st.spinner("Checking TP/SL outcomes…"):
                n = _refresh_outcomes()
            if n:
                st.success(f"✓ {n} outcome(s) updated.")
            else:
                st.info("No new outcomes found — signals may still be pending.")

    st.markdown("<br>", unsafe_allow_html=True)

    if not st.session_state.history:
        st.markdown("""
        <div class='empty-box'>
            <div class='empty-ico'>📋</div>
            <div class='empty-ttl'>No predictions yet</div>
            <div class='empty-sub'>Run predictions in the New Prediction tab — they will appear here.</div>
        </div>""", unsafe_allow_html=True)
        return

    # ── Stats ─────────────────────────────────────────────────────────────────
    history = st.session_state.history
    buy     = sum(1 for h in history if h.get("Signal") == "BUY")
    sell    = sum(1 for h in history if h.get("Signal") == "SELL")
    profit  = sum(1 for h in history if h.get("Outcome") == "PROFIT")
    loss    = sum(1 for h in history if h.get("Outcome") == "LOSS")
    total   = len(history)

    m1, m2, m3, m4, m5 = st.columns(5)
    stats = [
        ("Total",        str(total),  "#111844", "stat-card-navy"),
        ("Buy Signals",  str(buy),    "#059669", "stat-card-green"),
        ("Sell Signals", str(sell),   "#DC2626", "stat-card-red"),
        ("Profit",       str(profit), "#059669", "stat-card-green"),
        ("Loss",         str(loss),   "#DC2626", "stat-card-red"),
    ]
    for col, (label, val, color, cls) in zip([m1, m2, m3, m4, m5], stats):
        with col:
            st.markdown(f"""
            <div class='stat-card {cls}'>
                <div class='stat-lbl'>{label}</div>
                <div class='stat-val' style='color:{color};'>{val}</div>
            </div>""", unsafe_allow_html=True)

    # ── Table — Outcome column as colored badge ────────────────────────────────
    df = pd.DataFrame(history)

    # id column hide karo agar hai
    display_cols = [c for c in df.columns if c != "id"]
    df_display   = df[display_cols].copy()

    # Outcome ko simple text (styled separately below)
    st.dataframe(df_display, use_container_width=True, hide_index=True)

    # ── Outcome badges visual row ─────────────────────────────────────────────
    if "Outcome" in df.columns:
        badges_html = "<div style='display:flex;flex-wrap:wrap;gap:6px;margin:6px 0 14px;'>"
        for _, row in df.iterrows():
            pair    = row.get("Pair", "?")
            sig     = row.get("Signal", "?")
            outcome = row.get("Outcome", "PENDING")
            badge   = _outcome_badge(str(outcome))
            badges_html += (
                f"<span style='font-family:JetBrains Mono,monospace;font-size:.68rem;"
                f"color:#D4DEFA;'>{pair} {sig}</span> {badge} &nbsp;"
            )
        badges_html += "</div>"
        st.markdown(badges_html, unsafe_allow_html=True)

    # ── Action buttons ─────────────────────────────────────────────────────────
    st.markdown("<br>", unsafe_allow_html=True)
    col_dl, col_clr, _ = st.columns([1, 1, 2])
    with col_dl:
        st.download_button(
            "↓  Export CSV",
            df_display.to_csv(index=False),
            "nexus_ict_predictions.csv",
            "text/csv",
            use_container_width=True,
        )
    with col_clr:
        if st.button("🗑  Clear History", use_container_width=True):
            username = st.session_state.get("username", "")
            if username:
                db_clear_history(username)
            st.session_state.history = []
            st.rerun()
