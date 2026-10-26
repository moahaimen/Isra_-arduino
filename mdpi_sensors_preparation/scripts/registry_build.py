"""Build the number registry from the frozen phase-robust result files.

Every value is read programmatically. Tokens are used by the tables, figure
annotations and manuscript drafts; NUMBER_PROVENANCE_MDPI.csv is written from here.
"""
from __future__ import annotations

import re

import numpy as np

from common import (AMPS_BH, AMPS_SP, ARMS, EVID, FAULTS, LAYERS, PP, PRF, RES, SEEDS,
                    VARIANTS, Registry, cross_confusion, load_csv, load_json, mean_metric,
                    model_for, recall)

DR = RES / "decision_rules.json"
ARMS_CSV = RES / "attribution_arms.csv"
ATT_CSV = RES / "attribution_comparisons.csv"
AMP_CSV = RES / "amplitude_curves.csv"
NOMON = RES / "no_monitor_control.json"
SEP_CSV = RES / "afe_adc_separation.csv"
RL_CSV = RES / "per_class_recall_layer.csv"
RF_CSV = RES / "per_class_recall_fault.csv"
TIM = RES / "timing_and_parameters.json"
PREDS = RES / "seed_*/predictions.npz"
PROV = PP / "NUMBER_PROVENANCE.csv"
PROTO = PRF / "PROTOCOL_PHASE_ROBUST_FROZEN.md"
REPORT = PRF / "FINAL_PHASE_ROBUST_REPORT.md"

ATT_KEYS = {
    "DESC": "PR - R1 (descriptors alone)",
    "RAND": "R1r - R1 (phase randomisation alone)",
    "DESC_GIVEN_RAND": "PRr - R1r (descriptors, given randomisation)",
    "RAND_GIVEN_DESC": "PRr - PR (randomisation, given robust descriptors)",
    "COMB": "PRr - R1 (combination)",
    "MIXED": "PRrM - PRr (mixed training)",
    "VS_A0": "PRr - A0 (vs old method)",
}
ATT_LABEL = {
    "DESC": "PR − R1 (descriptors alone)", "RAND": "R1r − R1 (phase randomization alone)",
    "DESC_GIVEN_RAND": "PRr − R1r (descriptors, given randomization)",
    "RAND_GIVEN_DESC": "PRr − PR (randomization, given descriptors)",
    "COMB": "PRr − R1 (combination)", "MIXED": "PRrM − PRr (mixed-domain training)",
    "VS_A0": "PRr − A0 (vs. old method)",
}
B_BASELINES = ["two_point_mlp@A0", "passive_mlp@A0", "single_mlp@A0", "afe_only_mlp@A0",
               "adc_only_mlp@A0", "afe_only_mlp@PRr", "adc_only_mlp@PRr"]
B_LABEL = {"two_point_mlp@A0": "Two-point A0 (old descriptors)", "passive_mlp@A0": "Passive A0",
           "single_mlp@A0": "Single-probe A0", "afe_only_mlp@A0": "AFE-only A0",
           "adc_only_mlp@A0": "ADC-only A0", "afe_only_mlp@PRr": "AFE-only PRr (one-point)",
           "adc_only_mlp@PRr": "ADC-only PRr (one-point)"}
VAR_SHORT = {"known": "K", "mon0": "E0", "mon1": "E1", "mon2": "E2", "mon5": "E5"}


def pretty_key(k):
    """'sp|mon1|a80' -> 'ngspice, monitor E = ±1%, ×0.8' (for display; the raw key is kept in the locator)."""
    out = []
    for p in k.replace("vs ", "").split("|"):
        if p in ("bh", "sp"):
            out.append("behavioral" if p == "bh" else "ngspice")
        elif p == "known":
            out.append("known reference")
        elif re.fullmatch(r"mon\d", p):
            out.append("monitor E = " + ("0%" if p[-1] == "0" else f"±{p[-1]}%"))
        elif re.fullmatch(r"a\d+", p):
            out.append(f"×{int(p[1:]) / 100:g}")
        else:
            out.append("vs " + p.replace("_mlp@", " ").replace("_k", "").replace("_", "-")
                       .replace("afe-", "AFE-").replace("adc-", "ADC-"))
    return ", ".join(out)


def tok_arm(a):
    return a.upper()


def build() -> tuple[Registry, dict]:
    R = Registry()
    extra: dict = {}
    dr = load_json(DR)

    # ---------------- protocol facts (from meta.json of every seed)
    metas = [load_json(RES / f"seed_{s}" / "meta.json") for s in SEEDS]
    for key, tok in (("train_conditions", "TRAIN_COND"), ("val_conditions", "VAL_COND"),
                     ("test_conditions", "TEST_COND"), ("conditions_total", "TOTAL_COND"),
                     ("overlap", "OVERLAP"), ("n_ngspice_runs", "SPICE_RUNS_SEED")):
        vals = {m[key] for m in metas}
        assert len(vals) == 1, (key, vals)
        R.add(tok, int(vals.pop()), RES / "seed_*/meta.json", key,
              "identical in all three seeds (asserted)", decimals=None, status="protocol")
    R.add("SEEDS", ", ".join(str(m["dataset_seed"]) for m in metas), RES / "seed_*/meta.json",
          "dataset_seed", decimals=None, status="protocol")
    R.add("N_SEEDS", len(metas), RES / "seed_*/meta.json", "count of seed directories",
          decimals=None, status="protocol")
    R.add("SPICE_RUNS_TOTAL", int(sum(m["n_ngspice_runs"] for m in metas)), RES / "seed_*/meta.json",
          "n_ngspice_runs", "sum over seeds", decimals=None, status="protocol")
    phases = {tuple(m["phases"]) for m in metas}
    assert len(phases) == 1
    R.add("PHASES", ", ".join(f"{p:g}" for p in phases.pop()), RES / "seed_*/meta.json", "phases",
          decimals=None, status="protocol")
    R.add("N_PHASES", len(metas[0]["phases"]), RES / "seed_*/meta.json", "len(phases)",
          decimals=None, status="protocol")
    R.add("AMPS_BH", ", ".join(f"×{a:g}" for a in metas[0]["amplitudes_behavioral"]),
          RES / "seed_*/meta.json", "amplitudes_behavioral", decimals=None, status="protocol")
    R.add("AMPS_SP", ", ".join(f"×{a:g}" for a in metas[0]["amplitudes_ngspice"]),
          RES / "seed_*/meta.json", "amplitudes_ngspice", decimals=None, status="protocol")
    R.add("MON_E", ", ".join(("0%" if e == 0 else f"±{e}%") for e in metas[0]["monitor_error_percent"]),
          RES / "seed_*/meta.json", "monitor_error_percent", decimals=None, status="protocol")
    R.add("TEST_ROWS", int(metas[0]["test_conditions"]) * len(FAULTS), RES / "seed_*/meta.json",
          "test_conditions", "test_conditions × 9 fault classes", decimals=None, status="protocol")
    z = np.load(RES / f"seed_{SEEDS[0]}" / "predictions.npz")
    assert len(z["y_layer"]) == R.raw("TEST_ROWS")
    proto = PROTO.read_text()
    nboot = int(re.search(r"(\d+) resamples", proto).group(1))
    R.add("N_BOOT", nboot, PROTO, "section 4 ('... 5000 resamples')", "regex read", decimals=None,
          status="protocol")
    R.add("N_FAULTS", len(FAULTS), RES / "per_class_recall_fault.csv", "column count (classes)",
          decimals=None, status="protocol")
    for m in metas:
        R.add(f"RUNTIME_TOTAL_{m['dataset_seed']}", m["total_seconds"], RES / f"seed_{m['dataset_seed']}/meta.json",
              "total_seconds", decimals=1, status="protocol")
        R.add(f"RUNTIME_BH_{m['dataset_seed']}", m["behavioral_seconds"], RES / f"seed_{m['dataset_seed']}/meta.json",
              "behavioral_seconds", decimals=1, status="protocol")
        R.add(f"RUNTIME_SP_{m['dataset_seed']}", m["ngspice_wall_seconds"], RES / f"seed_{m['dataset_seed']}/meta.json",
              "ngspice_wall_seconds", decimals=1, status="protocol")

    # ---------------- N, gates
    R.add("N_BH", dr["N"]["bh"], DR, "N.bh", "layer macro-F1, PRr known reference, ×1.0, pooled over 5 phases")
    R.add("N_SP", dr["N"]["sp"], DR, "N.sp", "layer macro-F1, PRr known reference, ×1.0, pooled over 5 phases")
    R.add("DECISION", dr["decision"], DR, "decision", decimals=None)
    gates = dr["gates"]
    for g, ok in gates.items():
        R.add(f"GATE_{g}", "PASS" if ok else "FAIL", DR, f"gates.{g}", decimals=None)
    R.add("GATE_FAILED_N", len(dr["failed"]), DR, "len(failed)", decimals=None)
    mixed = dr["mixed_variant_reported_only"]
    R.add("MIXED_ALL_PASS", "PASS" if mixed["all_pass"] else "FAIL", DR,
          "mixed_variant_reported_only.all_pass", decimals=None, status="secondary")

    A = dr["A"]["detail"]
    for k, d in A.items():
        R.add(f"A_{k.replace('|', '_')}_F1", d["f1"], DR, f"A.detail['{k}'].f1")
        R.add(f"A_{k.replace('|', '_')}_RET", d["retention"], DR, f"A.detail['{k}'].retention")
    kmin = min(A, key=lambda k: A[k]["retention"])
    R.add("A_MIN_RET", A[kmin]["retention"], DR, f"A.detail['{kmin}'].retention",
          "min retention over A.detail")
    R.add("A_MIN_RET_WHERE", pretty_key(kmin), DR, "argmin key", decimals=None)
    R.add("A_THRESH", 0.85, PROTO, "section 5, gate A ('>= 0.85 N_d')", decimals=2, status="protocol")
    C = dr["C"]["detail"]
    for k, d in C.items():
        kk = k.replace("|", "_")
        R.add(f"C_{kk}_AFE", d["afe_recall"], DR, f"C.detail['{k}'].afe_recall")
        R.add(f"C_{kk}_ADC", d["adc_recall"], DR, f"C.detail['{k}'].adc_recall")
        R.add(f"C_{kk}_X", d["cross_confusion"], DR, f"C.detail['{k}'].cross_confusion")
    kmax = max(C, key=lambda k: C[k]["cross_confusion"])
    R.add("C_MAX", C[kmax]["cross_confusion"], DR, f"C.detail['{kmax}'].cross_confusion",
          "max cross_confusion over C.detail")
    R.add("C_MAX_WHERE", pretty_key(kmax), DR, "argmax key", decimals=None)
    R.add("C_MIN_AFE", min(d["afe_recall"] for d in C.values()), DR, "C.detail[*].afe_recall", "min")
    R.add("C_MIN_ADC", min(d["adc_recall"] for d in C.values()), DR, "C.detail[*].adc_recall", "min")
    R.add("C_THRESH", 0.15, PROTO, "section 5, gate C ('< 0.15')", decimals=2, status="protocol")
    D = dr["D"]["detail"]
    for k, d in D.items():
        R.add(f"D_{k.replace('|', '_')}_F1", d["f1"], DR, f"D.detail['{k}'].f1")
        R.add(f"D_{k.replace('|', '_')}_RET", d["retention"], DR, f"D.detail['{k}'].retention")
    kmin = min(D, key=lambda k: D[k]["retention"])
    R.add("D_MIN_RET", D[kmin]["retention"], DR, f"D.detail['{kmin}'].retention", "min retention over D.detail")
    R.add("D_MIN_RET_WHERE", pretty_key(kmin), DR, "argmin key", decimals=None)
    R.add("D_THRESH", 0.70, PROTO, "section 5, gate D ('>= 0.70 N_d')", decimals=2, status="protocol")
    B = dr["B"]["detail"]
    for k, d in B.items():
        var, amp, vs = k.split("|")
        base = vs.replace("vs ", "").replace("_k", "").replace("_e0", "").replace("_e1", "").replace("_e2", "").replace("_e5", "")
        t = f"B_{var}_{amp}_{base.replace('@', '_')}"
        R.add(t, d["diff"], DR, f"B.detail['{k}'].diff", signed=True)
        R.add(t + "_LO", d["ci_low"], DR, f"B.detail['{k}'].ci_low", signed=True)
        R.add(t + "_HI", d["ci_high"], DR, f"B.detail['{k}'].ci_high", signed=True)
    kmin = min(B, key=lambda k: B[k]["ci_low"])
    R.add("B_MIN_CI", B[kmin]["ci_low"], DR, f"B.detail['{kmin}'].ci_low", "min ci_low over B.detail", signed=True)
    R.add("B_MIN_CI_WHERE", pretty_key(kmin), DR, "argmin key", decimals=None)
    R.add("B_N", len(B), DR, "len(B.detail)", decimals=None)
    R.add("B_ALL_SEEDS_POS", "yes" if all(d["all_seeds_positive"] for d in B.values()) else "no",
          DR, "all(B.detail[*].all_seeds_positive)", decimals=None)

    E = dr["E"]
    for var, d in E["all"].items():
        s = VAR_SHORT[var]
        R.add(f"E_{s}_BB", d["BB"], DR, f"E.all.{var}.BB", "behavioral-trained PRr on behavioral data, ngspice grid (×0.8/1.0/1.2 × 5 phases)")
        R.add(f"E_{s}_BS", d["BS"], DR, f"E.all.{var}.BS", "behavioral-trained PRr on ngspice data, same grid")
        R.add(f"E_{s}_MS", d["MS"], DR, f"E.all.{var}.MS", "mixed-trained PRrM on ngspice data", status="secondary")
        R.add(f"E_{s}_DROP", d["drop"], DR, f"E.all.{var}.drop", "BB − BS", signed=False)
        R.add(f"E_{s}_DROP_LO", d["drop_ci"][0], DR, f"E.all.{var}.drop_ci[0]")
        R.add(f"E_{s}_DROP_HI", d["drop_ci"][1], DR, f"E.all.{var}.drop_ci[1]")
        R.add(f"E_{s}_MSBS", d["MS_minus_BS"], DR, f"E.all.{var}.MS_minus_BS", "MS − BS", signed=True, status="secondary")
        R.add(f"E_{s}_MSBS_LO", d["MS_minus_BS_ci"][0], DR, f"E.all.{var}.MS_minus_BS_ci[0]", signed=True, status="secondary")
        R.add(f"E_{s}_MSBS_HI", d["MS_minus_BS_ci"][1], DR, f"E.all.{var}.MS_minus_BS_ci[1]", signed=True, status="secondary")
        R.add(f"E_{s}_MDROP", d["mixed_drop_vs_BB"], DR, f"E.all.{var}.mixed_drop_vs_BB", "BB − MS", status="secondary")
    p = E["primary_E2"]
    R.add("E_PRIMARY_BB", p["BB"], DR, "E.primary_E2.BB", "PRr behavioral layer macro-F1 on the ngspice grid, E = ±2%")
    R.add("E_PRIMARY_BS", p["BS"], DR, "E.primary_E2.BS", "PRr ngspice layer macro-F1, E = ±2%")
    R.add("E_PRIMARY_MS", p["MS"], DR, "E.primary_E2.MS", "PRrM ngspice layer macro-F1, E = ±2%", status="secondary")
    R.add("E_DROP", p["drop"], DR, "E.primary_E2.drop", "BB − BS")
    R.add("E_DROP_LO", p["drop_ci"][0], DR, "E.primary_E2.drop_ci[0]", signed=True)
    R.add("E_DROP_HI", p["drop_ci"][1], DR, "E.primary_E2.drop_ci[1]", signed=True)
    R.add("E_MDROP", p["mixed_drop_vs_BB"], DR, "E.primary_E2.mixed_drop_vs_BB", "BB − MS", status="secondary")
    R.add("E_THRESH", 0.10, PROTO, "section 5, gate E ('<= 0.10')", decimals=2, status="protocol")

    G = dr["G"]["detail"]
    for k, d in G.items():
        dom, arm, var = k.split("|")
        R.add(f"G_{dom}_{tok_arm(arm)}_{VAR_SHORT[var]}_RANGE", d["range"], DR, f"G.detail['{k}'].range", "max − min over 5 phases")
        for ph, v in d["f1_by_phase"].items():
            R.add(f"G_{dom}_{tok_arm(arm)}_{VAR_SHORT[var]}_{ph.upper()}", v, DR, f"G.detail['{k}'].f1_by_phase.{ph}")
    prr = [d["range"] for k, d in G.items() if "|PRr|" in k]
    R.add("G_PRR_MIN", min(prr), DR, "G.detail[*|PRr|*].range", "min over PRr known/E2, both domains")
    R.add("G_PRR_MAX", max(prr), DR, "G.detail[*|PRr|*].range", "max over PRr known/E2, both domains")
    R.add("G_THRESH", 0.05, PROTO, "section 5, gate G ('<= 0.05')", decimals=2, status="protocol")

    # ---------------- previous stage (only indirectly available)
    prov = load_csv(PROV).set_index("token")
    for t, newt in (("PREV_E_DROP", "PREV_DROP"), ("PREV_E_LO", "PREV_DROP_LO"), ("PREV_E_HI", "PREV_DROP_HI"),
                    ("PREV_E_BB", "PREV_BB"), ("PREV_E_BS", "PREV_BS"), ("PREV_DECISION", "PREV_DECISION")):
        val = prov.loc[t, "raw_value"]
        try:
            val = float(val)
            dec = 3
        except ValueError:
            dec = None
        R.add(newt, val, PROV, f"token {t} (original locator: reference_monitor_final/.../decision_rules.json {prov.loc[t, 'locator']})",
              "read from the paper package provenance file; the previous-stage decision file is not in the evidence package",
              decimals=dec, status="previous-stage")
    rep = REPORT.read_text()
    m = re.search(r"lost \*\*([0-9.]+)\*\* layer macro-F1 \(frozen limit 0.10; behavioral ([0-9.]+) → ngspice ([0-9.]+), CI \[([0-9.]+), ([0-9.]+)\]\)", rep)
    extra["prev_report_check"] = m.groups() if m else None

    # ---------------- attribution arms
    arms = load_csv(ARMS_CSV)
    for r in arms.itertuples():
        t = f"ARM_{r.domain}_{tok_arm(r.arm)}"
        loc = f"row domain={r.domain}, arm={r.arm}"
        R.add(t + "_L", r.layer_macro_f1, ARMS_CSV, loc + ", layer_macro_f1",
              "E = ±2%, pooled over amplitudes (bh ×0.8–×1.2, sp ×0.8/1.0/1.2) and 5 phases",
              status="primary" if r.arm == "PRr" else "secondary")
        R.add(t + "_LBA", r.layer_balanced_accuracy, ARMS_CSV, loc + ", layer_balanced_accuracy")
        R.add(t + "_F", r.fault_macro_f1, ARMS_CSV, loc + ", fault_macro_f1")
        R.add(t + "_FBA", r.fault_balanced_accuracy, ARMS_CSV, loc + ", fault_balanced_accuracy")
        ph = [r.layer_f1_p000, r.layer_f1_p250, r.layer_f1_p500, r.layer_f1_p750, r.layer_f1_p999]
        for name, v in zip(("P000", "P250", "P500", "P750", "P999"), ph):
            R.add(f"{t}_{name}", v, ARMS_CSV, loc + f", layer_f1_{name.lower()}")
        R.add(t + "_RANGE", max(ph) - min(ph), ARMS_CSV, loc + ", layer_f1_p*", "max − min over the 5 phase columns")
    att = load_csv(ATT_CSV)
    for dom in ("bh", "sp"):
        for k, label in ATT_KEYS.items():
            row = att[(att.domain == dom) & (att.comparison == label)]
            if row.empty:
                continue
            r = row.iloc[0]
            t = f"ATT_{dom}_{k}"
            loc = f"row domain={dom}, comparison='{label}'"
            R.add(t, r["diff"], ATT_CSV, loc + ", diff", signed=True)
            R.add(t + "_LO", r.ci_low, ATT_CSV, loc + ", ci_low", signed=True)
            R.add(t + "_HI", r.ci_high, ATT_CSV, loc + ", ci_high", signed=True)
            R.add(t + "_CONS", "yes" if bool(r.consistent_3_seeds) else "no", ATT_CSV, loc + ", consistent_3_seeds", decimals=None)

    # ---------------- amplitude curves + no-monitor
    amp = load_csv(AMP_CSV)
    for r in amp.itertuples():
        ser = r.series.replace(" ", "_").replace("=", "").replace("%", "").replace(".", "")
        for col in ("x0.8", "x0.9", "x1.0", "x1.1", "x1.2", "pooled"):
            v = getattr(r, "_" + str(list(amp.columns).index(col) + 1)) if False else amp.loc[r.Index, col]
            if np.isnan(v):
                continue
            R.add(f"AMP_{r.domain}_{ser}_{r.target}_{col.replace('.', '')}", v, AMP_CSV,
                  f"row domain={r.domain}, series='{r.series}', target={r.target}, column {col}")
    nm = load_json(NOMON)["no_monitor_control_layer_macro_f1"]
    for a, d in nm.items():
        R.add(f"NOMON_K_{a.replace('.', '')}", d["known"], NOMON, f"no_monitor_control_layer_macro_f1.{a}.known",
              "behavioral, PRr known-reference classifier, pooled over 5 phases")
        R.add(f"NOMON_U_{a.replace('.', '')}", d["unmonitored"], NOMON, f"no_monitor_control_layer_macro_f1.{a}.unmonitored",
              "same classifier given nominal (assumed) levels; behavioral; pooled over 5 phases", status="secondary",
              note="control, not a method")

    # ---------------- separation per arm (amplitude-level, E=2%)
    sep = load_csv(SEP_CSV)
    for r in sep.itertuples():
        a = f"x{r.amplitude:g}".replace(".", "")
        t = f"SEP_{r.domain}_{tok_arm(r.arm)}_{a}"
        loc = f"row domain={r.domain}, arm={r.arm}, amplitude={r.amplitude}"
        R.add(t + "_AFE", r.afe_recall, SEP_CSV, loc + ", afe_recall")
        R.add(t + "_ADC", r.adc_recall, SEP_CSV, loc + ", adc_recall")
        R.add(t + "_X", r.cross_confusion, SEP_CSV, loc + ", cross_confusion")

    # ---------------- per-class recall
    rl = load_csv(RL_CSV)
    for r in rl.itertuples():
        arm = "UNMON" if "no monitor" in r.arm else tok_arm(r.arm)
        for c in LAYERS:
            R.add(f"RL_{r.domain}_{arm}_{c.upper()}", getattr(r, c), RL_CSV,
                  f"row domain={r.domain}, arm='{r.arm}', scope='{r.scope}', column {c}",
                  status="secondary" if arm == "UNMON" else "primary")
    rf = load_csv(RF_CSV)
    for r in rf.itertuples():
        for c in FAULTS:
            R.add(f"RF_{r.domain}_{tok_arm(r.arm)}_{c.upper()}", getattr(r, c), RF_CSV,
                  f"row domain={r.domain}, arm={r.arm}, column {c}")

    # ---------------- complexity
    tim = load_json(TIM)
    pl = {tim[str(s)]["params_layer"] for s in SEEDS}
    pf = {tim[str(s)]["params_fault"] for s in SEEDS}
    assert len(pl) == len(pf) == 1
    R.add("PARAMS_LAYER", f"{pl.pop():,}", TIM, "<seed>.params_layer", "identical in all seeds (asserted)", decimals=None)
    R.add("PARAMS_FAULT", f"{pf.pop():,}", TIM, "<seed>.params_fault", "identical in all seeds (asserted)", decimals=None)
    # architecture check: 20 inputs, 96 and 48 hidden units
    n_in, h1, h2 = 20, 96, 48
    pl_calc = n_in * h1 + h1 + h1 * h2 + h2 + h2 * 4 + 4
    pf_calc = n_in * h1 + h1 + h1 * h2 + h2 + h2 * 9 + 9
    assert f"{pl_calc:,}" == R.v("PARAMS_LAYER") and f"{pf_calc:,}" == R.v("PARAMS_FAULT")
    R.add("ARCH", f"{n_in}–{h1}–{h2}", PP / "PAPER_TABLES.csv", "T10 'Classifier' row (MLP 20-96-48-{4 or 9})",
          "parameter counts recomputed from 20-96-48-4 / 20-96-48-9 match timing_and_parameters.json", decimals=None, status="protocol")
    R.add("MACS_LAYER", f"{n_in*h1 + h1*h2 + h2*4:,}", "derived", "20·96 + 96·48 + 48·4", "multiply-accumulates per layer decision", decimals=None, status="derived")
    R.add("MACS_FAULT", f"{n_in*h1 + h1*h2 + h2*9:,}", "derived", "20·96 + 96·48 + 48·9", "multiply-accumulates per fault decision", decimals=None, status="derived")
    R.add("DESC_MS_R1", np.mean([tim[str(s)]["descriptor_extraction_ms_per_sample"]["revision1"] for s in SEEDS]),
          TIM, "<seed>.descriptor_extraction_ms_per_sample.revision1", "mean over 3 seeds (ms)", decimals=2)
    R.add("DESC_MS_PR", np.mean([tim[str(s)]["descriptor_extraction_ms_per_sample"]["phase_robust"] for s in SEEDS]),
          TIM, "<seed>.descriptor_extraction_ms_per_sample.phase_robust", "mean over 3 seeds (ms)", decimals=2)
    R.add("MLP_US", 1000 * np.mean([tim[str(s)]["mlp_predict_ms_per_sample"] for s in SEEDS]),
          TIM, "<seed>.mlp_predict_ms_per_sample", "mean over 3 seeds × 1000 (µs per record, batched)", decimals=2)
    R.add("SPICE_WALL_MEAN", np.mean([tim[str(s)]["ngspice_wall_seconds"] for s in SEEDS]), TIM,
          "<seed>.ngspice_wall_seconds", "mean over 3 seeds (s)", decimals=0)
    R.add("SPICE_WORKERS", int(tim[str(SEEDS[0])]["workers"]), TIM, "<seed>.workers", decimals=None)
    # training time of the primary two-point PRr models
    tr = []
    for s in SEEDS:
        mi = load_json(RES / f"seed_{s}" / "model_info.json")
        tr += [v["train_seconds"] for k, v in mi.items() if k.startswith("two_point_mlp@PRr_") and "PRrM" not in k]
    R.add("TRAIN_S_PRR_MEAN", np.mean(tr), RES / "seed_*/model_info.json", "two_point_mlp@PRr_*|*|*.train_seconds",
          f"mean over {len(tr)} models (s)", decimals=2)
    R.add("TRAIN_S_PRR_MAX", np.max(tr), RES / "seed_*/model_info.json", "two_point_mlp@PRr_*|*|*.train_seconds",
          f"max over {len(tr)} models (s)", decimals=2)

    # ---------------- development-seed (illustrative) numbers
    dv = load_json(PP / "figure_data" / "dev_seed_verification.json")
    extra["dev"] = dv
    fb = load_json(PP / "figure_data" / "fallback_check_dev_seed.json")
    R.add("DEV_FALLBACK_N", f"{fb['n_records']:,}", PP / "figure_data/fallback_check_dev_seed.json", "n_records",
          decimals=None, status="illustrative")
    R.add("DEV_FALLBACK_COUNT", fb["fallback_activations"], PP / "figure_data/fallback_check_dev_seed.json",
          "fallback_activations", decimals=None, status="illustrative")
    R.add("DEV_SEED", str(fb["seed"]), PP / "figure_data/fallback_check_dev_seed.json", "seed", decimals=None, status="illustrative")
    r1 = dv["descriptor_phase_invariance"]["revision1"]
    R.add("DEV_RISE2_SHIFT", max(r1["rise_2"]), PP / "figure_data/dev_seed_verification.json",
          "descriptor_phase_invariance.revision1.rise_2", "max over phases (σ units)", decimals=2, status="illustrative")
    prd = dv["descriptor_phase_invariance"]["phase_robust"]
    R.add("DEV_PR_MAX_SHIFT", max(max(v) for v in prd.values()), PP / "figure_data/dev_seed_verification.json",
          "descriptor_phase_invariance.phase_robust[*]", "max over descriptors and phases (σ units)", decimals=2, status="illustrative")
    nf = dv["noise_free_agreement_per_phase"]
    vals = nf.values() if isinstance(nf, dict) else nf
    vals = list(vals)
    R.add("DEV_AGREE_MIN", min(v["mean_rmse_mV"] for v in vals), PP / "figure_data/dev_seed_verification.json",
          "noise_free_agreement_per_phase[*].mean_rmse_mV", "min (mV)", decimals=2, status="illustrative")
    R.add("DEV_AGREE_MAX", max(v["mean_rmse_mV"] for v in vals), PP / "figure_data/dev_seed_verification.json",
          "noise_free_agreement_per_phase[*].mean_rmse_mV", "max (mV)", decimals=2, status="illustrative")

    # ---------------- derived from raw predictions (not stored in any summary file)
    pr = PREDS
    for var in ("known", "assumed"):
        for a in (80, 120):
            mdl = "two_point_mlp@PRr_k"
            cm_mean = np.mean([pooled_cm(s, i, var, mdl, a) for s in SEEDS for i in (11, 22)], axis=0)
            extra[f"cm_bh_{var}_a{a}"] = cm_mean
            rec_afe = mean_metric(lambda m: recall(m)[2], "bh", var, mdl, "layer", (a,))
            rec_adc = mean_metric(lambda m: recall(m)[3], "bh", var, mdl, "layer", (a,))
            xc = mean_metric(cross_confusion, "bh", var, mdl, "layer", (a,))
            st = "primary" if var == "known" else "secondary"
            R.add(f"SEPX_bh_{var}_a{a}_AFE", rec_afe, pr, f"keys bh_a{a}_p*_{var}|{mdl}|{{11,22}}|layer",
                  "AFE layer recall from confusion pooled over 5 phases; mean over 3 seeds × 2 inits", status=st)
            R.add(f"SEPX_bh_{var}_a{a}_ADC", rec_adc, pr, f"keys bh_a{a}_p*_{var}|{mdl}|{{11,22}}|layer",
                  "ADC layer recall, same pooling", status=st)
            R.add(f"SEPX_bh_{var}_a{a}_X", xc, pr, f"keys bh_a{a}_p*_{var}|{mdl}|{{11,22}}|layer",
                  "(C[AFE,ADC]+C[ADC,AFE])/(n_AFE+n_ADC), same pooling", status=st)
    return R, extra


def pooled_cm(seed, init, var, model, amp):
    from common import pooled_confusion
    return pooled_confusion(seed, init, "bh", var, model, "layer", (amp,))


if __name__ == "__main__":
    from common import OUT
    R, _ = build()
    R.to_csv(OUT / "NUMBER_PROVENANCE_MDPI.csv")
    print(len(R.entries), "numbers registered")
