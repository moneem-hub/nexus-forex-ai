"""
The agent loop: the LLM is given a goal and a set of tools, decides which to call and in what order, and is stopped by
hard limits (max steps, validated alerts, deterministic fallback). A setup the code found is never lost, even if the LLM fails.
"""
import json

from agent import journal as J
from agent.llm import LLMError
from agent.tools import SCHEMAS, ToolBox

SYSTEM = """You are the monitoring agent of a Forex trading assistant for one trader who follows an ICT strategy.
Goal of this run: check one pair and timeframe for a NEW setup and, if one exists, alert the trader.

Procedure:
1. Call scan_for_setup first.
2. If found is false: call finish with a one-sentence summary. Do not send an alert.
3. If found is true: optionally call get_journal_stats and/or get_recent_setups for context, then call send_alert once.
   Write the alert in under 110 words, using ONLY values from the tool results. Quote pair, direction, entry, stop loss and
   take profit exactly as given. State the quality label ("higher" or "lower") and give the 2-3 main reasons in plain words.
   Be honest: the model score is weak evidence, never a promise. If the agent's own live record is thin, say so.
4. After the alert is sent, call finish.
Never invent numbers. Never say a trade is guaranteed or safe."""


def _call(box: ToolBox, name: str, args: dict) -> dict:
    fns = {"scan_for_setup": box.scan_for_setup, "get_journal_stats": box.get_journal_stats,
           "get_recent_setups": box.get_recent_setups, "send_alert": box.send_alert, "finish": box.finish}
    if name not in fns:
        return {"error": f"unknown tool '{name}'. Available: {sorted(fns)}"}
    try:
        return fns[name](**args)
    except TypeError as e:
        return {"error": f"bad arguments for {name}: {e}"}
    except Exception as e:                                         # a tool failure is reported to the LLM, never a crash
        J.log_event(None, None, "TOOL_ERROR", f"{name}: {e}")
        return {"error": f"{name} failed: {e}"}


def run_agent(llm, box: ToolBox, pair: str, tf: int, max_steps: int = 8) -> dict:
    messages = [{"role": "system", "content": SYSTEM},
                {"role": "user", "content": f"Run now ({box.now:%Y-%m-%d %H:%M} UTC). Pair: {pair}. Timeframe: {tf} minutes."}]
    steps, fallback_reason = 0, None
    while box.finished is None and steps < max_steps:
        steps += 1
        try:
            msg = llm.chat(messages, SCHEMAS)
        except LLMError as e:
            fallback_reason = f"LLM error: {e}"
            break
        messages.append({k: v for k, v in msg.items() if k in ("role", "content", "tool_calls")} | {"role": "assistant"})
        calls = msg.get("tool_calls") or []
        if not calls:
            box.finished = (msg.get("content") or "").strip() or "ended without a summary"
            break
        for c in calls:
            name = c["function"]["name"]
            try:
                args = json.loads(c["function"].get("arguments") or "{}")
            except json.JSONDecodeError:
                args = None
            out = {"error": "arguments must be valid JSON"} if args is None else _call(box, name, args)
            messages.append({"role": "tool", "tool_call_id": c["id"], "content": json.dumps(out, default=str)})
    if box.finished is None and fallback_reason is None:
        fallback_reason = f"no result after {max_steps} steps"
    if fallback_reason and not box.scanned:
        box.scan_for_setup(pair, tf)                               # the LLM never got to scan: the code does it
    delivered = box.fallback_alerts()                              # safety net: a found setup is always alerted
    if fallback_reason and delivered:
        J.log_event(pair, tf, "FALLBACK", fallback_reason)
    return {"steps": steps, "found": len(box.found), "alerted": len(box.alerted),
            "fallback": bool(delivered), "summary": box.finished, "reason": fallback_reason}
