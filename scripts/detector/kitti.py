"""KITTI tracking benchmark: download of selected frames, labels, and the
static-camera segment selection used by R2.

Source: https://s3.eu-central-1.amazonaws.com/avg-kitti/ (official KITTI
download bucket). Licence: CC BY-NC-SA 3.0; images are NOT redistributed in
this repository, only frame ids, labels-derived tables and our outputs.

Only the 21 *training* sequences have public labels. R2 needs a static camera
(the M4 watcher uses frame differencing), so frames are selected where the
ego vehicle is stationary according to the OXTS GPS/IMU record:
speed = hypot(vf, vl) < STATIC_SPEED_MS for every frame of a run, and runs of
at least MIN_RUN frames. The selection is computed from OXTS alone, before
any detector or watcher output is looked at.

Labels (label_02): frame track_id type truncated occluded alpha x1 y1 x2 y2 ...
Evaluation classes follow the official KITTI convention for "moderate"
difficulty: Car (Van = ignore region for car), Pedestrian (Person_sitting and
Cyclist = ignore regions for person), DontCare = ignore region for both; boxes
with height < 25 px, occlusion level > 1 or truncation > 0.30 become ignore
regions.
"""
from __future__ import annotations

import io
import os
import struct
import urllib.request
import zipfile
from typing import Dict, List, Tuple

import numpy as np
import pandas as pd

import models

BUCKET = "https://s3.eu-central-1.amazonaws.com/avg-kitti"
STATIC_SPEED_MS = 0.2
MIN_RUN = 30
FRAME_MS = 100.0  # KITTI is recorded at 10 Hz
MIN_HEIGHT, MAX_OCC, MAX_TRUNC = 25.0, 1, 0.30


class HttpRangeFile(io.RawIOBase):
    """Seekable read-only file over HTTP range requests (for zipfile)."""

    def __init__(self, url: str, block: int = 1 << 20):
        self.url, self.pos, self.block, self.cache = url, 0, block, {}
        req = urllib.request.Request(url, method="HEAD")
        self.size = int(urllib.request.urlopen(req, timeout=120).headers["Content-Length"])

    def seekable(self):
        return True

    def readable(self):
        return True

    def tell(self):
        return self.pos

    def seek(self, off, whence=0):
        self.pos = off if whence == 0 else (self.pos + off if whence == 1 else self.size + off)
        return self.pos

    def _get_block(self, i: int) -> bytes:
        if i not in self.cache:
            a, b = i * self.block, min(self.size, (i + 1) * self.block) - 1
            req = urllib.request.Request(self.url, headers={"Range": f"bytes={a}-{b}"})
            for attempt in range(5):
                try:
                    self.cache[i] = urllib.request.urlopen(req, timeout=300).read()
                    break
                except Exception:
                    if attempt == 4:
                        raise
            if len(self.cache) > 64:
                self.cache.pop(next(iter(self.cache)))
        return self.cache[i]

    def read(self, n=-1):
        if n < 0:
            n = self.size - self.pos
        out = bytearray()
        while n > 0 and self.pos < self.size:
            i, off = divmod(self.pos, self.block)
            blk = self._get_block(i)
            chunk = blk[off:off + n]
            out += chunk
            self.pos += len(chunk)
            n -= len(chunk)
        return bytes(out)

    def readinto(self, b):
        d = self.read(len(b))
        b[:len(d)] = d
        return len(d)


def static_segments(root: str) -> pd.DataFrame:
    rows = []
    for f in sorted(os.listdir(os.path.join(root, "training", "oxts"))):
        seq = f[:4]
        d = np.loadtxt(os.path.join(root, "training", "oxts", f))
        speed = np.hypot(d[:, 8], d[:, 9])
        st = speed < STATIC_SPEED_MS
        start = None
        for i, s in enumerate(list(st) + [False]):
            if s and start is None:
                start = i
            elif not s and start is not None:
                if i - start >= MIN_RUN:
                    rows.append({"sequence": seq, "first_frame": start, "last_frame": i - 1, "n_frames": i - start,
                                 "max_speed_ms": float(speed[start:i].max())})
                start = None
    return pd.DataFrame(rows)


def download_frames(root: str, seq_frames: List[Tuple[str, int]]) -> int:
    """Extract training/image_02/<seq>/<frame>.png for the requested frames
    from the official 15.8 GB zip using HTTP range requests."""
    todo = [(s, f) for s, f in seq_frames
            if not os.path.exists(os.path.join(root, "training", "image_02", s, f"{f:06d}.png"))]
    if not todo:
        return 0
    z = zipfile.ZipFile(HttpRangeFile(f"{BUCKET}/data_tracking_image_2.zip"))
    names = set(z.namelist())
    n = 0
    for s, f in todo:
        name = f"training/image_02/{s}/{f:06d}.png"
        if name not in names:
            raise FileNotFoundError(name)
        dst = os.path.join(root, name)
        os.makedirs(os.path.dirname(dst), exist_ok=True)
        with z.open(name) as src, open(dst + ".part", "wb") as out:
            out.write(src.read())
        os.replace(dst + ".part", dst)
        n += 1
    return n


def read_labels(root: str, seq: str) -> pd.DataFrame:
    cols = ["frame", "track_id", "type", "truncated", "occluded", "alpha", "x1", "y1", "x2", "y2",
            "h", "w", "l", "x", "y", "z", "ry"]
    return pd.read_csv(os.path.join(root, "training", "label_02", f"{seq}.txt"), sep=" ", header=None,
                       names=cols, usecols=range(17))


def gt_rows(lab: pd.DataFrame, event_of_frame: Dict[int, int]) -> List[Dict]:
    out = []
    for r in lab.itertuples():
        if r.frame not in event_of_frame:
            continue
        eid = event_of_frame[r.frame]
        box = dict(x1=float(r.x1), y1=float(r.y1), x2=float(r.x2), y2=float(r.y2))
        if box["x2"] <= box["x1"] or box["y2"] <= box["y1"]:
            continue
        hard = (r.y2 - r.y1) < MIN_HEIGHT or r.occluded > MAX_OCC or r.truncated > MAX_TRUNC
        targets = []
        if r.type == "Car":
            targets = [(2, int(hard))]
        elif r.type == "Pedestrian":
            targets = [(1, int(hard))]
        elif r.type == "Van":
            targets = [(2, 1)]
        elif r.type in ("Person_sitting", "Cyclist"):
            targets = [(1, 1)]
        elif r.type == "DontCare":
            targets = [(1, 1), (2, 1)]
        for cid, ign in targets:
            out.append({"event_id": eid, "track_id": int(r.track_id), "class_id": cid,
                        "class_name": models.KITTI_CLASSES[cid], "ignore": ign, **box})
    return out


def load(root: str, split: str, sequences: str = "") -> Dict:
    """Frames + GT for the static segments assigned to `split` in
    data/splits/r2_kitti_splits.json (or explicit `sequences` = 'SSSS:a-b,...')."""
    import json
    if sequences:
        segs = []
        for part in sequences.split(","):
            s, rng = part.split(":")
            a, b = rng.split("-")
            segs.append((s, int(a), int(b)))
    else:
        sp = json.load(open(os.path.join(os.path.dirname(__file__), "..", "..", "data", "splits", "r2_kitti_splits.json")))
        segs = [(g["sequence"], g["first_frame"], g["last_frame"]) for g in sp["segments"] if g["split"] == split]
    frames, gts = [], []
    for s, a, b in segs:
        download_frames(root, [(s, f) for f in range(a, b + 1)])
        lab = read_labels(root, s)
        ev = {f: int(s) * 100000 + f for f in range(a, b + 1)}
        for f in range(a, b + 1):
            p = os.path.join("training", "image_02", s, f"{f:06d}.png")
            from PIL import Image
            with Image.open(os.path.join(root, p)) as im:
                w, h = im.size
            frames.append({"event_id": ev[f], "frame_id": f, "source_sequence": f"kitti_{s}",
                           "timestamp_ms": (f - a) * FRAME_MS, "image_path": p, "width": w, "height": h,
                           "split": split})
        gts += gt_rows(lab, ev)
    fr = pd.DataFrame(frames)
    gt = pd.DataFrame(gts)
    gt.insert(1, "gt_id", range(1, len(gt) + 1))
    return {"name": "KITTI tracking (training, static-camera segments)", "frames": fr, "gt": gt,
            "classes": dict(models.KITTI_CLASSES), "coco_to_class_id": dict(models.COCO_TO_KITTI_ID),
            "selection": {"segments": [{"sequence": s, "first_frame": a, "last_frame": b} for s, a, b in segs],
                          "static_speed_ms": STATIC_SPEED_MS, "min_run": MIN_RUN}}
