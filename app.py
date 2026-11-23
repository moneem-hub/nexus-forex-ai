import streamlit as st
from config import APP_TITLE, APP_ICON

st.set_page_config(
    page_title=APP_TITLE,
    page_icon=APP_ICON,
    layout="wide",
    initial_sidebar_state="expanded",
)

# ── Global CSS ─────────────────────────────────────────────────────────────────
from assets.styles import get_css
st.markdown(get_css(), unsafe_allow_html=True)

# ── MySQL database initialize karo (tables create if not exist) ────────────────
from utils.db import init_db
init_db()

# ── Session defaults ───────────────────────────────────────────────────────────
from tabs.history import load_history

st.session_state.setdefault('logged_in', False)
st.session_state.setdefault('username', '')
st.session_state.setdefault('go_calendar', False)
st.session_state.setdefault('auth_page', 'login')

# Login hone ke baad us user ki history MySQL se load karo
# 'history' session mein nahi hogi jab bhi fresh login hoga (clear ke baad)
if st.session_state.logged_in and st.session_state.username:
    if 'history' not in st.session_state:
        st.session_state['history'] = load_history()
else:
    if 'history' not in st.session_state:
        st.session_state['history'] = []

# ── Auth gate (login or signup) ────────────────────────────────────────────────
if not st.session_state.logged_in:
    if st.session_state.auth_page == 'signup':
        from components.signup import render_signup
        render_signup()
    else:
        from components.login import render_login
        render_login()
    st.stop()

# ── Sidebar ────────────────────────────────────────────────────────────────────
from components.sidebar import render_sidebar
pair = render_sidebar()
pair_label = pair.replace("=X", "")

# ── Dashboard header + live prices ────────────────────────────────────────────
from components.header import render_header, render_price_strip
render_header(pair, pair_label)
render_price_strip(pair, pair_label)
st.markdown("<br>", unsafe_allow_html=True)

# ── Main tabs (5th tab = Full Calendar) ───────────────────────────────────────
tab1, tab2, tab3, tab4, tab5, tab6 = st.tabs([
    "  Live Chart  ",
    "  New Prediction  ",
    "  Trading Signals  ",
    "  History  ",
    "  Full Calendar  ",
    "  Trading Agent  ",
])

with tab1:
    from tabs.chart import render_chart_tab
    render_chart_tab(pair, pair_label)

with tab2:
    from tabs.prediction import render_prediction_tab
    render_prediction_tab(pair, pair_label)

with tab3:
    from tabs.signals import render_signals_tab
    render_signals_tab(pair_label)

with tab4:
    from tabs.history import render_history_tab
    render_history_tab()

with tab5:
    st.markdown("<br>", unsafe_allow_html=True)
    st.markdown("""<div class='sec-hdr'>
        <div class='sec-bar'></div>
        <span class='sec-txt'>Investing.com — Economic Calendar</span>
        <span class='sec-line'></span>
    </div>""", unsafe_allow_html=True)

    # Info strip
    st.markdown("""
    <div style='display:flex;align-items:center;gap:12px;
    background:#F0F4FF;border:1px solid #D4DEFA;border-radius:10px;
    padding:10px 16px;margin-bottom:18px;'>
        <svg width="16" height="16" viewBox="0 0 24 24" fill="none"
             stroke="#111844" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
            <rect x="3" y="4" width="18" height="18" rx="2" ry="2"/>
            <line x1="16" y1="2" x2="16" y2="6"/>
            <line x1="8" y1="2" x2="8" y2="6"/>
            <line x1="3" y1="10" x2="21" y2="10"/>
        </svg>
        <span style='font-family:Roboto,sans-serif;font-size:.8rem;
        font-weight:500;color:#111844;'>
        Real-time economic calendar — HIGH impact events marked in red
        </span>
        <span style='margin-left:auto;font-family:JetBrains Mono,monospace;
        font-size:.6rem;color:#7AAACE;letter-spacing:.12em;text-transform:uppercase;'>
        Powered by Investing.com
        </span>
    </div>
    """, unsafe_allow_html=True)

    st.markdown("<div class='cal-container'>", unsafe_allow_html=True)
    st.components.v1.html("""
    <iframe
        src="https://sslecal2.investing.com?columns=exc_flags,exc_currency,exc_importance,exc_actual,exc_forecast,exc_previous&importance=3&features=datepicker,timezone&calType=week&timeZone=20&lang=1"
        width="100%"
        height="680"
        frameborder="0"
        allowtransparency="true"
        style="background:#FFFFFF;display:block;">
    </iframe>""", height=700)
    st.markdown("</div>", unsafe_allow_html=True)

with tab6:
    from tabs.agent_tab import render_agent_tab
    render_agent_tab()

# ── Auto-switch to Calendar tab when sidebar button was clicked ───────────────
if st.session_state.pop('go_calendar', False):
    st.components.v1.html("""
    <script>
    (function() {
        var attempts = 0;
        function switchTab() {
            var tabs = window.parent.document.querySelectorAll('[data-baseweb="tab"]');
            if (tabs.length >= 5) {
                tabs[4].click();
                return;
            }
            if (++attempts < 30) {
                setTimeout(switchTab, 80);
            }
        }
        setTimeout(switchTab, 120);
    })();
    </script>
    """, height=0)

# ── Footer ─────────────────────────────────────────────────────────────────────
st.markdown("""
<br><hr>
<p style='text-align:center;color:#D4DEFA;font-family:JetBrains Mono,monospace;
font-size:.52rem;padding:8px 0;letter-spacing:.12em;text-transform:uppercase;'>
Nexus Forex AI · NIAI Capstone Project 2026. All rights reserved. | Made with ❤️
</p>""", unsafe_allow_html=True)
