# Independent re-run (2026-10-02, fresh cloud container)

`scripts/detector/run_real_detector.py --dataset voc2007 --split test --model efficientdet_lite0_int8`
re-executed from scratch (models and VOC re-downloaded, SHA-256 verified):

* frames.csv, ground_truth.csv: SHA-256 identical to `trace_manifest.json`;
* mAP50 0.7075564205113882 and mAP50:95 0.45929746961109463, per-class AP
  and the number of detections (279,652) identical to `metrics.json`;
* predictions.csv differs only in the host_inference_ms /
  host_postprocess_ms columns (host timing is measured anew on every run),
  so its SHA-256 differs; boxes, classes and scores reproduce exactly.
