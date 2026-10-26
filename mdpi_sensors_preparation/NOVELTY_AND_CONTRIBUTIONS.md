# Novelty and Contributions

## Defensible novelty statement

> The novelty lies in integrating two-point electronic observability, reference-amplitude monitoring, phase-robust transient descriptors, and neural fault classification within a complete sensor-to-ADC interface.

No component is claimed as new in isolation: two-point testing, reference monitoring, transient fitting and MLP classifiers are each established. The contribution is the integrated design and its pre-registered evaluation. Wording to avoid: “first”, “state-of-the-art”, “outperforms existing methods”, “deep learning”, any hardware claim.

## Contributions and supporting evidence

| # | Contribution | Evidence (simulation) | Where |
|---|---|---|---|
| 1 | Two-point active self-test making AFE and ADC faults separately observable | AFE–ADC cross-confusion ≤ 0.089 with known/monitored reference; one-point baselines worse in all 70 comparisons (min CI lower bound +0.112) | Fig. 1, 7; Tables 6, 10 |
| 2 | Settled-plateau calibration + phase-robust transient descriptors (free edge time fit) | PRr phase range 0.005–0.011 vs R1 0.081; PR − R1 = +0.042 [+0.033, +0.051] (behavioral) | Fig. 2, 5, 9; Table 8 |
| 3 | Reference monitor compensating reference drift, tested at E = 0/±1/±2/±5% | Retention ≥ 0.916 at ×0.8/×1.2 and ≥ 0.924 at ±5%; no monitor: 0.310 (×0.8), 0.237 (×1.2) | Fig. 6; Table 7 |
| 4 | Compact MLP (20–96–48, 6,868 / 7,113 parameters) | Layer macro-F1 0.656 (behavioral grid) and 0.649 (ngspice grid), E = ±2% | Tables 4, 12 |
| 5 | Pre-registered behavioral→ngspice validation with ablation | Decision GO; transfer loss 0.002 [-0.003, +0.006] (limit 0.10) | Fig. 8, 9; Tables 5, 9 |

## Secondary finding (not a contribution claim)

PRrM (mixed-domain training) improves layer macro-F1 by +0.017 [+0.008, +0.025] (behavioral) and +0.014 [+0.005, +0.024] (ngspice) relative to PRr, but uses circuit-level training data and was not pre-registered as primary.
