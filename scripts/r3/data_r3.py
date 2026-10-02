"""R3 data access: frames and ground truth (trace V2 tables plus track_id) for
the R3 splits in data/splits/r3_splits.json.

event_id = seq_key * 100000 + frame, with seq_key = int(tracking sequence)
for KITTI tracking and 1000 + drive number for KITTI raw drives.

Ground-truth classes (same convention as R2): 1 person, 2 car.
KITTI tracking: as scripts/detector/kitti.py (Van / Person_sitting / Cyclist /
DontCare / hard boxes -> ignore regions).
KITTI raw tracklets: Car -> car; Pedestrian -> person; Van -> car ignore;
Person (sitting) and Cyclist -> person ignore; Truck, Tram, Misc -> ignore for
both classes; boxes with height < 25 px, occlusion state 2 (fully occluded)
or truncation state 1 (truncated) -> ignore; truncation state 2 (out of
image) or 99 -> dropped. The raw tracklets carry no DontCare regions, so
unlabelled distant objects can appear as false positives (affects precision
/ mAP, not recall of labelled tracks).
"""
from __future__ import annotations

import json
import os
import sys
from typing import Dict, List

import pandas as pd

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(HERE, "..", ".."))
sys.path.insert(0, HERE)
sys.path.insert(0, os.path.join(HERE, "..", "detector"))
import kitti  # noqa: E402

DATA_R2 = os.environ.get("R2_DATA", "/home/claude/data_r2")
DATA = os.environ.get("R3_DATA", "/home/claude/data_r3")
FRAME_MS = 100.0
SPLITS = os.path.join(ROOT, "data", "splits", "r3_splits.json")
CLASSES = {1: "person", 2: "car"}


def splits() -> Dict:
    return json.load(open(SPLITS))


def segments(split: str) -> List[Dict]:
    return [g for g in splits()["segments"] if g["split"] == split]


def seq_key(g: Dict) -> int:
    return int(g["sequence"]) if g["source"] == "kitti_tracking" else 1000 + int(g["sequence"][-4:])


def seg_name(g: Dict) -> str:
    return f"{g['sequence'][-4:] if g['source'] == 'kitti_tracking' else 'raw' + g['sequence'][-4:]}_{g['first_frame']:04d}"


def raw_image_path(g: Dict, f: int) -> str:
    return os.path.join("raw", g["sequence"], "image_02", f"{f:010d}.png")


def download_raw_frames(g: Dict) -> int:
    import zipfile
    from kitti_raw import BUCKET, DATE
    from kitti import HttpRangeFile
    todo = [f for f in range(g["first_frame"], g["last_frame"] + 1)
            if not os.path.exists(os.path.join(DATA, raw_image_path(g, f)))]
    if not todo:
        return 0
    d = g["sequence"]
    z = zipfile.ZipFile(HttpRangeFile(f"{BUCKET}/{d}/{d}_sync.zip"))
    for f in todo:
        name = f"{DATE}/{d}_sync/image_02/data/{f:010d}.png"
        dst = os.path.join(DATA, raw_image_path(g, f))
        os.makedirs(os.path.dirname(dst), exist_ok=True)
        with z.open(name) as src, open(dst + ".part", "wb") as out:
            out.write(src.read())
        os.replace(dst + ".part", dst)
    return len(todo)


def raw_gt(g: Dict, cal: Dict) -> List[Dict]:
    from kitti_raw import box2d, read_tracklets
    rows = []
    sk = seq_key(g)
    for obj in read_tracklets(int(g["sequence"][-4:])):
        t = obj["type"]
        for k, pose in enumerate(obj["poses"]):
            f = obj["first"] + k
            if f < g["first_frame"] or f > g["last_frame"] or pose["truncation"] in (2, 99):
                continue
            b = box2d(obj, pose, cal)
            if b is None:
                continue
            x1, y1, x2, y2, _ = b
            hard = (y2 - y1) < 25 or pose["occlusion"] == 2 or pose["truncation"] == 1
            if t == "Car":
                targets = [(2, int(hard))]
            elif t == "Pedestrian":
                targets = [(1, int(hard))]
            elif t == "Van":
                targets = [(2, 1)]
            elif t in ("Person (sitting)", "Person_sitting", "Cyclist"):
                targets = [(1, 1)]
            else:  # Truck, Tram, Misc
                targets = [(1, 1), (2, 1)]
            for cid, ign in targets:
                rows.append({"event_id": sk * 100000 + f, "track_id": obj["track_id"], "class_id": cid,
                             "class_name": CLASSES[cid], "ignore": ign, "x1": x1, "y1": y1, "x2": x2, "y2": y2})
    return rows


def load(split: str, with_images: bool = True) -> Dict:
    """frames (with absolute image path in column `abs_path`) and GT."""
    from PIL import Image
    frames, gts = [], []
    cal = None
    for g in segments(split):
        sk = seq_key(g)
        if g["source"] == "kitti_tracking":
            root = os.path.join(DATA_R2, "kitti")
            if with_images:
                kitti.download_frames(root, [(g["sequence"], f) for f in range(g["first_frame"], g["last_frame"] + 1)])
            lab = kitti.read_labels(root, g["sequence"])
            ev = {f: sk * 100000 + f for f in range(g["first_frame"], g["last_frame"] + 1)}
            gts += kitti.gt_rows(lab, ev)
            paths = {f: os.path.join(root, "training", "image_02", g["sequence"], f"{f:06d}.png") for f in ev}
        else:
            if cal is None:
                from kitti_raw import read_calib
                cal = read_calib()
            if with_images:
                download_raw_frames(g)
            gts += raw_gt(g, cal)
            paths = {f: os.path.join(DATA, raw_image_path(g, f)) for f in range(g["first_frame"], g["last_frame"] + 1)}
        for f, p in paths.items():
            if with_images:
                with Image.open(p) as im:
                    w, h = im.size
            else:
                w, h = 1242, 375
            frames.append({"event_id": sk * 100000 + f, "frame_id": f, "source_sequence": seg_name(g),
                           "timestamp_ms": (f - g["first_frame"]) * FRAME_MS, "image_path": p, "abs_path": p,
                           "width": w, "height": h, "split": split})
    fr = pd.DataFrame(frames)
    gt = pd.DataFrame(gts)
    gt.insert(1, "gt_id", range(1, len(gt) + 1))
    return {"frames": fr, "gt": gt, "classes": dict(CLASSES)}
