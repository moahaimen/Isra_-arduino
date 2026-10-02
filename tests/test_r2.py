"""R2 tests: detector trace V2, standard IoU/mAP, real-frame features
(Python reference vs C++ port), R2 simulator modes, label isolation,
determinism, and validation/test isolation of the frozen R2 configuration.

Tests that need the downloaded datasets/image bank (R2_DATA, default
/home/claude/data_r2) are skipped when the data are absent; every other test
is self-contained.
"""
from __future__ import annotations

import hashlib
import io
import json
import os
import subprocess
import sys
import tempfile
import unittest

import numpy as np
import pandas as pd

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
sys.path.insert(0, os.path.join(ROOT, "scripts", "detector"))
sys.path.insert(0, os.path.join(ROOT, "scripts", "r2"))
import coco_eval  # noqa: E402
import frame_features as ff  # noqa: E402
import trace_v2  # noqa: E402

SIM = os.path.join(ROOT, "build", "edge_sim")
FEAT = os.path.join(ROOT, "build", "r2_features")
DATA = os.environ.get("R2_DATA", "/home/claude/data_r2")
HAVE_BANK = os.path.exists(os.path.join(DATA, "bank", "bank_development.npz"))


def box_frames(n=2, w=100, h=100):
    return pd.DataFrame({"event_id": list(range(1, n + 1)), "frame_id": list(range(1, n + 1)),
                         "source_sequence": "t", "timestamp_ms": 0.0, "image_path": "x", "width": w, "height": h,
                         "split": "test"})


def gt_rows(rows):
    return pd.DataFrame(rows, columns=["event_id", "gt_id", "class_id", "class_name", "x1", "y1", "x2", "y2",
                                       "ignore"])


def pred_rows(rows):
    df = pd.DataFrame(rows, columns=["event_id", "prediction_id", "class_id", "class_name", "confidence", "x1", "y1",
                                     "x2", "y2"])
    df["host_inference_ms"] = 1.0
    df["host_postprocess_ms"] = 0.1
    df["detector_name"] = "unit"
    df["model_hash"] = "0" * 64
    return df


class TraceAndMapTests(unittest.TestCase):
    def test_multibox_trace_roundtrip(self):
        fr = box_frames(2)
        gt = gt_rows([(1, 1, 1, "a", 0, 0, 10, 10, 0), (1, 2, 2, "b", 20, 20, 40, 40, 0),
                      (1, 3, 1, "a", 50, 50, 60, 60, 1), (2, 1, 2, "b", 5, 5, 15, 25, 0)])
        pr = pred_rows([(1, 1, 1, "a", 0.9, 0, 0, 10, 10), (1, 2, 2, "b", 0.8, 20, 20, 40, 40),
                        (1, 3, 1, "a", 0.3, 70, 70, 80, 80), (2, 1, 2, "b", 0.7, 5, 5, 15, 25)])
        with tempfile.TemporaryDirectory() as d:
            man = trace_v2.write_trace(d, fr, gt, pr, {"m": 1}, {"x": 1})
            self.assertEqual(man["n_gt_boxes"], 4)
            self.assertEqual(man["n_predicted_boxes"], 4)
            t = trace_v2.read_trace(d)
            self.assertEqual(len(t.gt[t.gt.event_id == 1]), 3)
            self.assertEqual(len(t.pred[t.pred.event_id == 1]), 3)
            # tampering is detected through the manifest hashes
            with open(os.path.join(d, "predictions.csv"), "a") as fh:
                fh.write("2,9,1,a,0.5,1,1,2,2,1,0.1,unit," + "0" * 64 + "\n")
            with self.assertRaises(ValueError):
                trace_v2.read_trace(d)

    def test_trace_validation(self):
        fr = box_frames(1)
        gt = gt_rows([(1, 1, 1, "a", 10, 10, 5, 20, 0)])  # degenerate
        errs = trace_v2.validate(fr, gt, pred_rows([]))
        self.assertTrue(any("degenerate" in e for e in errs))
        dup = pred_rows([(1, 1, 1, "a", 0.5, 0, 0, 1, 1), (1, 1, 1, "a", 0.5, 0, 0, 1, 1)])
        self.assertTrue(any("duplicated" in e for e in trace_v2.validate(fr, gt_rows([]), dup)))

    def test_iou(self):
        self.assertAlmostEqual(coco_eval.iou_xyxy((0, 0, 10, 10), (0, 0, 10, 10)), 1.0)
        self.assertAlmostEqual(coco_eval.iou_xyxy((0, 0, 10, 10), (5, 0, 15, 10)), 50 / 150)
        self.assertEqual(coco_eval.iou_xyxy((0, 0, 10, 10), (20, 20, 30, 30)), 0.0)

    def test_one_to_one_matching(self):
        gt = gt_rows([(1, 1, 1, "a", 0, 0, 10, 10, 0)])
        pr = pred_rows([(1, 1, 1, "a", 0.9, 0, 0, 10, 10), (1, 2, 1, "a", 0.8, 0, 0, 10, 11)])
        self.assertEqual(coco_eval.match_frame(gt, pr), (1, 1, 0))  # duplicate detection = FP
        pr2 = pred_rows([(1, 1, 2, "b", 0.9, 0, 0, 10, 10)])
        self.assertEqual(coco_eval.match_frame(gt, pr2), (0, 1, 1))  # wrong class
        ign = gt_rows([(1, 1, 1, "a", 0, 0, 10, 10, 1)])
        self.assertEqual(coco_eval.match_frame(ign, pr), (0, 0, 0))  # ignore region: neither TP nor FP

    def test_map_known_values(self):
        fr = box_frames(1)
        gt = gt_rows([(1, 1, 1, "a", 0, 0, 10, 10, 0), (1, 2, 1, "a", 50, 50, 70, 70, 0)])
        perfect = pred_rows([(1, 1, 1, "a", 0.9, 0, 0, 10, 10), (1, 2, 1, "a", 0.8, 50, 50, 70, 70)])
        r = coco_eval.coco_map(fr, gt, perfect, {1: "a"})
        self.assertAlmostEqual(r["mAP50"], 1.0, places=6)
        self.assertAlmostEqual(r["mAP50_95"], 1.0, places=6)
        half = pred_rows([(1, 1, 1, "a", 0.9, 0, 0, 10, 10)])
        r = coco_eval.coco_map(fr, gt, half, {1: "a"})
        # 101-point interpolation: precision 1 for recall in [0, 0.5], 0 above
        self.assertAlmostEqual(r["mAP50"], 51 / 101, places=6)
        # a box at IoU 0.6 counts at thresholds 0.50..0.60 only (3 of 10)
        shifted = pred_rows([(1, 1, 1, "a", 0.9, 0, 0, 10, 10), (1, 2, 1, "a", 0.8, 50, 50, 70, 75)])
        iou = coco_eval.iou_xyxy((50, 50, 70, 75), (50, 50, 70, 70))
        r = coco_eval.coco_map(fr, gt, shifted, {1: "a"})
        n_ok = sum(iou >= t - 1e-9 for t in np.linspace(0.5, 0.95, 10))
        expected = (n_ok * 1.0 + (10 - n_ok) * 51 / 101) / 10
        self.assertAlmostEqual(r["mAP50_95"], expected, places=6)
        op = coco_eval.operating_point(fr, gt, half, 0.5)
        self.assertEqual((op["TP"], op["FP"], op["FN"]), (1, 0, 1))
        self.assertAlmostEqual(op["F1"], 2 / 3)


@unittest.skipUnless(os.path.exists(FEAT), "build/r2_features not built")
class FrameFeatureTests(unittest.TestCase):
    def _frames(self, n=40, seed=0):
        rng = np.random.default_rng(seed)
        base = rng.integers(40, 200, (32, 96)).astype(np.float64)
        out = []
        for i in range(n):
            L = base.copy()
            x = 5 + 2 * i
            if x + 6 < 96:
                L[10:20, x:x + 6] = 250  # a moving bright object
            if i % 7 == 3:
                L *= 0.7  # illumination flicker
            L = np.clip(L + rng.normal(0, 2, L.shape), 0, 255).astype(np.uint8)
            F = np.clip(rng.integers(0, 255, (16, 17)), 0, 255).astype(np.uint8)
            out.append((L, F))
        return out

    def test_cpp_port_matches_python(self):
        frames = self._frames()
        with tempfile.NamedTemporaryFile(suffix=".bin", delete=False) as fh:
            for L, F in frames:
                fh.write(L.tobytes() + F.tobytes())
            path = fh.name
        try:
            for typ, tol in (("double", 1e-9), ("float", 1e-5)):
                out = subprocess.run([FEAT, path, str(len(frames)), typ], capture_output=True, text=True,
                                     check=True).stdout
                c = pd.read_csv(io.StringIO(out), dtype={"motion_cells": str, "fg": str, "fp": str, "sig64": str})
                st = ff.FeatureState()
                for i, (L, F) in enumerate(frames):
                    p = ff.step(st, L, F)
                    for a, b in (("motion", "motion_score"), ("temporal", "temporal_change_score"),
                                 ("visual", "visual_score"), ("edge_change", "edge_change_score"),
                                 ("consistency", "sensor_consistency_score"), ("noise", "noise_score"),
                                 ("r2_motion", "r2_motion"), ("r2_temporal", "r2_temporal"),
                                 ("r2_visual", "r2_visual"), ("r2_consistency", "r2_consistency"), ("gain", "gain")):
                        self.assertAlmostEqual(c[a][i], p[b], delta=tol, msg=f"{typ} frame {i} {a}")
                    self.assertEqual(int(c.motion_cells[i], 16), p["motion_cells"])
                    self.assertEqual(c.fg[i], "".join(f"{w:016x}" for w in p["fg"]))
                    self.assertEqual(c.fp[i], "".join(f"{w:016x}" for w in p["fp"]))
                    self.assertEqual(int(c.sig64[i], 16), p["sig64"])
        finally:
            os.remove(path)

    def test_gain_compensation_suppresses_flicker(self):
        rng = np.random.default_rng(1)
        base = rng.integers(40, 200, (32, 96)).astype(np.float64)
        st = ff.FeatureState()
        F = np.zeros((16, 17), np.uint8)
        for _ in range(10):
            ff.step(st, base.astype(np.uint8), F)
        f = ff.step(st, np.clip(base * 0.7, 0, 255).astype(np.uint8), F)
        self.assertGreater(f["motion_score"], 0.9)   # basic front end: flicker looks like motion
        self.assertLess(f["r2_motion"], 0.2)         # compensated front end: it does not
        self.assertAlmostEqual(f["gain"], 1 / 0.7, delta=0.05)

    def test_features_never_read_labels(self):
        import inspect
        src = inspect.getsource(ff)
        for word in ("ground_truth", "track_id", "attack", "confidence", "class_id"):
            self.assertNotIn(word, src)


def r2_obs(eid, t, m, cells, fg_bits, fp0=1, attack="none", legit=True, gt_action="ignore"):
    fg = [0] * 12
    for b in fg_bits:
        fg[b // 64] |= 1 << (63 - b % 64)
    return {"event_id": eid, "timestamp_ms": t, "duration_ms": 100.0, "scenario": "clean", "episode_id": -1,
            "episode_type": "attack" if attack != "none" else "object", "is_legitimate": legit,
            "object_present": gt_action == "detect", "object_class": "person" if gt_action == "detect" else "none",
            "motion_score": m, "visual_score": m, "temporal_change_score": m, "sensor_consistency_score": 0.9,
            "noise_score": 0.1, "content_signature": f"{(eid * 2654435761) % (1 << 64):016x}",
            "attack_type": attack, "replay_id": -1, "burst_id": -1, "ground_truth_action": gt_action,
            "frame_has_object": gt_action == "detect", "frame_object_class": "person" if gt_action == "detect" else "none",
            "edge_change_score": m, "r2_motion": m, "r2_temporal": m, "r2_visual": m, "r2_consistency": 0.9,
            "mog2_fg": m / 10, "motion_cells": f"{cells:016x}", "fg_count": len(set(fg_bits)),
            "fp256": f"{fp0:016x}" + "0" * 48, "fg768": "".join(f"{w:016x}" for w in fg)}


def synthetic_r2_workload(path, n=300, flip_labels=False):
    """Objects appear at different cells, one is replayed 5 s later, plus a
    repeated flash. Labels can be flipped to check that decisions ignore them."""
    rows = []
    for i in range(n):
        t = i * 100.0
        m, cells, fg, attack, act = 0.02, 0, [], "none", "ignore"
        if 20 <= i < 40:
            m, cells, fg, act = 0.8, 1 << 3, list(range(100, 140)), "detect"
        if 60 <= i < 75:
            m, cells, fg, act = 0.8, 1 << 30, list(range(400, 450)), "detect"
        if 62 <= i < 70:
            cells |= 1 << 9
        if 100 <= i < 110:  # replay of frames 20..29
            m, cells, fg, attack, act = 0.8, 1 << 3, list(range(100, 140)), "replay", "block"
        if 150 <= i < 290 and i % 5 in (0, 1):  # repeated 2-frame flash at one place
            m, cells, fg, attack, act = 0.9, 1 << 40, list(range(700, 740)), "trigger_spam", "block"
        legit = attack == "none"
        if flip_labels:
            attack = {"none": "trigger_spam", "replay": "none", "trigger_spam": "none"}[attack]
            legit = not legit
            act = {"detect": "ignore", "ignore": "detect", "block": "detect"}[act]
        rows.append(r2_obs(i + 1, t, m, cells, fg, attack=attack, legit=legit, gt_action=act))
    with open(path, "w") as fh:
        for r in rows:
            fh.write(json.dumps(r) + "\n")
    with open(path + ".meta.json", "w") as fh:
        json.dump({"seed": 1, "seconds": n / 10.0, "scenario": "clean"}, fh)
    with open(os.path.join(os.path.dirname(path), "det.csv"), "w") as fh:
        fh.write("event_id,predicted_class,confidence,num_boxes,second_pass_confidence,"
                 "second_pass_predicted_class,second_pass_num_boxes\n")
        for i in range(n):
            c = 0.3 + 0.6 * ((i * 37) % 11) / 10
            fh.write(f"{i + 1},1,{c:.4f},1,{min(1.0, c + 0.1):.4f},1,1\n")


def run_sim(wl_dir, mode, extra=(), out=None):
    out = out or tempfile.mkdtemp(prefix="r2t_")
    cmd = [SIM, "--config", os.path.join(ROOT, "config", "default_config.json"), "--mode", mode, "--workload",
           os.path.join(wl_dir, "wl.jsonl"), "--detector-backend", "trace_replay", "--detector-trace",
           os.path.join(wl_dir, "det.csv"), "--trace-timing", "simulated", "--log-level", "decisions",
           "--out-dir", out] + list(extra)
    subprocess.run(cmd, cwd=ROOT, check=True, capture_output=True)
    return out


@unittest.skipUnless(os.path.exists(SIM), "build/edge_sim not built")
class R2SimulatorTests(unittest.TestCase):
    MODES = ["always_on", "motion_only", "fixed_threshold", "mog2_event", "event", "secure", "robust_event",
             "robust_secure"]

    @classmethod
    def setUpClass(cls):
        cls.tmp = tempfile.mkdtemp(prefix="r2wl_")
        os.makedirs(os.path.join(cls.tmp, "a"))
        os.makedirs(os.path.join(cls.tmp, "b"))
        synthetic_r2_workload(os.path.join(cls.tmp, "a", "wl.jsonl"))
        synthetic_r2_workload(os.path.join(cls.tmp, "b", "wl.jsonl"), flip_labels=True)
        cls.runs = {m: run_sim(os.path.join(cls.tmp, "a"), m) for m in cls.MODES}

    def obs(self, mode, which="a"):
        d = self.runs[mode] if which == "a" else run_sim(os.path.join(self.tmp, "b"), mode)
        return pd.read_csv(os.path.join(d, "observations.csv"), keep_default_na=False)

    def test_identical_detector_trace_across_modes(self):
        det = pd.read_csv(os.path.join(self.tmp, "a", "det.csv")).set_index("event_id")
        for m in self.MODES:
            o = self.obs(m)
            p = o[o.processed == 1]
            self.assertGreater(len(p), 0, m)
            for r in p.itertuples():
                self.assertAlmostEqual(r.s1_conf, det.loc[r.event_id, "confidence"], places=4)
                if r.second_pass == 1:
                    self.assertAlmostEqual(r.s2_conf, det.loc[r.event_id, "second_pass_confidence"], places=4)

    def test_decisions_blind_to_labels(self):
        # flipping every ground-truth / attack label leaves all decisions unchanged
        cols = ["score", "threshold", "triggered", "suppress_reason", "sec_evaluated", "sec_accept", "sec_reason",
                "processed", "s1_conf", "detect_start_ms", "watcher_z", "watcher_novel"]
        for m in ("event", "secure", "robust_event", "robust_secure"):
            a, b = self.obs(m), self.obs(m, "b")
            self.assertTrue((a.attack_type != b.attack_type).any())
            pd.testing.assert_frame_equal(a[cols], b[cols], check_exact=True, obj=m)

    def test_no_blocked_request_wakes_m7(self):
        for m in ("secure", "robust_secure"):
            o = self.obs(m)
            blk = o[(o.sec_evaluated == 1) & (o.sec_accept == 0)]
            self.assertGreater(len(blk), 0, m)
            self.assertTrue((blk.started == 0).all() and (blk.caused_wake == 0).all() and (blk.rpc_send_ms < 0).all())

    def test_robust_secure_blocks_replay_and_spam(self):
        o = self.obs("robust_secure")
        rep = o[(o.attack_type == "replay") & (o.sec_evaluated == 1)]
        self.assertGreater(len(rep), 0)
        self.assertTrue((rep.sec_accept == 0).all())
        self.assertTrue((rep.sec_reason == "REPLAY").all())
        spam = o[o.attack_type == "trigger_spam"]
        legit_obj = o[(o.ground_truth_action == "detect")]
        # spam is mostly suppressed (watcher content cooldown + gate buckets),
        # both legitimate objects still reach the M7
        self.assertLess(spam.started.mean(), 0.3)
        self.assertTrue(legit_obj[legit_obj.event_id.between(21, 40)].started.any())
        self.assertTrue(legit_obj[legit_obj.event_id.between(61, 75)].started.any())

    def test_multi_object_burst_triggers_each_object(self):
        o = self.obs("robust_event")
        t = o[(o.triggered == 1) & o.event_id.between(61, 75)]
        self.assertGreaterEqual(len(t), 2)  # second object (cell 9) triggers despite the first (cell 30)

    def test_determinism(self):
        for m in ("robust_secure", "secure"):
            d2 = run_sim(os.path.join(self.tmp, "a"), m)
            for f in ("observations.csv", "states.csv", "wake_intervals.csv", "events.jsonl"):
                a = open(os.path.join(self.runs[m], f), "rb").read()
                b = open(os.path.join(d2, f), "rb").read()
                self.assertEqual(hashlib.sha256(a).hexdigest(), hashlib.sha256(b).hexdigest(), f"{m} {f}")

    def test_r2_modes_refuse_workloads_without_real_features(self):
        wl = os.path.join(self.tmp, "r1.jsonl")
        r = subprocess.run([SIM, "--config", os.path.join(ROOT, "config", "default_config.json"), "--scenario",
                            "normal", "--seconds", "30", "--save-workload", wl, "--generate-only"], cwd=ROOT,
                           capture_output=True)
        self.assertEqual(r.returncode, 0)
        r = subprocess.run([SIM, "--config", os.path.join(ROOT, "config", "default_config.json"), "--mode",
                            "robust_event", "--workload", wl, "--log-level", "none"], cwd=ROOT, capture_output=True,
                           text=True)
        self.assertNotEqual(r.returncode, 0)
        self.assertIn("R2 real-frame features", r.stderr)

    def test_r1_workload_roundtrip_unchanged(self):
        # R1 workloads serialise exactly as before (no R2 keys appended)
        wl = os.path.join(self.tmp, "r1b.jsonl")
        subprocess.run([SIM, "--config", os.path.join(ROOT, "config", "default_config.json"), "--scenario",
                        "replay", "--seconds", "60", "--save-workload", wl, "--generate-only"], cwd=ROOT, check=True,
                       capture_output=True)
        first = json.loads(open(wl).readline())
        self.assertNotIn("fp256", first)


class SplitIsolationTests(unittest.TestCase):
    def test_splits_disjoint_by_segment(self):
        sp = json.load(open(os.path.join(ROOT, "data", "splits", "r2_kitti_splits.json")))
        frames = {}
        for g in sp["segments"]:
            for f in range(g["first_frame"], g["last_frame"] + 1):
                key = (g["sequence"], f)
                self.assertNotIn(key, frames)
                frames[key] = g["split"]
        counts = {s: sum(1 for v in frames.values() if v == s) for s in ("development", "validation", "test")}
        self.assertEqual(counts, {"development": sp["development_frames"], "validation": sp["validation_frames"],
                                  "test": sp["test_frames"]})

    def test_tuning_refuses_test_split(self):
        sys.path.insert(0, os.path.join(ROOT, "scripts", "r2"))
        import tune_r2
        with self.assertRaises(SystemExit):
            tune_r2.check_split("test")
        tune_r2.check_split("validation")

    def test_frozen_parameters_match_preregistration(self):
        frozen = os.path.join(ROOT, "results", "r2", "frozen_params.json")
        lock = os.path.join(ROOT, "results", "r2", "frozen_params.sha256")
        if not os.path.exists(frozen):
            self.skipTest("parameters not frozen yet")
        h = hashlib.sha256(open(frozen, "rb").read()).hexdigest()
        self.assertEqual(h, open(lock).read().split()[0])
        meta = json.load(open(frozen))
        self.assertEqual(meta["_tuned_on"], "validation")


if __name__ == "__main__":
    unittest.main()
