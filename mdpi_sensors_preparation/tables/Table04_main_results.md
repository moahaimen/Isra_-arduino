**Table 4.** Main classification results of the primary (PRr) and secondary (PRrM) methods.

| Method | Role | Domain | Layer macro-F1 | Layer balanced acc. | Fault macro-F1 | Fault balanced acc. |
|---|---|---|---|---|---|---|
| PRr | Primary (pre-registered) | Behavioral | 0.656 | 0.660 | 0.668 | 0.670 |
| PRr | Primary (pre-registered) | ngspice | 0.649 | 0.654 | 0.662 | 0.665 |
| PRrM | Secondary (mixed-domain training) | Behavioral | 0.672 | 0.674 | 0.675 | 0.676 |
| PRrM | Secondary (mixed-domain training) | ngspice | 0.663 | 0.666 | 0.671 | 0.673 |

*Monitor E = ±2%, pooled over amplitudes (behavioral ×0.8–×1.2; ngspice ×0.8, ×1.0, ×1.2) and the five phases; mean of 3 dataset seeds × 2 initializations. The behavioral and ngspice rows use different amplitude grids and must not be subtracted; the matched-grid transfer comparison is in Table 9. Nominal reference value N (known reference, ×1.0, pooled over phases): 0.659 behavioral, 0.660 ngspice. Source: attribution_arms.csv; decision_rules.json (N).*
