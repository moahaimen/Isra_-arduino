# R3.1 closure (direction stopped by the project owner)

Status: **stopped, preserved as historical evidence/baseline. Not merged.** No locked test partition (R3 723 frames, MEVA test clips) was accessed.

* MEVA reference tracks: 4 of 10 groups complete (3 with zero tracks, 1 with a single track); 6 groups were unfinished when stopped
  (partial detections only, checkpoints `ref_dets.partial.csv*` outside the repo). MEVA was therefore **never used** for any result; suitability as a second annotated dataset is **undetermined**
  (reference tracks are detector-derived, not human annotation; sampled clips mostly empty).
* Valid completed results (KITTI validation, corrected 3-tile cost): `docs/R3_1_GATE_B.md` (scheduler does not beat simple baselines; LOGO confirms),
  `docs/R3_1_DUTY_DIAGNOSIS.md` (duty 0.66–0.79 = ≈ 3–4× more wake requests than the event trigger × ≈ 2.8× per-activation tiled cost),
  `docs/R3_1_SECURITY_DESIGN.md` (cooldown carries most protection; plain rate limiter FRR 0.79 alone; gradient-tolerant replay gate partial gain),
  `docs/R3_1_GATE_C.md`, `docs/R3_1_ABLATIONS.md`, `docs/R3_1_COMPLEXITY.md`, `docs/R3_1_GPU_AUDIT.md` (blocked, no GPU), `docs/R3_1_NOVELTY_REVIEW.md` (snippet-level).
* Not done: consolidated A/B/C decision, MEVA suitability/object-density test, final freeze, locked-test evaluation (all intentionally not executed).
* Reusable infrastructure for later work: tiled-cost simulator (`tests/test_r3_1.py`), `scripts/r3_1/lib31.py`, event/gate modes in `edge_sim`.
