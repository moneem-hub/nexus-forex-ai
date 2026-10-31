import streamlit as st
from utils.auth import create_user
from components.login import AUTH_CSS, _left_panel_html


def render_signup():
    st.markdown(AUTH_CSS, unsafe_allow_html=True)

    left_col, right_col = st.columns([9, 11])

    # ── LEFT panel (same branding) ─────────────────────────────────────────────
    with left_col:
        st.markdown(_left_panel_html(), unsafe_allow_html=True)

    # ── RIGHT panel: signup form ───────────────────────────────────────────────
    with right_col:
        st.markdown("""
        <div style='height:40px'></div>
        <div class='auth-title'>CREATE ACCOUNT</div>
        <div class='auth-subtitle'>Join Nexus Forex — it only takes a minute</div>
        <div class='auth-divider'></div>
        """, unsafe_allow_html=True)

        # Row 1: Full Name + Username
        c1, c2 = st.columns(2)
        with c1:
            st.markdown("<span class='auth-lbl'>Full Name</span>",
                        unsafe_allow_html=True)
            full_name = st.text_input(
                "Full Name", placeholder="e.g. Ali Hassan",
                label_visibility="collapsed", key="su_name"
            )
        with c2:
            st.markdown(
                "<span class='auth-lbl'>Username "
                "<span style='color:#DC2626;'>*</span></span>",
                unsafe_allow_html=True,
            )
            username = st.text_input(
                "Username", placeholder="Choose a username",
                label_visibility="collapsed", key="su_user"
            )

        # Email
        st.markdown("<span class='auth-lbl'>Email Address</span>",
                    unsafe_allow_html=True)
        email = st.text_input(
            "Email", placeholder="you@example.com",
            label_visibility="collapsed", key="su_email"
        )

        # Row 2: Password + Confirm
        c3, c4 = st.columns(2)
        with c3:
            st.markdown(
                "<span class='auth-lbl'>Password "
                "<span style='color:#DC2626;'>*</span></span>",
                unsafe_allow_html=True,
            )
            password = st.text_input(
                "Password", placeholder="Min. 6 characters",
                type="password", label_visibility="collapsed", key="su_pass"
            )
        with c4:
            st.markdown(
                "<span class='auth-lbl'>Confirm Password "
                "<span style='color:#DC2626;'>*</span></span>",
                unsafe_allow_html=True,
            )
            confirm = st.text_input(
                "Confirm", placeholder="Repeat password",
                type="password", label_visibility="collapsed", key="su_conf"
            )

        # Hint
        st.markdown("""
        <div style='font-family:JetBrains Mono,monospace;font-size:.54rem;
            color:#9AB0CC;letter-spacing:.08em;margin-top:4px;margin-bottom:14px;'>
            ◈ &nbsp;Fields marked <span style='color:#DC2626;'>*</span>
            are required &nbsp;·&nbsp; Password min. 6 characters
        </div>
        """, unsafe_allow_html=True)

        # Submit
        st.markdown('<div class="cta-btn">', unsafe_allow_html=True)
        if st.button("CREATE ACCOUNT  →", use_container_width=True, key="signup_btn"):
            ok, msg = create_user(
                username=username,
                password=password,
                confirm=confirm,
                full_name=full_name,
                email=email,
            )
            if ok:
                st.session_state.su_success = msg
                st.session_state.auth_page = 'login'
                st.rerun()
            else:
                st.error(msg)
        st.markdown('</div>', unsafe_allow_html=True)

        # Divider
        st.markdown("""
        <div style='display:flex;align-items:center;gap:10px;margin:22px 0 6px;'>
            <div style='flex:1;height:1px;background:#E0EBF8;'></div>
            <span style='font-family:Roboto,sans-serif;font-size:.76rem;
                color:#B0C4EC;white-space:nowrap;padding:0 4px;'>
                Already have an account?
            </span>
            <div style='flex:1;height:1px;background:#E0EBF8;'></div>
        </div>
        """, unsafe_allow_html=True)

        # Login link
        st.markdown('<div class="auth-switch">', unsafe_allow_html=True)
        if st.button("Sign in instead  →", use_container_width=True, key="go_login"):
            st.session_state.auth_page = 'login'
            st.rerun()
        st.markdown('</div>', unsafe_allow_html=True)

        # Footer
        st.markdown("""
        <div style='margin-top:28px;padding-bottom:40px;'>
            <p style='font-family:JetBrains Mono,monospace;font-size:.5rem;
                color:#C8D8F0;letter-spacing:.1em;text-transform:uppercase;'>
                UAF &nbsp;·&nbsp; CS FYP 2024 &nbsp;·&nbsp; Systems Online &nbsp;
                <span style='display:inline-block;width:6px;height:6px;
                    background:#059669;border-radius:50%;vertical-align:middle;'></span>
            </p>
        </div>
        """, unsafe_allow_html=True)
