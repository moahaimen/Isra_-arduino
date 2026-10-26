#!/usr/bin/env python3
"""E2 causal controllers (preregistration Addendum A).

  select : leave-one-segment-out on VALIDATION -> out-of-fold probabilities -> choose thresholds;
           fit final models on all validation segments; write frozen_controllers.json + model pickles
  eval   : apply the frozen controllers to another split (test), once
"""
from __future__ import annotations

import argparse
import hashlib
import itertools
import json
import os
import pickle
import sys

import numpy as np
import pandas as pd

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import oracle_gate as og  # noqa: E402

FEATS = ["m_raw", "mog2_fg", "m_tile0", "m_tile1", "m_tile2", "m_max", "m_avg3", "m_avg10", "m_d1", "mog_avg3"]
SEED = 20261026


def features(S: og.Split) -> np.ndarray:
    m = S.m4.copy()
    m["m_max"] = m[["m_tile0", "m_tile1", "m_tile2"]].max(axis=1)
    g = m.groupby("seg", sort=False)
    m["m_avg3"] = g.m_raw.transform(lambda x: x.rolling(3, min_periods=1).mean())
    m["m_avg10"] = g.m_raw.transform(lambda x: x.rolling(10, min_periods=1).mean())
    m["m_d1"] = g.m_raw.transform(lambda x: x.diff().fillna(0))
    m["mog_avg3"] = g.mog2_fg.transform(lambda x: x.rolling(3, min_periods=1).mean())
    return m[FEATS].to_numpy(float)


def labels(S: og.Split):
    opp = S.HW.any(axis=2)  # [mode, frame]: running this mode at t timely-detects >= 1 moving track
    return {"FULL": opp[og.FULL_I], "LOW": opp[0], "ROI0": opp[1], "ROI1": opp[2], "ROI2": opp[3]}


def make(name):
    from sklearn.linear_model import LogisticRegression
    from sklearn.tree import DecisionTreeClassifier
    from sklearn.ensemble import HistGradientBoostingClassifier
    from sklearn.neural_network import MLPClassifier
    from sklearn.pipeline import make_pipeline
    from sklearn.preprocessing import StandardScaler
    if name == "logreg":
        return make_pipeline(StandardScaler(), LogisticRegression(C=1.0, class_weight="balanced", max_iter=2000))
    if name == "tree":
        return DecisionTreeClassifier(max_depth=4, min_samples_leaf=10, class_weight="balanced", random_state=SEED)
    if name == "gbt":
        return HistGradientBoostingClassifier(max_depth=3, max_iter=100, learning_rate=0.05, class_weight="balanced",
                                              random_state=SEED)
    if name == "mlp":
        return make_pipeline(StandardScaler(), MLPClassifier((16,), alpha=1e-3, max_iter=2000, random_state=SEED))
    raise ValueError(name)


MODELS = ["logreg", "tree", "gbt", "mlp"]
TARGETS = ["FULL", "LOW", "ROI0", "ROI1", "ROI2"]


def proba(model, X):
    return model.predict_proba(X)[:, 1]


def fit_predict(Xtr, ytr, Xte, name):
    if ytr.min() == ytr.max():
        return np.full(len(Xte), float(ytr[0])), None
    m = make(name).fit(Xtr, ytr)
    return proba(m, Xte), m


def act(S: og.Split, P: dict, tau, cool, rho=None):
    """P: target -> per-frame probability. rho None = FULL-only controller; else MSIP mode rule."""
    T = len(S.eid)
    m = -np.ones(T, dtype=int)
    p = P["FULL"]
    last = -10 ** 9
    for i in range(T):
        if S.start[i]:
            m[i], last = og.FULL_I, i
            continue
        if p[i] >= tau and i - last > cool:
            last = i
            if rho is None:
                m[i] = og.FULL_I
            else:
                r = np.array([P["ROI0"][i], P["ROI1"][i], P["ROI2"][i]])
                if r.max() >= rho * p[i]:
                    m[i] = 1 + int(r.argmax())
                elif P["LOW"][i] >= rho * p[i]:
                    m[i] = 0
                else:
                    m[i] = og.FULL_I
    return m


def choose(S, P, msip):
    taus = sorted(set(np.round(np.quantile(P["FULL"], np.linspace(0.0, 0.99, 60)), 6)))
    grid = itertools.product(taus, [0, 2, 5], [0.5, 0.7, 0.9] if msip else [None])
    best = None
    for tau, c, rho in grid:
        tl, cost = S.evaluate(act(S, P, tau, c, rho))
        r, cs = tl.mean(), cost.sum()
        key = (0, cs) if r >= 0.90 else (1, -r, cs)
        if best is None or key < best[0]:
            best = (key, {"tau": float(tau), "cool": c, "rho": rho}, float(r), float(cs / len(S.eid)))
    return best


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("cmd", choices=["select", "eval"])
    ap.add_argument("--train", default="/home/claude/e1/validation")
    ap.add_argument("--data")
    ap.add_argument("--out", default=os.path.join(HERE, "..", "04_experiments", "controller_results"))
    ap.add_argument("--tag", default="test")
    a = ap.parse_args()
    os.makedirs(a.out, exist_ok=True)
    S = og.Split(a.train)
    X, Y = features(S), labels(S)
    if a.cmd == "select":
        segs = S.seg_names
        frozen, rows = {"features": FEATS, "rule": "LOSO out-of-fold on validation; min cost s.t. R>=0.90 else max R"}, []
        models_out = {}
        for name in MODELS:
            oof = {t: np.zeros(len(S.eid)) for t in TARGETS}
            for s in segs:
                te = S.seg == s
                for t in TARGETS:
                    oof[t][te], _ = fit_predict(X[~te], Y[t][~te], X[te], name)
            from sklearn.metrics import roc_auc_score
            auc = float(roc_auc_score(Y["FULL"], oof["FULL"])) if Y["FULL"].any() else float("nan")
            for msip in (False, True):
                key, prm, r, c = choose(S, oof, msip)
                cname = f"{'msip' if msip else 'full'}_{name}"
                frozen[cname] = {"model": name, "params": prm, "oof_R_timely": r, "oof_cost_per_frame": c,
                                 "oof_auroc_full_opportunity": auc, "met_0.90_oof": key[0] == 0}
                rows.append({"controller": cname, **frozen[cname]})
            models_out[name] = {t: (make(name).fit(X, Y[t]) if Y[t].min() != Y[t].max() else float(Y[t][0]))
                                for t in TARGETS}
        pickle.dump(models_out, open(os.path.join(a.out, "frozen_models.pkl"), "wb"))
        fz = os.path.join(a.out, "frozen_controllers.json")
        json.dump(frozen, open(fz, "w"), indent=1, default=str)
        open(fz + ".sha256", "w").write(hashlib.sha256(open(fz, "rb").read()).hexdigest() + "\n")
        pd.DataFrame(rows).to_csv(os.path.join(a.out, "selection_validation_loso.csv"), index=False)
        print(pd.DataFrame(rows)[["controller", "params", "oof_R_timely", "oof_cost_per_frame", "oof_auroc_full_opportunity"]].to_string())
        return 0
    frozen = json.load(open(os.path.join(a.out, "frozen_controllers.json")))
    mods = pickle.load(open(os.path.join(a.out, "frozen_models.pkl"), "rb"))
    St = og.Split(a.data)
    Xt = features(St)
    rows, tl_by, cost_by = [], {}, {}
    for cname, v in frozen.items():
        if not isinstance(v, dict) or "model" not in v:
            continue
        P = {t: (proba(mods[v["model"]][t], Xt) if not isinstance(mods[v["model"]][t], float)
                 else np.full(len(Xt), mods[v["model"]][t])) for t in TARGETS}
        prm = v["params"]
        m = act(St, P, prm["tau"], prm["cool"], prm["rho"])
        tl, cost = St.evaluate(m)
        s = og.summarize(St, cname, tl, cost)
        s["mode_counts"] = json.dumps({("SKIP" if k < 0 else og.MODES[k]): int((m == k).sum()) for k in range(-1, 5)})
        rows.append(s)
        tl_by[cname], cost_by[cname] = tl, cost
    df = pd.DataFrame(rows)
    df.to_csv(os.path.join(a.out, f"controllers_{a.tag}.csv"), index=False)
    pt = St.tracks.copy()
    for k in tl_by:
        pt[f"timely_{k}"] = tl_by[k]
    pt.to_csv(os.path.join(a.out, f"per_track_{a.tag}.csv"), index=False)
    pd.DataFrame({k: v for k, v in cost_by.items()} | {"event_id": St.eid, "seg": St.seg}).to_csv(
        os.path.join(a.out, f"per_frame_cost_{a.tag}.csv"), index=False)
    print(df[["policy", "R_timely", "cost_per_frame", "rel_cost_vs_always_full", "mode_counts"]].to_string())
    return 0


if __name__ == "__main__":
    sys.exit(main())
