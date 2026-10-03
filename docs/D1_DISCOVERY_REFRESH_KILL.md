# D1 kill-test: discovery vs maintenance under a hard M7 budget

Status: **KILLED at K0 novelty audit after K1 feasibility check. Do not proceed to K2/K3 as a Q1 contribution.**

## Why this direction exists

R3.1 exposed a concrete failure mode that is independent of CAGE: the R3 scheduler spent 62–65% of processed activations on redundant refreshes, while only 23–27% produced a first detection, and corrected 3-tile cost pushed M7 duty to 0.74–0.79. The legacy event trigger was much cheaper but can delay or miss newly appearing tracks.

The candidate research question is therefore narrower than generic adaptive frame sampling:

> Can a dual-core MCU camera explicitly separate **discovery** of previously unseen moving objects from **maintenance/refresh** of already-known tracks, and use cheap M4-only evidence plus a protected discovery budget to reduce redundant M7 work while preserving timely first detection?

Tentative mechanism (only if the kill tests pass):
- M4 maintains a low-resolution spatial map of motion/change not explained by known detections.
- Each region accumulates **discovery debt** as unexplained evidence persists without a confirming M7 detection.
- M7 budget is split into a protected discovery reserve and a maintenance budget; refresh work cannot consume the discovery reserve.
- A confirmed detection explains/clears matching regions; maintenance is scheduled from track staleness/uncertainty, not periodic refresh alone.

This is deliberately **not** CAGE: no adversarial workload-cost prediction, no work contracts, and no slowdown/NMS claim.

## Novelty audit: final K0 decision

A deeper literature audit found direct prior-art overlap. Novelty is **not strong enough for D1 as the primary Q1 contribution**:

- **AdaPyramid** (Shi et al., IEEE TMC, DOI 10.1109/TMC.2023.3343448) explicitly separates handling of already-known/predicted objects from a dedicated **new-object detector**. The new-object detector runs every frame because missed new objects accumulate omissions, restricts work to regions where new objects can appear, chooses a cheap configuration meeting a recall target, and merges the new-object result back into the tracked-object pipeline. This directly occupies much of D1's discovery-vs-maintenance design space.
- **FrameBoost** (Yang et al., IEEE Access 2025, DOI 10.1109/ACCESS.2025.3558251) formulates inference-trigger-frame selection under resource constraints, identifies both redundant detector triggers and delayed triggers, and selects new detector inference based on estimated tracking error. This directly overlaps D1's motivation of avoiding redundant refresh while protecting timely detection.
- **Zhang & Tan, Real-time Accurate Object Tracking for Resource-constrained Edge Devices** (2024, DOI 10.11896/jsjkx.231200167) combines prediction/correction for known objects with a dedicated new-object detector based on clustered frame-difference features, again making the discovery/maintenance split itself prior art.
- Generic AoI/AoT scheduling already covers freshness-aware resource allocation under energy/computation constraints; a "discovery debt" variable or protected budget by itself would therefore need substantially stronger technical novelty than currently present.

The exact phrase **protected discovery reserve on an M4/M7 MCU** was not found in this audit. That implementation detail is not enough to rescue D1: the surrounding problem decomposition, new-object handling, redundant-refresh avoidance, and resource-constrained inference scheduling are already established. Continuing to K2/K3 would risk engineering a composition rather than creating a defensible Q1 contribution.
- Adaptive frame-rate / frame-sampling systems save detector work by skipping or warping frames.
- Edge tracking systems explicitly discuss delayed detection of newly entering objects under frame skipping.
- Some systems use frame differences or dedicated new-object detectors while propagating existing tracks.
- AoI/AoII scheduling formalizes freshness under resource/energy constraints.

What has not yet been verified as prior art is the exact combination of:
1. semantic separation of **first-discovery** and **maintenance** compute,
2. a **spatial unexplained-motion age/debt** state on an always-on low-power core,
3. a **protected discovery reserve** that maintenance cannot exhaust,
4. optimization/evaluation around **timely first-track discovery under a hard M7 duty budget** on a heterogeneous MCU.

Absence from the first search is not evidence of novelty. A deeper literature pass is mandatory before any paper claim.

## Kill tests — in this order

### K0 — novelty
Search IEEE/ACM/Elsevier/Springer/arXiv for combinations of:
- new-object discovery + adaptive detector invocation,
- detection/refresh budget separation,
- spatial AoI/AoII for visual object discovery,
- low-power always-on watcher + high-power detector,
- first-detection latency under energy/duty constraints.

**Kill D1** if an earlier method already implements the same state, reserve mechanism and objective with only cosmetic differences.

### K1 — clairvoyant feasibility bound
Use **only the existing KITTI validation split** and existing real detector bank. Never open the locked test split.

Question: even with future ground truth and detector hits known, can the corrected 3-tile detector reach the target under M7 duty <= 0.25?

Compute:
- an LP-relaxed maximum-coverage **upper bound** on timely track recall;
- a clairvoyant greedy attainable **lower bound**;
- per-segment and pooled results;
- both corrected cascade cost and an explicitly optimistic cost variant.

Primary decision:
- if the *optimistic LP upper bound* is < 0.90 timely recall at duty 0.25 -> **KILL**;
- if >= 0.90 -> proceed to K2; this only proves headroom exists.


### K1 result (completed before K0 closure)
Validation only; locked test was not opened. Seven KITTI validation segments, 61 moving tracks, duty budget 0.25, detector threshold 0.45.

- Corrected cascade simulated LP upper = **0.8689**; greedy = **0.8689**.
- Deliberately optimistic stage-1-cost / best-stage-hits LP upper = **0.9180**; greedy = **0.9180**.
- The budget was generally not binding; the limiting factor was detector timely-detection ceiling.
- The optimistic pass is thin: 56/61 tracks and only +0.018 above the 0.90 gate.

K1 therefore showed only narrow clairvoyant headroom under an intentionally generous detector model. It does **not** override the K0 novelty failure.

### K2 — M4 observability
**CANCELLED because K0 failed.**

Without using GT at runtime, test whether cheap M4 features can distinguish a **new-track opportunity** from redundant/empty refresh work.

Use validation only, group-separated evaluation. Report AUROC/AUPRC and precision lift at the wake budget.

Proceed only if there is useful separation (pre-registered target: AUROC >= 0.80 or >=2x precision lift over base rate at the allowed wake rate). Otherwise kill or reformulate.

### K3 — simple mechanism before a full algorithm
Implement the smallest possible discovery-debt + refresh-separation scheduler. Compare at equal M7 duty against:
- legacy event trigger,
- uniform periodic sampling,
- R3 scheduler,
- a simple motion/adaptive-frame baseline.

A publishable direction would need a material Pareto shift, not a tiny win. Pre-register before tuning; do not touch test until frozen.

## No-go rules

Do not:
- rename generic frame skipping and call it novelty;
- use locked test data during K0–K3;
- replace measured/simulated cost labels with hardware claims;
- add RL/ML complexity unless the simple mechanism first shows headroom;
- write a paper or claim Q1 readiness before K0–K3 pass.
