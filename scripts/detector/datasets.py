"""Loaders for real annotated datasets -> (frames, ground_truth) tables of
detector trace V2. Images are referenced relative to --data-root and are not
stored in the repository.

voc2007   PASCAL VOC 2007 (COCO-format annotations as distributed in the
          fast.ai mirror s3://fast-ai-imagelocal/pascal_2007.tgz; splits
          train / valid / test are the official VOC 2007 train / val / test).
          "difficult" objects (ignore=1) are ignore regions, as in the
          official VOC protocol.
kitti_tracking  KITTI tracking benchmark, training sequences (labels are not
          public for testing). See kitti.py for the class mapping and the
          static-camera segment selection.
"""
from __future__ import annotations

import json
import os
from typing import Dict

import pandas as pd

import models


def load_voc2007(root: str, split: str, _sequences: str = "") -> Dict:
    split_file = {"train": "train.json", "val": "valid.json", "valid": "valid.json", "test": "test.json"}[split]
    img_dir = "test" if split == "test" else "train"
    t = json.load(open(os.path.join(root, "pascal_2007", split_file)))
    cats = {c["id"]: c["name"] for c in t["categories"]}
    assert [cats[i] for i in range(1, 21)] == models.VOC_CLASSES, "unexpected VOC category order"
    frames = pd.DataFrame([{
        "event_id": int(im["id"]), "frame_id": int(im["id"]), "source_sequence": "voc2007_" + split,
        "timestamp_ms": 0.0, "image_path": os.path.join("pascal_2007", img_dir, im["file_name"]),
        "width": int(im["width"]), "height": int(im["height"]), "split": split} for im in t["images"]])
    frames = frames.sort_values("event_id").reset_index(drop=True)
    g = []
    for k, an in enumerate(t["annotations"]):
        x, y, w, h = an["bbox"]
        g.append({"event_id": int(an["image_id"]), "gt_id": int(an["id"]), "class_id": int(an["category_id"]),
                  "class_name": cats[an["category_id"]], "x1": float(x), "y1": float(y), "x2": float(x + w),
                  "y2": float(y + h), "ignore": int(an.get("ignore", 0) or an.get("iscrowd", 0))})
    gt = pd.DataFrame(g)
    gt = gt[(gt.x2 > gt.x1) & (gt.y2 > gt.y1)].reset_index(drop=True)
    return {"name": "PASCAL VOC 2007", "frames": frames, "gt": gt,
            "classes": {i + 1: c for i, c in enumerate(models.VOC_CLASSES)},
            "coco_to_class_id": models.COCO_TO_VOC_ID}


def load_kitti(root: str, split: str, sequences: str = "") -> Dict:
    import kitti
    return kitti.load(root, split, sequences)


LOADERS = {"voc2007": load_voc2007, "kitti_tracking": load_kitti}
