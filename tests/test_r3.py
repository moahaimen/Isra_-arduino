"""R3 tests: C++/Python parity of the R3 thumbnail, the hardware-measurement
importer (synthetic fixture, NOT a measurement), split integrity and test
locks, and simulator-level properties of the R3 modes (label blindness,
identical detector trace across modes, determinism, no blocked request
waking the M7, closed-loop feedback only from delivered results)."""
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
for d in ("scripts/r3", "scripts/r2", "scripts/detector", "scripts", "tests"):
    sys.path.insert(0, os.path.join(ROOT, d))
SIM = os.path.join(ROOT, "build", "edge_sim")
FEAT = os.path.join(ROOT, "build", "r2_features")


class ThumbParity(unittest.TestCase):
    @unittest.skipUnless(os.path.exists(FEAT), "build/r2_features missing")
    def test_thumb192_cpp_matches_python(self):
        import build_workloads_r3 as bw
        rng = np.random.default_rng(0)
        frames = [(rng.integers(0, 256, (32, 96)).astype(np.uint8), rng.integers(0, 256, (16, 17)).astype(np.uint8))
                  for _ in range(5)]
        with tempfile.NamedTemporaryFile(suffix=".bin", delete=False) as fh:
            for L, F in frames:
                fh.write(L.tobytes() + F.tobytes())
        out = subprocess.run([FEAT, fh.name, "5"], capture_output=True, text=True, check=True).stdout
        os.remove(fh.name)
        c = pd.read_csv(io.StringIO(out), dtype={"thumb192": str})
        for i, (L, _) in enumerate(frames):
            self.assertEqual(c.thumb192[i], bw.thumb192(L).tobytes().hex())

    def test_box_cells(self):
        import build_workloads_r3 as bw
        self.assertEqual(bw.box_cells(0, 0, 10, 10), 1)
        full = bw.box_cells(0, 0, 1242, 375)
        self.assertEqual(full, (1 << 48) - 1)
        self.assertEqual(bw.box_cells(1200, 300, 1241, 374), 1 << 47)


class Importer(unittest.TestCase):
    def test_import_synthetic_fixture(self):
        import import_hardware_measurements as ih
        base = json.load(open(os.path.join(ROOT, "config", "power_model.json")))
        # SYNTHETIC FIXTURE for the unit test only - not a measurement
        df = pd.DataFrame([{"state": "M4_MONITOR", "voltage": 5.0, "current": c, "duration": 60000, "trial": i}
                           for i, c in enumerate([10.0, 11.0, 12.0])] +
                          [{"state": "timing:m7_wakeup_ms", "voltage": 5.0, "current": 0, "duration": d, "trial": i}
                           for i, d in enumerate([2.0, 3.0, 4.0])])
        model, timing = ih.build(df, base)
        self.assertAlmostEqual(model["states"]["M4_MONITOR"]["power_mW"], 55.0)
        self.assertEqual(model["states"]["M4_MONITOR"]["source"], "measured")
        self.assertFalse(model["calibrated"])  # other states still assumptions
        self.assertIn("NOT measured", model["states"]["M7_SLEEP"]["source"])
        self.assertEqual(timing["m7_wakeup_ms"]["value"], 3.0)
        with self.assertRaises(SystemExit):
            ih.build(pd.DataFrame([{"state": "BOGUS", "voltage": 1, "current": 1, "duration": 1, "trial": 0}]), base)

    def test_never_overwrites_assumption_model(self):
        r = subprocess.run([sys.executable, os.path.join(ROOT, "scripts", "import_hardware_measurements.py"),
                            "/dev/null", "--out", os.path.join(ROOT, "config", "power_model.json")],
                           capture_output=True, text=True)
        self.assertNotEqual(r.returncode, 0)
        self.assertIn("refusing", r.stderr + r.stdout)


class Splits(unittest.TestCase):
    def test_r3_splits_hash_and_disjoint(self):
        p = os.path.join(ROOT, "data", "splits", "r3_splits.json")
        h = hashlib.sha256(open(p, "rb").read()).hexdigest()
        self.assertEqual(h, open(os.path.join(ROOT, "data", "splits", "r3_splits.sha256")).read().split()[0])
        sp = json.load(open(p))
        seen = {}
        for g in sp["segments"]:
            for f in range(g["first_frame"], g["last_frame"] + 1):
                k = (g["source"], g["sequence"], f)
                self.assertNotIn(k, seen)
                seen[k] = g["split"]
        test_drives = {g["sequence"] for g in sp["segments"] if g["split"] == "test"}
        mapping = pd.read_csv(os.path.join(ROOT, "results", "r3", "gate_a", "tracking_to_raw.csv"))
        used = {f"2011_09_26_drive_{int(d):04d}" for d in mapping.drive.dropna()}
        self.assertFalse(test_drives & used)  # test drives are not sources of any tracking sequence
        val_seqs = {g["sequence"] for g in sp["segments"] if g["split"] == "validation"}
        self.assertFalse(val_seqs & set(sp["detector_train_sequences"] + sp["detector_val_sequences"]))

    def test_test_split_locked(self):
        for script in ("run_detector_r3.py", "image_bank_r3.py"):
            r = subprocess.run([sys.executable, os.path.join(ROOT, "scripts", "r3", script), "--split", "test",
                                "--detector", "lite0_squash", "--out", "/tmp/x", "--step", "m4"],
                               capture_output=True, text=True)
            self.assertNotEqual(r.returncode, 0)


def r3_workload(path, n=320, flip=False):
    """Synthetic R3 workload: two objects together, a later replay of the
    first object's frames, repeated flashes. Thumbnails encode the objects."""
    from test_r2 import r2_obs
    base = (60 + (np.arange(192) * 37) % 120).astype(np.uint8)
    rows, det = [], []
    for i in range(n):
        t = i * 100.0
        th = base.copy()
        m, cells, fg, attack, act = 0.02, 0, [], "none", "ignore"
        pos = None
        if 40 <= i < 70:
            pos = (i - 40) // 2
            m, cells, fg, act = 0.8, (1 << min(11, pos // 2)) | (1 << 36), list(range(100, 140)), "detect"
        if 120 <= i < 130:  # replay of frames 40..49
            pos = (i - 120) // 2
            m, cells, fg, attack, act = 0.8, (1 << min(11, pos // 2)) | (1 << 36), list(range(100, 140)), "replay", "block"
        if 200 <= i < 300 and i % 6 in (0, 1):
            m, cells, fg, attack, act = 0.9, 1 << 30, list(range(700, 740)), "trigger_spam", "block"
            th[100:104] = 255
        if pos is not None:
            th[24 + pos:27 + pos] = 250
            th[150:153] = 240
        legit = attack == "none"
        if flip:
            attack = {"none": "trigger_spam", "replay": "none", "trigger_spam": "none"}[attack]
            legit = not legit
            act = {"detect": "ignore", "ignore": "detect", "block": "detect"}[act]
        o = r2_obs(i + 1, t, m, cells, fg, attack=attack, legit=legit, gt_action=act)
        o["thumb192"] = th.tobytes().hex()
        rows.append(o)
        c = 0.9 if 40 <= i < 70 else 0.1
        det.append(f"{i + 1},1,{c:.4f},1,{(cells if 40 <= i < 70 else 0):016x},{c:.4f},1,1,{(cells if 40 <= i < 70 else 0):016x}")
    with open(path, "w") as fh:
        fh.write("\n".join(json.dumps(r) for r in rows) + "\n")
    json.dump({"seed": 1, "seconds": n / 10.0, "scenario": "clean"}, open(path + ".meta.json", "w"))
    with open(os.path.join(os.path.dirname(path), "det.csv"), "w") as fh:
        fh.write("event_id,predicted_class,confidence,num_boxes,s1_cells,second_pass_confidence,"
                 "second_pass_predicted_class,second_pass_num_boxes,s2_cells\n" + "\n".join(det) + "\n")


@unittest.skipUnless(os.path.exists(SIM), "build/edge_sim missing")
class R3Sim(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        from test_r2 import run_sim
        cls.run_sim = staticmethod(run_sim)
        cls.tmp = tempfile.mkdtemp(prefix="r3t_")
        for d, flip in (("a", False), ("b", True)):
            os.makedirs(os.path.join(cls.tmp, d))
            r3_workload(os.path.join(cls.tmp, d, "wl.jsonl"), flip=flip)
        cls.runs = {m: run_sim(os.path.join(cls.tmp, "a"), m) for m in ("ugs_event", "ugs_secure", "always_on")}

    def obs(self, m, which="a"):
        d = self.runs[m] if which == "a" else self.run_sim(os.path.join(self.tmp, "b"), m)
        return pd.read_csv(os.path.join(d, "observations.csv"), keep_default_na=False)

    def test_blind_to_labels(self):
        cols = ["score", "triggered", "suppress_reason", "sec_evaluated", "sec_accept", "sec_reason", "processed",
                "detect_start_ms", "watcher_z", "watcher_novel", "region", "accum"]
        for m in ("ugs_event", "ugs_secure"):
            a, b = self.obs(m), self.obs(m, "b")
            pd.testing.assert_frame_equal(a[cols], b[cols], check_exact=True, obj=m)

    def test_identical_trace(self):
        det = pd.read_csv(os.path.join(self.tmp, "a", "det.csv")).set_index("event_id")
        for m in self.runs:
            o = self.obs(m)
            for r in o[o.processed == 1].itertuples():
                self.assertAlmostEqual(r.s1_conf, det.loc[r.event_id, "confidence"], places=4)

    def test_secure_properties(self):
        o = self.obs("ugs_secure")
        blk = o[(o.sec_evaluated == 1) & (o.sec_accept == 0)]
        self.assertTrue((blk.started == 0).all() and (blk.caused_wake == 0).all())
        rep = o[o.attack_type == "replay"]
        self.assertEqual(int(rep.started.sum()), 0)  # replay of stale object frames never reaches the M7
        legit = o[o.ground_truth_action == "detect"]
        self.assertGreater(int(legit.started.sum()), 0)
        self.assertEqual(int(((o.attack_type == "none") & (o.sec_reason == "REPLAY")).sum()), 0)  # no FRR by replay

    def test_flash_spam_backs_off(self):
        o = self.obs("ugs_event")
        spam = o[o.attack_type == "trigger_spam"]
        self.assertLessEqual(int(spam.started.sum()), 8)  # barren back-off after k_retry checks

    def test_determinism(self):
        for m in ("ugs_event", "ugs_secure"):
            d2 = self.run_sim(os.path.join(self.tmp, "a"), m)
            for f in ("observations.csv", "states.csv", "events.jsonl"):
                self.assertEqual(open(os.path.join(self.runs[m], f), "rb").read(), open(os.path.join(d2, f), "rb").read())


if __name__ == "__main__":
    unittest.main()
