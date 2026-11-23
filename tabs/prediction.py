import streamlit as st
import yfinance as yf

from utils.ict_strategy import run_ict_strategy
from tabs.history import save_history

PAIR_TICKER = {
    "EURUSD": "EURUSD=X",
    "GBPUSD": "GBPUSD=X",
    "USDJPY": "USDJPY=X",
}


def _sec(text):
    return (
        "<div class='sec-hdr'>"
        "<div class='sec-bar'></div>"
        f"<span class='sec-txt'>{text}</span>"
        "<span class='sec-line'></span>"
        "</div>"
    )


def _session_card(status: dict):
    in_kz = status["in_kz"]
    kz_badge = (
        "<span style='background:#059669;color:#fff;padding:3px 10px;"
        "border-radius:20px;font-size:.72rem;font-weight:700;'>✅ ACTIVE</span>"
        if in_kz else
        "<span style='background:#4B5563;color:#D1D5DB;padding:3px 10px;"
        "border-radius:20px;font-size:.72rem;font-weight:700;'>⏸ WAITING</span>"
    )
    asian_h = f"{status['asian_high']:.5f}" if status.get("asian_high") else "—"
    asian_l = f"{status['asian_low']:.5f}"  if status.get("asian_low")  else "—"

    next_kz_row = ""
    if not in_kz:
        next_kz_row = (
            "<div style='margin-top:10px;padding:8px 12px;background:#1E2D5A;"
            "border-radius:8px;font-family:JetBrains Mono,monospace;font-size:.72rem;color:#9CD5FF;'>"
            f"&#9193;  Next Kill Zone: {status['next_kz']}"
            "</div>"
        )

    cond_items = [
        ("Bullish FVG",     status.get("bull_fvg",   False)),
        ("Bearish FVG",     status.get("bear_fvg",   False)),
        ("Bull Sweep (SSL)", status.get("bull_sweep", False)),
        ("Bear Sweep (BSL)", status.get("bear_sweep", False)),
        ("Bull MSS",         status.get("bull_mss",  False)),
        ("Bear MSS",         status.get("bear_mss",  False)),
    ]
    conds = ""
    for label, present in cond_items:
        dot = "#10B981" if present else "#6B7280"
        conds += (
            f"<span style='display:inline-flex;align-items:center;gap:5px;"
            f"background:#1A2C5B;border:1px solid #2D3F6B;border-radius:6px;"
            f"padding:3px 9px;margin:3px;font-size:.7rem;color:#D4DEFA;'>"
            f"<span style='width:7px;height:7px;border-radius:50%;background:{dot};display:inline-block;'></span>"
            f"{label}</span>"
        )

    return (
        "<div style='background:#111844;border:1px solid #1E2D5A;border-radius:14px;"
        "padding:18px 20px;margin-bottom:18px;'>"
        "<div style='display:flex;align-items:center;justify-content:space-between;margin-bottom:12px;'>"
        "<span style='font-family:JetBrains Mono,monospace;font-size:.62rem;"
        "color:#7AAACE;letter-spacing:.14em;text-transform:uppercase;'>Current Session</span>"
        f"{kz_badge}"
        "</div>"
        "<div style='font-family:Roboto,sans-serif;font-size:.92rem;font-weight:700;"
        f"color:#E8F0FE;margin-bottom:10px;'>{status['session_label']}</div>"
        "<div style='display:flex;gap:20px;margin-bottom:10px;'>"
        f"<span style='font-family:JetBrains Mono,monospace;font-size:.72rem;color:#CE93D8;'>ASH: {asian_h}</span>"
        f"<span style='font-family:JetBrains Mono,monospace;font-size:.72rem;color:#CE93D8;'>ASL: {asian_l}</span>"
        "</div>"
        "<div style='margin-bottom:4px;font-family:Roboto,sans-serif;font-size:.7rem;color:#7AAACE;'>"
        "Conditions detected (last 10&#8211;15 bars):</div>"
        f"<div>{conds}</div>"
        f"{next_kz_row}"
        "</div>"
    )


def _signal_card(signal: dict):
    is_buy   = signal["direction"] == "BUY"
    sig_col  = "#10B981" if is_buy else "#EF4444"
    dir_icon = "&#9650;  BUY &#8212; LONG" if is_buy else "&#9660;  SELL &#8212; SHORT"
    bg_col   = "rgba(16,185,129,.07)" if is_buy else "rgba(239,68,68,.07)"
    bdr      = "#10B981" if is_buy else "#EF4444"
    rr_str   = f"1 : {signal['rr']:.1f}"

    return (
        f"<div style='border:1.5px solid {bdr};border-radius:14px;"
        f"background:{bg_col};padding:20px 22px;margin-bottom:16px;'>"
        f"<div style='font-family:JetBrains Mono,monospace;font-size:1.3rem;"
        f"font-weight:800;color:{sig_col};margin-bottom:14px;'>{dir_icon}</div>"
        f"<div style='font-family:Roboto,sans-serif;font-size:.72rem;color:#9CA3AF;margin-bottom:2px;'>"
        f"Session: {signal['session_label']}</div>"
        f"<div style='font-family:JetBrains Mono,monospace;font-size:.68rem;color:#7AAACE;margin-bottom:14px;'>"
        f"Signal Time (UTC): {signal['timestamp']}</div>"
        "<div style='display:grid;grid-template-columns:1fr 1fr 1fr;gap:10px;margin-bottom:14px;'>"
        "<div style='background:#1A2C5B;border-radius:10px;padding:12px 14px;'>"
        "<div style='font-size:.65rem;color:#9CA3AF;font-family:Roboto,sans-serif;margin-bottom:4px;'>Entry Price</div>"
        f"<div style='font-family:JetBrains Mono,monospace;font-size:.88rem;font-weight:700;color:#60A5FA;'>{signal['entry']:.5f}</div>"
        "</div>"
        "<div style='background:#1A2C5B;border-radius:10px;padding:12px 14px;'>"
        "<div style='font-size:.65rem;color:#9CA3AF;font-family:Roboto,sans-serif;margin-bottom:4px;'>Stop Loss</div>"
        f"<div style='font-family:JetBrains Mono,monospace;font-size:.88rem;font-weight:700;color:#EF4444;'>{signal['sl']:.5f}</div>"
        "</div>"
        "<div style='background:#1A2C5B;border-radius:10px;padding:12px 14px;'>"
        "<div style='font-size:.65rem;color:#9CA3AF;font-family:Roboto,sans-serif;margin-bottom:4px;'>Take Profit</div>"
        f"<div style='font-family:JetBrains Mono,monospace;font-size:.88rem;font-weight:700;color:#10B981;'>{signal['tp']:.5f}</div>"
        "</div>"
        "</div>"
        "<div style='display:flex;gap:10px;'>"
        "<div style='background:#111844;border-radius:8px;padding:8px 16px;"
        "font-family:JetBrains Mono,monospace;font-size:.78rem;'>"
        f"<span style='color:#9CA3AF;'>TP1 (1.5R):&nbsp;</span>"
        f"<span style='color:#FCD34D;font-weight:700;'>{signal['tp1']:.5f}</span>"
        "</div>"
        "<div style='background:#111844;border-radius:8px;padding:8px 16px;"
        "font-family:JetBrains Mono,monospace;font-size:.78rem;'>"
        f"<span style='color:#9CA3AF;'>R:R&nbsp;&nbsp;</span>"
        f"<span style='color:{sig_col};font-weight:700;'>{rr_str}</span>"
        "</div>"
        "</div>"
        "</div>"
    )


def _no_signal_card(status: dict):
    in_kz = status["in_kz"]
    if in_kz:
        msg = "In Kill Zone &#8212; waiting for full ICT setup (Sweep + MSS + FVG)"
        sub = "Conditions are being tracked above. Refresh to check for new signals."
        col = "#F59E0B"
    else:
        msg = "Not in Kill Zone &#8212; no trade zone active"
        sub = f"Next opportunity: {status.get('next_kz', 'London Kill Zone 07:00 GMT')}"
        col = "#6B7280"

    return (
        f"<div style='border:1.5px solid {col};border-radius:14px;"
        f"background:rgba(0,0,0,.2);padding:22px;text-align:center;margin-bottom:16px;'>"
        "<div style='font-size:2rem;margin-bottom:8px;'>&#9203;</div>"
        f"<div style='font-family:JetBrains Mono,monospace;font-size:.85rem;"
        f"font-weight:700;color:{col};margin-bottom:6px;'>{msg}</div>"
        f"<div style='font-family:Roboto,sans-serif;font-size:.78rem;color:#9CA3AF;'>{sub}</div>"
        "</div>"
    )


# ── Main render ────────────────────────────────────────────────────────────────

def render_prediction_tab(pair: str, pair_label: str):
    st.markdown("<br>", unsafe_allow_html=True)

    col_main, col_info = st.columns([3, 2])

    with col_main:
        st.markdown(_sec(f"ICT Kill Zone Signal  —  {pair_label}"), unsafe_allow_html=True)

        # Timeframe selector — use a unique key (not ict_tf which is stored separately)
        tf = st.radio(
            "Timeframe",
            ["5min", "15min"],
            horizontal=True,
            label_visibility="collapsed",
            key="ict_tf_radio",
        )
        tf_map = {"5min": "5m", "15min": "15m"}
        interval = tf_map[tf]

        st.markdown("<div class='cta-btn'>", unsafe_allow_html=True)
        run = st.button("&#9889;  SCAN ICT KILL ZONES", use_container_width=True)
        st.markdown("</div>", unsafe_allow_html=True)

        if run:
            with st.spinner(f"Scanning {pair_label} {tf} Kill Zone data…"):
                try:
                    ticker = PAIR_TICKER.get(pair_label, pair)
                    data   = yf.download(
                        ticker,
                        period="7d",
                        interval=interval,
                        auto_adjust=True,
                        progress=False,
                    )

                    if data.empty or len(data) < 60:
                        st.error("Not enough market data received. Try again or switch timeframe.")
                        return

                    if isinstance(data.columns, type(data.columns)) and hasattr(data.columns, "levels"):
                        data.columns = data.columns.get_level_values(0)
                    data.columns = [str(c).strip() for c in data.columns]

                    col_map = {}
                    for c in data.columns:
                        cl = c.lower()
                        if cl == "open":   col_map[c] = "Open"
                        elif cl == "high": col_map[c] = "High"
                        elif cl == "low":  col_map[c] = "Low"
                        elif cl in ("close", "adj close"): col_map[c] = "Close"
                        elif cl == "volume": col_map[c] = "Volume"
                    data = data.rename(columns=col_map)

                    required = ["Open", "High", "Low", "Close"]
                    if not all(c in data.columns for c in required):
                        st.error(f"Missing OHLC columns. Got: {list(data.columns)}")
                        return

                    signal, status = run_ict_strategy(data, pair_label)

                    st.session_state["ict_signal"]   = signal
                    st.session_state["ict_status"]   = status
                    st.session_state["ict_pair"]     = pair_label
                    st.session_state["ict_last_tf"]  = tf   # widget key se alag

                    if signal:
                        record = {
                            "Timestamp":   signal["timestamp"],
                            "Pair":        signal["pair"],
                            "Signal":      signal["direction"],
                            "Entry":       signal["entry"],
                            "Stop Loss":   signal["sl"],
                            "Take Profit": signal["tp"],
                            "R:R":         f"1:{signal['rr']:.1f}",
                        }
                        save_history(record)
                        st.session_state.history.append({**record, "Outcome": "PENDING"})
                        st.success("&#10003; ICT signal saved to history.")

                except Exception as e:
                    st.error(f"Strategy engine error: {e}")

        # ── Display last scan result ──────────────────────────────────────────
        if (
            st.session_state.get("ict_status")
            and st.session_state.get("ict_pair") == pair_label
        ):
            status = st.session_state["ict_status"]
            signal = st.session_state.get("ict_signal")
            last_tf = st.session_state.get("ict_last_tf", "5min")

            st.markdown("<br>", unsafe_allow_html=True)
            st.markdown(
                f"<div style='font-family:Roboto,sans-serif;font-size:.75rem;"
                f"color:#7AAACE;margin-bottom:6px;'>Last scan: {pair_label} &middot; {last_tf} chart</div>",
                unsafe_allow_html=True,
            )
            st.markdown(_session_card(status), unsafe_allow_html=True)

            if signal:
                st.markdown(_signal_card(signal), unsafe_allow_html=True)
            else:
                st.markdown(_no_signal_card(status), unsafe_allow_html=True)
        else:
            # After a refresh or re-login the last scan is gone from session memory: show the latest SAVED signal for this pair
            _saved = [h for h in st.session_state.get("history", []) if h.get("Pair") == pair_label]
            if _saved:
                _h = max(_saved, key=lambda r: str(r["Timestamp"]))
                try:
                    _risk = abs(float(_h["Entry"]) - float(_h["Stop Loss"]))
                    _tp1  = float(_h["Entry"]) + (1.5 * _risk if _h["Signal"] == "BUY" else -1.5 * _risk)   # the card's TP1 = 1.5R
                    _sig = {"direction": _h["Signal"], "rr": float(str(_h["R:R"]).split(":")[1]), "session_label": "saved signal",
                            "timestamp": _h["Timestamp"], "entry": float(_h["Entry"]), "sl": float(_h["Stop Loss"]),
                            "tp": float(_h["Take Profit"]), "tp1": _tp1, "pair": pair_label}
                    st.markdown("<br>", unsafe_allow_html=True)
                    st.markdown(f"<div style='font-family:Roboto,sans-serif;font-size:.75rem;color:#4A6699;margin-bottom:6px;'>"
                                f"Latest saved signal for {pair_label} (restored from history)</div>", unsafe_allow_html=True)
                    st.markdown(_signal_card(_sig), unsafe_allow_html=True)
                except (KeyError, ValueError, IndexError):
                    pass

    # ── Right info column ──────────────────────────────────────────────────────
    with col_info:
        st.markdown(_sec("ICT Strategy Rules"), unsafe_allow_html=True)
        st.markdown("""
        <div class='model-card'>
            <div class='model-hdr'>
                <span class='model-hdr-t'>Kill Zone &middot; Setup Checklist</span>
            </div>
            <div class='m-row'><span class='m-key'>Timeframes</span><span class='m-val m-blue'>5min &middot; 15min</span></div>
            <div class='m-row'><span class='m-key'>London KZ</span><span class='m-val'>07:00 &ndash; 10:00 GMT</span></div>
            <div class='m-row'><span class='m-key'>NY Open KZ</span><span class='m-val'>13:00 &ndash; 16:00 GMT</span></div>
            <div class='m-row'><span class='m-key'>Asian Range</span><span class='m-val'>00:00 &ndash; 07:00 GMT</span></div>
            <div class='m-row'><span class='m-key'>Step 1</span><span class='m-val' style='color:#CE93D8;'>Asian High/Low forms</span></div>
            <div class='m-row'><span class='m-key'>Step 2</span><span class='m-val' style='color:#60A5FA;'>Liquidity Sweep (BSL/SSL)</span></div>
            <div class='m-row'><span class='m-key'>Step 3</span><span class='m-val' style='color:#FCD34D;'>FVG forms in Kill Zone</span></div>
            <div class='m-row'><span class='m-key'>Step 4</span><span class='m-val' style='color:#10B981;font-weight:700;'>MSS &rarr; ENTRY</span></div>
            <div class='m-row'><span class='m-key'>SL</span><span class='m-val' style='color:#EF4444;'>Below/Above prev candle</span></div>
            <div class='m-row'><span class='m-key'>TP</span><span class='m-val'>1:2 Risk-to-Reward</span></div>
        </div>
        """, unsafe_allow_html=True)

        st.markdown("<br>", unsafe_allow_html=True)
        st.markdown(_sec("Risk Disclosure"), unsafe_allow_html=True)
        st.markdown("""
        <div style='background:#FFFBEB;border:1px solid #FDE68A;border-radius:12px;
        padding:16px 18px;border-left:4px solid #D97706;'>
        <p style='font-family:Roboto,sans-serif;font-size:.78rem;color:#92400E;line-height:1.7;margin:0;'>
        ICT signals are for <strong>educational purposes only</strong>.
        Kill Zone timing is in UTC/GMT. Always verify on your own chart before executing any trade.
        </p></div>
        """, unsafe_allow_html=True)
