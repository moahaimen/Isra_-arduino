# Simulation method

Secure Dual-Core Event-Triggered Object Detection for Always-On Edge Vision.
Target architecture: STM32H747 (Arduino Portenta H7), Cortex-M4 watcher +
Cortex-M7 detector. **Everything in this document describes a simulation
model.** Parameter values are simulation assumptions unless a calibration
source is named; none has been measured on hardware yet.

Legend used throughout: **[A]** assumption / simulator parameter,
**[O]** simulated observation, **[D]** derived metric, **[H]** future
physical measurement.

## 1. Architecture

```
            workload trace (JSONL, generated once per scenario+seed)
                      │  Observable fields only        │ GroundTruth (evaluator only)
                      ▼                                ▼
 ┌──────────────── Cortex-M4 ────────────────┐     observations.csv
 │ M4_MONITOR ─► M4_PROCESS (watcher score)   │
 │   ├─ below θ_t ─► ignore                   │
 │   ├─ cooldown  ─► TRIGGER_SUPPRESSED       │
 │   └─ TRIGGER ─► SECURITY_PROCESSING        │
 │        ├─ SECURITY_BLOCK (never reaches M7)│
 │        └─ SECURITY_ACCEPT ─► RPC_COMMUNICATION
 └───────────────────────────│────────────────┘
                 RPC channel (latency, jitter, contention, loss)
 ┌──────────────── Cortex-M7 ────────────────┐
 │ RPC_RECEIVE ─► queue (capacity K) ─► WAKE   │
 │ M7_WAKEUP ─► M7_INFERENCE (stage 1)         │
 │   ├─ early exit (c ≥ τ_hi or c ≤ τ_lo)      │
 │   └─ M7_SECOND_PASS (stage 2)               │
 │ M7_POSTPROCESS ─► RESULT ─► RPC back to M4  │
 │ queue empty ─► (linger) ─► M7_SLEEP          │
 └────────────────────────────────────────────┘
```

Source layout:

| component | path |
|---|---|
| discrete-event core | `simulation/core/simulator.{h,cpp}` |
| platform-independent RNG | `simulation/core/rng.h` |
| configuration registry / CLI | `simulation/config/sim_config.{h,cpp}`, `config/default_config.json` |
| workload generator | `simulation/workload/workload.{h,cpp}` |
| watcher (firmware-portable) | `simulation/watcher/watcher.h` |
| security gate (firmware-portable) | `simulation/security/security_gate.h` |
| RPC model | `simulation/communication/rpc_model.h` |
| detector backends | `simulation/detector/detector.{h,cpp}` |
| power-state energy | `simulation/energy/energy_model.{h,cpp}`, `config/power_model.json` |
| JSONL event log | `simulation/logging/event_log.{h,cpp}` |
| CLI entry point | `simulation/app/sim_main.cpp` (binary `build/edge_sim`) |
| Arduino mocks (millis/delay/RPC) | `simulation/core/arduino_mocks.h` |

Time is continuous (double, milliseconds). Events are processed in time order
with insertion order as tie-break, so a run is a pure function of
configuration and workload. The M4 is a serial server (one observation at a
time); the M7 is a serial server with a FIFO request queue.

## 2. Workload and ground truth

### 2.1 Schema

One JSON object per line, fixed key order, scores rounded to 1e-4 and times to
1e-3 ms so that files are byte-identical across repeated generation:

| field | role | description |
|---|---|---|
| event_id | id | 1..N in time order, unique |
| timestamp_ms, duration_ms | observable | onset and visibility of the stimulus |
| motion_score, visual_score, temporal_change_score, sensor_consistency_score, noise_score | observable | M4 sensing features in [0,1] |
| content_signature | observable | 64-bit perceptual hash of the captured frame |
| scenario, episode_id, episode_type, burst_id | ground truth | generating process |
| is_legitimate, attack_type, replay_id | ground truth | attack labels |
| object_present, object_class | ground truth | real object in the scene |
| ground_truth_action | ground truth | `detect` (real object), `ignore` (benign), `block` (attack) |
| frame_has_object, frame_object_class | physical frame content | what the camera images (a replayed frame shows the recorded object although none is present) |

The watcher and security gate receive only the *observable* fields (a
separate C++ struct). `frame_has_object` is used only by the detector model,
which simulates what the camera physically captures. The audit
(`scripts/audit_scientific.py`) verifies, by scrambling every ground-truth
label and re-running, that no decision changes.

### 2.2 Stochastic processes [A]

Legitimate activity is an **episode** process: a two-state Markov-modulated
Poisson process (CALM/ACTIVE). In state s, episodes arrive as Poisson with
rate λ_s; the state switches after exponential holding times. Each episode is
an `object` (real object), `benign_motion` (foliage, lighting, shadows) or
`noise` (sensor flicker) episode with fixed type probabilities.

* object episode: 1 + Poisson(2) repeated observations spaced U(0.5, 1.5) s,
  visibility v ~ N(0.70, 0.12) per episode; per observation
  visual = v + N(0, 0.06) − 0.3·max(0, noise − 0.15),
  motion ~ N(0.62, 0.15), temporal = motion + N(0, 0.08),
  consistency ~ N(0.86, 0.06) − 0.25·max(0, noise − 0.15);
  with probability 0.15 a repeated observation is a static frame (same
  signature, features within ±0.005). Class: person 0.50, vehicle 0.25,
  animal 0.15, package 0.10.
* benign motion: 1 + Poisson(0.5) observations; motion N(0.55, 0.18),
  visual N(0.30, 0.12), temporal = motion + N(0, 0.10), consistency N(0.80, 0.08).
* noise: 1 + Poisson(0.3) observations; noise level raised by 0.25;
  motion N(0.30, 0.15), visual N(0.22, 0.10), temporal N(0.50, 0.20), consistency N(0.60, 0.15).
* legitimate bursts (crowds, platoons): Poisson burst arrivals, each with
  U{min..max} episodes (80 % objects) spread over a span ≤ burst_span_s.

Scenario parameters (rates per second; `normal` is the reference):

| scenario | λ_calm | λ_active | calm→active | active→calm | object/benign/noise | noise base | bursts | attacks |
|---|---|---|---|---|---|---|---|---|
| quiet | 1/240 | 1/40 | 1/1800 | 1/300 | .60/.30/.10 | 0.08 | none | none |
| normal | 1/60 | 1/12 | 1/600 | 1/180 | .55/.30/.15 | 0.12 | 1/1200, 3–6 in 5 s | none |
| busy | 1/15 | 1/4 | 1/300 | 1/300 | .65/.25/.10 | 0.15 | 1/600, 3–6 | none |
| burst | as normal | | | | | | 1/180, 8–20 in 10 s | none |
| noisy | as normal | | | | .45/.25/.30 | 0.40 | as normal | none |
| trigger_spam | as normal | | | | | | as normal | spam sessions 1/300 × I |
| replay | as normal | | | | | | as normal | replay sessions 1/240 × I |
| mixed | as normal | | | | | | 1/900 | spam 0.5/300 × I, replay 0.5/240 × I |

I = `--attack-intensity` (default 1). Separate seeded sub-streams generate
the legitimate, burst, spam and replay processes, so for the same seed the
legitimate background of `normal`, `trigger_spam`, `replay` and an
intensity sweep is identical; only the attack layer changes.

**Trigger spam [A]:** sessions with exponential duration (mean 60 s); inside a
session fake triggers arrive as Poisson(3/s), duration U(100, 300) ms, fresh
signatures. A fraction `spam_sophistication` (0.3) mimics consistent
sensors (motion N(0.70,0.10), visual N(0.65,0.10), temporal ≈ motion,
consistency N(0.85,0.06)); the rest inject only the motion channel
(motion U(0.7,1), visual U(0.3,0.8), temporal U(0.2,0.7), consistency U(0.1,0.5)).
The camera sees an empty scene (`frame_has_object = false`).

**Replay [A]:** at Poisson session times the attacker replays a recorded
legitimate object episode whose onset lies 10 s–30 min in the past,
reproducing the recorded relative timing, 1–3 repetitions. With probability
`replay_perturb_prob` (0.3) each replayed frame is perturbed (features
+N(0, 0.03), new signature) to defeat exact hashing. `replay_id` names the
original event. The replayed frame still shows the recorded object.

## 3. M4 watcher [A]

S_t = w_m·motion + w_v·visual + w_t·temporal + w_c·consistency, with
(w_m, w_v, w_t, w_c) = (0.30, 0.35, 0.20, 0.15).

Adaptive threshold (proposed): n̂_t = α·noise_t + (1 − α)·n̂_{t−1}, α = 0.05,
θ_t = θ + g·max(0, n̂_t − n_ref), θ = 0.55, g = 0.5, n_ref = 0.15.
Fixed threshold: θ_t = θ. Motion-only baseline: motion_t ≥ 0.55.

Trigger_t = 1 if S_t ≥ θ_t and t − t_last_trigger ≥ cooldown (1500 ms), else
0. Each evaluation costs `m4_process_ms` = 1 ms of M4_PROCESS.

## 4. Security gate [A]

Runs on the M4 for every trigger (cost 0.4 ms SECURITY_PROCESSING). History:
ring buffer of the last 512 observed frames (signature, features, time),
plus trigger-candidate and accepted-trigger timestamps. Checks in order:

1. CONSISTENCY_FAILURE: c = min(consistency, 1 − |motion − temporal|) < 0.5.
2. DUPLICATE: identical signature within 2 s.
3. REPLAY: identical signature, or L∞ feature distance < 0.01, at age in
   (2 s, 600 s].
4. BURST: more than 10 watcher-positive candidates (including cooldown-
   suppressed ones) in the last 5 s.
5. RATE_LIMIT: at least 20 accepted triggers in the last 60 s.

A blocked trigger never sends an RPC and never wakes the M7. The legacy
probability blocking exists only as `--debug-random-block-prob` (default 0);
runs that use it are marked `research_valid: false`.

## 5. RPC / inter-core communication [A]

Transmission t_tx = 0.5 ms + 0.2 ms·|N(0,1)|; a single channel carries one
message at a time (requests and results contend), so channel wait =
max(0, channel_free − t_request). Loss: Bernoulli(`rpc_loss`, default 0) on
requests; with loss 0 no message is dropped. M7 request queue capacity 8;
an arriving request finding 8 waiting requests is dropped (QUEUE_FULL).
Queue delay = start of service − max(enqueue time, end of wake-up); the
wake-up share is reported separately (`wake_wait_ms`). No retransmission.

## 6. M7 detector workload model [A]

Backends: `synthetic_distribution` (default) and `trace_replay`
(`data/detector_traces/README.md`). Synthetic model, with draws keyed by
(seed, event_id, stage) so every mode sees the same outcome for the same event:

* stage 1: logit z ~ N(μ, 0.9), μ = 1.4 + 2(visual − 0.6) − 2.5·max(0, noise − 0.15)
  for a frame with an object, μ = −1.6 + (visual − 0.3) + max(0, noise − 0.15) otherwise;
  confidence c = σ(z); class correct with probability min(0.99, 0.55 + 0.40c);
  latency log-normal, median 140 ms, σ_log 0.08.
* stage 2 (second pass): z₂ = z + N(0.6, 0.5) with object, z + N(−0.5, 0.5) without;
  class correct with probability min(0.99, 0.65 + 0.33c₂); latency median 110 ms.
* postprocessing: 6 ms + 1.5 ms per box; boxes = 1 + Poisson(0.4) if detected.
* detection: final confidence ≥ 0.5. Wake-up latency 3 ms. No linger (0 ms).

**Early exit:** after stage 1, stop if c ≥ 0.80 or c ≤ 0.15; otherwise run stage 2.
With early exit disabled, every frame runs stage 2.

mAP is never computed for the synthetic backend (no boxes). It is computed by
`scripts/eval_energy/map_eval.py` only for traces with real box annotations.

## 7. Operating modes and baselines

| mode | watcher | adaptive θ | cooldown | security | early exit |
|---|---|---|---|---|---|
| always_on | none, M7 runs back-to-back inference | – | – | – | on |
| motion_only | motion ≥ 0.55 | no | yes | no | off |
| fixed_threshold | score ≥ θ | no | yes | no | off |
| event | score ≥ θ_t | yes | yes | no | on |
| event_no_early_exit | score ≥ θ_t | yes | yes | no | off |
| secure | score ≥ θ_t | yes | yes | yes | on |

In always_on the M7 captures a frame at the start of each inference cycle
and processes the earliest still-visible observation (or an empty
background frame); the M4 is idle. All shared parameters are identical
across modes; the audit verifies this from every run's `config.json`.
Literature baselines can be added as further modes in
`apply_mode_defaults`; no external results are reproduced or invented.

## 8. Energy model

See `docs/ENERGY_MODEL.md`. E_s = P_s·T_s, E_total = Σ_s E_s, one state per
core at any time.

## 9. Metrics (definitions in `scripts/eval_energy/metrics.py`)

* Duty cycle D = Σ_j (t_sleep,j − t_wake,j) / T.
* Trigger-to-result latency L_i = t_result_delivered,i − t_trigger,i (event modes).
  Onset-to-result latency = t_result − t_observation_onset (all modes, used for
  cross-mode comparison). Episode latency = first correct detection − episode onset.
* Watcher (observation level, positive = `detect`): TP/FP/FN/TN, precision,
  recall, F1, false-trigger rate FP/(FP+TN), missed-event rate FN/(TP+FN).
* Detector (processed legitimate frames): TP = object present, detected,
  class correct; FP = detected and (no object or wrong class); FN = object
  not correctly detected. Classification accuracy, confidence statistics.
* System: object-episode recall (episode detected at least once), false
  alarms (detections on frames without a real object, attack-induced ones
  counted separately).
* Security (gate level, positive = attack): ADR = blocked attacks / attacks
  reaching the gate; FRR = blocked legitimate / legitimate reaching the gate;
  FRR on real objects; precision, F1; block rate R = N_blocked/(N_blocked+N_accepted).
  End-to-end attack success rate = attack observations that reached M7
  execution / all attack observations.
* Communication: RPC latency (channel wait + transmission) statistics, queue
  delay, drops by reason.
* Energy: total, per minute, per observation, per accepted trigger, per useful
  and per correct detection, M4/M7 split, security energy, saving
  1 − E_mode/E_always_on on the same workload.

All ratios return NaN for an empty denominator.

## 10. Determinism

Same configuration + same workload ⇒ byte-identical outputs (tested). The
RNG and all distributions are implemented in `rng.h` instead of the
implementation-defined `<random>` distributions. Bit-identity is guaranteed on
the same platform and toolchain; `std::log`/`std::cos` may differ in the last
ulp across C libraries, which the fixed-precision output usually but not
provably hides.

## 11. Limitations

* All timing and power values are assumptions [A] pending hardware calibration.
* The detector is a parametric model, not a CNN; detection quality numbers
  describe the model, not a real network.
* Features are synthetic; the watcher has not been evaluated on real sensor data.
* Attack models are stylised; an adaptive attacker who learns the thresholds
  is not modelled.
* The cooldown is global (not per object), which by design suppresses
  concurrent objects in bursts.
* Inter-core RPC is modelled abstractly (no cache, bus or OS effects).
* The M4 watcher is evaluated per observation; continuous sampling between
  observations is folded into the M4_MONITOR power state.
