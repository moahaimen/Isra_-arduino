**Table 7.** Reference-monitor robustness: layer macro-F1 versus actual reference amplitude.

| Reference condition | Behavioral ×0.8 | Behavioral ×0.9 | Behavioral ×1.0 | Behavioral ×1.1 | Behavioral ×1.2 | ngspice ×0.8 | ngspice ×1.0 | ngspice ×1.2 |
|---|---|---|---|---|---|---|---|---|
| Known reference | 0.615 | 0.645 | 0.658 | 0.667 | 0.642 | 0.616 | 0.660 | 0.642 |
| Monitor E = 0% | 0.610 | 0.638 | 0.655 | 0.665 | 0.642 | 0.606 | 0.655 | 0.644 |
| Monitor E = ±1% | 0.608 | 0.638 | 0.658 | 0.670 | 0.644 | 0.604 | 0.655 | 0.644 |
| Monitor E = ±2% | 0.614 | 0.647 | 0.673 | 0.681 | 0.663 | 0.611 | 0.671 | 0.664 |
| Monitor E = ±5% | 0.611 | 0.644 | 0.661 | 0.676 | 0.649 | 0.610 | 0.663 | 0.646 |
| No-monitor control (nominal levels assumed) | 0.310 | 0.423 | 0.659 | 0.389 | 0.237 | — | — | — |

*PRr layer macro-F1 pooled over the five phases (mean of three seeds). Monitored variants are trained with the matching error bound E. The no-monitor control is the PRr known-reference classifier given the nominal levels; it was evaluated in the behavioral domain only. Retention relative to N: worst 0.916 at ±20% (known, E ≤ ±2%) and 0.924 at E = ±5%. Source: amplitude_curves.csv; no_monitor_control.json; decision_rules.json (A, D).*
