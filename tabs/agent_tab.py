"""
"Trading Agent" tab: what the monitoring agent has seen and done, and how its setups actually ended.

Shows: agent status (heartbeat), counts, win rate by model-quality bucket WITH its uncertainty, cumulative result in R,
the journal, the latest alerts with their reasons, and the agent's activity log.
Data comes from the agent_journal / agent_log tables. "Replay demo" shows the separate <db>_replay database, so demo runs
never mix with the live track record.

Styling: the app's own CSS gives the page a light background, so everything visible here is drawn as HTML with explicit
colours from the app palette (navy text on white cards) rather than relying on Streamlit's theme text colour. The only
native widgets are the three buttons.
"""
import contextlib
import html
import json
import math
from pathlib import Path

import pandas as pd
import streamlit as st

import utils.db as D
from agent import journal as J
from agent.tools import fmt_price

BREAKEVEN = 1 / 3                  # win rate needed at a 1:2 reward-to-risk to break even (before costs)
HEARTBEAT_OK_MIN = 20              # the monitor logs a heartbeat at start-up and every 15 minutes
MIN_N = 10                         # below this many resolved setups a win rate is shown but flagged "too few to judge"
NAVY, BLUE, GREY, GREEN, RED = "#111844", "#4A6699", "#8A97B8", "#059669", "#DC2626"
BADGE = {"PROFIT": ("#ECFDF5", GREEN, "✓ PROFIT"), "LOSS": ("#FEE2E2", RED, "✗ LOSS"),
         "PENDING": ("#FFFBEB", "#D97706", "⏳ PENDING"), "EXPIRED": ("#E8EEFF", BLUE, "– EXPIRED")}

_CSS_FILE = Path(__file__).resolve().parent.parent / "assets" / "agent_tab.css"


def _css() -> str:
    """The tab's styling lives in assets/agent_tab.css: edit that file, save, then refresh the browser."""
    return "<style>" + _CSS_FILE.read_text(encoding="utf-8") + "</style>"


def _e(x) -> str:
    return html.escape("" if x is None else str(x))


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
        return "warning", "No heartbeat yet: the live monitor is not running. Start it in a terminal with: python -m agent.monitor"
    age = (pd.Timestamp.now(tz="UTC").tz_localize(None) - pd.Timestamp(beats[0]["ts"])).total_seconds() / 60
    if age <= HEARTBEAT_OK_MIN:
        return "success", f"Monitor running: last heartbeat {age:.0f} min ago."
    return "warning", f"Monitor not running? Last heartbeat {age / 60:.1f} h ago."


BANNER = {"info": ("#E6F0FF", "#B0C4EC", "#1E3A8A", "ℹ"), "success": ("#ECFDF5", "#A7F3D0", "#065F46", "●"),
          "warning": ("#FFFBEB", "#FDE68A", "#92400E", "!")}


def _banner(level: str, msg: str) -> str:
    bg, bd, fg, icon = BANNER[level]
    return f"<div class='ag-banner' style='background:{bg};border:1px solid {bd};color:{fg}'><span class='ag-banner-ico'>{icon}</span>{_e(msg)}</div>"


def _active_button_css(key: str) -> str:
    """Make the selected mode button clearly 'on' (navy, white text)."""
    return (f"<style>.st-key-{key} button{{background:#111844 !important;border-color:#111844 !important}}"
            f".st-key-{key} button *{{color:#FFFFFF !important}}</style>")


def _empty_html(replay: bool) -> str:
    if replay:
        title = "No replay data yet"
        sub = ("Run the replay demo in a terminal:<br><span class='ag-code'>python -m agent.monitor --replay --from \"2020-01-13 07:00\" "
               "--to \"2020-01-14 12:00\" --pairs EURUSD --tfs 5 --fresh</span>")
    else:
        title = "No live agent activity yet"
        sub = ("Start the live monitor in a terminal: <span class='ag-code'>python -m agent.monitor</span><br>"
               "Setups are rare, so an empty journal is normal at first. Use <b>Replay demo</b> to see the agent in action.")
    return f"<div class='ag-empty'><div class='ag-empty-ico'>🤖</div><div class='ag-empty-ttl'>{title}</div><div class='ag-empty-sub'>{sub}</div></div>"


# ── HTML building blocks ──────────────────────────────────────────────────────────────
def _md(html_str: str) -> None:
    st.markdown(html_str, unsafe_allow_html=True)


def _h(text: str) -> None:
    _md(f"<div class='ag-h'>{text}</div>")


def _card(label: str, value: str, sub: str = "", sub_color: str = GREY, dim: bool = False) -> None:
    val_style = f" style='color:{GREY}'" if dim else ""
    sub_html = f"<div class='ag-sub' style='color:{sub_color}'>{sub}</div>" if sub else ""
    _md(f"<div class='ag-card'><div class='ag-lbl'>{label}</div><div class='ag-val'{val_style}>{value}</div>{sub_html}</div>")


def _track_card(label: str, s: dict) -> None:
    if s["n"] == 0:
        _card(label, "—", "no resolved setups yet", GREY, dim=True)
        return
    wins = round(s["win_rate"] * s["n"])
    few = s["n"] < MIN_N
    sub = f"{s['mean_r']:+.2f} R per setup · n={s['n']} · ±{_interval(wins, s['n']):.0f} pts" + (" · too few to judge" if few else "")
    _card(label, f"{s['win_rate']:.1%}", sub, GREY if few else (GREEN if s["mean_r"] > 0 else RED), dim=few)


def _bars(s: dict) -> str:
    be = BREAKEVEN * 100
    rows = ""
    for key, label in (("higher", "Higher quality"), ("lower", "Lower quality")):
        v = s[key]
        if v["n"] == 0:
            width, txt, color = 0, "no resolved setups", GREY
        else:
            width = v["win_rate"] * 100
            txt, color = f"{width:.1f}%  (n={v['n']})", GREEN if width >= be else RED
        rows += (f"<div class='ag-brow'><div class='ag-blbl'>{label}</div><div class='ag-btrack'>"
                 f"<div class='ag-bfill' style='width:{width}%;background:{color}'></div>"
                 f"<div class='ag-bmark' style='left:{be}%'></div></div><div class='ag-bval'>{txt}</div></div>")
    return rows + f"<div class='ag-note'>The dark marker is the break-even win rate ({be:.1f}%) at a 1:2 reward-to-risk.</div>"


def _badge(outcome: str) -> str:
    bg, fg, text = BADGE.get(outcome, ("#E8EEFF", BLUE, _e(outcome)))
    return f"<span class='ag-badge' style='background:{bg};color:{fg}'>{text}</span>"


def _cum_svg(series: list[dict]) -> str:
    vals, c = [], 0.0
    for r in series:
        c += float(r["r_result"])
        vals.append(c)
    n, w, h, pad = len(vals), 600, 150, 12
    lo, hi = min(0.0, min(vals)), max(0.0, max(vals))
    span = (hi - lo) or 1.0

    def xy(i, v):
        return pad + (w - 2 * pad) * (i / (n - 1)), pad + (h - 2 * pad) * (1 - (v - lo) / span)

    pts = " ".join(f"{x:.1f},{y:.1f}" for x, y in (xy(i, v) for i, v in enumerate(vals)))
    zero_y = xy(0, 0.0)[1]
    color = GREEN if vals[-1] >= 0 else RED
    return (f"<div class='ag-card'><svg viewBox='0 0 {w} {h}' width='100%' height='{h}' preserveAspectRatio='none'>"
            f"<line x1='{pad}' y1='{zero_y:.1f}' x2='{w - pad}' y2='{zero_y:.1f}' stroke='#B0C4EC' stroke-dasharray='5 4' vector-effect='non-scaling-stroke'/>"
            f"<polyline points='{pts}' fill='none' stroke='{color}' stroke-width='2.5' vector-effect='non-scaling-stroke'/></svg>"
            f"<div class='ag-note'>{n} resolved setups · now <b style='color:{color}'>{vals[-1]:+.1f} R</b> (dashed line = 0)</div></div>")


def _journal_html(rows: list[dict]) -> str:
    head = ["Time (UTC)", "Pair", "TF", "Side", "Entry", "SL", "TP", "Quality", "Win chance", "Alerted", "Outcome", "R"]
    body = ""
    for r in rows[:100]:
        side_c = GREEN if r["direction"] == "BUY" else RED
        res = "" if r["r_result"] is None else f"{float(r['r_result']):+.1f}"
        res_c = GREEN if res.startswith("+") else RED if res.startswith("-") else NAVY
        body += (f"<tr><td>{pd.Timestamp(r['signal_time']):%Y-%m-%d %H:%M}</td><td>{_e(r['pair'])}</td><td>{r['tf_min']}m</td>"
                 f"<td style='color:{side_c};font-weight:700'>{_e(r['direction'])}</td>"
                 f"<td>{fmt_price(r['pair'], float(r['entry']))}</td><td>{fmt_price(r['pair'], float(r['sl']))}</td>"
                 f"<td>{fmt_price(r['pair'], float(r['tp']))}</td><td>{_e(r['quality'] or '—')}</td>"
                 f"<td>{float(r['p_win']):.0%}</td><td>{'yes' if r['alerted'] else 'no'}</td><td>{_badge(r['outcome'])}</td>"
                 f"<td style='color:{res_c};font-weight:700'>{res}</td></tr>")
    return (f"<div class='ag-tbl-wrap'><table class='ag-tbl'><thead><tr>{''.join(f'<th>{h}</th>' for h in head)}</tr></thead>"
            f"<tbody>{body}</tbody></table></div>")


def _alerts_html(rows: list[dict]) -> str:
    out = ""
    for r in [x for x in rows if x["explanation"]][:5]:
        try:
            factors = json.loads(r["factors"] or "[]")
        except ValueError:
            factors = []
        side_c = GREEN if r["direction"] == "BUY" else RED
        fac = ("<div class='ag-note'><b>Main factors behind the score:</b> "
               + "; ".join(f"{_e(f['factor'])} ({_e(f['effect'])})" for f in factors) + "</div>") if factors else ""
        out += (f"<div class='ag-alert'><div class='ag-alert-top'><b>{pd.Timestamp(r['signal_time']):%Y-%m-%d %H:%M}</b> UTC · {_e(r['pair'])} {r['tf_min']}m · "
                f"<b style='color:{side_c}'>{_e(r['direction'])}</b> &nbsp;{_badge(r['outcome'])}</div>"
                f"<div class='ag-alert-text'>{_e(r['explanation'])}</div>{fac}</div>")
    return out or "<div class='ag-note'>No alert text has been stored yet.</div>"


def _log_html(log: list[dict]) -> str:
    body = "".join(f"<tr><td>{_e(r['ts'])}</td><td><b>{_e(r['event'])}</b></td><td>{_e(r['pair'])}</td><td>{_e(r['tf_min'])}</td>"
                   f"<td style='white-space:normal'>{_e((r['details'] or '')[:160])}</td></tr>" for r in log[:60])
    return (f"<details class='ag-details'><summary>Agent activity log ({len(log)} recent events)</summary><div class='ag-tbl-wrap'>"
            f"<table class='ag-tbl'><thead><tr><th>Time (UTC)</th><th>Event</th><th>Pair</th><th>TF</th><th>Details</th></tr></thead>"
            f"<tbody>{body}</tbody></table></div></details>")


# ── the tab ───────────────────────────────────────────────────────────────────────────
def render_agent_tab():
    _md(_css())
    mode = st.session_state.setdefault("agent_mode", "Live journal")
    b1, b2, _spacer, b3 = st.columns([1.4, 1.5, 4.5, 1])
    for col, name, key in ((b1, "Live journal", "ag_live"), (b2, "Replay demo", "ag_replay")):
        active = mode == name
        if col.button(("● " if active else "") + name, type="primary" if active else "secondary", key=key):
            st.session_state["agent_mode"] = name
            st.rerun()
    if b3.button("Refresh", key="ag_refresh"):
        st.rerun()
    replay = mode == "Replay demo"
    _md(_active_button_css("ag_replay" if replay else "ag_live"))

    try:
        with _using_db(replay):
            ready = f"agent_tables_ready_{replay}"
            if not st.session_state.get(ready):
                J.init_journal()
                st.session_state[ready] = True
            data = _load()
    except Exception as e:
        st.error(f"Could not read the agent journal. Is MySQL running? ({e})")
        return

    level, msg = _status(data["log"], replay)
    _md(_banner(level, msg))

    rows = data["rows"]
    if not rows:
        _md(_empty_html(replay))
        return

    s = data["stats"]
    pending = sum(r["outcome"] == "PENDING" for r in rows)
    for col, (label, value) in zip(st.columns(4), (("Setups seen", len(rows)), ("Alerts sent", sum(int(r["alerted"] or 0) for r in rows)),
                                                   ("Resolved", s["all"]["n"]), ("Pending", pending))):
        with col:
            _card(label, str(value))

    _h("Live track record")
    for col, (label, key) in zip(st.columns(3), (("All setups", "all"), ("Model: higher quality", "higher"), ("Model: lower quality", "lower"))):
        with col:
            _track_card(label, s[key])
    _md(f"<div class='ag-note'>Break-even win rate at 1:2 is {BREAKEVEN:.1%} (before costs). The ± range shows the statistical noise: "
        "with few setups, differences inside it mean nothing. The model's quality score is weak evidence (offline test: AUC about 0.54-0.55).</div>")

    if s["all"]["n"] >= MIN_N:
        _h("Win rate by model quality")
        _md(_bars(s))
    if len(data["series"]) >= 2:
        _h("Cumulative result (R)")
        _md(_cum_svg(data["series"]))

    _h("Journal")
    _md(_journal_html(rows))
    _h("Latest alerts")
    _md(_alerts_html(rows))
    _md(_log_html(data["log"]))
