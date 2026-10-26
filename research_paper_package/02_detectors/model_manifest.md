# Model manifest

| item | value |
|---|---|
| model | EfficientDet-Lite0 INT8, MediaPipe object detector (Apache-2.0, COCO-trained, not fine-tuned) |
| source | https://storage.googleapis.com/mediapipe-models/object_detector/efficientdet_lite0/int8/1/efficientdet_lite0.tflite |
| SHA-256 | 0720bf247bd76e6594ea28fa9c6f7c5242be774818997dbbeffc4da460c723bb (pinned in scripts/detector/models.py, verified on download) |
| parameters | 3,323,396 |
| MACs per invocation | 0.974 G (conv/depthwise/FC, from the TFLite graph) |
| input | 320 × 320 × 3 uint8 |
| runtime | mediapipe 1.0.1 + ai-edge-litert 2.2.0, 1 CPU thread, score floor 0.01, operating threshold 0.45 |
| class map | COCO person → person (1), COCO car → car (2); other classes dropped |
| role | host reference. NOT an MCU-class model. No Cortex-M7 latency measured. |

Not available (never assumed):
* TinyissimoYOLO (MCU target): upstream ETH-PBL/TinyissimoYOLO @ 19bea4bd publishes no checkpoint. The CPU-trained checkpoints of R2/R3
  (30 + 20 epochs) lived outside git and are gone; they also failed R3 Gate A (timely ceiling 0.57 / 0.27). Training to the upstream
  recipe (1000 epochs, batch 512) needs a GPU (`scripts/detector/tinyissimo/train_full_gpu.sh`, not run).
* EfficientDet-Lite2, YOLOv8n/s were used in R3 Gate A only; not used here.
