# Detector traces (trace_replay backend)

`edge_sim --detector-backend trace_replay --detector-trace <file.csv>` replaces
the synthetic detector model with per-event predictions produced offline by a
real object detector. The simulator architecture is unchanged; only the
detector backend differs.

## Schema (CSV, header required, `#` lines are comments)

| column | required | meaning |
|---|---|---|
| event_id | yes | workload event id the frame belongs to |
| ground_truth_class | yes | annotated class (`none`, `person`, `vehicle`, `animal`, `package` or integer 0-4) |
| predicted_class | yes | stage-1 predicted class |
| confidence | yes | stage-1 confidence in [0,1] |
| inference_ms | yes | measured stage-1 inference time |
| postprocess_ms | yes | measured postprocessing time |
| num_boxes | yes | number of boxes after NMS |
| correct | yes | 1 if predicted_class == ground_truth_class |
| second_pass_confidence | optional | stage-2 confidence (enables the second pass) |
| second_pass_predicted_class | optional | stage-2 class |
| second_pass_ms | optional | measured stage-2 time |
| gt_x, gt_y, gt_w, gt_h | optional | ground-truth box (pixels) |
| pred_x, pred_y, pred_w, pred_h | optional | predicted box (pixels) |

Every event the M7 processes must have a row; a missing row is an error, never
a silent default. mAP@0.5 and mAP@0.5:0.95 (`scripts/eval_energy/map_eval.py`)
are computed **only** when the box columns are filled with real annotations
and predictions.

## Files

* `example_trace_SCHEMA_ONLY.csv` - a hand-written 4-row example that shows
  the format. **It is not detector output and must never be used for results.**
* `scripts/make_trace_template.py <workload.jsonl> <out.csv>` writes a template
  with one row per workload event (ground-truth columns filled, prediction
  columns empty) to be completed by running a real detector on the
  corresponding frames.
