import streamlit as st
import yfinance as yf
from datetime import datetime


def render_header(pair: str, pair_label: str):
    st.markdown(f"""
    <div class='dash-hdr'>
        <div>
            <div class='dash-eyebrow'>
                <span class='ey-dot'></span>
                AI-Powered Forex Analytics
            </div>
            <div class='dash-title'>
                Market <span class='dash-title-accent'>Intelligence</span>
            </div>
        </div>
        <div class='dash-meta'>
            <div class='dash-meta-lbl'>Session Active</div>
            <div class='dash-meta-time'>{datetime.now().strftime("%d %b %Y  ·  %H:%M")}</div>
        </div>
    </div>
    """, unsafe_allow_html=True)


def render_price_strip(pair: str, pair_label: str):
    st.markdown(f"""
    <div class='live-strip'>
        <span class='live-dot'></span>
        <span class='live-lbl'>Live Feed</span>
        <span class='live-pair'>◈ {pair_label}</span>
    </div>""", unsafe_allow_html=True)

    try:
        ticker = yf.Ticker(pair)
        hist   = ticker.history(period="5d", interval="1d")
        latest = hist.iloc[-1]
        prev   = hist.iloc[-2]
        change = latest['Close'] - prev['Close']
        pct    = (change / prev['Close']) * 100
        is_up  = change >= 0
        color  = "#059669" if is_up else "#DC2626"
        arrow  = "▲" if is_up else "▼"

        cols  = st.columns(5)
        cards = [
            ("Close Price", f"{latest['Close']:.5f}", f"{arrow} {change:+.5f}", color, "pc-navy",  "◎"),
            ("Open Price",  f"{latest['Open']:.5f}",  "",                       "#7AAACE", "pc-blue",  "○"),
            ("Day High",    f"{latest['High']:.5f}",  "",                       "#059669", "pc-green", "↑"),
            ("Day Low",     f"{latest['Low']:.5f}",   "",                       "#DC2626", "pc-red",   "↓"),
            ("24h Change",  f"{pct:+.2f}%",           pair_label,               color, "pc-navy",  "%"),
        ]
        for col, (label, value, sub, col_hex, top_cls, icon) in zip(cols, cards):
            with col:
                st.markdown(f"""
                <div class='price-card {top_cls}'>
                    <span class='pc-icon'>{icon}</span>
                    <div class='pc-label'>{label}</div>
                    <div class='pc-value' style='color:{col_hex};'>{value}</div>
                    <div class='pc-change' style='color:{col_hex};'>{sub}</div>
                </div>""", unsafe_allow_html=True)

    except Exception:
        st.warning("⚡ Connecting to live market feed…")
