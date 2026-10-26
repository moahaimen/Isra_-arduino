**Table 9.** Behavioral-to-ngspice domain transfer (layer macro-F1).

| Reference condition | Behavioral BB (PRr) | ngspice BS (PRr) | Transfer loss BB − BS | 95% CI | ≤ 0.10 | ngspice MS (PRrM) | MS − BS [95% CI] |
|---|---|---|---|---|---|---|---|
| Known reference | 0.639 | 0.639 | -0.001 | [-0.005, 0.004] | PASS | 0.677 | +0.038 [+0.029, +0.047] |
| Monitor E = 0% | 0.636 | 0.635 | 0.001 | [-0.003, 0.004] | PASS | 0.675 | +0.040 [+0.031, +0.050] |
| Monitor E = ±1% | 0.637 | 0.634 | 0.002 | [-0.001, 0.006] | PASS | 0.670 | +0.036 [+0.027, +0.045] |
| Monitor E = ±2% | 0.650 | 0.649 | 0.002 | [-0.003, 0.006] | PASS | 0.663 | +0.014 [+0.005, +0.024] |
| Monitor E = ±5% | 0.640 | 0.640 | 0.001 | [-0.003, 0.005] | PASS | 0.655 | +0.015 [+0.006, +0.024] |
| Previous stage, E = ±2% (REVISE) | 0.658 | 0.539 | 0.119 | [0.107, 0.132] | FAIL | — | — |

*Matched grid: ×0.8, ×1.0, ×1.2 × five phases in both domains. BB and BS use the same behavioral-trained PRr classifier; MS is the mixed-trained secondary variant PRrM. The pre-registered gate E uses E = ±2%. The previous-stage row is the failed earlier validation (reference_monitor_final), read from paper_package/NUMBER_PROVENANCE.csv because its decision file is not in the evidence package. Source: decision_rules.json (E).*
