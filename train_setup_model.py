"""
STEP 2: can a model tell good ICT setups from bad ones?

    python train_setup_model.py                 # reads every data/setups*.csv made by collect_setups.py

Evaluation is chronological walk-forward on SETUPS (not rows of prices):
  - the model is trained only on earlier setups and scores later, unseen ones;
  - setups from the 24h before a test block are excluded from training (their outcomes were not
    known yet = "embargo"), so no label information leaks across the boundary;
  - every model is compared with the baseline "take every setup";
  - a shuffled-label control checks the pipeline itself cannot produce fake skill.
Results are reported with 95% intervals that resample whole calendar days (setups on the same day
are correlated), because with a few hundred setups a result inside the interval is noise, not skill.
"""
import argparse
import glob
import pickle
import warnings

import numpy as np
import pandas as pd
import sklearn
from sklearn.ensemble import RandomForestClassifier
from sklearn.impute import SimpleImputer
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import roc_auc_score
from sklearn.pipeline import make_pipeline
from sklearn.preprocessing import StandardScaler

warnings.filterwarnings("ignore")
# Direction-aware inputs (suffix _dir): the same number must mean the same thing for a BUY and a SELL.
# e.g. ret_12h_dir > 0 = "price has been moving WITH my trade direction", for both BUY and SELL.
FEATURES = ["is_buy", "is_ny", "hour", "dow", "risk_pct", "atr_pct", "risk_atr", "asian_range_pct",
            "asian_pos_dir", "ret_4h_dir", "ret_12h_dir", "ret_24h_dir", "dist_sma_24h_dir", "tf_min"]
LEGACY = {"ret_16": "ret_4h", "ret_48": "ret_12h", "ret_96": "ret_24h", "dist_sma_96": "dist_sma_24h"}  # old 15m files
EMBARGO = pd.Timedelta(days=1)
RNG = np.random.default_rng(42)


def add_direction_features(df: pd.DataFrame) -> pd.DataFrame:
    """Make inputs direction-aware. Used by training AND by the live agent, so both see identical inputs."""
    df = df.copy()
    sgn = np.where(df["is_buy"] == 1, 1.0, -1.0)
    for c in ("ret_4h", "ret_12h", "ret_24h", "dist_sma_24h"):
        df[c + "_dir"] = df[c] * sgn                                     # momentum / stretch relative to the trade
    df["asian_pos_dir"] = np.where(df["is_buy"] == 1, df["asian_pos"], 1 - df["asian_pos"])  # 0 = entered at the favourable end
    return df


def load_setups(pattern: str) -> pd.DataFrame:
    files = sorted(glob.glob(pattern))
    if not files:
        raise SystemExit(f"No files match {pattern}. Run collect_setups.py first.")
    df = pd.concat([pd.read_csv(f, parse_dates=["time"]).rename(columns=LEGACY) for f in files])
    if "tf_min" not in df.columns:
        df["tf_min"] = 15
    df["tf_min"] = df["tf_min"].fillna(15).astype(int)                 # files from the first version are 15-minute
    df = add_direction_features(df)
    df = df.drop_duplicates(["pair", "time", "tf_min"])
    df = df[df.outcome != "PENDING"].sort_values("time").reset_index(drop=True)
    df["y"] = (df.outcome == "PROFIT").astype(int)
    df["r"] = np.where(df.y == 1, df.rr, -1.0)          # result of the trade in R (risk units)
    print(f"Loaded {len(df)} resolved setups from {len(files)} file(s); "
          f"{df.time.min().date()} -> {df.time.max().date()}; win rate {df.y.mean():.1%}; "
          f"mean result {df.r.mean():+.3f} R per setup")
    for tf, g in df.groupby("tf_min"):
        print(f"  {tf:>2}-minute setups: {len(g)}, win rate {g.y.mean():.1%}, mean {g.r.mean():+.3f} R")
    return df


def models():
    return {
        "Logistic Regression": lambda: make_pipeline(SimpleImputer(strategy="median"), StandardScaler(),
                                                     LogisticRegression(C=0.05, max_iter=1000)),
        "Random Forest": lambda: make_pipeline(SimpleImputer(strategy="median"),
                                               RandomForestClassifier(n_estimators=300, max_depth=3,
                                                                      min_samples_leaf=20, n_jobs=-1, random_state=42)),
    }


def walk_forward(df, factory, min_train=0.4, blocks=5, y_col="y"):
    n = len(df)
    edges = np.linspace(int(n * min_train), n, blocks + 1).astype(int)
    parts = []
    for k in range(blocks):
        lo, hi = edges[k], edges[k + 1]
        test = df.iloc[lo:hi]
        train = df.iloc[:lo]
        train = train[train.time <= test.time.min() - EMBARGO]            # embargo
        if train[y_col].nunique() < 2 or test.empty:
            continue
        m = factory().fit(train[FEATURES], train[y_col])
        p = m.predict_proba(test[FEATURES])[:, 1]
        parts.append(test.assign(p=p, keep=(p >= np.median(p))))          # keep the better-scored half of each block
    return pd.concat(parts)


def boot_ci(stat, days, B=2000):
    """95% interval by resampling whole CALENDAR DAYS. Setups on the same day (other pairs, other
    timeframes) come from the same market moves, so they are not independent; resampling single
    setups would make the interval look much tighter than it really is."""
    groups = [np.flatnonzero(days == d) for d in np.unique(days)]
    vals = []
    for _ in range(B):
        pick = RNG.integers(0, len(groups), len(groups))
        i = np.concatenate([groups[k] for k in pick])
        v = stat(i)
        if not np.isnan(v):
            vals.append(v)
    return np.percentile(vals, [2.5, 97.5])


def evaluate(oos: pd.DataFrame, name: str):
    y, p, r, keep = oos.y.values, oos.p.values, oos.r.values, oos.keep.values
    days = oos.time.dt.strftime("%Y-%m-%d").values
    auc = roc_auc_score(y, p)
    lo, hi = boot_ci(lambda i: roc_auc_score(y[i], p[i]) if len(set(y[i])) > 1 else np.nan, days)
    d_mean = r[keep].mean() - r.mean()
    dlo, dhi = boot_ci(lambda i: r[i][keep[i]].mean() - r[i].mean() if keep[i].any() else np.nan, days)
    print(f"\n{name}  ({len(oos)} out-of-sample setups)")
    print(f"  AUC {auc:.3f}  [95% interval {lo:.3f}-{hi:.3f}]     (0.500 = no skill)")
    print(f"  take ALL setups      : win rate {y.mean():.1%}  mean {r.mean():+.3f} R  (n={len(y)})")
    print(f"  take model's top half: win rate {y[keep].mean():.1%}  mean {r[keep].mean():+.3f} R  (n={keep.sum()})")
    print(f"  improvement {d_mean:+.3f} R per setup  [95% interval {dlo:+.3f} to {dhi:+.3f}]")
    return auc, (dlo, dhi)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--setups", default="data/setups*.csv")
    ap.add_argument("--out", default="setup_model.pkl")
    ap.add_argument("--no-save", action="store_true")
    ap.add_argument("--blocks", type=int, default=5)
    ap.add_argument("--min-train", type=float, default=0.4)
    a = ap.parse_args()

    df = load_setups(a.setups)
    if len(df) < 100:
        raise SystemExit("Fewer than 100 resolved setups: too few to train anything meaningful. Collect more data.")
    print(f"Walk-forward: first {a.min_train:.0%} of setups = training only, then {a.blocks} chronological test blocks.")

    for name, factory in models().items():
        evaluate(walk_forward(df, factory, a.min_train, a.blocks), name)

    # control: same pipeline with the labels randomly shuffled must show ~no skill
    shuf = df.copy()
    shuf["y_shuf"] = RNG.permutation(shuf.y.values)
    oos = walk_forward(shuf, models()["Logistic Regression"], a.min_train, a.blocks, y_col="y_shuf")
    print(f"\nControl (shuffled labels): AUC {roc_auc_score(oos.y_shuf, oos.p):.3f}  <- should be near 0.500")

    if not a.no_save:
        final = models()["Logistic Regression"]().fit(df[FEATURES], df.y)
        coefs = final[-1].coef_[0]
        order = np.argsort(-np.abs(coefs))
        print("\nWhat the (explainable) Logistic Regression leans on, standardized weights (+ = more likely to win):")
        for j in order[:6]:
            print(f"  {FEATURES[j]:18s} {coefs[j]:+.3f}")
        with open(a.out, "wb") as f:
            pickle.dump({"model": final, "features": FEATURES,
                         "meta": {"n_train": int(len(df)), "trained_through": str(df.time.max().date()),
                                  "score_median": float(np.median(final.predict_proba(df[FEATURES])[:, 1])),
                                  "sklearn": sklearn.__version__}}, f)
        print(f"\nSaved Logistic Regression -> {a.out}")
        print("Read the AUC and improvement intervals above BEFORE trusting this model: if they include 0.500 / 0, it has shown no proven skill.")


if __name__ == "__main__":
    main()
