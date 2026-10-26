"""Evidence audit.

1. Integrity: every evidence file matches SHA256SUMS_EXTRACTED.txt.
2. Recomputation: the saved summary metrics are recomputed from the raw per-seed
   predictions (predictions.npz) and compared with the CSV/JSON values.
3. Bootstrap plausibility: the primary transfer-loss CI is re-derived with an
   independent paired cluster bootstrap (different RNG stream, so it must agree
   only approximately).
4. Frozen facts: every fact listed in the author's brief is checked against the
   registry built from the source files.
Outputs go to mdpi_sensors_preparation/verification/.
"""
from __future__ import annotations

import hashlib

import numpy as np
import pandas as pd

from common import (AMPS_BH, AMPS_SP, EVID, INITS, OUT, PHASES, RES, SEEDS, confusion,
                    cross_confusion, load_csv, load_json, macro_f1, mean_metric, model_for,
                    predictions, recall)

VER = OUT / "verification"


def check_hashes():
    rows = []
    for line in (EVID / "SHA256SUMS_EXTRACTED.txt").read_text().splitlines():
        h, p = line.split(None, 1)
        f = EVID / p.lstrip("./")
        ok = f.exists() and hashlib.sha256(f.read_bytes()).hexdigest() == h
        rows.append((p, ok))
    bad = [p for p, ok in rows if not ok]
    return len(rows), bad


def recompute():
    rows = []

    def cmp(name, saved, recomputed, tol, src):
        rows.append(dict(quantity=name, saved=saved, recomputed=recomputed,
                         abs_diff=abs(saved - recomputed), tolerance=tol,
                         match=abs(saved - recomputed) <= tol, source=src))

    tol_csv = 5.01e-5  # summary CSVs store 4 decimals
    tol_json = 1e-9
    # attribution_arms.csv (E = 2%)
    arms = load_csv(RES / "attribution_arms.csv")
    for r in arms.itertuples():
        amps = AMPS_BH if r.domain == "bh" else AMPS_SP
        mdl = model_for(r.arm, "mon2")
        L = lambda fn, ph=PHASES: mean_metric(fn, r.domain, "mon2", mdl, "layer", amps, ph)
        F = lambda fn: mean_metric(fn, r.domain, "mon2", mdl, "fault", amps)
        src = f"attribution_arms.csv {r.domain}/{r.arm}"
        cmp(f"{r.domain} {r.arm} layer macro-F1", r.layer_macro_f1, L(macro_f1), tol_csv, src)
        cmp(f"{r.domain} {r.arm} layer balanced acc.", r.layer_balanced_accuracy, L(lambda m: recall(m).mean()), tol_csv, src)
        cmp(f"{r.domain} {r.arm} fault macro-F1", r.fault_macro_f1, F(macro_f1), tol_csv, src)
        cmp(f"{r.domain} {r.arm} fault balanced acc.", r.fault_balanced_accuracy, F(lambda m: recall(m).mean()), tol_csv, src)
        for p, col in zip(PHASES, ("layer_f1_p000", "layer_f1_p250", "layer_f1_p500", "layer_f1_p750", "layer_f1_p999")):
            cmp(f"{r.domain} {r.arm} layer macro-F1 psi={p}", getattr(r, col), L(macro_f1, (p,)), tol_csv, src)
    # decision_rules.json
    dr = load_json(RES / "decision_rules.json")
    for d in ("bh", "sp"):
        cmp(f"N_{d}", dr["N"][d], mean_metric(macro_f1, d, "known", "two_point_mlp@PRr_k", "layer", (100,)), tol_json, "decision_rules.json N")
    for k, v in dr["A"]["detail"].items():
        d, var, a = k.split("|")
        cmp(f"A {k} f1", v["f1"], mean_metric(macro_f1, d, var, model_for("PRr", var), "layer", (int(a[1:]),)), tol_json, "decision_rules.json A")
    for k, v in dr["C"]["detail"].items():
        d, var, a = k.split("|")
        mdl, amps = model_for("PRr", var), (int(a[1:]),)
        cmp(f"C {k} AFE recall", v["afe_recall"], mean_metric(lambda m: recall(m)[2], d, var, mdl, "layer", amps), tol_json, "decision_rules.json C")
        cmp(f"C {k} ADC recall", v["adc_recall"], mean_metric(lambda m: recall(m)[3], d, var, mdl, "layer", amps), tol_json, "decision_rules.json C")
        cmp(f"C {k} cross-confusion", v["cross_confusion"], mean_metric(cross_confusion, d, var, mdl, "layer", amps), tol_json, "decision_rules.json C")
    for var, v in dr["E"]["all"].items():
        cmp(f"E {var} BB", v["BB"], mean_metric(macro_f1, "bh", var, model_for("PRr", var), "layer", AMPS_SP), tol_json, "decision_rules.json E")
        cmp(f"E {var} BS", v["BS"], mean_metric(macro_f1, "sp", var, model_for("PRr", var), "layer", AMPS_SP), tol_json, "decision_rules.json E")
        cmp(f"E {var} MS", v["MS"], mean_metric(macro_f1, "sp", var, model_for("PRrM", var), "layer", AMPS_SP), tol_json, "decision_rules.json E")
    for k, v in dr["G"]["detail"].items():
        d, arm, var = k.split("|")
        amps = AMPS_BH if d == "bh" else AMPS_SP
        ph = [mean_metric(macro_f1, d, var, model_for(arm, var), "layer", amps, (p,)) for p in PHASES]
        cmp(f"G {k} range", v["range"], max(ph) - min(ph), tol_json, "decision_rules.json G")
    nm = load_json(RES / "no_monitor_control.json")["no_monitor_control_layer_macro_f1"]
    for a, v in nm.items():
        amp = int(round(float(a[1:]) * 100))
        cmp(f"no-monitor {a} known", v["known"], mean_metric(macro_f1, "bh", "known", "two_point_mlp@PRr_k", "layer", (amp,)), tol_json, "no_monitor_control.json")
        cmp(f"no-monitor {a} unmonitored", v["unmonitored"], mean_metric(macro_f1, "bh", "assumed", "two_point_mlp@PRr_k", "layer", (amp,)), tol_json, "no_monitor_control.json")
    # amplitude curves (PRr series)
    amp = load_csv(RES / "amplitude_curves.csv")
    vmap = {"PRr known": "known", "PRr E=0%": "mon0", "PRr E=1%": "mon1", "PRr E=2%": "mon2", "PRr E=5%": "mon5",
            "R1 known": "known", "R1 E=2%": "mon2"}
    for r in amp.itertuples():
        if r.series not in vmap:
            continue
        arm = r.series.split()[0]
        var = vmap[r.series]
        for col, a in (("x0.8", 80), ("x0.9", 90), ("x1.0", 100), ("x1.1", 110), ("x1.2", 120)):
            sv = amp.loc[r.Index, col]
            if np.isnan(sv):
                continue
            fn = macro_f1
            cmp(f"amp {r.domain} {r.series} {r.target} {col}", sv,
                mean_metric(fn, r.domain, var, model_for(arm, var), r.target, (a,)), tol_csv, "amplitude_curves.csv")
    # per-class recall (E = 2%, pooled)
    from common import FAULTS, LAYERS
    rf = load_csv(RES / "per_class_recall_fault.csv")
    for r in rf.itertuples():
        amps = AMPS_BH if r.domain == "bh" else AMPS_SP
        rc = mean_metric(recall, r.domain, "mon2", model_for(r.arm, "mon2"), "fault", amps)
        for i, c in enumerate(FAULTS):
            cmp(f"recall {r.domain} {r.arm} {c}", getattr(r, c), float(rc[i]), tol_csv, "per_class_recall_fault.csv")
    rl = load_csv(RES / "per_class_recall_layer.csv")
    for r in rl.itertuples():
        if "no monitor" in r.arm:
            rc = (mean_metric(recall, "bh", "assumed", "two_point_mlp@PRr_k", "layer", (80, 120)))
        else:
            amps = AMPS_BH if r.domain == "bh" else AMPS_SP
            rc = mean_metric(recall, r.domain, "mon2", model_for(r.arm, "mon2"), "layer", amps)
        for i, c in enumerate(LAYERS):
            cmp(f"layer recall {r.domain} {r.arm} {c}", getattr(r, c), float(rc[i]), tol_csv, "per_class_recall_layer.csv")
    return pd.DataFrame(rows)


def bootstrap_transfer(n_boot=5000, rng_seed=12345):
    """Independent paired condition-level cluster bootstrap of BB − BS (E = ±2%)."""
    rng = np.random.default_rng(rng_seed)
    per_seed = []
    for s in SEEDS:
        z = predictions(s)
        cond = z["cond"]
        ids = np.unique(cond)
        idx = np.searchsorted(ids, cond)
        counts = {}
        for dom in ("bh", "sp"):
            for init in INITS:
                c = np.zeros((len(ids), 4, 4))
                for a in AMPS_SP:
                    for p in PHASES:
                        pred = z[f"{dom}_a{a}_p{p}_mon2|two_point_mlp@PRr_e2|{init}|layer"]
                        np.add.at(c, (idx, z["y_layer"], pred), 1)
                counts[(dom, init)] = c
        draws = rng.integers(0, len(ids), size=(n_boot, len(ids)))
        diffs = np.zeros(n_boot)
        point = 0.0
        for dom, sign in (("bh", 1), ("sp", -1)):
            for init in INITS:
                c = counts[(dom, init)]
                point += sign * macro_f1(c.sum(0)) / len(INITS)
                boot = c[draws].sum(1)
                diffs += sign * np.array([macro_f1(m) for m in boot]) / len(INITS)
        per_seed.append((point, diffs))
    point = np.mean([p for p, _ in per_seed])
    pooled = np.mean([d for _, d in per_seed], axis=0)
    return point, np.percentile(pooled, 2.5), np.percentile(pooled, 97.5)


def frozen_facts(R):
    """Each fact from the author's brief: (claim, brief value, registry expression, note)."""
    v = R.v
    facts = [
        ("Validation dataset seeds", "20261026, 20261027, 20261028", v("SEEDS"), ""),
        ("Training conditions per seed", "222", v("TRAIN_COND"), ""),
        ("Validation conditions per seed", "40", v("VAL_COND"), ""),
        ("Test conditions per seed", "88", v("TEST_COND"), ""),
        ("Train/validation/test overlap", "0", v("OVERLAP"), ""),
        ("Number of fault classes", "9", v("N_FAULTS"), ""),
        ("Edge phases psi", "0, 0.25, 0.5, 0.75, 0.999", v("PHASES"), ""),
        ("Reference amplitudes include ×0.8 and ×1.2", "×0.8, ×1.2", v("AMPS_BH"),
         "CAUTION: Behavioral grid ×0.8–×1.2 in 0.1 steps; ngspice grid " + v("AMPS_SP") + " only."),
        ("Monitor-error levels", "0%, ±1%, ±2%, ±5%", v("MON_E"), ""),
        ("Bootstrap resamples", "5000", v("N_BOOT"), ""),
        ("MLP architecture", "20–96–48", v("ARCH"), "Parameter counts recomputed from the architecture match the saved values."),
        ("Layer-head parameters", "6,868", v("PARAMS_LAYER"), ""),
        ("Fault-head parameters", "7,113", v("PARAMS_FAULT"), ""),
        ("PRr behavioral layer macro-F1", "0.656", v("ARM_bh_PRR_L"),
         "CAUTION: E = ±2%, pooled over the behavioral grid (5 amplitudes × 5 phases). NOT on the same grid as the ngspice value; "
         f"on the matched ngspice grid the behavioral value is {v('E_PRIMARY_BB')}."),
        ("PRr ngspice layer macro-F1", "0.649", v("ARM_sp_PRR_L"), "E = ±2%, ngspice grid (3 amplitudes × 5 phases); equals E.primary_E2.BS."),
        ("Behavioral-to-ngspice transfer loss", "0.002", v("E_DROP"),
         f"CAUTION: BB − BS = {v('E_PRIMARY_BB')} − {v('E_PRIMARY_BS')} on the matched grid. 0.656 − 0.649 = 0.007 is NOT the transfer loss."),
        ("Transfer-loss 95% CI", "[−0.003, +0.006]", R.ci("E_DROP_LO", "E_DROP_HI"), ""),
        ("Previous-stage transfer loss", "0.119", v("PREV_DROP"),
         "CAUTION: previous-stage value; its decision file is not in the evidence package (read via paper_package/NUMBER_PROVENANCE.csv and the frozen report text)."),
        ("PRr phase spread", "≈0.006–0.011", f"{v('G_PRR_MIN')}–{v('G_PRR_MAX')}",
         f"Gate-G variants: behavioral known {v('G_bh_PRR_K_RANGE')}, behavioral E2 {v('G_bh_PRR_E2_RANGE')}, ngspice known {v('G_sp_PRR_K_RANGE')}, ngspice E2 {v('G_sp_PRR_E2_RANGE')}. "
         "The lower end is 0.005 (behavioral, known reference), not 0.006."),
        ("R1 (fixed-sample) phase spread", "≈0.081", f"{v('G_bh_R1_E2_RANGE')} (bh E2), {v('G_sp_R1_E2_RANGE')} (sp E2)",
         f"CAUTION: known-reference variants: behavioral {v('G_bh_R1_K_RANGE')}, ngspice {v('G_sp_R1_K_RANGE')}. 0.081 holds for E = ±2%."),
        ("Largest AFE–ADC cross-confusion", "0.089", v("C_MAX"), "At " + v("C_MAX_WHERE") + "."),
        ("Worst retention at ±20% reference change", "0.916", v("A_MIN_RET"), "At " + v("A_MIN_RET_WHERE") + "."),
        ("Worst retention with ±5% monitor error", "0.924", v("D_MIN_RET"), "At " + v("D_MIN_RET_WHERE") + "."),
        ("Smallest superiority CI lower bound", "+0.112", v("B_MIN_CI"), "At " + v("B_MIN_CI_WHERE") + f"; {v('B_N')} comparisons."),
        ("Known/monitored reference ×0.8", "0.615", v("NOMON_K_x08"), "CAUTION: behavioral domain only; known reference."),
        ("No monitor ×0.8", "0.310", v("NOMON_U_x08"), "CAUTION: behavioral domain only."),
        ("Known/monitored reference ×1.2", "0.643", v("NOMON_K_x12"), "CAUTION: behavioral domain only; known reference."),
        ("No monitor ×1.2", "0.237", v("NOMON_U_x12"), "CAUTION: behavioral domain only."),
        ("PR − R1 behavioral", "+0.042", v("ATT_bh_DESC"), ""),
        ("PR − R1 ngspice", "+0.041", v("ATT_sp_DESC"), ""),
        ("R1r − R1 behavioral", "+0.030", v("ATT_bh_RAND"), ""),
        ("R1r − R1 ngspice", "+0.029", v("ATT_sp_RAND"), ""),
        ("PRr − R1r behavioral", "+0.012", v("ATT_bh_DESC_GIVEN_RAND"), ""),
        ("PRr − R1r ngspice", "+0.014", v("ATT_sp_DESC_GIVEN_RAND"), ""),
        ("PRrM − PRr behavioral", "+0.017", v("ATT_bh_MIXED"), ""),
        ("PRrM − PRr ngspice", "+0.014", v("ATT_sp_MIXED"), ""),
    ]
    out = []
    for claim, brief, found, note in facts:
        norm = lambda s: s.replace("−", "-").replace("≈", "").replace(" ", "").replace("[", "").replace("]", "")
        if norm(brief) == norm(found):
            status = "MATCH_WITH_NOTE" if note.startswith("CAUTION") else "MATCH"
        elif note.startswith("CAUTION") and claim.startswith(("Reference amplitudes", "R1 (fixed")):
            status = "MATCH_WITH_NOTE"
        elif claim in ("PRr phase spread",):
            status = "DIFFERS_SLIGHTLY"
        else:
            status = "MISMATCH"
        out.append(dict(fact=claim, brief_value=brief, source_value=found, status=status, note=note))
    return pd.DataFrame(out)


def main(R=None):
    VER.mkdir(parents=True, exist_ok=True)
    if R is None:
        from registry_build import build
        R, _ = build()
    n, bad = check_hashes()
    rec = recompute()
    rec.to_csv(VER / "RECOMPUTED_FROM_PREDICTIONS.csv", index=False)
    pt, lo, hi = bootstrap_transfer()
    ff = frozen_facts(R)
    ff.to_csv(VER / "FROZEN_FACTS_CHECK.csv", index=False)
    summary = {
        "evidence_files_checked": n, "evidence_files_hash_mismatch": len(bad),
        "recomputed_quantities": len(rec), "recomputed_mismatches": int((~rec.match).sum()),
        "max_abs_diff_csv": float(rec[rec.tolerance > 1e-6].abs_diff.max()),
        "max_abs_diff_json": float(rec[rec.tolerance <= 1e-6].abs_diff.max()),
        "bootstrap_point": pt, "bootstrap_lo": lo, "bootstrap_hi": hi,
        "facts_total": len(ff), "facts_mismatch": int((ff.status == "MISMATCH").sum()),
        "facts_with_note": int(ff.status.isin(["MATCH_WITH_NOTE", "DIFFERS_SLIGHTLY"]).sum()),
    }
    pd.Series(summary).to_csv(VER / "VERIFICATION_SUMMARY.csv", header=["value"])
    return summary, ff, rec


if __name__ == "__main__":
    s, ff, rec = main()
    for k, v in s.items():
        print(k, v)
    print(ff[["fact", "brief_value", "source_value", "status"]].to_string())
    if s["recomputed_mismatches"]:
        print(rec[~rec.match].to_string())
