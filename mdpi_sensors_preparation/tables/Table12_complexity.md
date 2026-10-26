**Table 12.** Model and computational complexity.

| Quantity | Value | Source |
|---|---|---|
| MLP architecture | 20–96–48 hidden layout; 20 inputs; ReLU; output 4 (layer) or 9 (fault) | PAPER_TABLES.csv T10; parameter count check |
| MLP parameters | 6,868 (layer head); 7,113 (fault head) | timing_and_parameters.json |
| Multiply-accumulates per inference | 6,720 (layer); 6,960 (fault) | derived from the architecture |
| MLP inference time | 0.68 µs per record (batched, Python, mean of 3 seeds) | timing_and_parameters.json |
| Descriptor extraction time | Phase-robust 0.79 ms; Revision-1 0.47 ms per record (Python, 1 core) | timing_and_parameters.json |
| MLP training time (PRr models) | mean 0.72 s, max 1.49 s per model | seed_*/model_info.json |
| ngspice runs | 13,878 per seed; 41,634 total | seed_*/meta.json |
| Validation runtime per seed | 20261026: total 1175.6 s (ngspice wall 908.1 s, behavioral 707.7 s); 20261027: total 1179.0 s (ngspice wall 908.9 s, behavioral 708.5 s); 20261028: total 1179.1 s (ngspice wall 905.9 s, behavioral 703.8 s) | seed_*/meta.json |
| ngspice workers | 3 parallel workers | timing_and_parameters.json |
| Important assumptions | Timings are desktop Python (macOS arm64) measurements, not microcontroller measurements; no energy, power, area or hardware cost was measured | REPRODUCIBILITY_CHECKLIST.md (environment) |

*No embedded-target timing or energy figure exists in the evidence package; none is claimed.*
