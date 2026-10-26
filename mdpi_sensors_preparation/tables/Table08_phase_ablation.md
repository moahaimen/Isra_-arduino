**Table 8.** Phase-robustness ablation: layer macro-F1 per edge phase.

| Domain | Arm | ψ = 0 | ψ = 0.25 | ψ = 0.5 | ψ = 0.75 | ψ = 0.999 | Range (max − min) | ≤ 0.05 |
|---|---|---|---|---|---|---|---|---|
| Behavioral | A0 | 0.279 | 0.279 | 0.281 | 0.281 | 0.282 | 0.003 | yes |
| Behavioral | R1 | 0.649 | 0.636 | 0.614 | 0.590 | 0.568 | 0.081 | no |
| Behavioral | R1r | 0.651 | 0.650 | 0.648 | 0.641 | 0.626 | 0.025 | yes |
| Behavioral | PR | 0.657 | 0.656 | 0.655 | 0.655 | 0.653 | 0.004 | yes |
| Behavioral | PRr | 0.659 | 0.658 | 0.656 | 0.653 | 0.652 | 0.006 | yes |
| Behavioral | PRrM | 0.677 | 0.676 | 0.672 | 0.668 | 0.667 | 0.010 | yes |
| ngspice | R1 | 0.642 | 0.625 | 0.606 | 0.584 | 0.561 | 0.081 | no |
| ngspice | R1r | 0.643 | 0.642 | 0.638 | 0.631 | 0.617 | 0.026 | yes |
| ngspice | PR | 0.649 | 0.648 | 0.647 | 0.644 | 0.642 | 0.007 | yes |
| ngspice | PRr | 0.654 | 0.651 | 0.649 | 0.645 | 0.643 | 0.010 | yes |
| ngspice | PRrM | 0.667 | 0.665 | 0.664 | 0.659 | 0.658 | 0.009 | yes |

*Layer macro-F1 per edge phase, monitor E = ±2%, pooled over amplitudes; range computed as max − min of the five stored phase values. Gate G itself applies to PRr (known reference and E = ±2%; Table 5): PRr ranges 0.005 / 0.006 (behavioral known / E2) and 0.011 / 0.010 (ngspice). A0 was not simulated in ngspice; its flat profile reflects uniformly low accuracy. Source: attribution_arms.csv; decision_rules.json (G).*
