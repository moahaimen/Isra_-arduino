# CAGE C0 — compact specification (hypothesis; may fail)
Research question: can an adversary that controls what the camera sees exploit *both* the wake decision and the input-dependent M7 detector cost to amplify total energy/work, and can an always-on M4 guardian bound that amplification while keeping legitimate events serviceable?
No novelty is claimed (prior art: event-triggered/wake-up vision, denial-of-sleep, cooldown/token buckets, replay checks, DNN energy-latency attacks, bounded NMS). The *hypothesis* is the joint treatment: pre-wake admission driven by measured post-wake cost, a protected legitimate reserve, and an end-to-end malicious-work bound.

## Threat model (evaluation scope: simulation on real frame traces)
* Attacker controls the scene content seen by the camera (physical/displayed content, or injected frames), not the M4/M7 firmware, not the power supply. Capabilities used here are **frame selection/ordering from natural frames and existing bounded transformations only** — no adversarial-example crafting, no gradient access. Knowledge levels: (K0) none/oblivious; (K1) knows the watcher/cooldown and detector cascade structure (cost drivers); (K2, adaptive, C4 only) also knows CAGE's budget structure.
* Goal: maximise extra M7 work/energy per unit time while staying under any visible rate limit; secondary goal: starve legitimate events (reserve stealing); tertiary: poison cost history so legitimate expensive events get punished (feedback poisoning).

## Quantities
Per event x_t: wake score S(x) (watcher), downstream cost C(x) (M7 busy time ms ⇒ energy via the assumed power model; modeled, not measured). Benign reference energy E_ben over the same duration/scene.
* Joint attack objective (per time budget T): max over admissible sequences {x_t} of Σ_t 1[wake(x_t)]·C(x_t), i.e. maximise P(wake|x)·C(x) jointly, not either factor alone.
* CEAF = E_attack / E_benign (same duration, same device model). Cross-stage gain G = CEAF(Joint) / max(CEAF(WakeOnly), CEAF(InferenceOnly), CEAF(Naive)).

## CAGE state and rule (M4)
State: cost/risk history H (small table keyed by compact scene signature: bucketed 8×4 thumbnail hash + region count) holding running mean μ_C, deviation σ_C, risk R∈[0,1]; budgets B_G (general work budget, ms of M7 work) and B_R (protected reserve), each a token bucket with capacity K_G,K_R and refill r_G,r_R (ms of work per s).
1. Reject if watcher evidence below threshold (no wake). 2. Utility U = persistence·novelty·quality evidence ∈[0,1] (legitimate events: sustained, new region). 3. Look up H(sig): C_safe = μ_C + κ·σ_C (prior μ_0 if unseen). 4. Action:
 REJECT if R ≥ R_rej, or B_G < C_safe·c_min and not eligible for reserve;
 PROTECTED if U ≥ U_hi, R < R_prot, and B_R ≥ C_safe (charges B_R);
 NORMAL if B_G ≥ C_safe (charges B_G); LIMITED otherwise if B_G ≥ C_min (charges B_G, contract smaller).
5. Contract = (MaxWork, MaxLatency, Priority): MaxWork = min(C_safe·(1+δ), remaining budget), MaxLatency = L_max. M7 runs the detector under the contract; if MaxWork/MaxLatency is reached it terminates stage 2 / truncates candidates (bounded candidate set N_max) and returns partial result.
6. Feedback = (energy, latency, work C_act, candidate load, detection utility). Amplification A = C_act/(C_safe+ε). Update H: μ_C,σ_C by EMA; R ← R + η·max(0, A−1)·(1−u) − decay, where u is detection utility (useful expensive events are *not* punished: if detection utility is high the risk increment is scaled down). 7. Refund unused contract work to the originating bucket. 8. Refill B_G,B_R independently; ordinary (low-U or high-R) events can never charge B_R.

## Candidate properties (to test, not assume)
* Malicious-work bound: over any window W, M7 work admitted ≤ K_G + r_G·W + K_R + r_R·W (+ per-contract overrun ≤ δ·MaxWork), regardless of the input stream. Holds by construction only if the contract is enforced; the contract enforcement itself is simulated here, not implemented on M7.
* Availability: legitimate events with U ≥ U_hi and R < R_prot are served from B_R as long as their arrival work ≤ r_R (+K_R burst); LAR measures the realised fraction.

## Known attack vectors on CAGE (C4, only if C2 passes)
Reserve stealing: craft events that look high-U and low-R but are costly. Feedback poisoning: make legitimate expensive events look anomalous by first training H with benign-cheap lookalikes then switching. Budget-aware attacker: operate at the refill rate. Open weakness: signature collisions; U is gameable if persistence/novelty are observable.

## Gates
C1 (attack kill test): GO iff G ≥ 1.5 (and absolute CEAF(Joint) > 1.5). Else NO-GO, stop. C2 only if C1 GO: CAGE vs strongest composed baseline (cooldown + wake limiter + work budget); targets LAR ≥ 0.95, FRR < 0.05, benign overhead < 5 %, malicious excess ↓ ≥ 80 %.
No contradiction found in C0 → proceed to C1.
