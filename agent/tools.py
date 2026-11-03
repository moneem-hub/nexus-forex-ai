"""
The agent's tools. Everything that touches numbers, the market, the model or the database is ordinary tested
code. The LLM chooses WHICH tools to call and in what order, and writes the alert wording, but it cannot change
a price, a score or an outcome, and its message is checked against the real figures before anything is sent.
"""
import json

from agent import journal as J
from agent.alerts import send_alert as deliver
from agent.detect import detect_new_setup
from agent.scoring import score_signal

BANNED = ("guarantee", "guaranteed", "risk-free", "risk free", "can't lose", "cannot lose", "sure thing", "100%", "certain win")


def fmt_price(pair: str, x: float) -> str:
    decimals = 3 if pair.endswith("JPY") else 2 if pair.startswith("XAU") else 5
    return f"{x:.{decimals}f}"


def validate_alert(message: str, exp: dict) -> str | None:
    """Return None if the message is faithful to the real setup, otherwise a short error for the LLM to fix."""
    if len(message) > 900:
        return "message too long (max 900 characters)"
    low = message.lower()
    for word in BANNED:
        if word in low:
            return f"never use promising language such as '{word}'"
    missing = [name for name, val in (("pair", exp["pair"]), ("direction", exp["direction"]), ("entry", exp["entry"]),
                                      ("stop loss", exp["sl"]), ("take profit", exp["tp"])) if val.lower() not in low]
    if missing:
        return "message must quote exactly these values from the tool result: " + ", ".join(missing)
    if exp.get("quality") and exp["quality"] not in low:
        return f"message must state the setup quality ('{exp['quality']}')"
    return None


def template_alert(f: dict) -> str:
    """Deterministic wording, used when the LLM is unavailable or fails. Passes validate_alert by construction."""
    reasons = "; ".join(f"{r['factor']} {r['effect']}" for r in f["reasons"]) or "no standout factors"
    return (f"{f['pair']} {f['timeframe']} {f['direction']} setup\n"
            f"Entry {f['entry']} | Stop loss {f['stop_loss']} | Take profit {f['take_profit']} (1:{f['reward_to_risk']})\n"
            f"Model quality: {f['quality']} ({f['model_win_chance_percent']}% estimated win chance; weak evidence, not a guarantee).\n"
            f"Reasons: {reasons}")


class ToolBox:
    def __init__(self, source, bundle, now, seen: set, alert_fn=deliver, max_age_minutes: int = 45):
        self.source, self.bundle, self.now, self.seen = source, bundle, now, seen
        self.alert_fn, self.max_age = alert_fn, max_age_minutes
        self.found: dict[int, dict] = {}          # journal id -> facts, for validation and the fallback
        self.alerted: set[int] = set()
        self.finished = None
        self.scanned = False

    # ── tools ─────────────────────────────────────────────────────────────────────────
    def scan_for_setup(self, pair: str, timeframe_min: int) -> dict:
        self.scanned = True
        window = self.source.bars(pair, timeframe_min, self.now)
        sig = detect_new_setup(window, pair, timeframe_min, self.now, self.seen, self.max_age)
        if sig is None:
            J.log_event(pair, timeframe_min, "SCAN", "no new setup")
            return {"found": False, "bars_checked": len(window)}
        scored = score_signal(self.bundle, window.loc[:sig["signal_time"]], sig, timeframe_min)
        jid, is_new = J.log_setup(sig, scored)
        if not is_new:
            return {"found": False, "note": "setup already journaled earlier"}
        f = scored["features"]
        sgn = 1 if sig["direction"] == "BUY" else -1
        facts = {
            "setup_id": jid, "pair": pair, "timeframe": f"{timeframe_min}m", "direction": sig["direction"],
            "signal_time_utc": sig["signal_time"].strftime("%Y-%m-%d %H:%M"),
            "entry": fmt_price(pair, sig["entry"]), "stop_loss": fmt_price(pair, sig["sl"]),
            "take_profit": fmt_price(pair, sig["tp"]), "reward_to_risk": sig["rr"],
            "model_win_chance_percent": round(scored["p_win"] * 100, 1), "quality": scored["quality"],
            "reasons": scored["factors"],
            "context": {"move_last_12h_with_trade_percent": round(f["ret_12h"] * sgn * 100, 2),
                        "stop_size_vs_recent_range": round(f["risk_atr"], 2)},
        }
        self.found[jid] = facts
        J.log_event(pair, timeframe_min, "SETUP", {"id": jid, "dir": sig["direction"], "quality": scored["quality"]})
        return {"found": True, **facts}

    def get_journal_stats(self) -> dict:
        s = J.stats()
        return {k: {"resolved_setups": v["n"], "win_rate": None if v["win_rate"] is None else round(v["win_rate"], 3),
                    "mean_result_R": None if v["mean_r"] is None else round(v["mean_r"], 3)} for k, v in s.items()} | \
               {"note": "live record of this agent only; small samples are noise"}

    def get_recent_setups(self, pair: str, limit: int = 5) -> dict:
        rows = [r for r in J.recent(50) if r["pair"] == pair][:min(int(limit), 10)]
        return {"recent": [{"time_utc": str(r["signal_time"]), "direction": r["direction"], "quality": r["quality"],
                            "outcome": r["outcome"]} for r in rows]}

    def send_alert(self, setup_id: int, message: str) -> dict:
        exp_facts = self.found.get(setup_id)
        if exp_facts is None:
            return {"sent": False, "error": "unknown setup_id; use the setup_id from scan_for_setup"}
        if setup_id in self.alerted:
            return {"sent": False, "error": "alert already sent for this setup"}
        err = validate_alert(message, {"pair": exp_facts["pair"], "direction": exp_facts["direction"], "entry": exp_facts["entry"],
                                       "sl": exp_facts["stop_loss"], "tp": exp_facts["take_profit"], "quality": exp_facts["quality"]})
        if err:
            J.log_event(exp_facts["pair"], None, "ALERT_REJECTED", err)
            return {"sent": False, "error": err}
        return self._deliver(setup_id, message, "ALERT")

    def _deliver(self, setup_id: int, message: str, event: str) -> dict:
        res = self.alert_fn(message)
        J.set_explanation(setup_id, message)
        J.mark_alerted(setup_id)
        self.alerted.add(setup_id)
        J.log_event(self.found[setup_id]["pair"], None, event, {"id": setup_id, "channel": res.get("channel")})
        return res

    def fallback_alerts(self) -> list[int]:
        """Deliver templated alerts for any setup found but not yet alerted (LLM down, failed, or out of steps)."""
        done = []
        for jid, facts in self.found.items():
            if jid not in self.alerted:
                self._deliver(jid, template_alert(facts), "FALLBACK_ALERT")
                done.append(jid)
        return done

    def finish(self, summary: str) -> dict:
        self.finished = summary
        J.log_event(None, None, "FINISH", summary)
        return {"done": True}


SCHEMAS = [
    {"type": "function", "function": {"name": "scan_for_setup", "description":
        "Fetch the latest completed bars and check for a NEW ICT setup. If one is found it is scored by the model and journaled; "
        "returns exact entry, stop loss, take profit, model quality label, and the main reasons. Call this first.",
        "parameters": {"type": "object", "properties": {"pair": {"type": "string"}, "timeframe_min": {"type": "integer", "enum": [5, 15]}},
                       "required": ["pair", "timeframe_min"]}}},
    {"type": "function", "function": {"name": "get_journal_stats", "description":
        "The agent's own live track record: win rate and mean result in R for resolved setups, overall and by model quality label.",
        "parameters": {"type": "object", "properties": {}}}},
    {"type": "function", "function": {"name": "get_recent_setups", "description": "The most recent journaled setups for a pair and how they ended.",
        "parameters": {"type": "object", "properties": {"pair": {"type": "string"}, "limit": {"type": "integer"}}, "required": ["pair"]}}},
    {"type": "function", "function": {"name": "send_alert", "description":
        "Send the trader an alert about a found setup. The message is checked against the real figures: it must quote pair, direction, "
        "entry, stop loss and take profit exactly as returned by scan_for_setup, state the quality label, and never promise results.",
        "parameters": {"type": "object", "properties": {"setup_id": {"type": "integer"}, "message": {"type": "string"}},
                       "required": ["setup_id", "message"]}}},
    {"type": "function", "function": {"name": "finish", "description": "End this run with a one-sentence summary of what you did.",
        "parameters": {"type": "object", "properties": {"summary": {"type": "string"}}, "required": ["summary"]}}},
]
