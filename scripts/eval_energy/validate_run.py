#!/usr/bin/env python3
"""Structural validation of one simulator run.

Checks (each returns pass/fail with a count of violations):
  jsonl_valid            every event-log line is valid JSON with t and ev
  time_monotonic         event-log timestamps never decrease
  no_event_after_end     nothing is logged after SIM_END
  wake_sleep_paired      every WAKE has exactly one following SLEEP
  no_overlap_active      M7 active windows do not overlap
  blocked_never_wakes    a SECURITY_BLOCK event never reaches RPC/M7
  trigger_result_map     every RESULT belongs to an event that was triggered
                         and accepted (event modes) and appears at most once
  event_ids_consistent   event ids in the log exist in the workload records
  nonnegative_latency    no negative trigger/onset latency
  nonnegative_queue      no negative queue delay
  no_artificial_loss     rpc_loss == 0 implies no LOSS drops
  state_time_sums        per-core state times sum to the simulated duration
  energy_consistent      states.csv energy equals summary.json energy

Usage: python3 scripts/eval_energy/validate_run.py <run_dir>
"""
from __future__ import annotations

import gzip
import json
import os
import sys
from typing import Dict, List, Tuple

import pandas as pd

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from metrics import find_file, load_observations  # noqa: E402


def _open(path: str):
    return gzip.open(path, "rt") if path.endswith(".gz") else open(path)


def validate_run(run_dir: str) -> Dict[str, Tuple[bool, int, str]]:
    res: Dict[str, Tuple[bool, int, str]] = {}
    with open(os.path.join(run_dir, "summary.json")) as fh:
        summary = json.load(fh)
    with open(os.path.join(run_dir, "config.json")) as fh:
        cfg = json.load(fh)
    T = float(summary["seconds"]) * 1000.0
    df = load_observations(run_dir)
    ids = set(df["event_id"].tolist())

    events: List[dict] = []
    bad_json = 0
    log_path = None
    try:
        log_path = find_file(run_dir, "events.jsonl")
    except FileNotFoundError:
        pass
    if log_path:
        with _open(log_path) as fh:
            for line in fh:
                try:
                    e = json.loads(line)
                    if "t" not in e or "ev" not in e:
                        bad_json += 1
                    else:
                        events.append(e)
                except json.JSONDecodeError:
                    bad_json += 1
    res["jsonl_valid"] = (bad_json == 0, bad_json, f"{len(events)} lines")

    nonmono = sum(1 for a, b in zip(events, events[1:]) if b["t"] < a["t"] - 1e-9)
    res["time_monotonic"] = (nonmono == 0, nonmono, "")

    after_end = 0
    seen_end = False
    for e in events:
        if seen_end:
            after_end += 1
        if e["ev"] == "SIM_END":
            seen_end = True
        if e["t"] > T + 1e-6:
            after_end += 1
    res["no_event_after_end"] = (after_end == 0 and (seen_end or not events), after_end, "")

    depth, unpaired = 0, 0
    for e in events:
        if e["ev"] == "WAKE":
            if depth != 0:
                unpaired += 1
            depth += 1
        elif e["ev"] == "SLEEP":
            if depth != 1:
                unpaired += 1
            depth = max(0, depth - 1)
    unpaired += depth
    wakes = pd.read_csv(os.path.join(run_dir, "wake_intervals.csv"))
    if events:
        n_w = sum(1 for e in events if e["ev"] == "WAKE")
        n_s = sum(1 for e in events if e["ev"] == "SLEEP")
        unpaired += abs(n_w - n_s) + abs(n_w - len(wakes))
    res["wake_sleep_paired"] = (unpaired == 0, unpaired, f"{len(wakes)} active windows")

    w = wakes.sort_values("wake_ms").values
    overlap = sum(1 for i in range(1, len(w)) if w[i][0] < w[i - 1][1] - 1e-9)
    overlap += int((wakes["active_ms"] < 0).sum())
    res["no_overlap_active"] = (overlap == 0, overlap, "")

    blocked_ids = {e["event_id"] for e in events if e["ev"] == "SECURITY_BLOCK"}
    downstream = {"RPC_SEND", "RPC_RECEIVE", "RPC_ENQUEUE", "RPC_DEQUEUE", "DETECT_START", "RESULT", "WAKE"}
    leak = sum(1 for e in events if e["ev"] in downstream and e.get("event_id") in blocked_ids)
    blk_rec = df[df["sec_evaluated"] & ~df["sec_accept"]]
    leak += int((blk_rec["started"] | blk_rec["caused_wake"] | (blk_rec["rpc_send_ms"] >= 0)).sum())
    res["blocked_never_wakes"] = (leak == 0, leak, f"{len(blk_rec)} blocked")

    bad_map = 0
    result_ids = [e["event_id"] for e in events if e["ev"] == "RESULT"]
    bad_map += len(result_ids) - len(set(result_ids))
    if summary["mode"] != "always_on":
        trig = set(df.loc[df["triggered"], "event_id"])
        bad_map += sum(1 for i in result_ids if i not in trig)
        proc = df[df["processed"]]
        bad_map += int((~proc["triggered"]).sum())
        if bool(cfg["security"]):
            bad_map += int((~proc["sec_accept"]).sum())
    res["trigger_result_map"] = (bad_map == 0, bad_map, f"{len(result_ids)} results")

    unknown = sum(1 for e in events if "event_id" in e and e["event_id"] not in ids)
    res["event_ids_consistent"] = (unknown == 0, unknown, "")

    dl = df["result_delivered_ms"] >= 0
    neg = int(((df.loc[dl, "result_delivered_ms"] - df.loc[dl, "timestamp_ms"]) < -1e-9).sum())
    dd = dl & (df["decision_ms"] >= 0)
    neg += int(((df.loc[dd, "result_delivered_ms"] - df.loc[dd, "decision_ms"]) < -1e-9).sum())
    res["nonnegative_latency"] = (neg == 0, neg, "")

    negq = int((df.loc[df["dequeue_ms"] >= 0, "queue_delay_ms"] < -1e-9).sum())
    res["nonnegative_queue"] = (negq == 0, negq, "")

    loss = int((df["rpc_status"] == "lost").sum())
    ok_loss = loss == 0 if float(cfg["rpc_loss"]) == 0.0 else True
    res["no_artificial_loss"] = (ok_loss, loss if not ok_loss else 0, f"rpc_loss={cfg['rpc_loss']}")

    st = pd.read_csv(os.path.join(run_dir, "states.csv"))
    err = 0
    for core in ("M4", "M7"):
        tot = st.loc[st["core"] == core, "time_ms"].sum()
        if abs(tot - T) > 1e-3 * max(1.0, len(st)):
            err += 1
    res["state_time_sums"] = (err == 0, err, "")

    e_sum = float(st["energy_mJ"].sum())
    ok_e = abs(e_sum - float(summary["energy_mJ"])) <= 1e-3 * max(1.0, abs(e_sum)) * 1e-3 + 0.01
    res["energy_consistent"] = (ok_e, 0 if ok_e else 1, f"{e_sum:.3f} mJ")
    return res


def main() -> int:
    if len(sys.argv) < 2:
        print(__doc__)
        return 1
    res = validate_run(sys.argv[1])
    ok = True
    for k, (passed, n, note) in res.items():
        print(f"{'PASS' if passed else 'FAIL'}  {k:24s} violations={n} {note}")
        ok &= passed
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
