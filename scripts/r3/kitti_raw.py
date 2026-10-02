"""KITTI raw data (official avg-kitti bucket) for R3: static-camera segments
of the 38 drives that carry tracklet labels, their mapping to the KITTI
tracking benchmark sequences (so that R3's new test data never overlaps the
data used in R1/R2), frame extraction by HTTP range requests, and 2D boxes
projected from the 3D tracklets.

Licence: KITTI raw data, CC BY-NC-SA 3.0. Images are NOT redistributed in the
repository.

Projection (KITTI raw devkit convention): a tracklet box (h, w, l) with pose
(tx, ty, tz, rz) in the Velodyne frame gives 8 corners; x_img = P2 * R0 *
Tr_velo_to_cam * X; the 2D box is the extent of the projected corners that
lie in front of the camera, clipped to the image. Frames where the tracklet's
truncation state is 99 (unset) or 2 (out of image) are dropped.
"""
from __future__ import annotations

import io
import os
import sys
import xml.etree.ElementTree as ET
import zipfile
from typing import Dict, List, Tuple

import numpy as np
import pandas as pd

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, "..", "detector"))
from kitti import HttpRangeFile  # noqa: E402

BUCKET = "https://s3.eu-central-1.amazonaws.com/avg-kitti/raw_data"
TRACKLET_DRIVES = [1, 2, 5, 9, 11, 13, 14, 15, 17, 18, 19, 20, 22, 23, 27, 28, 29, 32, 35, 36, 39, 46, 48, 51, 52,
                   56, 57, 59, 60, 61, 64, 70, 79, 84, 86, 87, 91, 93]
DATE = "2011_09_26"
STATIC_SPEED_MS = 0.2
MIN_RUN = 30


def drive_name(n: int) -> str:
    return f"{DATE}_drive_{n:04d}"


def sync_zip(n: int) -> zipfile.ZipFile:
    return zipfile.ZipFile(HttpRangeFile(f"{BUCKET}/{drive_name(n)}/{drive_name(n)}_sync.zip"))


def read_oxts(n: int) -> np.ndarray:
    z = sync_zip(n)
    pre = f"{DATE}/{drive_name(n)}_sync/oxts/data/"
    names = sorted(x for x in z.namelist() if x.startswith(pre) and x.endswith(".txt"))
    return np.array([np.array(z.read(x).decode().split(), float) for x in names])


def static_runs(oxts: np.ndarray) -> List[Tuple[int, int]]:
    speed = np.hypot(oxts[:, 8], oxts[:, 9])
    st = speed < STATIC_SPEED_MS
    runs, start = [], None
    for i, s in enumerate(list(st) + [False]):
        if s and start is None:
            start = i
        elif not s and start is not None:
            if i - start >= MIN_RUN:
                runs.append((start, i - 1))
            start = None
    return runs


def match_tracking(raw: Dict[int, np.ndarray], tracking_oxts_dir: str) -> pd.DataFrame:
    """Map each tracking training sequence to (drive, first raw frame) by exact
    match of its first OXTS record (lat, lon, alt, roll, pitch, yaw)."""
    rows = []
    for f in sorted(os.listdir(tracking_oxts_dir)):
        t = np.loadtxt(os.path.join(tracking_oxts_dir, f))
        first = t[0, :6]
        hit = None
        for n, o in raw.items():
            d = np.abs(o[:, :6] - first).max(axis=1)
            j = int(d.argmin())
            if d[j] < 1e-9:
                hit = (n, j)
                break
        rows.append({"tracking_seq": f[:4], "n_frames": len(t), "drive": hit[0] if hit else None,
                     "raw_first_frame": hit[1] if hit else None})
    return pd.DataFrame(rows)


def read_calib() -> Dict[str, np.ndarray]:
    z = zipfile.ZipFile(io.BytesIO(__import__("urllib.request").request.urlopen(
        f"{BUCKET}/{DATE}_calib.zip", timeout=120).read()))

    def parse(name):
        out = {}
        for line in z.read(f"{DATE}/{name}").decode().splitlines():
            k, _, v = line.partition(":")
            try:
                out[k] = np.array(v.split(), float)
            except ValueError:
                pass
        return out
    c2c, v2c = parse("calib_cam_to_cam.txt"), parse("calib_velo_to_cam.txt")
    Tr = np.eye(4)
    Tr[:3, :3] = v2c["R"].reshape(3, 3)
    Tr[:3, 3] = v2c["T"]
    R0 = np.eye(4)
    R0[:3, :3] = c2c["R_rect_00"].reshape(3, 3)
    P2 = c2c["P_rect_02"].reshape(3, 4)
    W, H = c2c["S_rect_02"].astype(int)
    return {"Tr": Tr, "R0": R0, "P2": P2, "W": int(W), "H": int(H)}


def read_tracklets(n: int) -> List[Dict]:
    z = zipfile.ZipFile(io.BytesIO(__import__("urllib.request").request.urlopen(
        f"{BUCKET}/{drive_name(n)}/{drive_name(n)}_tracklets.zip", timeout=300).read()))
    xml = [x for x in z.namelist() if x.endswith("tracklet_labels.xml")][0]
    root = ET.fromstring(z.read(xml))
    out = []
    for tid, it in enumerate(root.find("tracklets").findall("item")):
        obj = {"track_id": tid, "type": it.findtext("objectType"), "h": float(it.findtext("h")),
               "w": float(it.findtext("w")), "l": float(it.findtext("l")), "first": int(it.findtext("first_frame"))}
        poses = []
        for p in it.find("poses").findall("item"):
            poses.append({k: float(p.findtext(k)) for k in ("tx", "ty", "tz", "rx", "ry", "rz")} |
                         {"occlusion": int(p.findtext("occlusion")), "truncation": int(p.findtext("truncation"))})
        obj["poses"] = poses
        out.append(obj)
    return out


def box2d(obj: Dict, pose: Dict, cal: Dict):
    h, w, l = obj["h"], obj["w"], obj["l"]
    x = np.array([l / 2, l / 2, -l / 2, -l / 2, l / 2, l / 2, -l / 2, -l / 2])
    y = np.array([w / 2, -w / 2, -w / 2, w / 2, w / 2, -w / 2, -w / 2, w / 2])
    zc = np.array([0, 0, 0, 0, h, h, h, h])
    c, s = np.cos(pose["rz"]), np.sin(pose["rz"])
    R = np.array([[c, -s, 0], [s, c, 0], [0, 0, 1]])
    corners = R @ np.vstack([x, y, zc]) + np.array([[pose["tx"]], [pose["ty"]], [pose["tz"]]])
    X = np.vstack([corners, np.ones(8)])
    cam = cal["R0"] @ cal["Tr"] @ X
    if (cam[2] <= 0.1).any():
        if (cam[2] <= 0.1).all():
            return None
        cam = cam[:, cam[2] > 0.1]
    p = cal["P2"] @ cam
    u, v = p[0] / p[2], p[1] / p[2]
    x1, y1 = max(0.0, u.min()), max(0.0, v.min())
    x2, y2 = min(cal["W"] - 1.0, u.max()), min(cal["H"] - 1.0, v.max())
    if x2 <= x1 or y2 <= y1:
        return None
    return float(x1), float(y1), float(x2), float(y2), float(cam[2].mean())
