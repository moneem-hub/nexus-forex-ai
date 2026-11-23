"""
Score a live ICT setup with the trained setup-quality model.

Train/serve parity by construction: the raw inputs come from collect_setups.setup_features (the same
function that built the training data) and the direction-aware transform comes from
train_setup_model.add_direction_features (the same function the trainer uses).

The score is a QUALITY INDICATOR (weak evidence, see the evaluation), never a guarantee.
"""
import pickle

import numpy as np
import pandas as pd

from collect_setups import setup_features
from train_setup_model import add_direction_features

PRETTY = {
    "ret_12h_dir": "12h momentum with the trade", "ret_4h_dir": "4h momentum with the trade",
    "ret_24h_dir": "24h momentum with the trade", "dist_sma_24h_dir": "price stretched from its 24h average",
    "risk_atr": "stop size vs recent volatility", "risk_pct": "stop size (% of price)",
    "asian_pos_dir": "entry position in the Asian range", "asian_range_pct": "size of the Asian range",
    "atr_pct": "recent volatility", "is_buy": "buy direction", "is_ny": "New York session",
    "hour": "hour of day", "dow": "day of week", "tf_min": "timeframe",
}


# Only these are offered as human-readable reasons. day-of-week, hour, direction, session and timeframe still feed the
# model, but their evidence is weak and they have no trading rationale, so presenting them as "reasons" would mislead.
SHOW = {"ret_12h_dir", "ret_4h_dir", "ret_24h_dir", "dist_sma_24h_dir", "risk_atr", "risk_pct",
        "asian_pos_dir", "asian_range_pct", "atr_pct"}


def load_scorer(path: str = "setup_model.pkl") -> dict:
    with open(path, "rb") as f:
        return pickle.load(f)


def score_signal(bundle: dict, window: pd.DataFrame, signal: dict, tf: int, top_n: int = 3) -> dict:
    """
    window : COMPLETED bars (UTC index) up to and including the signal bar
    signal : dict with direction, entry, sl (what run_ict_strategy returns)
    Returns p_win, quality ('higher'/'lower'), and the top factors behind the score.
    """
    feats = setup_features(window, signal["direction"], signal["entry"], signal["sl"], tf)
    row = add_direction_features(pd.DataFrame([feats]))[bundle["features"]]
    model = bundle["model"]
    p = float(model.predict_proba(row)[:, 1][0])
    thr = bundle["meta"].get("score_median")
    quality = None if thr is None else ("higher" if p >= thr else "lower")

    factors = []
    try:                                                    # explanation for the Logistic Regression pipeline
        x = model[:-1].transform(row)[0]
        contrib = x * model[-1].coef_[0]
        for j in np.argsort(-np.abs(contrib)):
            name = bundle["features"][j]
            if name not in SHOW:
                continue
            if len(factors) == top_n:
                break
            factors.append({"factor": PRETTY.get(name, name), "effect": "helps" if contrib[j] > 0 else "hurts",
                            "strength": round(float(abs(contrib[j])), 3)})
    except Exception:
        pass
    return {"p_win": round(p, 4), "quality": quality, "factors": factors, "features": feats}
