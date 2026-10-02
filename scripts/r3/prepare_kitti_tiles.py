#!/usr/bin/env python3
"""Tile the R3 detector fine-tuning set (scripts/r3/prepare_kitti_yolo.py)
into the 3 near-square tiles used at inference (width ceil(W/3 * 1.1),
starts at linspace(0, W - tw, 3)), for the MCU-target TinyissimoYOLO
(square 256x256 input). A box is kept in a tile when >= 50 % of its area lies
inside the tile (clipped to the tile). Classes: 0 person, 1 car."""
from __future__ import annotations

import json
import os
import sys

import numpy as np
from PIL import Image

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import data_r3  # noqa: E402

SRC = os.path.join(data_r3.DATA, "kitti_yolo")
OUT = os.path.join(data_r3.DATA, "kitti_tiles")
W, H = 1242, 375
TW = int(np.ceil(W / 3 * 1.1))
STARTS = np.linspace(0, W - TW, 3).astype(int)


def main() -> int:
    counts = {}
    for part in ("train", "val"):
        os.makedirs(os.path.join(OUT, "images", part), exist_ok=True)
        os.makedirs(os.path.join(OUT, "labels", part), exist_ok=True)
        n_img = n_box = 0
        for f in sorted(os.listdir(os.path.join(SRC, "images", part))):
            name = os.path.splitext(f)[0]
            img = Image.open(os.path.join(SRC, "images", part, f)).convert("RGB")
            if img.size != (W, H):
                img = img.crop((0, 0, W, H)) if img.size[0] >= W else img.resize((W, H))
            boxes = []
            for line in open(os.path.join(SRC, "labels", part, name + ".txt")).read().split("\n"):
                if line.strip():
                    c, cx, cy, bw, bh = line.split()
                    cx, cy, bw, bh = float(cx) * W, float(cy) * H, float(bw) * W, float(bh) * H
                    boxes.append((int(c), cx - bw / 2, cy - bh / 2, cx + bw / 2, cy + bh / 2))
            for k, x0 in enumerate(STARTS):
                tile = img.crop((int(x0), 0, int(x0) + TW, H))
                tile.save(os.path.join(OUT, "images", part, f"{name}_t{k}.jpg"), quality=95)
                lines = []
                for c, x1, y1, x2, y2 in boxes:
                    a = (x2 - x1) * (y2 - y1)
                    cx1, cx2 = max(x1, x0), min(x2, x0 + TW)
                    if cx2 <= cx1 or (cx2 - cx1) * (y2 - y1) < 0.5 * a:
                        continue
                    lines.append(f"{c} {((cx1 + cx2) / 2 - x0) / TW:.6f} {(y1 + y2) / 2 / H:.6f} "
                                 f"{(cx2 - cx1) / TW:.6f} {(y2 - y1) / H:.6f}")
                with open(os.path.join(OUT, "labels", part, f"{name}_t{k}.txt"), "w") as fh:
                    fh.write("\n".join(lines) + ("\n" if lines else ""))
                n_img += 1
                n_box += len(lines)
        counts[part] = {"tiles": n_img, "boxes": n_box}
    with open(os.path.join(OUT, "kitti_tiles.yaml"), "w") as fh:
        fh.write(f"path: {OUT}\ntrain: images/train\nval: images/val\nnames:\n  0: person\n  1: car\n")
    json.dump({"tile_width": TW, "starts": STARTS.tolist(), **counts}, open(os.path.join(OUT, "counts.json"), "w"))
    print(counts)
    return 0


if __name__ == "__main__":
    sys.exit(main())
