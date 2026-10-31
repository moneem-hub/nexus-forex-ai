import streamlit as st


def _sec(text: str) -> str:
    return f"""<div class='sec-hdr'>
        <div class='sec-bar'></div>
        <span class='sec-txt'>{text}</span>
        <span class='sec-line'></span>
    </div>"""


def render_chart_tab(pair: str, pair_label: str):
    st.markdown("<br>", unsafe_allow_html=True)
    st.markdown(_sec(f"TradingView Chart  —  {pair_label}"), unsafe_allow_html=True)
    st.components.v1.html(f"""
    <!DOCTYPE html><html>
    <head><style>
        body {{ margin:0; padding:0; background:#FFFFFF; }}
    </style></head>
    <body>
    <div id="tv_{pair_label}"></div>
    <script src="https://s3.tradingview.com/tv.js"></script>
    <script>
    new TradingView.widget({{
        "width": "100%",
        "height": 540,
        "symbol": "FX:{pair_label}",
        "interval": "D",
        "timezone": "Etc/UTC",
        "theme": "light",
        "style": "1",
        "locale": "en",
        "toolbar_bg": "#FFFFFF",
        "hide_top_toolbar": false,
        "save_image": false,
        "container_id": "tv_{pair_label}",
        "overrides": {{
            "paneProperties.background": "#FFFFFF",
            "paneProperties.backgroundType": "solid",
            "paneProperties.vertGridProperties.color": "#F0F4FF",
            "paneProperties.horzGridProperties.color": "#F0F4FF",
            "scalesProperties.textColor": "#111844"
        }}
    }});
    </script>
    </body></html>""", height=570)
