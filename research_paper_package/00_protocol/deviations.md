# Deviations and additions (relative to the user's prompt)

1. **Added criterion S1** (mode attribution). The prompt's P1/P2 compare a clairvoyant oracle with causal baselines; a clairvoyant
   oracle that knows when objects appear can win by temporal skipping alone, which R3.1 and D1 already studied and closed.
   S1 checks that the LOW/ROI modes, the part that distinguishes this proposal, add ≥ 20 % savings beyond a {SKIP, FULL} oracle.
   It can only make the gate stricter.
2. **No simulated M7 queueing.** Results of every invocation count at the invoked frame, for all policies and the oracle alike.
   R3/R3.1 used a simulated M7 latency (~140 ms/frame, modelled). This makes all timely-recall values optimistic by the same rule.
3. **Detector.** Only EfficientDet-Lite0 INT8 (host-reference, COCO-trained) has real mode-specific outputs obtainable here.
   TinyissimoYOLO (MCU target) has no published checkpoint; the CPU-trained R2/R3 checkpoints were not preserved and failed
   R3 Gate A (timely ceiling 0.57 / 0.27). It is not used.
4. **Baseline B4.** The R3/R3.1 utility-gated scheduler is not re-run; R3.1 Gate B (LOGO) showed it dominated by MOG2-event and the legacy
   event trigger. MOG2-event stands in as the strongest existing adaptive scheduler.
5. **Published adaptive method (prompt item 8.7).** No 2023–2026 adaptive-inference method in novelty_audit.md could be reproduced
   faithfully with one detector and these modes (they require multi-branch models, trackers or GPU-class hardware). Not included.
6. **Datasets.** BDD100K/MOT17 were not used: MOT17/HF/PyTorch hosts were blocked in R2/R3 and BDD100K needs a login. KITTI only.
7. **Proposal .docx** (`Heterogeneous_Dual_Core_Object_Detection_Research_Proposal.docx`) was not found in the repo, the project files,
   or any git branch. The protocol follows the prompt text.
