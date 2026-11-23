"""
One agent run (what the scheduler will call every few minutes).

  python -m agent.run_agent --pair EURUSD --tf 15                              # live market, Groq LLM
  python -m agent.run_agent --pair EURUSD --tf 5 --replay data/raw/eurusd-m5-....csv --at "2025-03-04 10:00"
  python -m agent.run_agent --pair EURUSD --tf 15 --no-llm                     # skip the LLM: deterministic fallback only

Replay runs write to a SEPARATE database (<name>_replay), so demos never mix with the live track record.
"""
import argparse

import pandas as pd

import utils.db as D
from agent import journal as J
from agent.agent import run_agent
from agent.config import load_env
from agent.data_sources import LiveSource, ReplaySource
from agent.llm import FakeLLM, GroqLLM, LLMError
from agent.scoring import load_scorer
from agent.tools import ToolBox
from collect_setups import load_ohlc


def main():
    load_env()
    ap = argparse.ArgumentParser()
    ap.add_argument("--pair", default="EURUSD")
    ap.add_argument("--tf", type=int, default=15, choices=[5, 15])
    ap.add_argument("--model", default="setup_model.pkl")
    ap.add_argument("--replay", help="Dukascopy CSV: replay history instead of the live market")
    ap.add_argument("--at", help='replay moment in UTC, e.g. "2025-03-04 10:00"')
    ap.add_argument("--no-llm", action="store_true")
    ap.add_argument("--max-age-minutes", type=int, default=45)
    a = ap.parse_args()

    if a.replay:
        if not a.at:
            raise SystemExit("--replay needs --at")
        D.DB_NAME = D.DB_NAME + "_replay"
        source, now, seen_days = ReplaySource({(a.pair, a.tf): load_ohlc(a.replay)}), pd.Timestamp(a.at, tz="UTC"), 36500
    else:
        source, now, seen_days = LiveSource(), pd.Timestamp.now(tz="UTC"), 3

    J.init_journal()
    for r in J.resolve_pending(source, now):                       # first: settle earlier setups whose outcome is now known
        print(f"outcome: setup {r['id']} {r['pair']} -> {r['outcome']}")
    box = ToolBox(source, load_scorer(a.model), now, J.load_seen(seen_days), max_age_minutes=a.max_age_minutes)
    llm = FakeLLM(lambda m: LLMError("LLM disabled (--no-llm)")) if a.no_llm else GroqLLM()
    print(run_agent(llm, box, a.pair, a.tf))


if __name__ == "__main__":
    main()
