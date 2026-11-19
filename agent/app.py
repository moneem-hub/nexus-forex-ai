"""
Where the agent gets its bars.

  LiveSource   : Yahoo Finance, the SAME call the Streamlit app already uses (7 days, 5m or 15m).
  ReplaySource : history from your Dukascopy CSVs, "as of" any past moment. Same agent code, no live market needed,
                 so the demo works any day and the live logic can be tested against history.

Both return only COMPLETED bars (a bar opening at t is complete once t + timeframe <= now), with a UTC index and
columns Open/High/Low/Close, covering the last 7 days, which is what the ICT engine is fed in the app.
"""
import warnings

import pandas as pd

warnings.filterwarnings("ignore", module="yfinance")   # yfinance triggers harmless pandas deprecation warnings that clutter the console

TICKERS = {"EURUSD": "EURUSD=X", "GBPUSD": "GBPUSD=X", "USDJPY": "USDJPY=X",
           "XAUUSD": "GC=F"}   # gold: Yahoo only offers futures (GC=F), which differ slightly from spot gold
LOOKBACK = pd.Timedelta(days=7)


def _completed(df: pd.DataFrame, tf: int, now: pd.Timestamp) -> pd.DataFrame:
    df = df[df.index + pd.Timedelta(minutes=tf) <= now]
    return df[df.index >= now - LOOKBACK]


class LiveSource:
    def bars(self, pair: str, tf: int, now: pd.Timestamp | None = None) -> pd.DataFrame:
        import yfinance as yf
        now = now or pd.Timestamp.now(tz="UTC")
        data = yf.download(TICKERS[pair], period="7d", interval=f"{tf}m", auto_adjust=True, progress=False)
        if data is None or data.empty:
            return pd.DataFrame(columns=["Open", "High", "Low", "Close"])
        if hasattr(data.columns, "levels"):
            data.columns = data.columns.get_level_values(0)
        data = data.rename(columns={c: str(c).strip().capitalize() for c in data.columns})[["Open", "High", "Low", "Close"]]
        data.index = data.index.tz_localize("UTC") if data.index.tz is None else data.index.tz_convert("UTC")
        return _completed(data.dropna(), tf, now)


class ReplaySource:
    def __init__(self, frames: dict):
        """frames: {(pair, tf_minutes): UTC-indexed OHLC DataFrame}"""
        self.frames = frames

    def bars(self, pair: str, tf: int, now: pd.Timestamp) -> pd.DataFrame:
        return _completed(self.frames[(pair, tf)], tf, now)
