"""
Run with:  python test_agent_loop.py     (needs MySQL running; uses a separate throw-away database, nexus_forex_test)
Tests the agent loop with a SCRIPTED stand-in for the LLM: tool use, guardrails, fallback and de-duplication.
"""
import glob
import json

import numpy as np
import pandas as pd

import utils.db as D

D.DB_NAME = "nexus_forex_test"                       # safety: never touch the real journal

from agent import journal as J
from agent.agent import run_agent
from agent.data_sources import ReplaySource
from agent.llm import FakeLLM, LLMError
from agent.tools import ToolBox
from collect_setups import load_ohlc
from train_setup_model import FEATURES, load_setups, models

RAW = sorted(glob.glob("data/raw/eurusd-m5-*.csv"))[0]
BARS = load_ohlc(RAW)
SETUPS = pd.read_csv("data/setups_5m.csv", parse_dates=["time"]).query("pair == 'EURUSD'")
T = SETUPS.time.iloc[3]
NOW = T.floor("h") + pd.Timedelta(hours=1)                                   # a moment right after a known setup
SUNDAY = (BARS.index[0] + pd.Timedelta(days=8)).normalize()
SUNDAY = SUNDAY + pd.Timedelta(days=(6 - SUNDAY.dayofweek) % 7, hours=12)    # markets closed: nothing can be new
_df = load_setups("data/setups*.csv")
_m = models()["Logistic Regression"]().fit(_df[FEATURES], _df.y)
BUNDLE = {"model": _m, "features": FEATURES, "meta": {"score_median": float(np.median(_m.predict_proba(_df[FEATURES])[:, 1]))}}
SOURCE = ReplaySource({("EURUSD", 5): BARS})


def call(name, args, cid="c"):
    return {"role": "assistant", "content": None,
            "tool_calls": [{"id": cid, "type": "function", "function": {"name": name, "arguments": json.dumps(args) if isinstance(args, dict) else args}}]}


def good_message(f):
    return (f"{f['pair']} {f['direction']} setup. Entry {f['entry']}, stop loss {f['stop_loss']}, take profit {f['take_profit']}. "
            f"Model quality: {f['quality']}. Reasons: " + ", ".join(r["factor"] for r in f["reasons"]) + ". Weak evidence only.")


def scripted(steps):
    """steps: list of callables (last_tool_result_dict_or_None) -> assistant message. One per LLM turn; the last repeats."""
    state = {"i": 0}
    def script(messages):
        tools = [m for m in messages if m["role"] == "tool"]
        last = json.loads(tools[-1]["content"]) if tools else None
        fn = steps[min(state["i"], len(steps) - 1)]
        state["i"] += 1
        return fn(last)
    return script


def fresh(now=NOW, seen=None, max_age=60):
    sent = []
    box = ToolBox(SOURCE, BUNDLE, now, set() if seen is None else seen, alert_fn=lambda t: sent.append(t) or {"sent": True, "channel": "test"}, max_age_minutes=max_age)
    return box, sent


def reset():
    J.init_journal()
    J._run("DELETE FROM agent_journal")
    J._run("DELETE FROM agent_log")


def scan(_): return call("scan_for_setup", {"pair": "EURUSD", "timeframe_min": 5})
def finish(_): return call("finish", {"summary": "done"})


def test_happy_path():
    reset(); box, sent = fresh()
    steps = [scan, lambda r: call("get_journal_stats", {}), lambda r: call("get_recent_setups", {"pair": "EURUSD"}),
             lambda r: call("send_alert", {"setup_id": list(box.found)[0], "message": good_message(box.found[list(box.found)[0]])}), finish]
    out = run_agent(FakeLLM(scripted(steps)), box, "EURUSD", 5)
    row = J.recent(5)[0]
    assert out["found"] == 1 and out["alerted"] == 1 and not out["fallback"] and out["summary"] == "done", out
    assert len(sent) == 1 and row["alerted"] == 1 and row["explanation"] == sent[0] and row["quality"] in ("higher", "lower")
    assert {"SETUP", "ALERT", "FINISH"} <= {r["event"] for r in J.recent_log(50)}


def test_invented_numbers_and_promises_are_rejected_then_fixed():
    reset(); box, sent = fresh()
    seen_errors = []
    def bad_numbers(r):
        f = box.found[list(box.found)[0]]
        return call("send_alert", {"setup_id": f["setup_id"], "message": good_message(f).replace(f["entry"], "1.00000")})
    def promise(r):
        seen_errors.append(r["error"])
        f = box.found[list(box.found)[0]]
        return call("send_alert", {"setup_id": f["setup_id"], "message": good_message(f) + " This is guaranteed."})
    def fixed(r):
        seen_errors.append(r["error"])
        f = box.found[list(box.found)[0]]
        return call("send_alert", {"setup_id": f["setup_id"], "message": good_message(f)})
    run_agent(FakeLLM(scripted([scan, bad_numbers, promise, fixed, finish])), box, "EURUSD", 5)
    assert "entry" in seen_errors[0] and "guarantee" in seen_errors[1] and len(sent) == 1


def test_quiet_market_sends_nothing():
    reset(); box, sent = fresh(now=SUNDAY)
    out = run_agent(FakeLLM(scripted([scan, finish])), box, "EURUSD", 5)
    assert out["found"] == 0 and out["alerted"] == 0 and not sent and J.recent(5) == [] and out["summary"] == "done"


def test_llm_down_fallback_still_alerts():
    reset(); box, sent = fresh()
    out = run_agent(FakeLLM(lambda m: LLMError("boom")), box, "EURUSD", 5)       # LLM never got to scan: the code does
    assert out["fallback"] and out["alerted"] == 1 and len(sent) == 1 and "Model quality" in sent[0]
    assert J.recent(1)[0]["alerted"] == 1 and "FALLBACK_ALERT" in {r["event"] for r in J.recent_log(50)}


def test_out_of_steps_fallback():
    reset(); box, sent = fresh()
    out = run_agent(FakeLLM(scripted([scan, lambda r: call("get_journal_stats", {})])), box, "EURUSD", 5, max_steps=4)
    assert out["fallback"] and out["alerted"] == 1 and out["summary"] is None and "steps" in out["reason"]


def test_bad_tool_calls_do_not_crash():
    reset(); box, sent = fresh()
    steps = [lambda r: call("hack_the_planet", {}), lambda r: call("scan_for_setup", "{not json"), lambda r: call("scan_for_setup", {"pair": "EURUSD"}),
             scan, lambda r: call("send_alert", {"setup_id": 999, "message": "x"}),
             lambda r: call("send_alert", {"setup_id": list(box.found)[0], "message": good_message(box.found[list(box.found)[0]])}), finish]
    out = run_agent(FakeLLM(scripted(steps)), box, "EURUSD", 5, max_steps=10)
    assert out["alerted"] == 1 and len(sent) == 1 and not out["fallback"]


def test_a_setup_is_alerted_only_once_across_runs():
    reset(); box, sent = fresh()
    run_agent(FakeLLM(lambda m: LLMError("x")), box, "EURUSD", 5)
    assert len(sent) == 1
    box2, sent2 = fresh(seen=J.load_seen(36500))                                 # a restart: seen-set rebuilt from the journal
    out = run_agent(FakeLLM(scripted([scan, finish])), box2, "EURUSD", 5)
    assert out["found"] == 0 and not sent2 and len(J.recent(10)) == 1


if __name__ == "__main__":
    try:
        for name, fn in list(globals().items()):
            if name.startswith("test_"):
                fn(); print("PASS", name)
    finally:
        import mysql.connector
        from db_config import DB_HOST, DB_PASSWORD, DB_PORT, DB_USER
        c = mysql.connector.connect(host=DB_HOST, user=DB_USER, password=DB_PASSWORD, port=DB_PORT)
        c.cursor().execute("DROP DATABASE IF EXISTS nexus_forex_test"); c.close()
