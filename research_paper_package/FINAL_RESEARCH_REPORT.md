# Final research report: dual-core minimum-sufficient inference, feasibility gate

**Decision: STOP (NO-GO for controller training and the full paper package).**
Date 2026-10-26. Branch `claude/project-thread-1z9eiv` (based on `research/q1-novelty-screen-round2`; no existing branch was modified).

## Answer to the research question

*Can a low-cost companion core predict the minimum detector workload that preserves timely detection while reducing M7 load?*

Not with the evidence available. On held-out KITTI sequences:

1. **A privileged oracle has large headroom.** Choosing per frame among SKIP / LOW / ROI / FULL with real EfficientDet-Lite0 outputs,
   a clairvoyant oracle keeps timely first-detection recall at 0.906 for 3.5 % of the cost of the best causal baseline
   (MOG2-triggered FULL, 0.80 invocation units/frame) and at 35 % of the cost of a SKIP/FULL-only oracle. The preregistered E1
   criteria all pass.
2. **The M4 cannot see that headroom.** Cheap M4 features predict "an invocation now would timely-detect an object" at chance level
   (out-of-fold AUROC 0.49–0.53). Every learned controller (logistic regression, depth-4 tree, gradient boosting, MLP, and the proposed
   cost-aware mode rule) either runs almost every frame to keep recall or loses recall; the validation-selected one costs 3.75× the
   MOG2 baseline (95 % CI 2.9–5.9×). The preregistered E2 gate (≤ 0.60× baseline cost at equal recall) fails by a wide margin.
3. **The detector is not deployable on the target.** All modes use Lite0 (≥ 3.07 MB activations, 4.1 MB weights) against ≈ 1 MB SRAM and
   2 MB flash on STM32H747. The only MCU-class detector tried (TinyissimoYOLO) has no public checkpoint and failed accuracy in R3.
4. **Novelty risk is high.** Per-frame choice among skip / resolution / ROI / full detection from cheap features is occupied
   (AdaPyramid TMC 2023/24, FrameBoost Access 2025, Albireo arXiv 2026, Statues ISLPED 2024, ApproxDet / SmartAdapt / LiteReconfig,
   Remix), and the M4-front-end / M7-inference split on STM32H747 is Lee, Kim & Hong, IEEE Access 2024. See `00_protocol/novelty_audit.md`.

This repeats, with real mode-specific outputs, the pattern seen in R3.1 Gate B and D1 K1: the bottleneck is not detector cost
modelling but the information available to the cheap core.

## What was produced

| path | content |
|---|---|
| `00_protocol/preregistration.md` | frozen E1 criteria + Addendum A (E2 gate), both committed before test results |
| `00_protocol/novelty_audit.md` | 14 closest works, collision verdict |
| `00_protocol/deviations.md` | 9 stated deviations (added S1/E2 gates, no M7 queueing, Lite0 only, boot frame, …) |
| `01_datasets/` | dataset and per-segment split manifests, frame-content SHA-256 |
| `02_detectors/` | model manifest, mode resource/deployability table, run metadata |
| `03_oracle_gate/` | `GO_STOP.txt`, `oracle_report.md`, `oracle_results.csv` (+ per split/segment/track), frozen baselines, raw mode outputs (`mode_outputs/*.tar.gz`) |
| `04_experiments/controller_results/` | LOSO selection, frozen controllers and models, test results |
| `07_statistics/` | segment-clustered bootstrap summary, E2 comparison |
| `scripts/` | `run_modes.py`, `oracle_gate.py`, `controllers.py`, `mode_feasibility.py`, `e2_stats.py` |

Not produced, by design (gate failed): E3–E9, Figures 1–12, Tables 1–12, `05_figures`, `06_tables`, `08_manuscript_material`.

## Reproduce

```
# deps: mediapipe 1.0.1, ai-edge-litert 2.2.0, opencv, pycocotools, scipy, scikit-learn; apt libegl1 libgles2
python3 research_paper_package/scripts/run_modes.py --split validation --out $E1/validation   # ~3 min + ~1 GB KITTI frames
python3 research_paper_package/scripts/run_modes.py --split test --out $E1/test               # ~2 min + ~0.6 GB KITTI raw frames
python3 research_paper_package/scripts/oracle_gate.py tune --data $E1/validation
python3 research_paper_package/scripts/oracle_gate.py gate --data $E1/test --tag test
python3 research_paper_package/scripts/controllers.py select --train $E1/validation
python3 research_paper_package/scripts/controllers.py eval --data $E1/test --tag test
python3 research_paper_package/scripts/e2_stats.py $E1/test
```
The cached mode outputs in `03_oracle_gate/mode_outputs/` let the last five steps run without images or the detector.

## Limitations

* Small held-out set: 6 segments, 723 frames, 32 moving tracks, all cars; validation 61 tracks. Static-camera dashcam footage at
  standstill, not a surveillance camera. Half the validation tracks are left-censored by the segment cut.
* Single host-reference detector (COCO-trained, not fine-tuned); costs are invocation/MAC counts, not Cortex-M7 measurements; no
  energy measured; results count at the invoked frame (no M7 queueing).
* The M4 feature set is the existing R2 front end plus MOG2; richer features (edges, texture, detector feedback) might help, but the
  chance-level AUROC leaves little reason to expect a 2× cost gap to close.

## Journal readiness

Not ready, and this direction should not be pursued as the primary contribution. A paper built on it would rest on a privileged
oracle result, a non-deployable detector and a mechanism with direct prior art. If the project continues, the remaining option from
the earlier screens is S4 (measured M7→M4 interference on the real Portenta H7), which needs hardware, not more simulation.
