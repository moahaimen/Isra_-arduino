"""Registry of real pretrained detectors and their complexity analysis.

Host-reference detectors are the MediaPipe Model Maker object detectors
(Apache-2.0), downloaded unmodified from Google's public model bucket and
pinned by SHA-256. They are COCO-trained (90 labels). They are NOT the
MCU-target detector: TinyissimoYOLO (scripts/detector/tinyissimo/) is the
MCU target, for which no public pretrained checkpoint exists (see
docs/R2_DETECTOR.md).
"""
from __future__ import annotations

import os
from typing import Dict

import numpy as np

MP_BUCKET = "https://storage.googleapis.com/mediapipe-models/object_detector"

MODELS: Dict[str, Dict] = {
    "efficientdet_lite0_int8": {
        "file": "efficientdet_lite0_int8.tflite",
        "url": f"{MP_BUCKET}/efficientdet_lite0/int8/1/efficientdet_lite0.tflite",
        "sha256": "0720bf247bd76e6594ea28fa9c6f7c5242be774818997dbbeffc4da460c723bb",
        "architecture": "EfficientDet-Lite0", "precision": "INT8 (post-training quantized weights/activations, float I/O decode)",
        "input": [320, 320], "training_set": "COCO 2017", "role": "host_reference_primary",
    },
    "efficientdet_lite0_fp32": {
        "file": "efficientdet_lite0_float32.tflite",
        "url": f"{MP_BUCKET}/efficientdet_lite0/float32/1/efficientdet_lite0.tflite",
        "sha256": "40338edf5ec70d43e318b0a716a84d4564cd1802759a7a07170c7e43796dbf58",
        "architecture": "EfficientDet-Lite0", "precision": "FP32",
        "input": [320, 320], "training_set": "COCO 2017", "role": "host_reference",
    },
    "ssd_mobilenet_v2_fp32": {
        "file": "ssd_mobilenet_v2_float32.tflite",
        "url": f"{MP_BUCKET}/ssd_mobilenet_v2/float32/1/ssd_mobilenet_v2.tflite",
        "sha256": "b8ccb1a25d45455ba52e85f26531948e1cb75efeb94c7c3d456d54fd4d6fbdd2",
        "architecture": "SSD MobileNetV2 (RetinaNet-style head)", "precision": "FP32",
        "input": [256, 256], "training_set": "COCO 2017", "role": "host_reference",
    },
    "efficientdet_lite2_int8": {
        "file": "efficientdet_lite2_int8.tflite",
        "url": f"{MP_BUCKET}/efficientdet_lite2/int8/1/efficientdet_lite2.tflite",
        "sha256": "b3f50554cb0ea559e90328845f7d9ba4d13c8bff372914d24e06bc8bb72fa896",
        "architecture": "EfficientDet-Lite2", "precision": "INT8",
        "input": [448, 448], "training_set": "COCO 2017", "role": "host_reference_upper",
    },
}

# PASCAL VOC class ids (1..20, as in the VOC 2007 COCO-format annotations) and
# the COCO label each corresponds to. All 20 VOC classes exist in COCO.
VOC_CLASSES = ["aeroplane", "bicycle", "bird", "boat", "bottle", "bus", "car", "cat", "chair", "cow",
               "diningtable", "dog", "horse", "motorbike", "person", "pottedplant", "sheep", "sofa",
               "train", "tvmonitor"]
VOC_TO_COCO = {"aeroplane": "airplane", "diningtable": "dining table", "motorbike": "motorcycle",
               "pottedplant": "potted plant", "sofa": "couch", "tvmonitor": "tv"}
COCO_TO_VOC_ID = {VOC_TO_COCO.get(c, c): i + 1 for i, c in enumerate(VOC_CLASSES)}

# KITTI tracking evaluation classes (see kitti.py for the label mapping).
KITTI_CLASSES = {1: "person", 2: "car"}
COCO_TO_KITTI_ID = {"person": 1, "car": 2}


def model_path(model_dir: str, name: str) -> str:
    return os.path.join(model_dir, MODELS[name]["file"])


def tflite_complexity(path: str) -> Dict:
    """Parameter count and multiply-accumulate count from the TFLite graph.

    Parameters = elements of all constant tensors consumed by operators
    (weights, biases, quantization-free constants). MACs are counted for
    CONV_2D (out_elems * kh * kw * cin), DEPTHWISE_CONV_2D (out_elems * kh * kw)
    and FULLY_CONNECTED (out_elems * in_features); element-wise ops, pooling
    and resizing are not counted (they are small for these models)."""
    from ai_edge_litert.interpreter import Interpreter, OpResolverType

    # Without the default XNNPACK delegate so every operator stays visible.
    it = Interpreter(model_path=path, num_threads=1,
                     experimental_op_resolver_type=OpResolverType.BUILTIN_WITHOUT_DEFAULT_DELEGATES)
    it.allocate_tensors()
    tensors = {t["index"]: t for t in it.get_tensor_details()}
    ops = it._get_ops_details()
    produced = set()
    for op in ops:
        produced.update(int(i) for i in op["outputs"])
    graph_inputs = {d["index"] for d in it.get_input_details()}
    const = set()
    for op in ops:
        for i in op["inputs"]:
            i = int(i)
            if i >= 0 and i not in produced and i not in graph_inputs:
                const.add(i)
    params = int(sum(int(np.prod(tensors[i]["shape"])) for i in const if i in tensors))
    macs = 0
    for op in ops:
        name = op["op_name"]
        if name not in ("CONV_2D", "DEPTHWISE_CONV_2D", "FULLY_CONNECTED"):
            continue
        out = tensors[int(op["outputs"][0])]["shape"]
        w = tensors[int(op["inputs"][1])]["shape"]
        out_elems = int(np.prod(out))
        if name == "CONV_2D":
            macs += out_elems * int(w[1]) * int(w[2]) * int(w[3])
        elif name == "DEPTHWISE_CONV_2D":
            macs += out_elems * int(w[1]) * int(w[2])
        else:
            macs += out_elems * int(w[-1])
    n_delegate = sum(1 for op in ops if op["op_name"] == "DELEGATE")
    return {"parameters": params, "macs": int(macs), "model_bytes": os.path.getsize(path),
            "macs_note": "conv/depthwise/FC only" + (f"; {n_delegate} ops pre-delegated to XNNPACK are not counted"
                                                      if n_delegate else "")}
