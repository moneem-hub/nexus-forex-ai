import streamlit as st
from utils.auth import verify_login


# ── Left branding panel (shared with signup) ───────────────────────────────────
# IMPORTANT: HTML is built with string concatenation (no indented multiline
# strings) because Streamlit's markdown parser treats lines with 4+ leading
# spaces as code blocks, which makes raw HTML appear as plain text.
def _left_panel_html() -> str:
    features = [
        "AI-Powered Forex Price Predictions",
        "Real-Time Live Market Data Feed",
        "EUR/USD · GBP/USD · USD/JPY",
        "Integrated Risk Management Tools",
    ]

    feat_html = ""
    for text in features:
        feat_html += (
            "<div style='display:flex;align-items:flex-start;gap:12px;margin-bottom:14px;'>"
            "<div style='width:22px;height:22px;min-width:22px;"
            "background:rgba(156,213,255,.1);border:1px solid rgba(156,213,255,.2);"
            "border-radius:6px;display:flex;align-items:center;justify-content:center;margin-top:1px;'>"
            "<svg width='11' height='11' viewBox='0 0 24 24' fill='none'"
            " stroke='#9CD5FF' stroke-width='2.5' stroke-linecap='round' stroke-linejoin='round'>"
            "<polyline points='20 6 9 17 4 12'/></svg></div>"
            f"<span style='font-family:Roboto,sans-serif;font-size:.82rem;"
            f"color:rgba(255,255,255,.78);line-height:1.45;'>{text}</span>"
            "</div>"
        )

    return (
        # Outer wrapper
        "<div style='min-height:100%;display:flex;flex-direction:column;"
        "justify-content:space-between;padding:52px 44px;background:#111844;'>"

        # Logo row
        "<div>"
        "<div style='display:flex;align-items:center;gap:12px;margin-bottom:44px;'>"
        "<div style='width:46px;height:46px;min-width:46px;"
        "background:rgba(156,213,255,.1);border:1px solid rgba(156,213,255,.25);"
        "border-radius:13px;display:flex;align-items:center;justify-content:center;'>"
        "<svg width='22' height='22' viewBox='0 0 24 24' fill='none'"
        " stroke='#9CD5FF' stroke-width='1.7' stroke-linecap='round' stroke-linejoin='round'>"
        "<polyline points='22 7 13.5 15.5 8.5 10.5 2 17'/>"
        "<polyline points='16 7 22 7 22 13'/>"
        "</svg></div>"
        "<span style='font-family:JetBrains Mono,monospace;font-size:.58rem;"
        "color:rgba(156,213,255,.45);letter-spacing:.22em;text-transform:uppercase;'>"
        "AI Trading Platform</span>"
        "</div>"

        # Brand name
        "<div style='font-family:Anton,sans-serif;font-size:4.4rem;color:#FFFFFF;"
        "line-height:.9;letter-spacing:.02em;'>NEXUS</div>"
        "<div style='font-family:Anton,sans-serif;font-size:4.4rem;color:#9CD5FF;"
        "line-height:.9;letter-spacing:.02em;margin-bottom:14px;'>FOREX</div>"
        "<div style='font-family:JetBrains Mono,monospace;font-size:.6rem;"
        "color:rgba(156,213,255,.4);letter-spacing:.16em;"
        "text-transform:uppercase;margin-bottom:40px;'>"
        "AI Trading System &nbsp;&middot;&nbsp; v2.0</div>"

        # Chart card
        "<div style='background:rgba(156,213,255,.04);border:1px solid rgba(156,213,255,.1);"
        "border-radius:13px;padding:16px 18px;margin-bottom:34px;'>"
        "<div style='display:flex;align-items:center;justify-content:space-between;margin-bottom:10px;'>"
        "<span style='font-family:JetBrains Mono,monospace;font-size:.52rem;"
        "color:rgba(156,213,255,.38);letter-spacing:.18em;text-transform:uppercase;'>"
        "EUR / USD &nbsp;&middot;&nbsp; Performance</span>"
        "<span style='font-family:JetBrains Mono,monospace;font-size:.6rem;"
        "color:#9CD5FF;font-weight:600;'>+0.72%</span>"
        "</div>"
        "<svg viewBox='0 0 280 80' xmlns='http://www.w3.org/2000/svg' style='width:100%;display:block;'>"
        "<defs>"
        "<linearGradient id='cg' x1='0' y1='0' x2='0' y2='1'>"
        "<stop offset='0%' stop-color='#9CD5FF' stop-opacity='0.18'/>"
        "<stop offset='100%' stop-color='#9CD5FF' stop-opacity='0'/>"
        "</linearGradient>"
        "</defs>"
        "<line x1='0' y1='20' x2='280' y2='20' stroke='rgba(156,213,255,.07)' stroke-width='1'/>"
        "<line x1='0' y1='40' x2='280' y2='40' stroke='rgba(156,213,255,.07)' stroke-width='1'/>"
        "<line x1='0' y1='60' x2='280' y2='60' stroke='rgba(156,213,255,.07)' stroke-width='1'/>"
        "<polygon points='0,64 35,56 70,60 105,42 140,46 175,26 210,34 245,14 280,10 280,80 0,80' fill='url(#cg)'/>"
        "<polyline points='0,64 35,56 70,60 105,42 140,46 175,26 210,34 245,14 280,10'"
        " fill='none' stroke='#9CD5FF' stroke-width='2' stroke-linejoin='round' stroke-linecap='round'/>"
        "<circle cx='280' cy='10' r='4' fill='#9CD5FF'/>"
        "<circle cx='280' cy='10' r='9' fill='#9CD5FF' opacity='0.15'/>"
        "</svg></div>"

        # Features list
        f"<div>{feat_html}</div>"
        "</div>"

        # Footer quote
        "<div style='margin-top:32px;'>"
        "<div style='height:1px;background:rgba(156,213,255,.1);margin-bottom:20px;'></div>"
        "<div style='font-family:Roboto,sans-serif;font-size:.9rem;font-style:italic;"
        "color:rgba(156,213,255,.4);line-height:1.5;margin-bottom:10px;'>"
        "&ldquo;Precision. Speed. Edge.&rdquo;</div>"
        "<div style='font-family:JetBrains Mono,monospace;font-size:.5rem;"
        "color:rgba(156,213,255,.18);letter-spacing:.14em;text-transform:uppercase;'>"
        "NIAI &nbsp;&middot;&nbsp; Nexus Forex AI</div>"
        "</div>"
        "</div>"
    )


# ── Shared CSS (login + signup) ────────────────────────────────────────────────
AUTH_CSS = """
<style>
@import url('https://fonts.googleapis.com/css2?family=Anton&family=Roboto:wght@300;400;500;700&family=JetBrains+Mono:wght@300;400;500;600&display=swap');

section[data-testid='stSidebar'] { display: none !important; }
[data-testid='collapsedControl']  { display: none !important; }

html, body { background: #111844 !important; }
.stApp,
[data-testid="stAppViewContainer"],
[data-testid="stMain"],
.main { background: #111844 !important; }
[data-testid="stMain"] { padding: 0 !important; }

.block-container {
padding: 5vh 0 5vh 0 !important;
max-width: 1100px !important;
width: 100% !important;
margin: 0 auto !important;
background: transparent !important;
}

[data-testid="stHorizontalBlock"] {
gap: 0 !important;
column-gap: 0 !important;
padding: 0 !important;
margin: 0 !important;
align-items: stretch !important;
border-radius: 20px !important;
overflow: hidden !important;
box-shadow: 0 32px 80px rgba(0,0,0,.55), 0 0 0 1px rgba(156,213,255,.1) !important;
}

[data-testid="stHorizontalBlock"] > [data-testid="column"]:first-child {
background: #111844 !important;
flex: 0 0 44% !important;
max-width: 44% !important;
min-height: 88vh !important;
padding: 0 !important;
overflow: hidden !important;
}
[data-testid="stHorizontalBlock"] > [data-testid="column"]:first-child > div,
[data-testid="stHorizontalBlock"] > [data-testid="column"]:first-child [data-testid="stVerticalBlock"] {
background: #111844 !important;
height: 100% !important;
}

[data-testid="stHorizontalBlock"] > [data-testid="column"]:last-child {
background: #FFFFFF !important;
flex: 0 0 56% !important;
max-width: 56% !important;
min-height: 88vh !important;
padding: 0 52px !important;
box-sizing: border-box !important;
}
[data-testid="stHorizontalBlock"] > [data-testid="column"]:last-child > div,
[data-testid="stHorizontalBlock"] > [data-testid="column"]:last-child [data-testid="stVerticalBlock"],
[data-testid="stHorizontalBlock"] > [data-testid="column"]:last-child [data-testid="stVerticalBlockBorderWrapper"] {
background: #FFFFFF !important;
}

[data-testid="stHorizontalBlock"] > [data-testid="column"]:last-child .stTextInput > div > div > input {
background: #F5F8FF !important;
border: 1.5px solid #C8D8F0 !important;
color: #111844 !important;
border-radius: 10px !important;
font-family: Roboto, sans-serif !important;
font-size: .86rem !important;
padding: 12px 16px !important;
}
[data-testid="stHorizontalBlock"] > [data-testid="column"]:last-child .stTextInput > div > div > input:focus {
border-color: #111844 !important;
box-shadow: 0 0 0 3px rgba(17,24,68,.1) !important;
outline: none !important;
background: #FFFFFF !important;
}
[data-testid="stHorizontalBlock"] > [data-testid="column"]:last-child .stTextInput > div > div > input::placeholder {
color: #8A9EC4 !important;
opacity: 1 !important;
}

[data-testid="stHorizontalBlock"] > [data-testid="column"]:last-child .stAlert {
font-family: Roboto, sans-serif !important;
font-size: .82rem !important;
border-radius: 8px !important;
}

.auth-lbl {
font-family: 'JetBrains Mono', monospace !important;
font-size: .58rem !important;
font-weight: 600 !important;
color: #7AAACE !important;
letter-spacing: .22em !important;
text-transform: uppercase !important;
display: block !important;
margin-bottom: 7px !important;
margin-top: 20px !important;
}

.auth-title {
font-family: 'Anton', sans-serif;
font-size: 2.2rem;
color: #111844;
letter-spacing: .02em;
line-height: 1;
margin-bottom: 8px;
}
.auth-subtitle {
font-family: 'Roboto', sans-serif;
font-size: .88rem;
color: #7AAACE;
margin-bottom: 22px;
}
.auth-divider { height: 1px; background: #E0EBF8; margin-bottom: 8px; }

[data-testid="stHorizontalBlock"] > [data-testid="column"]:last-child .cta-btn > button {
background: #111844 !important;
border: none !important;
color: #FFFFFF !important;
font-family: Anton, sans-serif !important;
font-size: .95rem !important;
letter-spacing: .06em !important;
border-radius: 10px !important;
padding: 14px 20px !important;
box-shadow: 0 4px 16px rgba(17,24,68,.3) !important;
cursor: pointer !important;
}
[data-testid="stHorizontalBlock"] > [data-testid="column"]:last-child .cta-btn > button:hover {
background: #1A2580 !important;
box-shadow: 0 6px 22px rgba(17,24,68,.4) !important;
transform: translateY(-2px) !important;
}

.auth-switch > button {
background: transparent !important;
border: none !important;
color: #111844 !important;
font-family: Roboto, sans-serif !important;
font-weight: 700 !important;
font-size: .84rem !important;
padding: 4px 0 !important;
text-decoration: underline !important;
cursor: pointer !important;
box-shadow: none !important;
}
.auth-switch > button:hover {
color: #7AAACE !important;
background: transparent !important;
transform: none !important;
box-shadow: none !important;
}
</style>
"""


# ── Login page ─────────────────────────────────────────────────────────────────
def render_login():
    st.markdown(AUTH_CSS, unsafe_allow_html=True)

    if st.session_state.get('su_success'):
        msg = st.session_state.pop('su_success')
        st.success(f"✓ {msg}  Please sign in.")

    left_col, right_col = st.columns([9, 11])

    with left_col:
        st.markdown(_left_panel_html(), unsafe_allow_html=True)

    with right_col:
        st.markdown(
            "<div style='height:60px'></div>"
            "<div class='auth-title'>WELCOME BACK</div>"
            "<div class='auth-subtitle'>Sign in to access your trading dashboard</div>"
            "<div class='auth-divider'></div>",
            unsafe_allow_html=True,
        )

        st.markdown("<span class='auth-lbl'>Username</span>", unsafe_allow_html=True)
        username = st.text_input(
            "Username", placeholder="Enter your username",
            label_visibility="collapsed", key="login_user",
        )

        st.markdown("<span class='auth-lbl'>Password</span>", unsafe_allow_html=True)
        password = st.text_input(
            "Password", placeholder="Enter your password",
            type="password", label_visibility="collapsed", key="login_pass",
        )

        st.markdown("<div style='height:10px'></div>", unsafe_allow_html=True)

        st.markdown('<div class="cta-btn">', unsafe_allow_html=True)
        if st.button("ACCESS DASHBOARD  →", use_container_width=True, key="login_btn"):
            if not username or not password:
                st.error("Please enter both username and password.")
            elif verify_login(username, password):
                st.session_state.logged_in = True
                st.session_state.username  = username
                st.session_state.auth_page = 'login'
                st.rerun()
            else:
                st.error("Invalid username or password — please try again.")
        st.markdown('</div>', unsafe_allow_html=True)

        st.markdown(
            "<div style='display:flex;align-items:center;gap:10px;margin:24px 0 6px;'>"
            "<div style='flex:1;height:1px;background:#E0EBF8;'></div>"
            "<span style='font-family:Roboto,sans-serif;font-size:.76rem;"
            "color:#B0C4EC;white-space:nowrap;padding:0 4px;'>New to Nexus Forex?</span>"
            "<div style='flex:1;height:1px;background:#E0EBF8;'></div>"
            "</div>",
            unsafe_allow_html=True,
        )

        st.markdown('<div class="auth-switch">', unsafe_allow_html=True)
        if st.button("Create a free account  →", use_container_width=True, key="go_signup"):
            st.session_state.auth_page = 'signup'
            st.rerun()
        st.markdown('</div>', unsafe_allow_html=True)

        st.markdown(
            "<div style='margin-top:36px;padding-bottom:48px;'>"
            "<p style='font-family:JetBrains Mono,monospace;font-size:.5rem;"
            "color:#C8D8F0;letter-spacing:.1em;text-transform:uppercase;'>"
            "UAF &nbsp;&middot;&nbsp; CS FYP 2024 &nbsp;&middot;&nbsp; Systems Online &nbsp;"
            "<span style='display:inline-block;width:6px;height:6px;"
            "background:#059669;border-radius:50%;vertical-align:middle;'></span>"
            "</p></div>",
            unsafe_allow_html=True,
        )
