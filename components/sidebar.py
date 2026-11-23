import streamlit as st
from config import PAIRS, CALENDAR_EVENTS


def render_sidebar() -> str:
    with st.sidebar:

        # ── Brand ──────────────────────────────────────────────────
        st.markdown("""
        <div class='sb-wrap'>
            <div class='sb-top-line'></div>
            <div class='sb-inner'>
                <div class='sb-logo-row'>
                    <div class='sb-icon'>
                        <svg width="20" height="20" viewBox="0 0 24 24" fill="none"
                             stroke="#9CD5FF" stroke-width="1.8"
                             stroke-linecap="round" stroke-linejoin="round">
                            <polyline points="22 7 13.5 15.5 8.5 10.5 2 17"/>
                            <polyline points="16 7 22 7 22 13"/>
                        </svg>
                    </div>
                    <div>
                        <div class='sb-brand-name'>NEXUS FX</div>
                        <div class='sb-brand-tag'>AI Predictor · v2.4</div>
                    </div>
                </div>
                <div class='sb-version'>◈ ML Trading System</div>
            </div>
        </div>
        """, unsafe_allow_html=True)

        # ── Instrument selector ─────────────────────────────────────
        st.markdown("""
        <div class='sb-sec'>
            <svg class='sb-sec-icon' width="13" height="13" viewBox="0 0 24 24" fill="none"
                 stroke="#7AAACE" stroke-width="2.2" stroke-linecap="round" stroke-linejoin="round">
                <circle cx="12" cy="12" r="10"/>
                <path d="M16 8h-6a2 2 0 1 0 0 4h4a2 2 0 1 1 0 4H8"/>
                <path d="M12 18V6"/>
            </svg>
            <span class='sb-sec-t'>Instrument</span>
            <span class='sb-sec-l'></span>
        </div>
        """, unsafe_allow_html=True)

        st.markdown("<div style='padding:0 12px 2px;'>", unsafe_allow_html=True)
        pair = st.selectbox(
            "Pair",
            PAIRS,
            format_func=lambda x: x.replace("=X", ""),
            label_visibility="collapsed",
        )
        st.markdown("</div>", unsafe_allow_html=True)

        pl = pair.replace("=X", "")
        base, quote = pl[:3], pl[3:]
        st.markdown(f"""
        <div class='pair-box'>
            <div>
                <div class='pair-lbl'>Active Pair</div>
                <div class='pair-val'>{base} / {quote}</div>
            </div>
            <span class='pair-badge'>FOREX</span>
        </div>
        """, unsafe_allow_html=True)

        # ── Calendar Events ─────────────────────────────────────────
        st.markdown("""
        <div class='sb-sec'>
            <svg class='sb-sec-icon' width="13" height="13" viewBox="0 0 24 24" fill="none"
                 stroke="#7AAACE" stroke-width="2.2" stroke-linecap="round" stroke-linejoin="round">
                <rect x="3" y="4" width="18" height="18" rx="2" ry="2"/>
                <line x1="16" y1="2" x2="16" y2="6"/>
                <line x1="8" y1="2" x2="8" y2="6"/>
                <line x1="3" y1="10" x2="21" y2="10"/>
            </svg>
            <span class='sb-sec-t'>Calendar Events</span>
            <span class='sb-sec-l'></span>
        </div>
        """, unsafe_allow_html=True)

        st.markdown("<div style='padding:4px 0 10px;'>", unsafe_allow_html=True)
        _map = {
            "high": ("sb-card-high", "sb-imp-h", "dot-h"),
            "med":  ("sb-card-med",  "sb-imp-m", "dot-m"),
            "low":  ("sb-card-low",  "sb-imp-l", "dot-l"),
        }
        for name, subtitle, desc, imp_label, imp_key in CALENDAR_EVENTS:
            card_cls, tag_cls, dot_cls = _map[imp_key]
            st.markdown(f"""
            <div class='sb-card {card_cls}'>
                <div class='sb-card-row'>
                    <span class='sb-card-name'>{name}</span>
                    <span class='sb-card-tag {tag_cls}'>{imp_label}</span>
                </div>
                <div class='sb-card-sub'>{subtitle}</div>
                <div class='sb-card-desc'>{desc}</div>
                <div class='sb-card-foot'>
                    <div class='sb-imp-dot {dot_cls}'></div>
                    <span class='sb-imp-label {tag_cls}'>Impact: {imp_label}</span>
                </div>
            </div>
            """, unsafe_allow_html=True)
        st.markdown("</div>", unsafe_allow_html=True)

        # ── Full Calendar button → opens Calendar tab ───────────────
        st.markdown("<div style='padding:0 12px 10px;'>", unsafe_allow_html=True)
        st.markdown('<div class="sb-cal-btn">', unsafe_allow_html=True)
        if st.button("📅  Open Full Calendar", use_container_width=True, key="open_cal"):
            st.session_state.go_calendar = True
            st.rerun()
        st.markdown('</div>', unsafe_allow_html=True)
        st.markdown("</div>", unsafe_allow_html=True)

        st.markdown(
            "<hr style='border-color:#1F2B78;margin:4px 0 10px;'>",
            unsafe_allow_html=True,
        )

        # ── Sign Out ────────────────────────────────────────────────
        st.markdown("<div style='padding:0 12px 14px;'>", unsafe_allow_html=True)
        if st.button("⬡  Sign Out", use_container_width=True, key="signout"):
            from utils.session import end_session
            end_session()              # delete the saved login so the old URL stops working
            st.session_state.clear()   # sari session state saaf karo
            st.rerun()
        st.markdown("</div>", unsafe_allow_html=True)

        st.markdown(
            "<p style='text-align:center;color:#1F2B78;font-family:JetBrains Mono,monospace;"
            "font-size:.5rem;letter-spacing:.1em;padding-bottom:10px;'>NIAI Capstone Project 2026. All rights reserved. | Made with ❤️</p>",
            unsafe_allow_html=True,
        )

    return pair
