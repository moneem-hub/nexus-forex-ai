APP_TITLE   = "NEXUS FOREX — AI Trading System"
APP_VERSION = "v2.4"
APP_ICON    = "📈"

PAIRS = ["EURUSD=X", "GBPUSD=X", "USDJPY=X"]

CREDENTIALS = {"admin": "admin123"}

MODEL_FILES = ["best_forex_model.pkl", "forex_model.pkl"]

CALENDAR_EVENTS = [
    (
        "CPI",
        "Consumer Price Index",
        "Measures inflation in consumer goods & services. Strong influence on central bank rate decisions and USD pairs.",
        "HIGH", "high",
    ),
    (
        "NFP",
        "Non-Farm Payrolls",
        "Monthly US jobs report — one of the most market-moving events. Beats/misses cause sharp volatility spikes.",
        "HIGH", "high",
    ),
    (
        "FOMC",
        "Fed Rate Decision",
        "Federal Open Market Committee interest rate decision & monetary policy statement. Directly drives USD trend.",
        "HIGH", "high",
    ),
    (
        "GDP",
        "Gross Domestic Product",
        "Quarterly economic growth rate. Sustained above-trend growth signals tightening; contraction signals easing.",
        "MED", "med",
    ),
    (
        "Retail Sales",
        "Consumer Spending",
        "Monthly consumer spending indicator. Strong retail data signals economic health and can fuel inflation.",
        "MED", "med",
    ),
    (
        "PMI",
        "Purchasing Managers Index",
        "Index >50 signals sector expansion. Flash PMI is a leading indicator watched closely by algo traders.",
        "LOW", "low",
    ),
]

SL_PIPS = {"USDJPY=X": 0.30, "default": 0.0030}
TP_PIPS = {"USDJPY=X": 0.60, "default": 0.0060}
