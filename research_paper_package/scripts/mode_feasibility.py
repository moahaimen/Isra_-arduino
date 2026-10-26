#!/usr/bin/env python3
"""Per-mode resource figures for the STM32H747 deployability check.

Peak activation memory: tensor-liveness bound over the TFLite execution order (sum of bytes of
non-constant tensors alive at each op; no fragmentation, no scratch buffers, so a LOWER bound on
the TFLM arena). Weights: bytes of constant tensors. MACs from scripts/detector/models.py.
Host latency summary from run_modes.py timing.csv (host CPU, NOT Cortex-M7).
"""
import json
import os
import sys

import numpy as np
import pandas as pd

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(HERE, "..", ".."))
sys.path.insert(0, os.path.join(ROOT, "scripts", "detector"))
import models  # noqa: E402


def liveness(path):
    from ai_edge_litert.interpreter import Interpreter, OpResolverType
    it = Interpreter(model_path=path, experimental_preserve_all_tensors=True,
                     experimental_op_resolver_type=OpResolverType.BUILTIN_WITHOUT_DEFAULT_DELEGATES)
    it.allocate_tensors()
    td = {t["index"]: t for t in it.get_tensor_details()}
    ops = it._get_ops_details()
    nbytes = lambda i: int(np.prod(td[i]["shape"]) * np.dtype(td[i]["dtype"]).itemsize) if len(td[i]["shape"]) else 0
    inputs = [d["index"] for d in it.get_input_details()]
    # activations: tensors data-dependent on the model input (ops on constants only, e.g. weight
    # DEQUANTIZE, are folded into the weights)
    act = set(inputs)
    for o in ops:
        if any(int(x) in act for x in o["inputs"] if x >= 0):
            act |= set(int(x) for x in o["outputs"] if x >= 0)
    last = {}
    for k, o in enumerate(ops):
        for x in list(o["inputs"]) + list(o["outputs"]):
            if x >= 0 and x in act:
                last[int(x)] = k
    first = {i: -1 for i in inputs}
    for k, o in enumerate(ops):
        for x in o["outputs"]:
            if x >= 0:
                first.setdefault(int(x), k)
    last_conv = max(k for k, o in enumerate(ops) if o["op_name"] in ("CONV_2D", "DEPTHWISE_CONV_2D"))
    peak, peak_op, peak_cnn = 0, -1, 0
    for k in range(len(ops)):
        live = sum(nbytes(i) for i in act if first.get(i, 99999) <= k <= last.get(i, -1))
        if live > peak:
            peak, peak_op = live, k
        if k <= last_conv:
            peak_cnn = max(peak_cnn, live)
    const = sum(nbytes(i) for i in td if i not in act)
    return {"peak_activation_bytes_lower_bound": peak, "peak_op": ops[peak_op]["op_name"],
            "peak_activation_bytes_lower_bound_cnn_only": peak_cnn,
            "note": "cnn_only = up to the last convolution, i.e. excluding the 19,206-anchor x 90-class COCO decode tail",
            "const_weight_bytes": const,
            "ops": len(ops), "input_shape": [int(v) for v in it.get_input_details()[0]["shape"]]}


def main():
    path = models.model_path(os.path.join(os.environ.get("R2_DATA", "/home/claude/data_r2"), "models"), "efficientdet_lite0_int8")
    lv = liveness(path)
    cx = models.tflite_complexity(path)
    tim = []
    for s in ("validation", "test"):
        p = os.path.join(sys.argv[1], s, "timing.csv")
        if os.path.exists(p):
            t = pd.read_csv(p)
            t["split"] = s
            tim.append(t)
    tim = pd.concat(tim) if tim else pd.DataFrame(columns=["mode", "host_invoke_ms"])
    inv = tim.groupby("mode").host_invoke_ms.agg(["median", lambda x: np.percentile(x, 95), "count"])
    inv.columns = ["median_ms", "p95_ms", "n"]
    out = {"model": "EfficientDet-Lite0 INT8 (MediaPipe)", "file_bytes": os.path.getsize(path), **lv, "complexity": cx,
           "host_invoke_ms_per_invocation": inv.reset_index().to_dict("records"),
           "stm32h747": {"internal_sram_bytes_total_incl_TCM": (64 + 128 + 512 + 288 + 64) * 1024, "largest_contiguous_axi_sram": 524288,
                         "internal_flash_bytes": 2097152, "portenta_sdram_bytes": 8388608, "portenta_qspi_bytes": 16777216}}
    print(json.dumps(out, indent=1, default=float))
    json.dump(out, open(os.path.join(sys.argv[2], "mode_resources.json"), "w"), indent=1, default=float)


if __name__ == "__main__":
    main()
