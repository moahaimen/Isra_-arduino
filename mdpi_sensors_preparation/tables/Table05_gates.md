**Table 5.** Pre-registered gate results for the primary method PRr.

| Gate | Criterion | Threshold | Observed (PRr) | 95% CI | Behavioral | ngspice |
|---|---|---|---|---|---|---|
| A | Retention at ×0.8 and ×1.2 (known, E ≤ ±2%) | ≥ 0.85·N | worst 0.916 (ngspice, monitor E = ±1%, ×0.8) | — | PASS | PASS |
| B | Superiority over old method and one-point baselines (behavioral) | pooled CI lower bound > 0 | smallest lower bound +0.112 over 70 comparisons | per comparison, Table 6 | PASS | — |
| C | AFE–ADC cross-confusion at ×0.8 and ×1.2 | < 0.15 | largest 0.089 (behavioral, known reference, ×1.2) | — | PASS | PASS |
| D | Retention with monitor E = ±5% | ≥ 0.70·N | worst 0.924 (ngspice, ×0.8) | — | PASS | PASS |
| E | Behavioral → ngspice transfer loss (E = ±2%, ngspice grid) | ≤ 0.10 (point estimate) | 0.002 | [-0.003, +0.006] | PASS | — |
| F | Every claimed improvement supported by a paired-bootstrap CI excluding zero | CI excludes 0 | satisfied | 5000 resamples | procedural† | procedural† |
| G | Layer macro-F1 range over five phases (known, E = ±2%) | ≤ 0.05 | largest 0.011 (smallest 0.005) | — | PASS | PASS |

*Decision: GO (0 failed gates). N = PRr layer macro-F1 with known reference at ×1.0 (0.659 behavioral, 0.660 ngspice). †Gate F has no separate key in decision_rules.json; it was checked here against the saved CIs. The mixed-domain variant PRrM also passes the ngspice-domain gates (reported only). Source: decision_rules.json (gates, A–E, G details); PROTOCOL_PHASE_ROBUST_FROZEN.md §5 (thresholds).*
