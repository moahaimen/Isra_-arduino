# Research Gap Matrix

Five categories, compared on the four ingredients the proposed system integrates. Entries for published work describe the cited papers' scope as summarized for this draft; references marked VERIFY in `references.bib` must be checked before submission. **This matrix is provisional until a systematic search (IEEE Xplore, Scopus, Web of Science) is completed; no priority (“first”) claim is made.**

| Category | Representative works | Two-point AFE/ADC observability | Reference monitoring | Phase-robust transients | Neural classifier | Full sensor→ADC chain |
|---|---|---|---|---|---|---|
| Neural-network diagnosis of analog circuits | Aminian & Aminian 2000, Sun, He & Tan 2004, Zhao et al. 2018 | No | No | No | Yes | No |
| Sensor/MEMS BIST and self-validation | Mir et al. 2006, Deb & Blanton 2002, Henry & Clarke | No; Partly (stimulus at sensor) | No | No | No | Partly |
| ADC testing and calibration | IEEE Std 1241, Jin et al. 2005 | ADC point only | Stimulus error handled; Stimulus must be known | No | No | No |
| Sampling-transient analysis | IEEE Std 181, Golub & Pereyra 1973 | No | No | Method used; Partly (transition measures) | No | No |
| Proposed integrated system | This work (simulation) | Yes (R1 at AFE input, R2 at ADC input) | Yes (E up to ±5%) | Yes (free edge time fit) | Yes (MLP) | Yes |

## Gap statement

Within the works listed, neural-network analog diagnosis assumes an ideal stimulus and a single circuit under test; sensor/MEMS BIST and self-validation verify the sensor element; ADC test and calibration isolate the converter; and transient-measurement standards and separable least squares are not applied to phase-invariant fault descriptors. The gap addressed is their integration in one sensor-to-ADC interface:

> The novelty lies in integrating two-point electronic observability, reference-amplitude monitoring, phase-robust transient descriptors, and neural fault classification within a complete sensor-to-ADC interface.

## Evidence that the integration matters (this work, simulation)

- Without the monitor, layer macro-F1 at ×1.2 falls to 0.237 (known reference: 0.643; behavioral).
- Without phase-robust descriptors (R1), the phase range is 0.081 (behavioral, E = ±2%); PRr: 0.005–0.011.
- One-point (AFE-only/ADC-only) baselines are worse than two-point PRr in all 70 comparisons (smallest CI lower bound +0.112).
- Transfer loss behavioral→ngspice: 0.002 [-0.003, +0.006] versus 0.119 in the previous design stage.
