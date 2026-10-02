# Energy model

**All energy reported by this project is MODELED energy.** It is computed
from simulated state durations and power values that are simulation
assumptions (`config/power_model.json`: `"source": "simulation_assumption"`,
`"calibrated": false`). It is not a measurement and must not be presented as
physical energy saving until the power values are calibrated per
`docs/HARDWARE_VALIDATION_PLAN.md`. Duty-cycle reduction is reported
separately and is not, by itself, an energy claim.

## States

Each core is in exactly one state at any time; the simulator tracks
transitions (`CoreStateTracker`) and integrates state time over [0, T].

| state | core | assumed power (mW) | entered when |
|---|---|---|---|
| M4_IDLE | M4 | 5 | always_on mode (watcher unused) |
| M4_MONITOR | M4 | 60 | watcher sensing loop, between observations |
| M4_PROCESS | M4 | 90 | computing watcher features/score (1 ms per observation) |
| SECURITY_PROCESSING | M4 | 95 | security gate checks (0.4 ms per trigger) |
| RPC_COMMUNICATION | M4 | 85 | M4 sending a request (incl. channel wait) |
| M7_SLEEP | M7 | 8 | M7 stopped |
| M7_WAKEUP | M7 | 150 | leaving sleep (3 ms) |
| M7_INFERENCE | M7 | 420 | stage-1 inference (includes frame capture) |
| M7_SECOND_PASS | M7 | 420 | stage-2 inference |
| M7_POSTPROCESS | M7 | 300 | box decoding / NMS / result packaging |
| M7_IDLE_AWAKE | M7 | 200 | awake but idle (linger; always_on bookkeeping) |

The values are order-of-magnitude placeholders chosen only so that the
relative ordering of states is plausible for an STM32H747 with a camera. The
result message sent by the M7 is accounted inside M7_POSTPROCESS; the M4's
reception of results is not modelled separately.

## Equations

E_s = P_s · T_s  (mW · ms / 1000 = mJ)

E_total = Σ_s E_s = E_M4 + E_M7

Energy per minute = E_total / (T / 60 000 ms); per useful detection =
E_total / N_useful; per correct detection = E_total / N_correct; per accepted
trigger = E_total / N_delivered requests.

Modeled saving relative to always-on on the same workload:
Saving = 1 − E_mode / E_always_on.

Duty cycle D = T_active / T with T_active = Σ_j (t_sleep,j − t_wake,j).

## Checks

* Unit test (`tests/cpp/unit_tests.cpp::test_energy_tracker`) integrates a
  hand-computed state sequence: 850 ms sleep, 3 ms wake, 140 ms inference,
  7 ms postprocess → 68.15 mJ exactly.
* Integration test 10 and the validator check that per-core state times sum
  to T (no double counting) and that the Python recomputation equals the
  simulator's energy.

## Sensitivity to the assumptions

Because E_total is linear in the power values, the effect of any power
assumption can be evaluated exactly without re-simulation:
`aggregate.energy_model_sensitivity` rescales M4_MONITOR, M7_INFERENCE,
M7_SLEEP and M7_WAKEUP by ×0.25…×4 and recomputes the saving for every run
(`aggregate/energy_model_sensitivity.csv` of the main campaign). The always-
on M4_MONITOR power dominates event-mode energy under the default
assumptions, so its calibration is the single most important hardware
measurement for any energy claim.
