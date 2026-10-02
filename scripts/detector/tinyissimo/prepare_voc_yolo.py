#!/usr/bin/env python3
"""Convert PASCAL VOC 2007 (COCO-format json of the fast.ai mirror) to the
YOLO txt layout expected by the TinyissimoYOLO / Ultralytics trainer.

  <out>/images/{trainval,test}/<id>.jpg   (symlinks to the original files)
  <out>/labels/{trainval,test}/<id>.txt   class cx cy w h (normalised, class 0..19)
  <out>/voc2007.yaml

trainval = official VOC07 train + val (5,011 images); test = official VOC07
test (4,952 images). "difficult" objects are left out of the training
labels, as in the Ultralytics VOC recipe; evaluation never uses these txt
files (it uses the original annotations through scripts/detector/coco_eval.py).
"""
from __future__ import annotations

import argparse
import json
import os


def convert(voc_root: str, out: str) -> dict:
    counts = {}
    for split, files, img_dir in (("trainval", ("train.json", "valid.json"), "train"), ("test", ("test.json",), "test")):
        os.makedirs(os.path.join(out, "images", split), exist_ok=True)
        os.makedirs(os.path.join(out, "labels", split), exist_ok=True)
        n_img = n_box = 0
        for fn in files:
            t = json.load(open(os.path.join(voc_root, "pascal_2007", fn)))
            by = {}
            for a in t["annotations"]:
                by.setdefault(a["image_id"], []).append(a)
            for im in t["images"]:
                src = os.path.join(voc_root, "pascal_2007", img_dir, im["file_name"])
                dst = os.path.join(out, "images", split, im["file_name"])
                if not os.path.lexists(dst):
                    os.symlink(src, dst)
                W, H = im["width"], im["height"]
                lines = []
                for a in by.get(im["id"], []):
                    if a.get("ignore", 0) or a.get("iscrowd", 0):
                        continue
                    x, y, w, h = a["bbox"]
                    if w <= 0 or h <= 0:
                        continue
                    lines.append(f"{a['category_id'] - 1} {(x + w / 2) / W:.6f} {(y + h / 2) / H:.6f} {w / W:.6f} {h / H:.6f}")
                with open(os.path.join(out, "labels", split, os.path.splitext(im["file_name"])[0] + ".txt"), "w") as f:
                    f.write("\n".join(lines) + ("\n" if lines else ""))
                n_img += 1
                n_box += len(lines)
        counts[split] = {"images": n_img, "boxes": n_box}
    names = ["aeroplane", "bicycle", "bird", "boat", "bottle", "bus", "car", "cat", "chair", "cow", "diningtable",
             "dog", "horse", "motorbike", "person", "pottedplant", "sheep", "sofa", "train", "tvmonitor"]
    with open(os.path.join(out, "voc2007.yaml"), "w") as f:
        f.write(f"path: {out}\ntrain: images/trainval\nval: images/test\nnames:\n")
        for i, n in enumerate(names):
            f.write(f"  {i}: {n}\n")
    return counts


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--voc-root", default="/home/claude/data_r2/voc")
    ap.add_argument("--out", default="/home/claude/data_r2/voc_yolo")
    a = ap.parse_args()
    print(json.dumps(convert(a.voc_root, a.out)))
