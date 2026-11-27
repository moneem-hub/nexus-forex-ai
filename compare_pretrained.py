"""
Does a PRE-TRAINED market model (Kronos) add information beyond our own scoring model? Judged strictly out-of-sample.

  python compare_pretrained.py          (after: python kronos_features.py ...)

Same leak-free protocol as train_setup_model.py (chronological walk-forward, embargo, day-clustered intervals), on the SAME
setups for every variant, so the comparison is paired:
    A  our model (14 features)             B  our model + Kronos forecast features             C  Kronos features only
Also reports the plain "accuracy" of Kronos's forecast direction against what the market really did over the next 2 hours.
"""
import argparse

import numpy as np
import pandas as pd
from sklearn.metrics import roc_auc_score

from kronos_features import KR_COLS
from train_setup_model import EMBARGO, FEATURES as BASE, boot_ci, load_setups, models


def wf(df, factory, features, min_train=0.4, blocks=5):
    n = len(df)
    edges = np.linspace(int(n * min_train), n, blocks + 1).astype(int)
    parts = []
    for k in range(blocks):
        lo, hi = edges[k], edges[k + 1]
        test, train = df.iloc[lo:hi], df.iloc[:lo]
        train = train[train.time <= test.time.min() - EMBARGO]
        if train.y.nunique() < 2 or test.empty:
            continue
        p = factory().fit(train[features], train.y).predict_proba(test[features])[:, 1]
        parts.append(test.assign(p=p, keep=p >= np.median(p)))
    return pd.concat(parts)


def _auc(y, p):
    return roc_auc_score(y, p) if len(set(y)) > 1 else np.nan


def paired(a, b):
    """B minus A on identical rows: AUC difference and 'top half' result difference (R per setup), with day-clustered 95% intervals."""
    assert (a.index == b.index).all()
    y, pa, pb, r, ka, kb = a.y.values, a.p.values, b.p.values, a.r.values, a.keep.values, b.keep.values
    days = a.time.dt.strftime("%Y-%m-%d").values
    d_auc = _auc(y, pb) - _auc(y, pa)
    d_r = r[kb].mean() - r[ka].mean()
    auc_ci = boot_ci(lambda i: _auc(y[i], pb[i]) - _auc(y[i], pa[i]), days)
    r_ci = boot_ci(lambda i: r[i][kb[i]].mean() - r[i][ka[i]].mean() if kb[i].any() and ka[i].any() else np.nan, days)
    return {"auc": _auc(y, pb), "auc_base": _auc(y, pa), "d_auc": d_auc, "d_auc_ci": tuple(auc_ci), "d_r": d_r, "d_r_ci": tuple(r_ci),
            "r_top": r[kb].mean(), "r_top_base": r[ka].mean()}


def direction_accuracy(df):
    """Accuracy of Kronos's forecast direction vs the realised 2h move, against the naive 'trust the setup' rule."""
    d = df.dropna(subset=["kr_ret_dir", "eval_real_ret_dir"])
    d = d[(d.kr_ret_dir != 0) & (d.eval_real_ret_dir != 0)]
    days = d.time.dt.strftime("%Y-%m-%d").values
    ok = (np.sign(d.kr_ret_dir.values) == np.sign(d.eval_real_ret_dir.values)).astype(float)
    naive = (d.eval_real_ret_dir.values > 0).astype(float)
    ci = lambda x: tuple(boot_ci(lambda i: x[i].mean(), days))
    return {"n": len(d), "kronos": ok.mean(), "kronos_ci": ci(ok), "naive": naive.mean(), "naive_ci": ci(naive)}


def compare(df, base=BASE, kr=KR_COLS, model_names=("Logistic Regression", "Random Forest"), min_train=0.4, blocks=5, show=print):
    results = {}
    for name in model_names:
        f = models()[name]
        a, b, c = wf(df, f, base, min_train, blocks), wf(df, f, base + kr, min_train, blocks), wf(df, f, kr, min_train, blocks)
        results[name] = {"B_vs_A": paired(a, b), "C_vs_A": paired(a, c)}
        for label, key in (("A -> B (our model + Kronos features)", "B_vs_A"), ("A -> C (Kronos features only)", "C_vs_A")):
            r = results[name][key]
            show(f"{name:20s} {label:40s} AUC {r['auc_base']:.3f} -> {r['auc']:.3f}  "
                 f"(change {r['d_auc']:+.3f}, 95% {r['d_auc_ci'][0]:+.3f} to {r['d_auc_ci'][1]:+.3f}) | top-half result {r['r_top_base']:+.3f} -> {r['r_top']:+.3f} R "
                 f"(change {r['d_r']:+.3f}, 95% {r['d_r_ci'][0]:+.3f} to {r['d_r_ci'][1]:+.3f})")
    return results


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--setups", default="data/setups*.csv")
    ap.add_argument("--kronos", default="data/kronos_features.csv")
    a = ap.parse_args()
    df = load_setups(a.setups)
    kr = pd.read_csv(a.kronos, parse_dates=["time"])
    df = df.merge(kr, on=["pair", "time", "tf_min"], how="inner").dropna(subset=KR_COLS).sort_values("time").reset_index(drop=True)
    if len(df) < 300:
        raise SystemExit(f"Only {len(df)} setups have Kronos features: far too few for a meaningful comparison "
                         "(walk-forward needs hundreds). Run kronos_features.py WITHOUT --limit first.")
    print(f"\n{len(df)} setups have Kronos features.\n")
    print("Kronos forecast direction vs what the market really did over the next 2 hours:")
    d = direction_accuracy(df)
    print(f"  Kronos direction accuracy {d['kronos']:.1%} (95% {d['kronos_ci'][0]:.1%}-{d['kronos_ci'][1]:.1%}) | "
          f"naive 'the setup is right' {d['naive']:.1%} (95% {d['naive_ci'][0]:.1%}-{d['naive_ci'][1]:.1%})  n={d['n']}\n")
    res = compare(df)
    best = max(res.values(), key=lambda v: v["B_vs_A"]["d_auc_ci"][0])["B_vs_A"]
    print("\nVerdict:", "the pretrained model adds measurable information (the interval is above zero)." if best["d_auc_ci"][0] > 0
          else "no proven gain: the improvement is inside the noise. That is a valid, honest finding.")


if __name__ == "__main__":
    main()
