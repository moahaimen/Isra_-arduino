#!/usr/bin/env python3
"""Per-run metrics computed from stored simulator outputs.

Every number produced here is derived from the files the simulator wrote for
one run (observations.csv[.gz], states.csv, wake_intervals.csv, summary.json,
config.json). Nothing is typed in by hand.

Conventions
-----------
* Ratios use safe denominators: x / 0 -> NaN (reported as empty in CSV).
* "Legit object observation" = ground_truth_action == "detect".
* Attack observations have attack_type != "none" (ground_truth_action "block").
* Energy is MODELED energy (power-state assumptions x simulated state time).

Usage:
    python3 scripts/eval_energy/metrics.py <run_dir> [--json]
"""
from __future__ import annotations

import json
import math
import os
import sys
from typing import Dict, Iterable

import numpy as np
import pandas as pd

NAN = float("nan")


def sdiv(a: float, b: float) -> float:
    """Safe division: returns NaN when the denominator is zero."""
    return float(a) / float(b) if b else NAN


def f1(p: float, r: float) -> float:
    if p is None or r is None or math.isnan(p) or math.isnan(r) or (p + r) == 0:
        return NAN
    return 2.0 * p * r / (p + r)


def dist_stats(values: Iterable[float], prefix: str) -> Dict[str, float]:
    v = np.asarray([x for x in values if x is not None and not math.isnan(x)], dtype=float)
    keys = ["n", "mean", "median", "std", "p90", "p95", "p99", "min", "max"]
    if v.size == 0:
        out = {f"{prefix}_{k}": NAN for k in keys}
        out[f"{prefix}_n"] = 0
        return out
    return {
        f"{prefix}_n": int(v.size),
        f"{prefix}_mean": float(v.mean()),
        f"{prefix}_median": float(np.median(v)),
        f"{prefix}_std": float(v.std(ddof=1)) if v.size > 1 else 0.0,
        f"{prefix}_p90": float(np.percentile(v, 90)),
        f"{prefix}_p95": float(np.percentile(v, 95)),
        f"{prefix}_p99": float(np.percentile(v, 99)),
        f"{prefix}_min": float(v.min()),
        f"{prefix}_max": float(v.max()),
    }


def find_file(run_dir: str, name: str) -> str:
    for cand in (name, name + ".gz"):
        p = os.path.join(run_dir, cand)
        if os.path.exists(p):
            return p
    raise FileNotFoundError(f"{name}[.gz] not found in {run_dir}")


def load_observations(run_dir: str) -> pd.DataFrame:
    df = pd.read_csv(find_file(run_dir, "observations.csv"), keep_default_na=False)
    for col in ("is_legitimate", "object_present", "frame_has_object", "m4_evaluated", "raw_positive",
                "triggered", "sec_evaluated", "sec_accept", "caused_wake", "started", "processed",
                "early_exit", "second_pass", "detected"):
        df[col] = df[col].astype(int).astype(bool)
    return df


def compute_run_metrics(run_dir: str) -> Dict[str, float]:
    with open(os.path.join(run_dir, "summary.json")) as fh:
        summary = json.load(fh)
    with open(os.path.join(run_dir, "config.json")) as fh:
        cfg = json.load(fh)
    df = load_observations(run_dir)
    states = pd.read_csv(os.path.join(run_dir, "states.csv"))
    wakes = pd.read_csv(os.path.join(run_dir, "wake_intervals.csv"))

    mode = summary["mode"]
    T_ms = float(summary["seconds"]) * 1000.0
    minutes = T_ms / 60000.0
    always_on = mode == "always_on"
    m: Dict[str, float] = {
        "mode": mode,
        "scenario": summary["scenario"],
        "seed": int(summary["seed"]),
        "seconds": float(summary["seconds"]),
        "workload_hash": summary["workload_hash_fnv1a64"],
        "research_valid": bool(summary.get("research_valid", True)),
        "detector_backend": summary["detector_backend"],
        "power_model_calibrated": bool(summary["power_model_calibrated"]),
        "ablations": "|".join(cfg.get("ablations", [])),
    }

    legit = df["is_legitimate"]
    attack = ~legit
    obj = df["ground_truth_action"] == "detect"
    processed = df["processed"]

    # ------------------------------------------------------------------ system
    active_ms = float(wakes["active_ms"].sum()) if len(wakes) else 0.0
    correct_cls = df["final_class"] == df["object_class"]
    tp_frame = processed & obj & df["detected"] & correct_cls
    useful = processed & obj & df["detected"]
    m.update({
        "observations": int(len(df)),
        "legit_observations": int(legit.sum()),
        "object_observations": int(obj.sum()),
        "attack_observations": int(attack.sum()),
        "m7_active_ms": active_ms,
        "duty_cycle": sdiv(active_ms, T_ms),
        "wakeups": int(len(wakes)),
        "wakeups_per_min": sdiv(len(wakes), minutes),
        "results": int(processed.sum()),
        "throughput_results_per_min": sdiv(processed.sum(), minutes),
        "useful_detections": int(useful.sum()),
        "correct_detections": int(tp_frame.sum()),
        "triggers": int(df["triggered"].sum()),
    })

    # Episode-level detection of real objects (system recall).
    obj_df = df[obj]
    n_ep = obj_df["episode_id"].nunique()
    det_eps = df[tp_frame].groupby("episode_id")["result_delivered_ms"].min()
    onsets = obj_df.groupby("episode_id")["timestamp_ms"].min()
    ep_lat = (det_eps - onsets.reindex(det_eps.index)).values if len(det_eps) else []
    m["object_episodes"] = int(n_ep)
    m["object_episodes_detected"] = int(len(det_eps))
    m["episode_recall"] = sdiv(len(det_eps), n_ep)
    m["missed_episode_rate"] = 1.0 - m["episode_recall"] if n_ep else NAN
    m["observation_recall"] = sdiv(tp_frame.sum(), obj.sum())
    m.update(dist_stats(ep_lat, "episode_latency_ms"))

    # ------------------------------------------------------------------ latency
    delivered = df["result_delivered_ms"] >= 0
    trig_lat = (df.loc[delivered & (df["decision_ms"] >= 0), "result_delivered_ms"]
                - df.loc[delivered & (df["decision_ms"] >= 0), "decision_ms"])
    onset_lat = df.loc[delivered, "result_delivered_ms"] - df.loc[delivered, "timestamp_ms"]
    if always_on:
        m.update(dist_stats([], "trigger_latency_ms"))
    else:
        m.update(dist_stats(trig_lat.values, "trigger_latency_ms"))
    m.update(dist_stats(onset_lat.values, "onset_latency_ms"))
    m["negative_latency_count"] = int((trig_lat < 0).sum() + (onset_lat < 0).sum())

    # ------------------------------------------------------------------ watcher
    if always_on:
        for k in ("watcher_tp", "watcher_fp", "watcher_fn", "watcher_tn", "watcher_precision", "watcher_recall",
                  "watcher_f1", "false_trigger_rate", "missed_event_rate", "trigger_precision"):
            m[k] = NAN
    else:
        ev = df[df["m4_evaluated"]]
        pos = ev["ground_truth_action"] == "detect"
        pred = ev["raw_positive"]
        tp, fp = int((pos & pred).sum()), int((~pos & pred).sum())
        fn, tn = int((pos & ~pred).sum()), int((~pos & ~pred).sum())
        p, r = sdiv(tp, tp + fp), sdiv(tp, tp + fn)
        trig = ev["triggered"]
        m.update({
            "watcher_tp": tp, "watcher_fp": fp, "watcher_fn": fn, "watcher_tn": tn,
            "watcher_precision": p, "watcher_recall": r, "watcher_f1": f1(p, r),
            "false_trigger_rate": sdiv(fp, fp + tn),
            "missed_event_rate": sdiv(fn, tp + fn),
            "trigger_precision": sdiv((trig & pos).sum(), trig.sum()),
            "watcher_fp_attack": int((pred & (ev["attack_type"] != "none")).sum()),
        })

    # ------------------------------------------------------------------ detector
    lp = df[processed & legit]
    d_obj = lp["ground_truth_action"] == "detect"
    d_tp = int((d_obj & lp["detected"] & (lp["final_class"] == lp["object_class"])).sum())
    d_fp = int((lp["detected"] & (~d_obj | (lp["final_class"] != lp["object_class"]))).sum())
    d_fn = int((d_obj & ~(lp["detected"] & (lp["final_class"] == lp["object_class"]))).sum())
    dp, dr = sdiv(d_tp, d_tp + d_fp), sdiv(d_tp, d_tp + d_fn)
    det_obj = lp[d_obj & lp["detected"]]
    m.update({
        "detector_tp": d_tp, "detector_fp": d_fp, "detector_fn": d_fn,
        "detector_precision": dp, "detector_recall": dr, "detector_f1": f1(dp, dr),
        "classification_accuracy": sdiv((det_obj["final_class"] == det_obj["object_class"]).sum(), len(det_obj)),
        "conf_object_mean": float(lp.loc[d_obj, "final_conf"].mean()) if d_obj.any() else NAN,
        "conf_object_std": float(lp.loc[d_obj, "final_conf"].std()) if d_obj.sum() > 1 else NAN,
        "conf_nonobject_mean": float(lp.loc[~d_obj, "final_conf"].mean()) if (~d_obj).any() else NAN,
        "early_exit_rate": sdiv(df.loc[processed, "early_exit"].sum(), processed.sum()),
        "second_pass_rate": sdiv(df.loc[processed, "second_pass"].sum(), processed.sum()),
        # mAP needs bounding-box ground truth and predictions; the synthetic
        # backend has none, so it is deliberately not computed.
        "map50": NAN,
        "map50_95": NAN,
        "map_status": "not_computed_no_bbox_data",
    })
    false_alarm = processed & df["detected"] & ~obj
    m["false_alarms"] = int(false_alarm.sum())
    m["false_alarms_attack"] = int((false_alarm & attack).sum())
    m["false_alarms_per_hour"] = sdiv(false_alarm.sum(), T_ms / 3600000.0)
    m["background_cycles"] = int(summary.get("bg_cycles", 0))
    m["background_false_alarms"] = int(summary.get("bg_detections", 0))

    # ------------------------------------------------------------------ security
    sec = df[df["sec_evaluated"]]
    blocked = sec[~sec["sec_accept"]]
    accepted = sec[sec["sec_accept"]]
    sec_attack = sec["attack_type"] != "none"
    a_blk = int((blocked["attack_type"] != "none").sum())
    a_acc = int((accepted["attack_type"] != "none").sum())
    l_blk = int((blocked["attack_type"] == "none").sum())
    l_acc = int((accepted["attack_type"] == "none").sum())
    obj_eval = sec["ground_truth_action"] == "detect"
    sp, sr = sdiv(a_blk, a_blk + l_blk), sdiv(a_blk, a_blk + a_acc)
    attack_reached = int((attack & df["started"]).sum())
    m.update({
        "attack_attempts": int(attack.sum()),
        "attack_triggers": int((attack & df["triggered"]).sum()) if not always_on else NAN,
        "attacks_evaluated": int(sec_attack.sum()),
        "attacks_blocked": a_blk,
        "attacks_accepted": a_acc,
        "legit_evaluated": int((~sec_attack).sum()),
        "legit_blocked": l_blk,
        "legit_accepted": l_acc,
        "legit_object_blocked": int((~sec["sec_accept"] & obj_eval).sum()),
        "attack_detection_rate": sr,
        "attack_success_rate": sdiv(attack_reached, attack.sum()),
        "attacks_reached_m7": attack_reached,
        "false_rejection_rate": sdiv(l_blk, l_blk + l_acc),
        "false_rejection_rate_object": sdiv((~sec["sec_accept"] & obj_eval).sum(), obj_eval.sum()),
        "security_block_rate": sdiv(len(blocked), len(sec)),
        "security_precision": sp,
        "security_recall": sr,
        "security_f1": f1(sp, sr),
        "security_latency_overhead_ms": float(cfg["security_process_ms"]) if bool(cfg["security"]) else 0.0,
    })
    for reason in ("RATE_LIMIT", "REPLAY", "DUPLICATE", "BURST", "CONSISTENCY_FAILURE", "DEBUG_RANDOM"):
        m[f"block_{reason.lower()}"] = int((blocked["sec_reason"] == reason).sum())
    # Real objects missed because an attack consumed the cooldown/rate budget
    # are visible as suppressed legit-object observations.
    m["legit_object_suppressed_cooldown"] = int(
        (obj & (df["suppress_reason"] == "COOLDOWN")).sum()) if not always_on else NAN

    # ------------------------------------------------------------------ communication
    sent = df[df["rpc_send_ms"] >= 0]
    m.update(dist_stats((sent["rpc_channel_wait_ms"] + sent["rpc_tx_ms"]).values, "rpc_latency_ms"))
    dq = df[df["queue_delay_ms"] >= 0]
    m.update(dist_stats(dq["queue_delay_ms"].values, "queue_delay_ms"))
    m["rpc_sent"] = int(len(sent))
    m["rpc_drops_loss"] = int((df["rpc_status"] == "lost").sum())
    m["rpc_drops_queue_full"] = int((df["rpc_status"] == "queue_full").sum())
    m["rpc_drops"] = m["rpc_drops_loss"] + m["rpc_drops_queue_full"]
    m["negative_queue_delay_count"] = int((dq["queue_delay_ms"] < 0).sum())

    # ------------------------------------------------------------------ energy (modeled)
    e_total = float(states["energy_mJ"].sum())
    for _, row in states.iterrows():
        m[f"time_{row['state']}_ms"] = float(row["time_ms"])
        m[f"energy_{row['state']}_mJ"] = float(row["energy_mJ"])
    m["energy_m4_mJ"] = float(states.loc[states["core"] == "M4", "energy_mJ"].sum())
    m["energy_m7_mJ"] = float(states.loc[states["core"] == "M7", "energy_mJ"].sum())
    m["energy_total_mJ"] = e_total
    m["energy_per_min_mJ"] = sdiv(e_total, minutes)
    m["energy_per_observation_mJ"] = sdiv(e_total, len(df))
    m["energy_per_accepted_trigger_mJ"] = sdiv(e_total, (df["rpc_status"] == "delivered").sum()) if not always_on else NAN
    m["energy_per_useful_detection_mJ"] = sdiv(e_total, useful.sum())
    m["energy_per_correct_detection_mJ"] = sdiv(e_total, tp_frame.sum())
    m["security_energy_mJ"] = float(states.loc[states["state"] == "SECURITY_PROCESSING", "energy_mJ"].sum())
    m["energy_summary_check_mJ"] = float(summary["energy_mJ"])
    m["state_time_m4_ms"] = float(states.loc[states["core"] == "M4", "time_ms"].sum())
    m["state_time_m7_ms"] = float(states.loc[states["core"] == "M7", "time_ms"].sum())
    return m


def main() -> int:
    if len(sys.argv) < 2:
        print(__doc__)
        return 1
    metrics = compute_run_metrics(sys.argv[1])
    print(json.dumps(metrics, indent=2, default=lambda x: None if isinstance(x, float) and math.isnan(x) else x))
    return 0


if __name__ == "__main__":
    sys.exit(main())
