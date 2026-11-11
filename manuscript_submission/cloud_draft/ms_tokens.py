"""Number registry for the manuscript.

All numbers printed in the manuscript come from the registry of the evidence
package (mdpi_sensors_preparation/scripts/registry_build.py) or are computed
here from the saved per-record predictions. Nothing is typed by hand.
"""
from __future__ import annotations

import contextlib
import io
import sys
from pathlib import Path

import numpy as np

BUILD = Path(__file__).resolve().parent
ROOT = BUILD.parents[1]
PREP = ROOT / "mdpi_sensors_preparation"
sys.path.insert(0, str(PREP / "scripts"))

import common  # noqa: E402
import registry_build  # noqa: E402
import tables as prep_tables  # noqa: E402
from common import (AMPS_BH, AMPS_SP, FAULTS, INITS, RES, SEEDS, macro_f1, mean_metric,  # noqa: E402
                    pooled_confusion)

PRED = "phase_robust_final/phase_robust_results/seed_*/predictions.npz"
GRID = {"bh": AMPS_BH, "sp": AMPS_SP}
MEAN = "mean over 3 data sets x 2 initializations of the quantity computed on the pooled confusion matrix"


def _rows(m):
    return m / m.sum(1, keepdims=True)


def _f1(m):
    tp = np.diag(m)
    return 2 * tp / (m.sum(0) + m.sum(1))


def load():
    with contextlib.redirect_stdout(io.StringIO()):
        R, extra = registry_build.build()
        prep = {}
        for name, fn in zip(prep_tables.NAMES, prep_tables.TABLES):
            prep[name] = fn(R)  # registers the tokens that the package tables add
    X = {}
    e2 = "two_point_mlp@PRr_e2"
    for dom in ("bh", "sp"):
        amps = GRID[dom]
        key = f"keys {dom}_a*_p*_mon2|{e2}|*|"
        rl = mean_metric(_rows, dom, "mon2", e2, "layer", amps)
        rf = mean_metric(_rows, dom, "mon2", e2, "fault", amps)
        fl = mean_metric(_f1, dom, "mon2", e2, "layer", amps)
        ff = mean_metric(_f1, dom, "mon2", e2, "fault", amps)
        miss = mean_metric(lambda m: m[1:, 0].sum() / m[1:].sum(), dom, "mon2", e2, "layer", amps)
        acc = mean_metric(lambda m: np.trace(m) / m.sum(), dom, "mon2", e2, "layer", amps)
        X[dom] = dict(rl=rl, rf=rf, fl=fl, ff=ff)
        add = lambda tok, val, what, tgt="layer": R.add(tok, float(val), PRED, key + tgt, f"{what}; {MEAN}", status="primary")  # noqa: E731
        for i, c in enumerate(("HEALTHY", "SENSOR", "AFE", "ADC")):
            add(f"X_F1L_{dom}_{c}", fl[i], f"F1 score of layer class {c.lower()}")
        add(f"X_H2S_{dom}", rl[0, 1], "fraction of healthy records assigned to the sensor layer")
        add(f"X_H2A_{dom}", rl[0, 2], "fraction of healthy records assigned to the AFE layer")
        add(f"X_H2D_{dom}", rl[0, 3], "fraction of healthy records assigned to the ADC layer")
        add(f"X_FLAG_{dom}", 1 - rl[0, 0], "fraction of healthy records assigned to any fault layer")
        add(f"X_MISS_{dom}", miss, "fraction of faulty records assigned to the healthy layer")
        add(f"X_ACC_{dom}", acc, "layer accuracy")
        add(f"X_FH2SB_{dom}", rf[0, 1], "fraction of healthy records assigned to the sensor bias class", "fault")
        add(f"X_FH2SG_{dom}", rf[0, 2], "fraction of healthy records assigned to the sensor gain class", "fault")
        add(f"X_FH2CLIP_{dom}", rf[0, 8], "fraction of healthy records assigned to the ADC clipping class", "fault")
        add(f"X_FCLIP2H_{dom}", rf[8, 0], "fraction of ADC clipping records assigned to the healthy class", "fault")
        for i in range(4):
            for j in range(4):
                R.add(f"CML_{dom}_{i}_{j}", float(rl[i, j]), PRED, key + "layer", f"row-normalized layer confusion, true class {i}, assigned class {j}; {MEAN}", status="primary")
        for i in range(9):
            for j in range(9):
                R.add(f"CMF_{dom}_{i}_{j}", float(rf[i, j]), PRED, key + "fault", f"row-normalized fault confusion, true class {i}, assigned class {j}; {MEAN}", status="primary")
        strong = [3, 4, 5, 6, 7]
        add(f"X_F1F_{dom}_STRONG_MIN", min(ff[strong]), "smallest F1 among sensor noise, AFE offset, AFE bandwidth, ADC offset, ADC gain", "fault")
        add(f"X_F1F_{dom}_STRONG_MAX", max(ff[strong]), "largest F1 among the same five classes", "fault")
        add(f"X_F1F_{dom}_WEAK_MAX", max(np.delete(ff, strong)), "largest F1 among healthy, sensor bias, sensor gain, ADC clipping", "fault")
        for n, s in enumerate(SEEDS, 1):
            for tgt, tk in (("layer", "SEED"), ("fault", "SEEDF")):
                v = np.mean([macro_f1(pooled_confusion(s, i, dom, "mon2", e2, tgt, amps)) for i in INITS])
                R.add(f"X_{tk}_{dom}_{n}", float(v), f"phase_robust_final/phase_robust_results/seed_{s}/predictions.npz", key + tgt,
                      f"{tgt} macro-F1 of data set {s}, pooled over amplitudes and phases, mean of 2 initializations", status="primary")
    strong_rec = [R.raw(f"RF_{d}_PRR_{FAULTS[i].upper()}") for d in ("bh", "sp") for i in (3, 4, 5, 6, 7)]
    R.add("X_MIN_STRONG", float(min(strong_rec)), "per_class_recall_fault.csv (refined from predictions)", "RF_{bh,sp}_PRR_*",
          "smallest recall among sensor noise, AFE offset, AFE bandwidth, ADC offset, ADC gain over both domains", decimals=2, status="primary")
    k = "two_point_mlp@PRr_k"
    r80 = mean_metric(_rows, "bh", "known", k, "layer", (80,))
    r120 = mean_metric(_rows, "bh", "known", k, "layer", (120,))
    R.add("X_K80_H2D", float(r80[0, 3]), PRED, f"keys bh_a80_p*_known|{k}|*|layer", f"fraction of healthy records assigned to the ADC layer; {MEAN}")
    R.add("X_K120_H2S", float(r120[0, 1]), PRED, f"keys bh_a120_p*_known|{k}|*|layer", f"fraction of healthy records assigned to the sensor layer; {MEAN}")
    import csv
    with open(PREP / "verification" / "RECOMPUTED_FROM_PREDICTIONS.csv") as fh:
        rows = list(csv.DictReader(fh))
    assert all(r["match"] == "True" for r in rows)
    R.add("N_RECOMPUTED", len(rows), "mdpi_sensors_preparation/verification/RECOMPUTED_FROM_PREDICTIONS.csv", "row count",
          "number of stored summary values recomputed from predictions; all match", decimals=None, status="derived")
    return R, extra, prep, X


if __name__ == "__main__":
    R, extra, prep, X = load()
    for t in sorted(R.entries):
        if t.startswith("X_") or t in ("N_RECOMPUTED",):
            print(t, R.v(t))
    for t in ("A_MIN_RET_WHERE", "C_MAX_WHERE", "D_MIN_RET_WHERE", "B_MIN_CI_WHERE", "B_MIN_CI", "C_MIN_AFE", "C_MIN_ADC", "E_PRIMARY_BB", "E_PRIMARY_BS",
              "E_DROP", "E_DROP_LO", "E_DROP_HI", "PREV_DROP", "G_bh_R1_E2_RANGE", "G_PRR_MAX", "G_PRR_MIN", "DEV_SEED", "DEV_FALLBACK_N", "DEV_FALLBACK_COUNT",
              "DEV_RISE2_SHIFT", "DEV_PR_MAX_SHIFT", "DEV_AGREE_MIN", "DEV_AGREE_MAX", "SEEDS", "PHASES", "AMPS_BH", "AMPS_SP", "MON_E", "N_BH", "N_SP", "ARCH",
              "DESC_MS_PR", "MLP_US", "TRAIN_S_PRR_MEAN", "A_THRESH", "D_THRESH", "DECISION", "GATE_F_CHECK", "TEST_ROWS", "SPICE_WORKERS", "ATT_bh_VS_A0",
              "BASEF1_passive_a80", "BASEF1_single_a80", "TPF1_PRr_a80", "ARM_bh_R1R_RANGE", "ARM_bh_PR_RANGE", "E_MDROP", "E_PRIMARY_MS"):
        print(t, "=", R.v(t))
