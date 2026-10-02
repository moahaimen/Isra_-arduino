# Q1-readiness audit of R3 (hostile Reviewer 2)

State at the time of writing: branch `research/q1-contribution-r3`. Gates A, B and C were run on
the VALIDATION split only. **The final test campaign was NOT run and the final pre-registration
was NOT written**, because the stage-gate rule was not satisfied (Gate A: MCU detector fails;
Gate B: pooled/noisy criteria fail; Gate C: spam and shifted replay unresolved). The R3 test
split (723 raw KITTI frames) is untouched and remains available for a single future evaluation.

**Verdict: not ready for a Q1 submission; not yet ready to start the hardware phase as a validation of
the full system. Ready to start hardware measurements of the M4/M7 constants (they do not depend on
the unresolved algorithmic issues).**

## 1. What exactly is novel?

Candidates, with their evidence status (no systematic literature search was done in this work; novelty
against the published literature is UNVERIFIED and must be checked before any claim):

1. A closed-loop wake scheduler in which the M4 learns, from the M7's own returned detections, which
   content regions are worth waking for (confirm -> slow refresh; unconfirmed -> quick retry;
   repeatedly empty -> exponential back-off) combined with component-level novelty priority.
   Evidence: on clean validation video it gives the best retention at its duty (iteration-1 configuration: UR_timely 0.91,
   track 0.99 at duty 0.25 vs 0.77-0.85 for motion/MOG2/R2-robust at 0.20-0.28). Not confirmed on test; not better on noisy video.
2. A temporal-context replay test (session state; "stale AND discontinuous with the live past") that keeps FRR at
   0.7-2.9 % (R2 gate: 62-65 %) while blocking 96 % of exact replays. Weak on shifted replay.
3. Methodology: real-frame event-trigger benchmark with tiled detection, matched traces, pre-registration (R2),
   validation-only tuning. The finding that the R2 detector ceiling was an input-geometry artefact (33 % -> 98 % track recall by tiling) is solid.

## 2. Algorithmic or integration?

Items 1-2 are algorithmic but small and heuristic (no analysis/guarantees), and are partially negative:
item 1 loses to the legacy EWMA rule on noisy video; item 2 does not address spam. A reviewer would call
the present state an engineering system with one promising component, not yet a defensible algorithmic contribution.

## 3. Is the detector strong enough?

Host reference: yes (tiled Lite0/Lite2: frame-level track ceiling 0.98 / 1.00 on validation). MCU target: no
(TinyissimoYOLO after 30 + 20 CPU epochs: 0.87 / 0.41 track ceiling, mAP50 0.48 / 0.41); the MCU claim of the title
therefore rests on a host detector whose cost on the Portenta is unknown (Lite0 x3 tiles = 2.9 GMACs/frame).

## 4. Is the temporal dataset appropriate?

Partly. KITTI static-camera segments are real, annotated and sequential, but they are dashcam standstills
(traffic lights, junctions), only 61 moving tracks in validation, 2 effective scene groups for tuning, and
object-dense: wakes almost never fall on empty scenes, so avoiding useless wakes cannot be rewarded.
MOT17 / VisDrone / UA-DETRAC / VIRAT were unreachable from this container. The new test split is 6 raw drives not
used before (723 frames); tracklet-projected GT has no DontCare regions.

## 5. Does the watcher retain detector utility?

Clean: yes at 0.25 duty (0.91). Pooled with noisy: 0.817. Noisy: 0.784 vs 0.896 (legacy). Target 0.90 not met overall.

## 6. Does security preserve legitimate availability?

Yes on replay (FRR 0.7-2.9 %, SUR 0.98), unlike R1/R2 gates (FRR 62-88 %). No under spam x8 (FRR 10.7 %).

## 7. Better than simply rate limiting?

Not demonstrated: no pure rate-limit baseline with the same scheduler was run. The ablation `ug_replay=false` /
`ug_budget=false` exists in the code (config flags) but was not evaluated. Spam suppression is no better than
no gate (0.284 vs 0.288), i.e. the gate does nothing against spam; the benefit is replay-specific.

## 8. Burst events

Burst timely retention 0.838 (vs R2 robust_event 0.801, legacy event 0.867, fixed 0.844): better than R2's watcher,
not better than the best simple baselines. Not a demonstrated strength.

## 9. Shifted replays

Not handled (success 0.178 vs 0.217 unsecured).

## 10. Generalization across sequences

Not shown: all selection used 2 validation scene groups with 61 tracks; the test split would be the first out-of-sample look.
Three scheduler iterations (disclosed) were made on validation, so validation numbers are optimistic.

## 11. Was the test set untouched?

Yes (R3 test). Locks in code: `--allow-test` flags, `tests/test_r3.py::test_test_split_locked`. Caveat: the R2 test
segments were reused as R3 validation and informed the design (documented).

## 12. Identical evaluation of all competitors?

Yes in the validation campaigns: one workload directory (frames, GT, detector trace, overlay) per
(segment, scenario, seed) replayed by all modes; detector outputs keyed by event. Grids differ in size (UGS 120 of 128 sampled,
legacy event 80 full, baselines 24-36 full, robust 120 sampled): the search effort is comparable but not identical.

## 13. Statistically supported claims?

None yet: no pre-registered confirmatory test exists for R3; validation numbers are descriptive and selection-biased.

## 14. Is the M4 implementation feasible?

Memory (host build) 92 KB with a 64-frame history, ~1.5 x 10^5 ops/frame for features; fits in principle but
not verified against the real memory map and not timed (docs/R3_COMPLEXITY.md). Tuning used history 256; the
64-frame variant is unevaluated.

## 15. Modeled quantities

All M7 timings (inference 140 ms + 110 ms second pass; tiled inference is NOT charged 3x: each frame costs the same
as in R2), RPC and wake latency, all power values and therefore duty, energy and latency. Host detector latency is
host-only.

## 16. Missing hardware evidence

Everything in docs/R3_HARDWARE.md (rows 1-9), including whether three-tile inference of any detector fits the
latency/energy assumed.

## 17. More than an Arduino implementation?

Not yet. The potentially defensible science is (a) closed-loop wake scheduling and (b) availability-preserving replay
detection, but (a) lacks a demonstrated advantage under noise and on test data, and (b) lacks spam and shifted-replay results.

## Exact next action

1. Acquire a GPU (Colab/cloud) and run `scripts/detector/tinyissimo/train_full_gpu.sh`; evaluate INT8 on VOC and on the R3 tiled
   validation frames (Gate A for the MCU target).
2. Obtain a second temporal dataset with empty/benign periods (allowlist motchallenge.net for MOT17, or a VisDrone/UA-DETRAC
   mirror) and add it as validation/test groups; re-run Gate B with leave-one-group-out selection.
3. Fix, on validation only: noise-robust evidence (compensate contrast loss in the accumulator), spam (rate of unconfirmed
   novel regions per time, not only per region), shifted replay (search small displacement before block comparison);
   evaluate `ug_replay` / `ug_budget` / `ugs_feedback` / `ugs_novelty` / `ugs_persistence` ablations on validation.
4. Only then write `docs/PREREGISTERED_R3_FINAL.md`, freeze `config/r3_frozen.json`, run the test split once.
