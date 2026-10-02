#!/usr/bin/env python3
"""Integration / regression tests for the simulator and evaluation pipeline.

The test names map one-to-one onto the required test list in
docs/EXPERIMENT_PROTOCOL.md (section "Test suite"). Run with:

    python3 -m unittest discover -s tests -v
"""
from __future__ import annotations

import gzip
import json
import os
import shutil
import subprocess
import sys
import tempfile
import unittest

import pandas as pd

REPO = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
BIN = os.path.join(REPO, "build", "edge_sim")
CFG = os.path.join(REPO, "config", "default_config.json")
sys.path.insert(0, os.path.join(REPO, "scripts", "eval_energy"))
from metrics import compute_run_metrics, load_observations  # noqa: E402
from stats import holm, paired_test  # noqa: E402
from validate_run import validate_run  # noqa: E402

MODES = ["always_on", "motion_only", "fixed_threshold", "event", "event_no_early_exit", "secure"]
GT_COLS = ["event_id", "episode_id", "episode_type", "timestamp_ms", "duration_ms", "is_legitimate",
           "object_present", "object_class", "attack_type", "replay_id", "burst_id", "ground_truth_action",
           "frame_has_object", "frame_object_class"]


def sim(*args, cwd=REPO):
    r = subprocess.run([BIN, *map(str, args)], cwd=cwd, capture_output=True, text=True)
    if r.returncode != 0:
        raise RuntimeError(r.stderr)
    return r.stdout


def gen(path, scenario="mixed", seed=1, seconds=600, *extra):
    sim("--config", CFG, "--scenario", scenario, "--seed", seed, "--seconds", seconds,
        "--save-workload", path, "--generate-only", *extra)
    return path


def run(wl, out, mode, *extra):
    sim("--config", CFG, "--mode", mode, "--workload", wl, "--out-dir", out, *extra)
    return out


def load_json(p):
    with open(p) as fh:
        return json.load(fh)


def read_bytes(p):
    with open(p, "rb") as fh:
        return fh.read()


class PipelineTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        if not os.path.exists(BIN):
            raise unittest.SkipTest("build/edge_sim missing; build first")
        cls.tmp = tempfile.mkdtemp(prefix="edge_sim_test_")
        cls.wl = gen(os.path.join(cls.tmp, "mixed.jsonl"), "mixed", 4, 1800)
        cls.runs = {m: run(cls.wl, os.path.join(cls.tmp, m), m) for m in MODES}

    @classmethod
    def tearDownClass(cls):
        shutil.rmtree(cls.tmp, ignore_errors=True)

    # 1
    def test_01_same_seed_identical_workload(self):
        for sc in ("normal", "trigger_spam", "replay", "burst"):
            a = gen(os.path.join(self.tmp, f"{sc}_a.jsonl"), sc, 9, 900)
            b = gen(os.path.join(self.tmp, f"{sc}_b.jsonl"), sc, 9, 900)
            self.assertEqual(read_bytes(a), read_bytes(b), sc)
            c = gen(os.path.join(self.tmp, f"{sc}_c.jsonl"), sc, 10, 900)
            self.assertNotEqual(read_bytes(a), read_bytes(c), sc)

    # 2
    def test_02_same_workload_identical_ground_truth_every_mode(self):
        ref = load_observations(self.runs["always_on"])[GT_COLS]
        wl = pd.read_json(self.wl, lines=True)
        self.assertEqual(len(ref), len(wl))
        for m in MODES:
            df = load_observations(self.runs[m])[GT_COLS]
            pd.testing.assert_frame_equal(df, ref, check_dtype=False)
            with open(os.path.join(self.runs[m], "summary.json")) as fh:
                self.assertEqual(json.load(fh)["workload_hash_fnv1a64"],
                                 load_json(self.wl + ".meta.json")["workload_hash_fnv1a64"])

    # 3
    def test_03_simulator_deterministic(self):
        for m in ("secure", "always_on"):
            out2 = run(self.wl, os.path.join(self.tmp, f"{m}_again"), m)
            for f in ("events.jsonl", "observations.csv", "states.csv", "wake_intervals.csv", "summary.json"):
                self.assertEqual(read_bytes(os.path.join(self.runs[m], f)), read_bytes(os.path.join(out2, f)), f)
        # Internal generation == replay of the saved workload.
        out3 = os.path.join(self.tmp, "secure_internal")
        sim("--config", CFG, "--mode", "secure", "--scenario", "mixed", "--seed", 4, "--seconds", 1800,
            "--out-dir", out3)
        self.assertEqual(read_bytes(os.path.join(self.runs["secure"], "observations.csv")),
                         read_bytes(os.path.join(out3, "observations.csv")))

    # 4
    def test_04_security_cannot_modify_ground_truth(self):
        on = load_observations(self.runs["secure"])[GT_COLS]
        off = load_observations(self.runs["event"])[GT_COLS]
        pd.testing.assert_frame_equal(on, off)
        wl_before = read_bytes(self.wl)
        run(self.wl, os.path.join(self.tmp, "sec2"), "secure")
        self.assertEqual(wl_before, read_bytes(self.wl))

    # 5
    def test_05_blocked_trigger_never_wakes_m7(self):
        df = load_observations(self.runs["secure"])
        blk = df[df["sec_evaluated"] & ~df["sec_accept"]]
        self.assertGreater(len(blk), 0)
        self.assertFalse((blk["started"] | blk["caused_wake"] | blk["processed"]).any())
        self.assertTrue((blk["rpc_send_ms"] < 0).all())
        self.assertTrue(validate_run(self.runs["secure"])["blocked_never_wakes"][0])

    # 6, 7, 8, 9, 13 (structural log checks)
    def test_06_to_13_structural_validation(self):
        for m in MODES:
            res = validate_run(self.runs[m])
            for check in ("wake_sleep_paired", "no_overlap_active", "trigger_result_map", "event_ids_consistent",
                          "no_event_after_end", "jsonl_valid", "time_monotonic", "state_time_sums"):
                self.assertTrue(res[check][0], f"{m}: {check} {res[check]}")

    # 9 explicitly: ids consistent through the pipeline
    def test_09_event_ids_consistent(self):
        df = load_observations(self.runs["secure"])
        ids = set(df["event_id"])
        with open(os.path.join(self.runs["secure"], "events.jsonl")) as fh:
            per_id = {}
            for line in fh:
                e = json.loads(line)
                if "event_id" in e:
                    self.assertIn(e["event_id"], ids)
                    per_id.setdefault(e["event_id"], []).append(e["ev"])
        order = ["TRIGGER", "SECURITY_ACCEPT", "RPC_SEND", "RPC_RECEIVE", "RPC_ENQUEUE", "RPC_DEQUEUE",
                 "DETECT_START", "RESULT", "RESULT_DELIVERED"]
        for eid, evs in per_id.items():
            if "RESULT_DELIVERED" in evs:
                pos = [evs.index(x) for x in order]
                self.assertEqual(pos, sorted(pos), eid)

    # 10
    def test_10_energy_integration(self):
        for m in MODES:
            st = pd.read_csv(os.path.join(self.runs[m], "states.csv"))
            pm = load_json(os.path.join(REPO, "config", "power_model.json"))["states"]
            e = sum(r["time_ms"] * pm[r["state"]]["power_mW"] / 1000.0 for _, r in st.iterrows())
            summ = load_json(os.path.join(self.runs[m], "summary.json"))
            self.assertAlmostEqual(e, summ["energy_mJ"], delta=1e-3)
            self.assertAlmostEqual(st[st["core"] == "M4"]["time_ms"].sum(), 1800000.0, delta=1e-3)
            self.assertAlmostEqual(st[st["core"] == "M7"]["time_ms"].sum(), 1800000.0, delta=1e-3)

    # 11, 12
    def test_11_12_no_negative_latency_or_queue_delay(self):
        for m in MODES:
            met = compute_run_metrics(self.runs[m])
            self.assertEqual(met["negative_latency_count"], 0, m)
            self.assertEqual(met["negative_queue_delay_count"], 0, m)
        # Stress the queue: no cooldown and slow inference.
        out = run(self.wl, os.path.join(self.tmp, "stress"), "event", "--cooldown-ms", 0, "--inference-ms", 900,
                  "--rpc-queue-capacity", 2)
        met = compute_run_metrics(out)
        self.assertEqual(met["negative_queue_delay_count"], 0)
        self.assertGreater(met["queue_delay_ms_max"], 0.0)
        self.assertTrue(all(v[0] for v in validate_run(out).values()))

    # 14
    def test_14_workload_duration_obeyed(self):
        wl = pd.read_json(self.wl, lines=True)
        self.assertTrue(((wl["timestamp_ms"] + wl["duration_ms"]) <= 1800000.0 + 1e-6).all())
        self.assertTrue((wl["timestamp_ms"] >= 0).all())

    # 15
    def test_15_always_on_duty_100(self):
        met = compute_run_metrics(self.runs["always_on"])
        self.assertAlmostEqual(met["duty_cycle"], 1.0, places=9)

    # 16
    def test_16_empty_workload(self):
        p = os.path.join(self.tmp, "empty.jsonl")
        open(p, "w").close()
        out = os.path.join(self.tmp, "empty_run")
        sim("--config", CFG, "--mode", "secure", "--workload", p, "--seconds", 60, "--out-dir", out)
        met = compute_run_metrics(out)
        self.assertEqual(met["observations"], 0)
        self.assertEqual(met["wakeups"], 0)
        self.assertTrue(all(v[0] for v in validate_run(out).values()))

    # 17
    def test_17_zero_attacks(self):
        wl = gen(os.path.join(self.tmp, "zero_att.jsonl"), "trigger_spam", 2, 900, "--attack-intensity", 0)
        out = run(wl, os.path.join(self.tmp, "zero_att"), "secure")
        met = compute_run_metrics(out)
        self.assertEqual(met["attack_attempts"], 0)
        self.assertTrue(pd.isna(met["attack_success_rate"]))
        self.assertTrue(all(v[0] for v in validate_run(out).values()))

    # 18
    def test_18_all_attack_workload(self):
        wl = pd.read_json(gen(os.path.join(self.tmp, "spam.jsonl"), "trigger_spam", 2, 1800,
                              "--attack-intensity", 6), lines=True)
        att = wl[wl["is_legitimate"] == False].copy()  # noqa: E712
        att["event_id"] = range(1, len(att) + 1)
        att["replay_id"] = -1
        p = os.path.join(self.tmp, "all_attack.jsonl")
        with open(p, "w") as fh:
            for rec in att.to_dict("records"):
                fh.write(json.dumps(rec) + "\n")
        for m in ("event", "secure", "always_on"):
            out = os.path.join(self.tmp, f"all_attack_{m}")
            sim("--config", CFG, "--mode", m, "--workload", p, "--seconds", 1800, "--seed", 2, "--out-dir", out)
            met = compute_run_metrics(out)
            self.assertEqual(met["legit_observations"], 0)
            self.assertGreater(met["attack_attempts"], 0)
            self.assertTrue(all(v[0] for v in validate_run(out).values()), m)

    # 19
    def test_19_zero_loss_no_artificial_drops(self):
        for m in MODES:
            met = compute_run_metrics(self.runs[m])
            self.assertEqual(met["rpc_drops_loss"], 0, m)
        out = run(self.wl, os.path.join(self.tmp, "lossy"), "event", "--rpc-loss", 0.2)
        self.assertGreater(compute_run_metrics(out)["rpc_drops_loss"], 0)

    # 20
    def test_20_csv_expected_columns(self):
        df = pd.read_csv(os.path.join(self.runs["secure"], "observations.csv"))
        for c in GT_COLS + ["score", "threshold", "triggered", "sec_reason", "rpc_status", "queue_delay_ms",
                            "early_exit", "second_pass", "detected", "result_delivered_ms"]:
            self.assertIn(c, df.columns)
        st = pd.read_csv(os.path.join(self.runs["secure"], "states.csv"))
        self.assertEqual(list(st.columns), ["core", "state", "time_ms", "power_mW", "energy_mJ"])
        self.assertEqual(len(st), 11)
        wl = pd.read_json(self.wl, lines=True)
        for c in ["event_id", "timestamp_ms", "duration_ms", "scenario", "is_legitimate", "object_present",
                  "object_class", "motion_score", "visual_score", "temporal_change_score",
                  "sensor_consistency_score", "noise_score", "attack_type", "replay_id", "burst_id",
                  "ground_truth_action"]:
            self.assertIn(c, wl.columns)

    # Extra: research mode never uses random blocking; debug flag is marked invalid.
    def test_21_no_random_blocking_in_research_mode(self):
        cfg = load_json(os.path.join(self.runs["secure"], "config.json"))
        self.assertEqual(cfg["debug_random_block_prob"], 0)
        self.assertNotIn("DEBUG_random_block", cfg["ablations"])
        met = compute_run_metrics(self.runs["secure"])
        self.assertEqual(met["block_debug_random"], 0)
        self.assertTrue(met["research_valid"])
        out = run(self.wl, os.path.join(self.tmp, "dbg"), "secure", "--debug-random-block-prob", 0.5)
        self.assertFalse(load_json(os.path.join(out, "summary.json"))["research_valid"])

    # Extra: gzip-compressed outputs are read identically.
    def test_22_gzip_outputs_readable(self):
        d = os.path.join(self.tmp, "gz")
        shutil.copytree(self.runs["secure"], d)
        for f in ("events.jsonl", "observations.csv"):
            with open(os.path.join(d, f), "rb") as src, gzip.open(os.path.join(d, f + ".gz"), "wb") as dst:
                dst.write(src.read())
            os.remove(os.path.join(d, f))
        a, b = compute_run_metrics(self.runs["secure"]), compute_run_metrics(d)
        self.assertEqual(a["energy_total_mJ"], b["energy_total_mJ"])
        self.assertEqual(a["attacks_blocked"], b["attacks_blocked"])

    # Extra: statistics helpers.
    def test_23_statistics(self):
        r = paired_test([1, 2, 3, 4, 5, 6, 7, 8], [0, 1, 2, 3, 4, 5, 6, 7])
        self.assertAlmostEqual(r["rank_biserial"], 1.0)
        self.assertLess(r["p_value"], 0.01)
        r0 = paired_test([1, 1, 1], [1, 1, 1])
        self.assertTrue(pd.isna(r0["p_value"]))
        self.assertEqual(holm([0.01, 0.04, 0.03]), [0.03, 0.06, 0.06])

    # Extra: trace_replay backend consumes an external trace without
    # architectural changes. The trace here is TEST DATA ONLY.
    def test_24_trace_replay_backend(self):
        wl = pd.read_json(self.wl, lines=True)
        p = os.path.join(self.tmp, "trace.csv")
        with open(p, "w") as fh:
            fh.write("# TEST DATA ONLY\nevent_id,ground_truth_class,predicted_class,confidence,inference_ms,"
                     "postprocess_ms,num_boxes,correct,second_pass_confidence,second_pass_predicted_class,"
                     "second_pass_ms\n")
            for i, r in wl.iterrows():
                conf = 0.9 if i % 2 else 0.5
                fh.write(f"{r.event_id},{r.frame_object_class},{r.frame_object_class},{conf},100,5,1,1,"
                         f"0.95,{r.frame_object_class},80\n")
        out = run(self.wl, os.path.join(self.tmp, "trace_run"), "secure", "--detector-backend", "trace_replay",
                  "--detector-trace", p)
        df = load_observations(out)
        proc = df[df["processed"]]
        self.assertGreater(len(proc), 0)
        self.assertTrue((proc.loc[proc["s1_conf"] >= 0.8, "early_exit"]).all())
        self.assertTrue((proc.loc[proc["s1_conf"] < 0.8, "second_pass"]).all())
        self.assertTrue(((proc["s1_ms"] - 100).abs() < 1e-6).all())
        self.assertTrue(all(v[0] for v in validate_run(out).values()))

    def test_25_map_only_with_boxes(self):
        from map_eval import compute_map
        df = pd.read_csv(os.path.join(REPO, "data", "detector_traces", "example_trace_SCHEMA_ONLY.csv"), comment="#")
        res = compute_map(df)
        self.assertTrue(0.0 <= res["map50"] <= 1.0)
        perfect = pd.DataFrame({"event_id": [1, 2], "ground_truth_class": ["person", "person"],
                                "predicted_class": ["person", "person"], "confidence": [0.9, 0.8],
                                "gt_x": [0, 50], "gt_y": [0, 50], "gt_w": [10, 10], "gt_h": [10, 10],
                                "pred_x": [0, 50], "pred_y": [0, 50], "pred_w": [10, 10], "pred_h": [10, 10]})
        self.assertAlmostEqual(compute_map(perfect)["map50"], 1.0)
        with self.assertRaises(ValueError):
            compute_map(pd.DataFrame({"event_id": [1], "ground_truth_class": ["person"]}))
        met = compute_run_metrics(self.runs["secure"])
        self.assertTrue(pd.isna(met["map50"]))


if __name__ == "__main__":
    unittest.main(verbosity=2)
