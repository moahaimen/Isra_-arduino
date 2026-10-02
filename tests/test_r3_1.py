"""R3.1 tests: tiled-inference cost accounting, split/test locks, and (added
as the stages are implemented) scheduler / gate properties."""
from __future__ import annotations

import json
import os
import shutil
import subprocess
import sys
import tempfile
import unittest

import numpy as np
import pandas as pd

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
for d in ("scripts/r3_1", "scripts/r3", "scripts/r2", "scripts/detector", "tests"):
    sys.path.insert(0, os.path.join(ROOT, d))
SIM = os.path.join(ROOT, "build", "edge_sim")


def make_wl(path, s1_tiles=None, s2_tiles=None, n=200):
    """Static-ish synthetic R3 workload; det.csv optionally carries tile counts."""
    from test_r3 import r3_workload
    r3_workload(path, n=n)
    det = os.path.join(os.path.dirname(path), "det.csv")
    df = pd.read_csv(det)
    if s1_tiles is not None:
        df["s1_tiles"] = s1_tiles
    if s2_tiles is not None:
        df["s2_tiles"] = s2_tiles
    df.to_csv(det, index=False)


def run(wl_dir, mode, extra=()):
    out = tempfile.mkdtemp(prefix="r31_")
    cmd = [SIM, "--config", os.path.join(ROOT, "config", "default_config.json"), "--mode", mode, "--workload",
           os.path.join(wl_dir, "wl.jsonl"), "--detector-backend", "trace_replay", "--detector-trace",
           os.path.join(wl_dir, "det.csv"), "--trace-timing", "simulated", "--log-level", "none", "--out-dir", out,
           "--early-exit", "off"] + list(extra)
    subprocess.run(cmd, cwd=ROOT, check=True, capture_output=True)
    return out


@unittest.skipUnless(os.path.exists(SIM), "build/edge_sim missing")
class TileCost(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.tmp = tempfile.mkdtemp(prefix="r31wl_")
        cls.dirs = {}
        for name, (a, b) in {"t11": (1, 1), "t31": (3, 1), "t33": (3, 3)}.items():
            d = os.path.join(cls.tmp, name)
            os.makedirs(d)
            make_wl(os.path.join(d, "wl.jsonl"), a, b)
            cls.dirs[name] = d

    def obs(self, name, mode="ugs_event"):
        o = pd.read_csv(os.path.join(run(self.dirs[name], mode), "observations.csv"), keep_default_na=False)
        return o[o.processed == 1]

    def test_stage1_cost_scales_with_tiles(self):
        a, b = self.obs("t11"), self.obs("t31")
        self.assertGreater(len(a), 0)
        self.assertAlmostEqual(b.s1_ms.median() / a.s1_ms.median(), 3.0, delta=0.35)

    def test_stage2_cost_scales_with_tiles(self):
        b, c = self.obs("t31"), self.obs("t33")
        bs, cs = b[b.second_pass == 1], c[c.second_pass == 1]
        self.assertGreater(len(bs), 0)
        self.assertAlmostEqual(cs.s2_ms.median() / bs.s2_ms.median(), 3.0, delta=0.35)
        # stage-1 cost of the same event is identical in both runs (draws are keyed by event)
        m = b.merge(c, on="event_id", suffixes=("_b", "_c"))
        self.assertGreater(len(m), 0)
        np.testing.assert_allclose(m.s1_ms_b.values, m.s1_ms_c.values, atol=1e-6)

    def test_postprocess_includes_merge_cost_of_every_executed_stage(self):
        a, b, c = self.obs("t11"), self.obs("t31"), self.obs("t33")
        # same events, same boxes: stage-1 merge (2 extra tiles) is charged even though stage 2 has 1 tile
        for x, y, extra in ((a, b, 2.0), (b, c, 2.0)):
            m = x.merge(y, on="event_id", suffixes=("_x", "_y"))
            self.assertGreater(len(m), 0)
            np.testing.assert_allclose((m.post_ms_y - m.post_ms_x).values, extra, atol=0.01)

    def test_energy_and_active_time_see_the_extra_tiles(self):
        e = {}
        for n in ("t11", "t31", "t33"):
            out = run(self.dirs[n], "ugs_event")
            st = pd.read_csv(os.path.join(out, "states.csv"))
            wk = pd.read_csv(os.path.join(out, "wake_intervals.csv"))
            e[n] = (st.energy_mJ.sum(), wk.active_ms.sum(), st[st.state == "M7_INFERENCE"].time_ms.iloc[0],
                    st[st.state == "M7_SECOND_PASS"].time_ms.iloc[0])
        self.assertGreater(e["t31"][1], e["t11"][1])
        self.assertGreater(e["t31"][0], e["t11"][0])
        self.assertGreater(e["t31"][2], 2.5 * e["t11"][2] * 0.9)      # inference state time ~3x
        self.assertGreater(e["t33"][3], 2.5 * e["t31"][3])           # second-pass state time ~3x
        self.assertGreater(e["t33"][0], e["t31"][0])

    def test_always_on_background_frames_are_tiled(self):
        d = os.path.join(self.tmp, "sparse")
        os.makedirs(d)
        make_wl(os.path.join(d, "wl.jsonl"), None, None)
        rows = [l for i, l in enumerate(open(os.path.join(d, "wl.jsonl"))) if i % 40 == 0]   # sparse arrivals
        open(os.path.join(d, "wl.jsonl"), "w").writelines(rows)
        o1 = run(d, "always_on")
        o3 = run(d, "always_on", ["--detector-tiles", "3"])
        s1 = json.load(open(os.path.join(o1, "summary.json")))
        s3 = json.load(open(os.path.join(o3, "summary.json")))
        self.assertGreater(s1["bg_cycles"], 2 * s3["bg_cycles"])   # ~3x fewer cycles complete
        self.assertEqual(s1["m7_active_ms"], s3["m7_active_ms"])   # always awake either way

    def test_default_tiles_is_one_for_old_traces(self):
        d = os.path.join(self.tmp, "old")
        os.makedirs(d)
        make_wl(os.path.join(d, "wl.jsonl"))
        self.assertNotIn("s1_tiles", pd.read_csv(os.path.join(d, "det.csv")).columns)
        a = self.obs("t11")
        o = pd.read_csv(os.path.join(run(d, "ugs_event"), "observations.csv"), keep_default_na=False)
        o = o[o.processed == 1]
        pd.testing.assert_series_equal(a.s1_ms.reset_index(drop=True), o.s1_ms.reset_index(drop=True))


if __name__ == "__main__":
    unittest.main()
