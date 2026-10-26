"""MDPI-style tables in CSV, Markdown, LaTeX and Word.

Cells are filled only from the registry (frozen result files) or, where stated,
from the saved per-sample predictions; nothing is typed by hand.
"""
from __future__ import annotations

import re

import numpy as np
import pandas as pd
from docx import Document
from docx.enum.section import WD_ORIENT
from docx.oxml import OxmlElement
from docx.oxml.ns import qn
from docx.shared import Pt, Cm

from common import (AMPS_BH, AMPS_SP, FAULT_LABELS, FAULTS, LAYER_LABELS, LAYERS, OUT, PP, RES,
                    SEEDS, load_csv, load_json, macro_f1, mean_metric)

TAB = OUT / "tables"
VAR = [("known", "K", "Known reference"), ("mon0", "E0", "Monitor E = 0%"), ("mon1", "E1", "Monitor E = ±1%"),
       ("mon2", "E2", "Monitor E = ±2%"), ("mon5", "E5", "Monitor E = ±5%")]
DOM = {"bh": "Behavioral", "sp": "ngspice"}


def _t1_value(row):
    t = load_csv(PP / "PAPER_TABLES.csv")
    s = t[(t.table_id.isin(["T1", "T10"])) & (t.row == row) & (t.column == "value")]
    return s.value.iloc[0]


def _t1_source(row):
    t = load_csv(PP / "PAPER_TABLES.csv")
    s = t[(t.table_id.isin(["T1", "T10"])) & (t.row == row) & (t.column == "source")]
    return s.value.iloc[0]


def _items(row, starts):
    parts = [p.strip() for p in _t1_value(row).split(";")]
    return "; ".join(p for p in parts if p.startswith(starts))


# --------------------------------------------------------------------------------- tables

def t01(R):
    rows = [
        ("Sensor model", _items("Operating condition (per group)", ("baseline", "carrier", "frequency", "sensor noise", "slow", "random")),
         "Physical signal source; replaced by R1 during the AFE test window", _t1_source("Operating condition (per group)")),
        ("MUX 1 / reference R1", _t1_value("AFE reference window"),
         "Two-level reference at the AFE input; its response passes through AFE and ADC", _t1_source("AFE reference window")),
        ("AFE / filter", _items("Operating condition (per group)", ("AFE gain", "AFE tau")) + "; first-order RC low-pass with gain and offset",
         "Amplifies and filters; faults: offset, bandwidth", _t1_source("Operating condition (per group)")),
        ("MUX 2 / reference R2", _t1_value("ADC reference window"),
         "Two-level reference at the ADC input, bypassing the AFE; isolates the ADC transfer", _t1_source("ADC reference window")),
        ("ADC", _t1_value("Sampling"), "Digitises all paths; faults: offset, gain, clipping", _t1_source("Sampling")),
        ("Reference monitor", _t1_value("Reference monitor"),
         "Measures the actual reference levels used in calibration (simulated, not built)", _t1_source("Reference monitor")),
        ("Switches (ngspice)", _t1_value("Switch model (ngspice)"), "Circuit-level multiplexer model", _t1_source("Switch model (ngspice)")),
        ("Extra ngspice noise", _t1_value("ngspice-only noise"), "Circuit-domain noise not present in the behavioral model", _t1_source("ngspice-only noise")),
        ("Digital classifier", f"{_t1_value('Classifier')}; {R.v('PARAMS_LAYER')} (layer) / {R.v('PARAMS_FAULT')} (fault) parameters; "
                               f"input: {_t1_value('Descriptor vector')}",
         "Classifies faulty layer (4 classes) and fault (9 classes)", "phase_robust_results/timing_and_parameters.json; " + _t1_source("Classifier")),
        ("Component tolerances (test)", _t1_value("Component tolerances (test, both domains)"), "Applied in both domains, drawn per sample",
         _t1_source("Component tolerances (test, both domains)")),
    ]
    df = pd.DataFrame(rows, columns=["Block", "Model / parameters (simulation)", "Role in the self-test", "Source (code constant)"])
    note = ("Values are code constants copied programmatically from paper_package/PAPER_TABLES.csv (Table T1/T10); the "
            "simulator source code is not part of the evidence package, so these constants cannot be re-verified here.")
    return "Electronic system and circuit components of the simulated sensor interface.", df, note


def t02(R):
    sev = {}
    for part in _t1_value("Faults (severity)").split(";"):
        names, rng = part.split(":", 1)
        for n in names.split("/"):
            sev[n.strip().lower().replace(" ", "_")] = rng.strip()
    loc = {"healthy": ("—", "—"), "sensor_bias": ("Sensor", "Sensor element / sensor output"),
           "sensor_gain": ("Sensor", "Sensor element (sensitivity)"), "sensor_noise": ("Sensor", "Sensor element (excess noise)"),
           "afe_offset": ("AFE", "Amplifier stage (offset)"), "afe_bandwidth": ("AFE", "RC low-pass filter (time constant τ)"),
           "adc_offset": ("ADC", "ADC (offset)"), "adc_gain": ("ADC", "ADC (gain)"), "adc_clipping": ("ADC", "ADC input range (clipping)")}
    obs = {"Sensor": "Passive sensor segments only (references replace the sensor)", "AFE": "R1 window, after removing the ADC transfer from R2",
           "ADC": "R2 window (bypasses the AFE)", "—": "—"}
    rows = []
    for i, f in enumerate(FAULTS):
        layer, where = loc[f]
        rows.append((i, FAULT_LABELS[i], layer, where, sev.get(f, "no fault injected"), obs[layer]))
    df = pd.DataFrame(rows, columns=["#", "Fault class", "Layer", "Physical location", "Severity range (simulated)", "Primary observability"])
    note = ("Severity ranges parsed programmatically from the 'Faults (severity)' row of paper_package/PAPER_TABLES.csv "
            "(src/simulate.py: make_fault). Layer assignment follows the four-class layer label used by the classifier.")
    return "Fault taxonomy: nine fault classes and their physical location.", df, note


def t03(R):
    rows = [
        ("Simulator domains", "Behavioral discrete-time model; ngspice per-sample netlist of the same circuit"),
        ("Dataset seeds", f"{R.v('SEEDS')} ({R.v('N_SEEDS')} seeds, unseen before the protocol freeze)"),
        ("Conditions per seed", f"{R.v('TOTAL_COND')} operating conditions × {R.v('N_FAULTS')} fault classes"),
        ("Train / validation / test split", f"{R.v('TRAIN_COND')} / {R.v('VAL_COND')} / {R.v('TEST_COND')} conditions per seed; overlap {R.v('OVERLAP')}"),
        ("Test records per test cell", f"{R.v('TEST_ROWS')} ({R.v('TEST_COND')} conditions × {R.v('N_FAULTS')} classes)"),
        ("Edge phases ψ (test)", f"{R.v('PHASES')} ({R.v('N_PHASES')} phases); training ψ ~ U[0,1) for randomized arms"),
        ("Reference amplitudes", f"Behavioral {R.v('AMPS_BH')}; ngspice {R.v('AMPS_SP')}"),
        ("Monitor gain-error bound E", f"{R.v('MON_E')} (matched training) and known reference"),
        ("Component tolerances", _t1_value("Component tolerances (test, both domains)")),
        ("Noise", "ADC noise " + re.search(r"ADC noise ([^,;]+)", _t1_value("Sampling")).group(1) + "; ngspice adds " + _t1_value("ngspice-only noise")),
        ("Quantization", re.search(r"(12-bit ADC over [^,]+)", _t1_value("Sampling")).group(1)),
        ("ngspice runs", f"{R.v('SPICE_RUNS_SEED')} per seed; {R.v('SPICE_RUNS_TOTAL')} in total"),
        ("Initializations", "Two initialization seeds per model, averaged"),
        ("Primary metric", "Layer macro-F1 (4 classes); also fault macro-F1 (9 classes), balanced accuracy, per-class recall"),
        ("Statistics", f"Paired condition-level cluster bootstrap, {R.v('N_BOOT')} resamples per seed; pooled CI of the mean of the three per-seed differences"),
        ("Pre-registration", "Protocol, descriptors, arms, thresholds and decision rule frozen before validation data (source hashes recorded)"),
    ]
    df = pd.DataFrame(rows, columns=["Item", "Setting"])
    note = "Sources: seed_*/meta.json, PROTOCOL_PHASE_ROBUST_FROZEN.md, paper_package/PAPER_TABLES.csv (T1)."
    return "Simulation and validation protocol.", df, note


def t04(R):
    rows = []
    for arm, status in (("PRr", "Primary (pre-registered)"), ("PRrM", "Secondary (mixed-domain training)")):
        for dom in ("bh", "sp"):
            t = f"ARM_{dom}_{arm.upper()}"
            rows.append((arm, status, DOM[dom], R.v(t + "_L"), R.v(t + "_LBA"), R.v(t + "_F"), R.v(t + "_FBA")))
    df = pd.DataFrame(rows, columns=["Method", "Role", "Domain", "Layer macro-F1", "Layer balanced acc.", "Fault macro-F1", "Fault balanced acc."])
    note = (f"Monitor E = ±2%, pooled over amplitudes (behavioral ×0.8–×1.2; ngspice ×0.8, ×1.0, ×1.2) and the five phases; mean of "
            f"{R.v('N_SEEDS')} dataset seeds × 2 initializations. The behavioral and ngspice rows use different amplitude grids and "
            f"must not be subtracted; the matched-grid transfer comparison is in Table 9. Nominal reference value N (known reference, "
            f"×1.0, pooled over phases): {R.v('N_BH')} behavioral, {R.v('N_SP')} ngspice. Source: attribution_arms.csv; decision_rules.json (N).")
    return "Main classification results of the primary (PRr) and secondary (PRrM) methods.", df, note


def t05(R):
    dr = load_json(RES / "decision_rules.json")
    att = load_csv(RES / "attribution_comparisons.csv")
    claimed = att[~att.comparison.str.startswith("PRr - PR (")]
    f_ok = bool((claimed.ci_low > 0).all()) and all(v["ci_low"] > 0 for v in dr["B"]["detail"].values())
    R.add("GATE_F_CHECK", "satisfied" if f_ok else "violated", RES / "attribution_comparisons.csv; decision_rules.json",
          "ci_low of claimed comparisons and B.detail", "all claimed improvements have CI lower bound > 0 (checked here)", decimals=None)
    rows = [
        ("A", "Retention at ×0.8 and ×1.2 (known, E ≤ ±2%)", f"≥ {R.v('A_THRESH')}·N", f"worst {R.v('A_MIN_RET')} ({R.v('A_MIN_RET_WHERE')})", "—", R.v("GATE_A_bh"), R.v("GATE_A_sp")),
        ("B", "Superiority over old method and one-point baselines (behavioral)", "pooled CI lower bound > 0",
         f"smallest lower bound {R.v('B_MIN_CI')} over {R.v('B_N')} comparisons", "per comparison, Table 6", R.v("GATE_B"), "—"),
        ("C", "AFE–ADC cross-confusion at ×0.8 and ×1.2", f"< {R.v('C_THRESH')}", f"largest {R.v('C_MAX')} ({R.v('C_MAX_WHERE')})", "—", R.v("GATE_C_bh"), R.v("GATE_C_sp")),
        ("D", "Retention with monitor E = ±5%", f"≥ {R.v('D_THRESH')}·N", f"worst {R.v('D_MIN_RET')} ({R.v('D_MIN_RET_WHERE')})", "—", R.v("GATE_D_bh"), R.v("GATE_D_sp")),
        ("E", "Behavioral → ngspice transfer loss (E = ±2%, ngspice grid)", f"≤ {R.v('E_THRESH')} (point estimate)", R.v("E_DROP"),
         R.ci("E_DROP_LO", "E_DROP_HI"), R.v("GATE_E"), "—"),
        ("F", "Every claimed improvement supported by a paired-bootstrap CI excluding zero", "CI excludes 0",
         R.v("GATE_F_CHECK"), f"{R.v('N_BOOT')} resamples", "procedural†", "procedural†"),
        ("G", "Layer macro-F1 range over five phases (known, E = ±2%)", f"≤ {R.v('G_THRESH')}", f"largest {R.v('G_PRR_MAX')} (smallest {R.v('G_PRR_MIN')})",
         "—", R.v("GATE_G_bh"), R.v("GATE_G_sp")),
    ]
    df = pd.DataFrame(rows, columns=["Gate", "Criterion", "Threshold", "Observed (PRr)", "95% CI", "Behavioral", "ngspice"])
    note = (f"Decision: {R.v('DECISION')} ({R.v('GATE_FAILED_N')} failed gates). N = PRr layer macro-F1 with known reference at ×1.0 "
            f"({R.v('N_BH')} behavioral, {R.v('N_SP')} ngspice). †Gate F has no separate key in decision_rules.json; it was checked here "
            "against the saved CIs. The mixed-domain variant PRrM also passes the ngspice-domain gates (reported only). "
            "Source: decision_rules.json (gates, A–E, G details); PROTOCOL_PHASE_ROBUST_FROZEN.md §5 (thresholds).")
    return "Pre-registered gate results for the primary method PRr.", df, note


def t06(R):
    dr = load_json(RES / "decision_rules.json")["B"]["detail"]
    baselines = [("passive_mlp@A0", "Passive (sensor signal only), old descriptors", "passive"),
                 ("single_mlp@A0", "Single-probe active test, old descriptors", "single"),
                 ("afe_only_mlp@A0", "AFE-only reference, old descriptors", "afe_only_A0"),
                 ("adc_only_mlp@A0", "ADC-only reference, old descriptors", "adc_only_A0"),
                 ("two_point_mlp@A0", "A0: two-point, old descriptors (previous method)", "A0"),
                 ("afe_only_mlp@PRr_k", "AFE-only reference, PRr descriptors", "afe_only_PRr"),
                 ("adc_only_mlp@PRr_k", "ADC-only reference, PRr descriptors", "adc_only_PRr")]
    rows = []
    prr = {a: mean_metric(macro_f1, "bh", "known", "two_point_mlp@PRr_k", "layer", (a,)) for a in (80, 120)}
    for model, label, short in baselines:
        f1 = {a: mean_metric(macro_f1, "bh", "known", model, "layer", (a,)) for a in (80, 120)}
        cells = []
        for a in (80, 120):
            key = f"known|a{a}|vs {model}"
            d = dr[key]
            assert abs((prr[a] - f1[a]) - d["diff"]) < 1e-9, key  # consistency with the saved paired difference
            tok = f"BASEF1_{short}_a{a}"
            R.add(tok, f1[a], RES / "seed_*/predictions.npz", f"keys bh_a{a}_p*_known|{model}|*|layer",
                  "layer macro-F1 pooled over phases, mean 3 seeds × 2 inits; PRr − this equals B.detail diff (asserted)", status="secondary")
            cells += [R.v(tok), f"{R.v(_btok(key))} {R.ci(_btok(key) + '_LO', _btok(key) + '_HI')}"]
        rows.append((label, cells[0], cells[2], cells[1], cells[3], _att_vs(R, short)))
    for arm, label in (("R1", "R1: Revision-1 fixed-sample descriptors"), ("R1r", "R1r: R1 + phase-randomized training"),
                       ("PR", "PR: phase-robust descriptors, ψ = 0 training"), ("PRr", "PRr: proposed (primary)"),
                       ("PRrM", "PRrM: PRr + mixed-domain training (secondary)")):
        f1 = {}
        for a in (80, 120):
            tok = f"TPF1_{arm}_a{a}"
            f1[a] = mean_metric(macro_f1, "bh", "known", f"two_point_mlp@{arm}_k", "layer", (a,))
            R.add(tok, f1[a], RES / "seed_*/predictions.npz", f"keys bh_a{a}_p*_known|two_point_mlp@{arm}_k|*|layer",
                  "layer macro-F1 pooled over phases, mean 3 seeds × 2 inits", status="primary" if arm == "PRr" else "secondary")
        rows.append((label, R.v(f"TPF1_{arm}_a80"), R.v(f"TPF1_{arm}_a120"), "—", "—", _att_vs(R, arm)))
    df = pd.DataFrame(rows, columns=["Method", "Layer macro-F1 ×0.8", "Layer macro-F1 ×1.2", "PRr − method ×0.8 [95% CI]",
                                     "PRr − method ×1.2 [95% CI]", "PRr − method, E = ±2% pooled [95% CI]"])
    note = ("Behavioral domain, known reference, pooled over the five phases. Absolute layer macro-F1 values are computed from the saved "
            "per-sample predictions (they are not stored in a summary file); for every baseline the difference PRr − method equals the "
            "saved paired difference in decision_rules.json (B) to within 1e-9. Paired differences and CIs: decision_rules.json (B) and "
            "attribution_comparisons.csv; PRr − PRrM is the sign-reversed PRrM − PRr comparison (CI bounds reversed accordingly).")
    return "Baseline comparison (layer macro-F1, behavioral domain).", df, note


def _btok(key):
    var, amp, vs = key.split("|")
    base = re.sub(r"_(k|e\d)$", "", vs.replace("vs ", ""))
    return f"B_{var}_{amp}_{base.replace('@', '_')}"


def _att_vs(R, short):
    m = {"A0": ("ATT_bh_VS_A0", 1), "R1": ("ATT_bh_COMB", 1), "R1r": ("ATT_bh_DESC_GIVEN_RAND", 1),
         "PR": ("ATT_bh_RAND_GIVEN_DESC", 1), "PRrM": ("ATT_bh_MIXED", -1)}
    if short not in m:
        return "—"
    t, sign = m[short]
    if sign == 1:
        return f"{R.v(t)} {R.ci(t + '_LO', t + '_HI')}"
    r = f"{t}_REV"
    if r not in R.entries:  # register the sign-reversed comparison so it has its own provenance row
        e = R.entries[t]
        for suf, src in (("", ""), ("_LO", "_HI"), ("_HI", "_LO")):
            R.add(r + suf, -R.raw(t + src), e.source_file, f"−({R.entries[t + src].key})",
                  f"sign-reversed {t + src} (PRr − PRrM)", signed=True, status="secondary")
    return f"{R.v(r)} {R.ci(r + '_LO', r + '_HI')}"


def t07(R):
    rows = []
    ser = {"known": "PRr_known", "mon0": "PRr_E0", "mon1": "PRr_E1", "mon2": "PRr_E2", "mon5": "PRr_E5"}
    for v, s, lab in VAR:
        cells = [R.v(f"AMP_bh_{ser[v]}_layer_{c}") for c in ("x08", "x09", "x10", "x11", "x12")]
        cells += [R.v(f"AMP_sp_{ser[v]}_layer_{c}") for c in ("x08", "x10", "x12")]
        rows.append((lab, *cells))
    nm = [R.v(f"NOMON_U_{c}") for c in ("x08", "x09", "x10", "x11", "x12")]
    rows.append(("No-monitor control (nominal levels assumed)", *nm, "—", "—", "—"))
    cols = ["Reference condition"] + [f"Behavioral ×{x}" for x in ("0.8", "0.9", "1.0", "1.1", "1.2")] + [f"ngspice ×{x}" for x in ("0.8", "1.0", "1.2")]
    df = pd.DataFrame(rows, columns=cols)
    note = ("PRr layer macro-F1 pooled over the five phases (mean of three seeds). Monitored variants are trained with the matching "
            "error bound E. The no-monitor control is the PRr known-reference classifier given the nominal levels; it was evaluated "
            "in the behavioral domain only. Retention relative to N: worst "
            f"{R.v('A_MIN_RET')} at ±20% (known, E ≤ ±2%) and {R.v('D_MIN_RET')} at E = ±5%. Source: amplitude_curves.csv; no_monitor_control.json; decision_rules.json (A, D).")
    return "Reference-monitor robustness: layer macro-F1 versus actual reference amplitude.", df, note


def t08(R):
    rows = []
    for dom in ("bh", "sp"):
        for arm in ("A0", "R1", "R1r", "PR", "PRr", "PRrM"):
            t = f"ARM_{dom}_{arm.upper()}"
            if t + "_L" not in R.entries:
                continue
            ph = [R.v(f"{t}_{p}") for p in ("P000", "P250", "P500", "P750", "P999")]
            rng = R.raw(t + "_RANGE")
            rows.append((DOM[dom], arm, *ph, R.v(t + "_RANGE"), "yes" if rng <= R.raw("G_THRESH") else "no"))
    df = pd.DataFrame(rows, columns=["Domain", "Arm", "ψ = 0", "ψ = 0.25", "ψ = 0.5", "ψ = 0.75", "ψ = 0.999", "Range (max − min)", f"≤ {R.v('G_THRESH')}"])
    note = ("Layer macro-F1 per edge phase, monitor E = ±2%, pooled over amplitudes; range computed as max − min of the five stored "
            "phase values. Gate G itself applies to PRr (known reference and E = ±2%; Table 5): PRr ranges "
            f"{R.v('G_bh_PRR_K_RANGE')} / {R.v('G_bh_PRR_E2_RANGE')} (behavioral known / E2) and {R.v('G_sp_PRR_K_RANGE')} / "
            f"{R.v('G_sp_PRR_E2_RANGE')} (ngspice). A0 was not simulated in ngspice; its flat profile reflects uniformly low accuracy. "
            "Source: attribution_arms.csv; decision_rules.json (G).")
    return "Phase-robustness ablation: layer macro-F1 per edge phase.", df, note


def t09(R):
    rows = []
    for v, s, lab in VAR:
        rows.append((lab, R.v(f"E_{s}_BB"), R.v(f"E_{s}_BS"), R.v(f"E_{s}_DROP"), R.ci(f"E_{s}_DROP_LO", f"E_{s}_DROP_HI"),
                     "PASS" if R.raw(f"E_{s}_DROP") <= R.raw("E_THRESH") else "FAIL", R.v(f"E_{s}_MS"),
                     f"{R.v(f'E_{s}_MSBS')} {R.ci(f'E_{s}_MSBS_LO', f'E_{s}_MSBS_HI')}"))
    rows.append(("Previous stage, E = ±2% (REVISE)", R.v("PREV_BB"), R.v("PREV_BS"), R.v("PREV_DROP"), R.ci("PREV_DROP_LO", "PREV_DROP_HI"),
                 "FAIL", "—", "—"))
    df = pd.DataFrame(rows, columns=["Reference condition", "Behavioral BB (PRr)", "ngspice BS (PRr)", "Transfer loss BB − BS",
                                     "95% CI", f"≤ {R.v('E_THRESH')}", "ngspice MS (PRrM)", "MS − BS [95% CI]"])
    note = ("Matched grid: ×0.8, ×1.0, ×1.2 × five phases in both domains. BB and BS use the same behavioral-trained PRr classifier; MS "
            "is the mixed-trained secondary variant PRrM. The pre-registered gate E uses E = ±2%. The previous-stage row is the failed "
            "earlier validation (reference_monitor_final), read from paper_package/NUMBER_PROVENANCE.csv because its decision file is "
            "not in the evidence package. Source: decision_rules.json (E).")
    return "Behavioral-to-ngspice domain transfer (layer macro-F1).", df, note


def t10(R):
    rows = []
    for dom in ("bh", "sp"):
        for v, s, lab in VAR:
            for a in ("a80", "a120"):
                k = f"C_{dom}_{v}_{a}"
                rows.append((DOM[dom], lab, "×0.8" if a == "a80" else "×1.2", R.v(k + "_AFE"), R.v(k + "_ADC"), R.v(k + "_X")))
    for a in ("a80", "a120"):
        k = f"SEPX_bh_assumed_{a}"
        rows.append(("Behavioral", "No monitor (nominal levels assumed)", "×0.8" if a == "a80" else "×1.2", R.v(k + "_AFE"), R.v(k + "_ADC"), R.v(k + "_X")))
    df = pd.DataFrame(rows, columns=["Domain", "Reference / monitor condition", "Amplitude", "AFE recall", "ADC recall", "AFE–ADC cross-confusion"])
    note = ("PRr, layer classifier, pooled over the five phases (mean of three seeds × two initializations). Cross-confusion = fraction "
            "of AFE- and ADC-fault records assigned to the other of the two layers (gate C limit "
            f"{R.v('C_THRESH')}). Source: decision_rules.json (C); no-monitor rows computed from seed_*/predictions.npz with the same "
            "definition (the computation reproduces every saved C value exactly; see verification/RECOMPUTED_FROM_PREDICTIONS.csv).")
    return "AFE/ADC fault separation of PRr at ±20% reference amplitude.", df, note


def t11(R):
    rows = []
    for dom in ("bh", "sp"):
        for arm in ("A0", "R1", "R1r", "PR", "PRr", "PRrM"):
            if f"RF_{dom}_{arm.upper()}_HEALTHY" not in R.entries:
                continue
            fine = [R.v(f"RF_{dom}_{arm.upper()}_{f.upper()}") for f in FAULTS]
            lay = [R.v(f"RL_{dom}_{arm.upper()}_{c.upper()}") for c in LAYERS]
            rows.append((DOM[dom], arm, *fine, *lay))
    rows.append(("Behavioral", "PRr, no monitor (×0.8/×1.2)", *(["—"] * 9), *[R.v(f"RL_bh_UNMON_{c.upper()}") for c in LAYERS]))
    df = pd.DataFrame(rows, columns=["Domain", "Arm"] + list(FAULT_LABELS) + [f"Layer: {c}" for c in LAYER_LABELS])
    note = ("Recall, monitor E = ±2%, pooled over amplitudes and phases (mean of three seeds). Weak classes (recall < 0.5) for PRr: "
            "healthy, sensor bias, sensor gain and ADC clipping; healthy-layer recall "
            f"{R.v('RL_bh_PRR_HEALTHY')} (behavioral) / {R.v('RL_sp_PRR_HEALTHY')} (ngspice). "
            "Source: per_class_recall_fault.csv; per_class_recall_layer.csv.")
    return "Per-class recall (fine-fault and layer classes).", df, note


def t12(R):
    rows = [
        ("MLP architecture", f"{R.v('ARCH')} hidden layout; 20 inputs; ReLU; output 4 (layer) or 9 (fault)", "PAPER_TABLES.csv T10; parameter count check"),
        ("MLP parameters", f"{R.v('PARAMS_LAYER')} (layer head); {R.v('PARAMS_FAULT')} (fault head)", "timing_and_parameters.json"),
        ("Multiply-accumulates per inference", f"{R.v('MACS_LAYER')} (layer); {R.v('MACS_FAULT')} (fault)", "derived from the architecture"),
        ("MLP inference time", f"{R.v('MLP_US')} µs per record (batched, Python, mean of 3 seeds)", "timing_and_parameters.json"),
        ("Descriptor extraction time", f"Phase-robust {R.v('DESC_MS_PR')} ms; Revision-1 {R.v('DESC_MS_R1')} ms per record (Python, 1 core)", "timing_and_parameters.json"),
        ("MLP training time (PRr models)", f"mean {R.v('TRAIN_S_PRR_MEAN')} s, max {R.v('TRAIN_S_PRR_MAX')} s per model", "seed_*/model_info.json"),
        ("ngspice runs", f"{R.v('SPICE_RUNS_SEED')} per seed; {R.v('SPICE_RUNS_TOTAL')} total", "seed_*/meta.json"),
        ("Validation runtime per seed", "; ".join(f"{s}: total {R.v(f'RUNTIME_TOTAL_{s}')} s (ngspice wall {R.v(f'RUNTIME_SP_{s}')} s, behavioral {R.v(f'RUNTIME_BH_{s}')} s)" for s in SEEDS),
         "seed_*/meta.json"),
        ("ngspice workers", f"{R.v('SPICE_WORKERS')} parallel workers", "timing_and_parameters.json"),
        ("Important assumptions", "Timings are desktop Python (macOS arm64) measurements, not microcontroller measurements; no energy, "
                                  "power, area or hardware cost was measured", "REPRODUCIBILITY_CHECKLIST.md (environment)"),
    ]
    df = pd.DataFrame(rows, columns=["Quantity", "Value", "Source"])
    note = "No embedded-target timing or energy figure exists in the evidence package; none is claimed."
    return "Model and computational complexity.", df, note


TABLES = [t01, t02, t03, t04, t05, t06, t07, t08, t09, t10, t11, t12]
NAMES = ["Table01_system_components", "Table02_fault_taxonomy", "Table03_protocol", "Table04_main_results", "Table05_gates",
         "Table06_baselines", "Table07_reference_monitor", "Table08_phase_ablation", "Table09_domain_transfer",
         "Table10_afe_adc_separation", "Table11_per_class_recall", "Table12_complexity"]


# --------------------------------------------------------------------------------- writers

def to_md(n, title, df, note):
    head = "| " + " | ".join(df.columns) + " |"
    sep = "|" + "|".join("---" for _ in df.columns) + "|"
    body = ["| " + " | ".join(str(x) for x in r) + " |" for r in df.itertuples(index=False)]
    return "\n".join([f"**Table {n}.** {title}", "", head, sep, *body, "", f"*{note}*", ""])


LATEX_MAP = [("\\", r"\textbackslash{}"), ("&", r"\&"), ("%", r"\%"), ("_", r"\_"), ("#", r"\#"), ("$", r"\$"),
             ("±", r"$\pm$"), ("×", r"$\times$"), ("ψ", r"$\psi$"), ("τ", r"$\tau$"), ("σ", r"$\sigma$"), ("Δ", r"$\Delta$"),
             ("−", "--"), ("–", "--"), ("—", "---"), ("≤", r"$\leq$"), ("≥", r"$\geq$"), ("→", r"$\rightarrow$"),
             ("~", r"$\sim$"), ("µ", r"$\mu$"), ("·", r"$\cdot$"), ("↔", r"$\leftrightarrow$"), ("Ω", r"$\Omega$")]


def tex_escape(s):
    s = str(s)
    out = []
    for ch in s:
        rep = ch
        for a, b in LATEX_MAP:
            if ch == a:
                rep = b
                break
        out.append(rep)
    return "".join(out)


def to_tex(n, title, df, note, label):
    ncol = len(df.columns)
    wide = ncol > 6 or df.astype(str).map(len).max().max() > 60
    spec = ("p{3.2cm}" + "p{%.1fcm}" % max(1.2, (14.0 - 3.2) / max(ncol - 1, 1)) * (ncol - 1)) if wide else "l" + "c" * (ncol - 1)
    lines = [r"\begin{table}[H]", rf"\caption{{{tex_escape(title)}\label{{tab:{label}}}}}", r"\centering", r"\footnotesize" if wide else r"\small",
             rf"\begin{{tabular}}{{{spec}}}", r"\toprule",
             " & ".join(r"\textbf{" + tex_escape(c) + "}" for c in df.columns) + r" \\", r"\midrule"]
    for r in df.itertuples(index=False):
        lines.append(" & ".join(tex_escape(x) for x in r) + r" \\")
    lines += [r"\bottomrule", r"\end{tabular}", r"\begin{tablenotes}[flushleft]\footnotesize\item " + tex_escape(note) + r"\end{tablenotes}" if False else
              r"\par\vspace{2pt}\noindent{\footnotesize " + tex_escape(note) + "}", r"\end{table}", ""]
    return "\n".join(lines)


def _border(cell, edges):
    tcPr = cell._tc.get_or_add_tcPr()
    b = OxmlElement("w:tcBorders")
    for e, sz in edges.items():
        el = OxmlElement(f"w:{e}")
        el.set(qn("w:val"), "single")
        el.set(qn("w:sz"), str(sz))
        el.set(qn("w:color"), "000000")
        b.append(el)
    tcPr.append(b)


def docx_table(doc, n, title, df, note):
    p = doc.add_paragraph()
    r = p.add_run(f"Table {n}. ")
    r.bold = True
    r.font.size = Pt(9)
    r2 = p.add_run(title)
    r2.font.size = Pt(9)
    t = doc.add_table(rows=1 + len(df), cols=len(df.columns))
    t.autofit = True
    for j, c in enumerate(df.columns):
        cell = t.cell(0, j)
        cell.text = ""
        run = cell.paragraphs[0].add_run(str(c))
        run.bold = True
        run.font.size = Pt(7.5)
        _border(cell, {"top": 12, "bottom": 6})
    for i, row in enumerate(df.itertuples(index=False), 1):
        for j, v in enumerate(row):
            cell = t.cell(i, j)
            cell.text = ""
            run = cell.paragraphs[0].add_run(str(v))
            run.font.size = Pt(7.5)
            if i == len(df):
                _border(cell, {"bottom": 12})
    q = doc.add_paragraph()
    rr = q.add_run(note)
    rr.italic = True
    rr.font.size = Pt(7)
    doc.add_paragraph()


def new_doc(landscape=True):
    doc = Document()
    sec = doc.sections[0]
    if landscape:
        sec.orientation = WD_ORIENT.LANDSCAPE
        sec.page_width, sec.page_height = sec.page_height, sec.page_width
    for side in ("left_margin", "right_margin", "top_margin", "bottom_margin"):
        setattr(sec, side, Cm(1.5))
    style = doc.styles["Normal"]
    style.font.name = "Palatino Linotype"
    style.font.size = Pt(9)
    return doc


def build_all(R):
    TAB.mkdir(parents=True, exist_ok=True)
    all_md = ["# Tables (MDPI Sensors)", "",
              "Generated by `scripts/build_all.py` from the frozen result files; every cell is traceable through "
              "`NUMBER_PROVENANCE_MDPI.csv`. Each table is also available as CSV, LaTeX (`.tex`, booktabs) and Word (`.docx`).", ""]
    all_tex = ["% Tables for the MDPI Sensors manuscript (requires booktabs, float).", ""]
    combined = new_doc()
    out = {}
    for n, (fn, name) in enumerate(zip(TABLES, NAMES), 1):
        title, df, note = fn(R)
        df.to_csv(TAB / f"{name}.csv", index=False)
        md = to_md(n, title, df, note)
        (TAB / f"{name}.md").write_text(md)
        tex = to_tex(n, title, df, note, name.lower())
        (TAB / f"{name}.tex").write_text(tex)
        d = new_doc()
        docx_table(d, n, title, df, note)
        d.save(TAB / f"{name}.docx")
        docx_table(combined, n, title, df, note)
        all_md.append(md)
        all_tex.append(tex)
        out[name] = dict(n=n, title=title, df=df, note=note)
    (TAB / "ALL_TABLES.md").write_text("\n".join(all_md))
    (TAB / "ALL_TABLES.tex").write_text("\n".join(all_tex))
    combined.save(TAB / "ALL_TABLES.docx")
    return out


if __name__ == "__main__":
    from registry_build import build
    R, _ = build()
    o = build_all(R)
    for k, v in o.items():
        print(k, v["df"].shape)
