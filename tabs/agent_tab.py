"""
"Trading Agent" tab: what the monitoring agent has seen and done, and how its setups actually ended.

Shows: agent status (heartbeat), the journal, win rate by model-quality bucket WITH its uncertainty, cumulative result in R,
the alert text and reasons for each setup, and the agent's activity log.
Data comes from the agent_journal / agent_log tables. "Replay demo" shows the separate <db>_replay database, so demo runs
never mix with the live track record.

Styling: the app's own CSS gives the page a light background, so every visible element here is drawn with explicit colours
from the app palette (navy text on white cards) instead of relying on Streamlit's theme text colour.
"""
import contextlib
import json
import math

import pandas as pd
import streamlit as st

import utils.db as D
from agent import journal as J
from agent.tools import fmt_price

BREAKEVEN = 1 / 3                  # win rate needed at a 1:2 reward-to-risk to break even (before costs)
HEARTBEAT_OK_MIN = 75              # the monitor logs a heartbeat hourly
MIN_N = 10                         # below this many resolved setups a win rate is shown but flagged as "too few to judge"
OUTCOME_LABEL = {"PROFIT": "✓ PROFIT", "LOSS": "✗ LOSS", "PENDING": "⏳ PENDING", "EXPIRED": "– EXPIRED"}
NAVY, BLUE, GREY, GREEN, RED = "#111844", "#4A6699", "#8A97B8", "#059669", "#DC2626"

_CSS = """
<style>
[data-testid="stMain"] [data-testid="stRadio"] label *, section.main [data-testid="stRadio"] label * { color:#111844 !important; }
[data-testid="stMain"] [data-baseweb="select"] *, section.main [data-baseweb="select"] * { color:#111844 !important; }
[data-testid="stMain"] [data-testid="stExpander"] summary *, section.main [data-testid="stExpander"] summary * { color:#111844 !important; }
.ag-card{background:#fff;border:1px solid #D4DEFA;border-radius:14px;padding:14px 18px;box-shadow:0 1px 3px rgba(17,24,68,.06);height:100%}
.ag-lbl{font-size:.68rem;letter-spacing:.08em;text-transform:uppercase;color:#4A6699;font-weight:700}
.ag-val{font-size:1.9rem;font-weight:700;color:#111844;line-height:1.25}
.ag-sub{font-size:.76rem;margin-top:2px;font-weight:600}
.ag-h{font-size:1.05rem;font-weight:700;color:#111844;margin:26px 0 10px}
.ag-note{font-size:.8rem;color:#233070;line-height:1.55;margin:10px 0 4px}
.ag-brow{display:flex;align-items:center;gap:12px;margin:8px 0}
.ag-blbl{width:130px;font-size:.8rem;font-weight:600;color:#111844}
.ag-btrack{position:relative;flex:1;height:18px;background:#E8EEFF;border-radius:9px}
.ag-bfill{height:18px;border-radius:9px}
.ag-bmark{position:absolute;top:-3px;width:2px;height:24px;background:#111844}
.ag-bval{width:190px;font-size:.78rem;color:#233070}
</style>
"""


@contextlib.contextmanager
def _using_db(replay: bool):
    """Point the shared DB helpers at the replay database only while this tab reads, then restore (other tabs are unaffected)."""
    original = D.DB_NAME
    try:
        if replay and not original.endswith("_replay"):
            D.DB_NAME = original + "_replay"
        yield
    finally:
        D.DB_NAME = original


def _interval(wins: int, n: int) -> float:
    """Approximate 95% half-width of a win rate, in percentage points (rough; wide for small n)."""
    if n == 0:
        return 0.0
    p = wins / n
    return 1.96 * math.sqrt(p * (1 - p) / n) * 100


def _load() -> dict:
    return {"rows": J.recent(500), "log": J.recent_log(200), "stats": J.stats(("SELFTEST",)), "series": J.resolved_rows()}


def _status(log: list[dict], replay: bool) -> tuple[str, str]:
    if replay:
        return "info", "Replay demo: showing historical data produced by the simulated monitor."
    beats = [r for r in log if r["event"] == "HEARTBEAT"]
    if not beats:
        return "warning", "No heartbeat yet. Start the monitor: python -m agent.monitor"
    age = (pd.Timestamp.now(tz="UTC").tz_localize(None) - pd.Timestamp(beats[0]["ts"])).total_seconds() / 60
    if age <= HEARTBEAT_OK_MIN:
        return "success", f"Monitor running: last heartbeat {age:.0f} min ago."
    return "warning", f"Monitor not running? Last heartbeat {age / 60:.1f} h ago."


# ── small HTML building blocks ────────────────────────────────────────────────────────
def _h(text: str) -> None:
    st.markdown(f"<div class='ag-h'>{text}</div>", unsafe_allow_html=True)


def _card(label: str, value: str, sub: str = "", sub_color: str = GREY, dim: bool = False) -> None:
    val_style = f" style='color:{GREY}'" if dim else ""
    sub_html = f"<div class='ag-sub' style='color:{sub_color}'>{sub}</div>" if sub else ""
    st.markdown(f"<div class='ag-card'><div class='ag-lbl'>{label}</div><div class='ag-val'{val_style}>{value}</div>{sub_html}</div>",
                unsafe_allow_html=True)


def _track_card(label: str, s: dict) -> None:
    if s["n"] == 0:
        _card(label, "—", "no resolved setups yet", GREY, dim=True)
        return
    wins = round(s["win_rate"] * s["n"])
    few = s["n"] < MIN_N
    sub = f"{s['mean_r']:+.2f} R per setup · n={s['n']} · ±{_interval(wins, s['n']):.0f} pts" + (" · too few to judge" if few else "")
    color = GREY if few else (GREEN if s["mean_r"] > 0 else RED)
    _card(label, f"{s['win_rate']:.1%}", sub, color, dim=few)


def _bars(s: dict) -> str:
    be = BREAKEVEN * 100
    rows = ""
    for key, label in (("higher", "Higher quality"), ("lower", "Lower quality")):
        v = s[key]
        if v["n"] == 0:
            width, txt, color = 0, "no resolved setups", GREY
        else:
            width = v["win_rate"] * 100
            txt = f"{width:.1f}%  (n={v['n']})"
            color = GREEN if width >= be else RED
        rows += (f"<div class='ag-brow'><div class='ag-blbl'>{label}</div><div class='ag-btrack'>"
                 f"<div class='ag-bfill' style='width:{width}%;background:{color}'></div>"
                 f"<div class='ag-bmark' style='left:{be}%'></div></div><div class='ag-bval'>{txt}</div></div>")
    return rows + f"<div class='ag-note'>The dark marker is the break-even win rate ({be:.1f}%) at a 1:2 reward-to-risk.</div>"


def render_agent_tab():
    st.markdown(_CSS, unsafe_allow_html=True)
    top, refresh = st.columns([5, 1])
    mode = top.radio("Data", ["Live journal", "Replay demo"], horizontal=True, label_visibility="collapsed")
    if refresh.button("Refresh"):
        st.rerun()
    replay = mode == "Replay demo"

    try:
        with _using_db(replay):
            key = f"agent_tables_ready_{replay}"
            if not st.session_state.get(key):
                J.init_journal()
                st.session_state[key] = True
            data = _load()
    except Exception as e:
        st.error(f"Could not read the agent journal. Is MySQL running? ({e})")
        return

    level, msg = _status(data["log"], replay)
    getattr(st, level)(msg)

    rows = data["rows"]
    if not rows:
        st.markdown("<div class='empty-box'><div class='empty-ico'>🤖</div><div class='empty-ttl'>No agent activity yet</div>"
                    "<div class='empty-sub'>Run <b>python -m agent.monitor</b> (live) or the replay demo to see setups appear here.</div></div>",
                    unsafe_allow_html=True)
        return

    s = data["stats"]
    pending = sum(r["outcome"] == "PENDING" for r in rows)
    cols = st.columns(4)
    for col, (label, value) in zip(cols, (("Setups seen", len(rows)), ("Alerts sent", sum(int(r["alerted"] or 0) for r in rows)),
                                          ("Resolved", s["all"]["n"]), ("Pending", pending))):
        with col:
            _card(label, str(value))

    _h("Live track record")
    cols = st.columns(3)
    for col, (label, key) in zip(cols, (("All setups", "all"), ("Model: higher quality", "higher"), ("Model: lower quality", "lower"))):
        with col:
            _track_card(label, s[key])
    st.markdown(f"<div class='ag-note'>Break-even win rate at 1:2 is {BREAKEVEN:.1%} (before costs). The ± range shows the statistical noise: "
                "with few setups, differences inside it mean nothing. The model's quality score is weak evidence (offline test: AUC about 0.54-0.55).</div>",
                unsafe_allow_html=True)

    if s["all"]["n"] >= MIN_N:
        _h("Win rate by model quality")
        st.markdown(_bars(s), unsafe_allow_html=True)

    series = data["series"]
    if len(series) >= 2:
        df = pd.DataFrame(series)
        df["r_result"] = df["r_result"].astype(float)
        df["signal_time"] = pd.to_datetime(df["signal_time"])
        _h("Cumulative result (R)")
        st.line_chart(df.set_index("signal_time")["r_result"].cumsum(), height=220)

    _h("Journal")
    table = pd.DataFrame([{
        "Time (UTC)": pd.Timestamp(r["signal_time"]).strftime("%Y-%m-%d %H:%M"), "Pair": r["pair"], "TF": f"{r['tf_min']}m",
        "Side": r["direction"], "Entry": fmt_price(r["pair"], float(r["entry"])), "SL": fmt_price(r["pair"], float(r["sl"])),
        "TP": fmt_price(r["pair"], float(r["tp"])), "Quality": r["quality"] or "—", "Win chance": f"{float(r['p_win']):.0%}",
        "Alerted": "yes" if r["alerted"] else "no", "Outcome": OUTCOME_LABEL.get(r["outcome"], r["outcome"]),
        "R": "" if r["r_result"] is None else f"{float(r['r_result']):+.1f}",
    } for r in rows[:100]])
    st.dataframe(table, hide_index=True)

    _h("Alert detail")
    options = {f"{pd.Timestamp(r['signal_time']):%Y-%m-%d %H:%M}  {r['pair']} {r['direction']}  {OUTCOME_LABEL.get(r['outcome'], r['outcome'])}": r
               for r in rows[:30]}
    pick = st.selectbox("Setup", list(options), label_visibility="collapsed")
    r = options[pick]
    if r["explanation"]:
        st.info(r["explanation"])
    else:
        st.markdown("<div class='ag-note'>No alert text was stored for this setup.</div>", unsafe_allow_html=True)
    try:
        factors = json.loads(r["factors"] or "[]")
    except ValueError:
        factors = []
    if factors:
        st.markdown("<div class='ag-note'><b>Main factors behind the score:</b> "
                    + "; ".join(f"{f['factor']} ({f['effect']})" for f in factors) + "</div>", unsafe_allow_html=True)

    with st.expander("Agent activity log"):
        log = pd.DataFrame([{"Time (UTC)": r["ts"], "Event": r["event"], "Pair": r["pair"], "TF": r["tf_min"], "Details": r["details"]}
                            for r in data["log"][:100]])
        st.dataframe(log, hide_index=True)
