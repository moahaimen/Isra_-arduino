# Statistics (gate-level only)

* Unit of resampling: segment (sequence). Validation 7 segments, test 6 segments (5 with moving tracks). Bootstrap 10,000 replicates,
  seed 20261026 (`scripts/oracle_gate.py`, `scripts/e2_stats.py`). No frame-level bootstrap is reported.
* With 5–7 clusters and 32 test tracks, intervals are wide and coverage is approximate; they are reported as descriptive.
* E1 (test): oracle / MOG2 cost ratio 0.035, 95 % CI 0.014–0.042. MOG2 R_timely 0.906, CI 0.78–1.00.
* E2 (test): validation-selected controller (GBT) / MOG2 cost ratio 3.75, 95 % CI 2.88–5.86; recall difference +0.094, CI 0.00–0.22
  (paired by track: 3 tracks found only by the controller, 0 only by MOG2). The cost criterion fails over the whole interval.
* No multiple-comparison correction was needed for the decision: the gate is a single preregistered comparison against one
  frozen threshold, and the failure margin is large (lower CI bound 2.9 vs threshold 0.60).
* Oracle per-segment recall is uneven (0.5 on two segments) because its recall constraint is pooled over the split.
