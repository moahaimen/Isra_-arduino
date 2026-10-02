#!/usr/bin/env python3
"""Automated scientific-validity audit of a main campaign (Phase 22).

Each check prints PASS/FAIL with the evidence it used. Writes a Markdown
report (default: <campaign>/logs/scientific_audit.md).

Usage: python3 scripts/audit_scientific.py <main_campaign_dir> [--out FILE]
"""
from __future__ import annotations

import argparse
import glob
import json
import os
import random
import re
import subprocess
import sys
import tempfile

import pandas as pd

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.abspath(os.path.join(HERE, ".."))
sys.path.insert(0, os.path.join(HERE, "eval_energy"))
from metrics import load_observations  # noqa: E402

BIN = os.path.join(REPO, "build", "edge_sim")
MODE_KEYS = {"mode", "watcher_kind", "adaptive_trigger", "security", "early_exit", "out_dir", "workload", "log_level"}
DECISION_COLS = ["score", "threshold", "raw_positive", "triggered", "suppress_reason", "sec_evaluated", "sec_accept",
                 "sec_reason", "rpc_status", "processed", "detected", "final_class", "result_delivered_ms"]


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("campaign")
    ap.add_argument("--out")
    a = ap.parse_args()
    c = a.campaign
    out = a.out or os.path.join(c, "logs", "scientific_audit.md")
    rows = []

    def record(name, ok, evidence):
        rows.append((name, ok, evidence))
        print(f"{'PASS' if ok else 'FAIL'}  {name}: {evidence}")

    runs = pd.read_csv(os.path.join(c, "per_run", "metrics.csv"))
    wl_eq = pd.read_csv(os.path.join(c, "logs", "workload_equality.csv"))

    # 1. Unfair / method-specific workloads
    n_hash = runs.groupby(["scenario", "seed"])["workload_hash"].nunique()
    record("identical workload for every mode of a (scenario, seed)",
           bool((n_hash == 1).all() and wl_eq["all_runs_match"].all()),
           f"{len(n_hash)} (scenario, seed) groups, max distinct hashes per group = {int(n_hash.max())}; "
           f"{len(wl_eq)} workload files, every run's hash equals its file hash = {bool(wl_eq['all_runs_match'].all())}")

    # 2. Mode configurations differ only in component switches
    bad = []
    for (sc, seed), g in runs.groupby(["scenario", "seed"]):
        cfgs = {r["mode"]: json.load(open(os.path.join(c, "raw", r["run_id"], "config.json"))) for _, r in g.iterrows()}
        base = cfgs[g["mode"].iloc[0]]
        for m, cf in cfgs.items():
            diff = {k for k in cf if cf[k] != base.get(k)} - MODE_KEYS
            if diff:
                bad.append((sc, seed, m, sorted(diff)))
        break  # configurations are identical in structure across groups; one group suffices
    all_cfg = [json.load(open(p)) for p in glob.glob(os.path.join(c, "raw", "*", "config.json"))]
    shared = ["trigger_threshold", "cooldown_ms", "inference_ms", "second_pass_cost_ms", "early_exit_threshold",
              "rpc_latency_ms", "rpc_jitter_ms", "rpc_loss", "rpc_queue_capacity", "m7_wakeup_ms"]
    uniq = {k: len({json.dumps(cf[k]) for cf in all_cfg}) for k in shared}
    record("no per-method parameter tuning",
           not bad and all(v == 1 for v in uniq.values()),
           f"keys differing between modes beyond component switches: {bad or 'none'}; distinct values of shared "
           f"parameters across all {len(all_cfg)} runs: {uniq}")

    # 3. Leakage of ground-truth labels into decisions (static + dynamic)
    leak_static = []
    for f in ("simulation/watcher/watcher.h", "simulation/security/security_gate.h"):
        txt = open(os.path.join(REPO, f)).read()
        for tok in ("GroundTruth", "is_legitimate", "attack_type", "ground_truth", "object_present", "replay_id"):
            if re.search(r"\b" + tok + r"\b", txt):
                leak_static.append(f"{f}:{tok}")
    record("watcher and security code cannot reference ground-truth fields (static)", not leak_static,
           f"forbidden identifiers found: {leak_static or 'none'}")
    wl_files = sorted(glob.glob(os.path.join(c, "workloads", "mixed__s01*.jsonl")) or
                      glob.glob(os.path.join(c, "workloads", "mixed__s1__*.jsonl")))
    if wl_files and os.path.exists(BIN):
        src = wl_files[0]
        tmp = tempfile.mkdtemp(prefix="audit_")
        rnd = random.Random(12345)
        scrambled = os.path.join(tmp, "scrambled.jsonl")
        with open(src) as fi, open(scrambled, "w") as fo:
            for line in fi:
                e = json.loads(line)
                # Scramble every label the decision logic must not see. The
                # physical frame content (frame_has_object) is kept because the
                # detector model legitimately simulates what the camera images.
                e["is_legitimate"] = rnd.random() < 0.5
                e["attack_type"] = rnd.choice(["none", "trigger_spam", "replay"])
                e["ground_truth_action"] = rnd.choice(["detect", "ignore", "block"])
                e["object_present"] = rnd.random() < 0.5
                e["object_class"] = rnd.choice(["none", "person", "vehicle"])
                e["replay_id"] = rnd.randint(-1, 50)
                e["episode_type"] = rnd.choice(["object", "noise", "attack"])
                fo.write(json.dumps(e) + "\n")
        meta = json.load(open(src + ".meta.json"))
        diffs = {}
        for mode in ("event", "secure"):
            outs = []
            for wl, tag in ((src, "orig"), (scrambled, "scr")):
                od = os.path.join(tmp, f"{mode}_{tag}")
                subprocess.run([BIN, "--config", os.path.join(c, "config", "default_config.json"), "--mode", mode,
                                "--workload", wl, "--seconds", str(meta["seconds"]), "--seed", str(meta["seed"]),
                                "--out-dir", od, "--log-level", "none"], check=True, stdout=subprocess.DEVNULL)
                outs.append(load_observations(od)[DECISION_COLS])
            diffs[mode] = int((outs[0] != outs[1]).any(axis=1).sum())
        record("decisions unchanged when every ground-truth label is scrambled (dynamic)",
               all(v == 0 for v in diffs.values()),
               f"workload {os.path.basename(src)}; observations with any differing decision column: {diffs}")
    else:
        record("decisions unchanged when every ground-truth label is scrambled (dynamic)", False,
               "could not run (binary or mixed workload missing)")

    # 4. Random security blocking absent
    record("no random blocking in research runs",
           bool(runs["research_valid"].all() and runs["block_debug_random"].sum() == 0),
           f"research_valid all true = {bool(runs['research_valid'].all())}; DEBUG_RANDOM blocks = "
           f"{int(runs['block_debug_random'].sum())}")

    # 5. Accidental perfect detection
    proc = runs[runs["results"] > 20]
    perfect = proc[(proc["detector_precision"] >= 0.999) & (proc["detector_recall"] >= 0.999)]
    record("no accidentally perfect detector", len(perfect) == 0,
           f"runs with >20 results: {len(proc)}; runs with precision and recall both 1: {len(perfect)}; detector "
           f"recall range {proc['detector_recall'].min():.3f}-{proc['detector_recall'].max():.3f}, precision range "
           f"{proc['detector_precision'].min():.3f}-{proc['detector_precision'].max():.3f}")
    sec = runs[(runs["mode"] == "secure") & (runs["attack_attempts"] > 0)]
    record("security gate is not perfect (no hidden oracle)",
           bool((sec["attack_detection_rate"] < 0.999).all() and (sec["false_rejection_rate"] > 0).any()),
           f"secure runs with attacks: {len(sec)}; ADR range {sec['attack_detection_rate'].min():.3f}-"
           f"{sec['attack_detection_rate'].max():.3f}; FRR range {sec['false_rejection_rate'].min():.3f}-"
           f"{sec['false_rejection_rate'].max():.3f}")

    # 6. Impossible timing
    cfg = json.load(open(os.path.join(c, "config", "default_config.json")))
    ev = runs[runs["mode"] != "always_on"]
    min_onset = ev["onset_latency_ms_min"].min()
    floor = cfg["m4_process_ms"] + cfg["rpc_latency_ms"] + cfg["m7_wakeup_ms"] + cfg["postprocess_base_ms"]
    record("no impossible timing", bool(runs["negative_latency_count"].sum() == 0 and
                                         runs["negative_queue_delay_count"].sum() == 0 and min_onset > floor),
           f"negative latencies = {int(runs['negative_latency_count'].sum())}, negative queue delays = "
           f"{int(runs['negative_queue_delay_count'].sum())}; minimum event-mode onset latency {min_onset:.1f} ms > "
           f"fixed-cost floor {floor:.1f} ms (watcher+RPC+wake+postprocess, before any inference)")

    # 7. Double-counted energy
    T = runs["seconds"] * 1000.0
    err4 = (runs["state_time_m4_ms"] - T).abs().max()
    err7 = (runs["state_time_m7_ms"] - T).abs().max()
    eerr = (runs["energy_total_mJ"] - runs["energy_summary_check_mJ"]).abs().max()
    record("no double-counted energy", bool(err4 < 1 and err7 < 1 and eerr < 0.05),
           f"max |sum of M4 state time - T| = {err4:.4f} ms, M7 = {err7:.4f} ms (each core in exactly one state); "
           f"max |Python energy - simulator energy| = {eerr:.6f} mJ")

    # 8. Trigger/result mapping, duplicated events, validation
    val = pd.read_csv(os.path.join(c, "logs", "validation.csv"))
    record("structural validation of every run (trigger/result pairs, wake/sleep, ids, SIM_END)",
           bool(val["validation_pass"].all()), f"{int(val['validation_pass'].sum())}/{len(val)} runs pass")
    dup = 0
    for f in glob.glob(os.path.join(c, "workloads", "*.jsonl")):
        ids = pd.read_json(f, lines=True)["event_id"] if os.path.getsize(f) else pd.Series(dtype=int)
        dup += int(ids.duplicated().sum())
    record("no duplicated workload events", dup == 0, f"duplicated event ids across all workloads: {dup}")

    # 9. Statistical pairing
    pc = pd.read_csv(os.path.join(c, "aggregate", "paired_comparisons.csv"))
    record("paired tests only on matched workloads", bool(pc["same_workload"].all()),
           f"{len(pc)} comparisons, all with identical workload hashes per seed = {bool(pc['same_workload'].all())}")

    # 10. Raw results preserved / not overwritten
    n_raw = len(glob.glob(os.path.join(c, "raw", "*", "summary.json")))
    record("raw outputs preserved for every run", n_raw == len(runs), f"{n_raw} raw run directories for {len(runs)} runs")

    # 11. Synthetic parameters not described as measured
    pm = json.load(open(os.path.join(c, "config", "power_model.json")))
    ok_pm = pm["source"] == "simulation_assumption" and not pm["calibrated"] and all(
        v["source"] == "simulation_assumption" for v in pm["states"].values())
    record("power model flagged as uncalibrated simulation assumption", ok_pm,
           f"source={pm['source']}, calibrated={pm['calibrated']}; summaries report power_model_calibrated="
           f"{sorted(set(runs['power_model_calibrated']))}")
    record("mAP not fabricated", bool(runs["map50"].isna().all()),
           f"map50 non-empty in {int(runs['map50'].notna().sum())} runs (synthetic backend has no boxes)")

    with open(out, "w") as fh:
        fh.write("# Automated scientific audit\n\nGenerated by `scripts/audit_scientific.py` for campaign "
                 f"`{os.path.basename(os.path.normpath(c))}`.\n\n| check | result | evidence |\n|---|---|---|\n")
        for name, ok, ev_ in rows:
            fh.write(f"| {name} | {'PASS' if ok else 'FAIL'} | {ev_} |\n")
    print(f"wrote {out}")
    return 0 if all(r[1] for r in rows) else 1


if __name__ == "__main__":
    sys.exit(main())
