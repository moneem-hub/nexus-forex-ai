import streamlit as st
import pandas as pd


def _sec(text: str) -> str:
    return f"""<div class='sec-hdr'>
        <div class='sec-bar'></div>
        <span class='sec-txt'>{text}</span>
        <span class='sec-line'></span>
    </div>"""


def render_signals_tab(pair_label: str):
    st.markdown("<br>", unsafe_allow_html=True)
    st.markdown(_sec(f"Recent Signals — {pair_label}"), unsafe_allow_html=True)

    signals = [h for h in st.session_state.history if h['Pair'] == pair_label]
    if signals:
        df = pd.DataFrame(signals)
        st.dataframe(df, use_container_width=True, hide_index=True)
    else:
        st.markdown("""
        <div class='empty-box'>
            <div class='empty-ico'>📊</div>
            <div class='empty-ttl'>No signals yet for this pair</div>
            <div class='empty-sub'>Run a prediction in the <b>New Prediction</b> tab to populate this view.</div>
        </div>""", unsafe_allow_html=True)
