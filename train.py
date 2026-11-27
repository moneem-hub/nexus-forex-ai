"""
Train + honestly evaluate the direction model.

    python train.py                  # reads EURUSD.csv, GBPUSD.csv, USDJPY.csv from this folder
    python train.py --data-dir data  # or from another folder
    python train.py --no-save        # evaluate only

What it does
  1. Builds scale-free features (features.py) for all pairs and pools them.
  2. Walk-forward evaluation: train on the past, predict the next block, roll forward.
     The model never sees the future, so the score is the one you could expect live.
  3. Compares every model with a naive baseline ("always predict the usual direction").
  4. Runs a LEAK CHECK: adds High/Low-based features and warns if accuracy jumps.
  5. Retrains the best model on all data and saves it to forex_model.pkl.
"""
import argparse
import pickle
import warnings
from pathlib import Path

import numpy as np
import pandas as pd
import sklearn
from sklearn.ensemble import GradientBoostingClassifier, RandomForestClassifier
from sklearn.linear_model import LogisticRegression
from sklearn.pipeline import make_pipeline
from sklearn.preprocessing import StandardScaler

from features import BASE_FEATURES, RANGE_FEATURES, build_features

warnings.filterwarnings("ignore")
PAIRS = ["EURUSD", "GBPUSD", "USDJPY"]
CONFIDENCE_MARGIN = 0.05  # "confident" = probability at least 0.55 or at most 0.45


def load_pair(path: Path) -> pd.DataFrame:
    df = pd.read_csv(path, parse_dates=["Date"], index_col="Date").sort_index()
    df = df[~df.index.duplicated()]
    return df.dropna(subset=["Open", "High", "Low", "Close"])


def make_dataset(data_dir: str, include_range: bool = False) -> pd.DataFrame:
    frames = []
    for pair in PAIRS:
        f = Path(data_dir) / f"{pair}.csv"
        if not f.exists():
            print(f"  (skipping {pair}: {f} not found)")
            continue
        df = load_pair(f)
        X = build_features(df, include_range)
        nxt = df["Close"].shift(-1)
        X["target"] = (nxt > df["Close"]).astype(float).where(nxt.notna())  # NaN on last row
        X["pair"] = pair
        frames.append(X)
    if not frames:
        raise SystemExit("No CSV files found. Use --data-dir to point at them.")
    return pd.concat(frames).dropna().sort_index()


def model_zoo():
    return {
        "Logistic Regression": lambda: make_pipeline(StandardScaler(), LogisticRegression(C=0.1, max_iter=1000)),
        "Random Forest": lambda: RandomForestClassifier(
            n_estimators=200, max_depth=4, min_samples_leaf=50, n_jobs=-1, random_state=42),
        "Gradient Boosting": lambda: GradientBoostingClassifier(
            n_estimators=100, max_depth=2, learning_rate=0.05, subsample=0.8, random_state=42),
    }


def walk_forward(data, make_model, features, min_train_days=750, step=63):
    """Expanding-window walk-forward. Returns out-of-sample truth, probabilities, baseline, pair."""
    dates = data.index.unique().sort_values()
    y_true, proba, base, pairs = [], [], [], []
    for i in range(min_train_days, len(dates), step):
        train = data[data.index < dates[i]]
        end = dates[i + step] if i + step < len(dates) else None
        test = data[data.index >= dates[i]] if end is None else data[(data.index >= dates[i]) & (data.index < end)]
        if test.empty:
            continue
        model = make_model().fit(train[features], train["target"])
        proba.append(model.predict_proba(test[features])[:, 1])
        y_true.append(test["target"].values)
        base.append(np.full(len(test), float(train["target"].mean() >= 0.5)))
        pairs.append(test["pair"].values)
    return (np.concatenate(y_true), np.concatenate(proba), np.concatenate(base), np.concatenate(pairs))


def summarize(y, p, base, pairs):
    pred = (p >= 0.5).astype(float)
    n = len(y)
    acc = (pred == y).mean()
    ci = 1.96 * np.sqrt(acc * (1 - acc) / n)
    conf = np.abs(p - 0.5) >= CONFIDENCE_MARGIN
    return {
        "n": n, "acc": acc, "ci": ci, "base": (base == y).mean(),
        "conf_cov": conf.mean(), "conf_acc": (pred[conf] == y[conf]).mean() if conf.any() else np.nan,
        "per_pair": {pr: (pred[pairs == pr] == y[pairs == pr]).mean() for pr in np.unique(pairs)},
    }


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--data-dir", default=".")
    ap.add_argument("--out", default="forex_model.pkl")
    ap.add_argument("--no-save", action="store_true")
    ap.add_argument("--min-train", type=int, default=750, help="min training days before first test block")
    ap.add_argument("--step", type=int, default=63, help="test block length in days (~1 quarter)")
    a = ap.parse_args()

    data = make_dataset(a.data_dir)
    feats = BASE_FEATURES
    print(f"Dataset: {len(data)} rows, {data.index.min().date()} -> {data.index.max().date()}, "
          f"pairs: {sorted(data['pair'].unique())}, up-days: {data['target'].mean():.1%}")
    print(f"Walk-forward: first {a.min_train} days train only, then {a.step}-day blocks, retrain each block.\n")

    results, best = {}, None
    print(f"{'Model':22s} {'OOS acc':>9s} {'±95% CI':>8s} {'baseline':>9s} {'edge':>7s}   confident subset (|p-0.5|>={CONFIDENCE_MARGIN})")
    for name, factory in model_zoo().items():
        s = summarize(*walk_forward(data, factory, feats, a.min_train, a.step))
        results[name] = s
        print(f"{name:22s} {s['acc']:9.3f} {s['ci']:8.3f} {s['base']:9.3f} {s['acc'] - s['base']:+7.3f}   "
              f"acc {s['conf_acc']:.3f} on {s['conf_cov']:.0%} of days")
        if best is None or s["acc"] > results[best]["acc"]:
            best = name
    n = results[best]["n"]
    print(f"\n({n} out-of-sample predictions. A difference smaller than the ± CI is noise.)")
    print("Per-pair accuracy of best model:", {k: round(float(v), 3) for k, v in results[best]["per_pair"].items()})

    # ---- Leak check -------------------------------------------------------------------
    print("\nLEAK CHECK: Logistic Regression with High/Low-based features added")
    data_r = make_dataset(a.data_dir, include_range=True)
    s_r = summarize(*walk_forward(data_r, model_zoo()["Logistic Regression"], BASE_FEATURES + RANGE_FEATURES, a.min_train, a.step))
    jump = s_r["acc"] - results["Logistic Regression"]["acc"]
    print(f"  without: {results['Logistic Regression']['acc']:.3f}   with: {s_r['acc']:.3f}   jump: {jump:+.3f}")
    if jump > 0.05:
        print("  WARNING: a jump this large is not skill, it is leakage (High/Low windows leak the next move).")
        print("           Those features stay OFF in production.")

    # ---- Final fit + save -------------------------------------------------------------
    if not a.no_save:
        final = model_zoo()[best]().fit(data[feats], data["target"])
        meta = {"name": best, "features": feats, "walk_forward_acc": float(results[best]["acc"]),
                "baseline_acc": float(results[best]["base"]), "n_oos": int(n),
                "trained_through": str(data.index.max().date()), "sklearn": sklearn.__version__}
        with open(a.out, "wb") as f:
            pickle.dump({"model": final, "features": feats, "meta": meta}, f)
        print(f"\nSaved {best} -> {a.out}  (trained through {meta['trained_through']}).")
        print("Model files depend on your scikit-learn version: re-run train.py after upgrading it.")


if __name__ == "__main__":
    main()
