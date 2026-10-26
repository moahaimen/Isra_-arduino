**Table 2.** Fault taxonomy: nine fault classes and their physical location.

| # | Fault class | Layer | Physical location | Severity range (simulated) | Primary observability |
|---|---|---|---|---|---|
| 0 | Healthy | — | — | no fault injected | — |
| 1 | Sensor bias | Sensor | Sensor element / sensor output | ±U(0.06,0.24) V | Passive sensor segments only (references replace the sensor) |
| 2 | Sensor gain | Sensor | Sensor element (sensitivity) | ±U(6,28)% | Passive sensor segments only (references replace the sensor) |
| 3 | Sensor noise | Sensor | Sensor element (excess noise) | U(25,95) mV rms | Passive sensor segments only (references replace the sensor) |
| 4 | AFE offset | AFE | Amplifier stage (offset) | ±U(0.06,0.24) V | R1 window, after removing the ADC transfer from R2 |
| 5 | AFE bandwidth | AFE | RC low-pass filter (time constant τ) | tau x U(1.8,4.5) | R1 window, after removing the ADC transfer from R2 |
| 6 | ADC offset | ADC | ADC (offset) | ±U(0.06,0.24) V | R2 window (bypasses the AFE) |
| 7 | ADC gain | ADC | ADC (gain) | ±U(6,28)% | R2 window (bypasses the AFE) |
| 8 | ADC clipping | ADC | ADC input range (clipping) | full scale x U(0.72,0.93) | R2 window (bypasses the AFE) |

*Severity ranges parsed programmatically from the 'Faults (severity)' row of paper_package/PAPER_TABLES.csv (src/simulate.py: make_fault). Layer assignment follows the four-class layer label used by the classifier.*
