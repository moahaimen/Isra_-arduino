# R3 algorithm: Security-aware Utility-Gated Scheduler (S-UGS)

Code: `simulation/watcher/ugs_scheduler.h` (scheduler, modes `ugs_event` and
`ugs_secure`), `simulation/security/ugs_gate.h` (security gate, mode
`ugs_secure`), `simulation/watcher/frame_features.h` (M4 features,
bit-identical to `scripts/r2/frame_features.py`). All three are header-only,
fixed-size, heap-free C++ compiled both into the simulator and into the
M4 firmware host check (`firmware/host_check_r3.cpp`).

## Problem

An always-on camera node has a cheap core (M4) that sees every frame and an
expensive core (M7) that runs the detector. Waking the M7 costs energy (wake
transient, RPC, inference, optional second pass). The M4 must decide, frame
by frame and causally, whether a wake is worth its cost, while attackers try
to (i) waste M7 activations (trigger spam, denial of sleep) and (ii) make the
M7 process stale content (replay). R2 showed that (a) a single conservative
threshold misses real objects, (b) a global cooldown suppresses legitimate
bursts, (c) "looks like an old frame" replay rules reject static live scenes,
and (d) wake budgets never engage.

## Observable inputs per frame t (no labels, no future, no current M7 output)

* gain-compensated features m, v, tau, c of the 96x32 frame (R2 front end)
  and the score S_t = 0.30 m + 0.35 v + 0.20 tau + 0.15 c;
* the 12x4 motion-cell mask M_t;
* a 24x8 block thumbnail T_t (4x4 block means) and the foreground bit count;
* the M7 power state, the number of the M4's outstanding requests;
* RESULTS of earlier M7 inferences returned over RPC: the 12x4 cell mask D
  of the boxes the detector reported (closed loop, strictly past).

## 1. Noise-normalised evidence with persistence (replaces single-frame thresholds)

```
b_t, s_t = median, max(1.4826 MAD, s_floor) of idle scores      (prior b0, s0 until 8 samples)
b_t <- min(b_t, b_cap),  s_t <- min(s_t, s_cap)                  (bounded: noise cannot raise them indefinitely)
z_t = (S_t - b_t) / s_t
e_t = clip(z_t - z0, 0, e_max)        if S_t >= S_floor, else 0  (bounded excess evidence)
A_t = rho A_{t-1} + e_t                                          (leaky accumulator)
ACTIVE  <- A_t >= a_on ;  IDLE <- A_t < a_off                    (hysteresis)
```
With e_max < a_on no single frame can activate the watcher (one-frame
flashes and noise spikes are rejected), strong evidence activates on the
second frame, and weak but persistent evidence after a few frames (the R2
watcher missed these).

## 2. Content regions with novelty (replaces the global cooldown)

M_t is split into connected components (8-connectivity on the 12x4 grid,
<= 8). Each component is matched to a region table (<= 8 regions; match if
>= overlap_thr of its cells fall inside the 1-cell dilation of the region).
An unmatched component creates a region and is NOVEL. Each region keeps
n_req, n_hit, last request time, in-flight flag and a confirmed flag.

## 3. Utility rule with closed-loop feedback (the core contribution)

A wake is requested for frame t iff the watcher is ACTIVE and
```
some region is NOVEL                                                  (novelty: wake now)
or some region is DUE and  outstanding < max_inflight                 (load)
DUE(r) = not in flight and  t - last_req(r) >= period(r) * (awake_factor if M7 awake else 1)
period(r) = dt_track                      if r confirmed (last result hit r)
          = dt_retry                      if not confirmed and n_req(r) < k_retry
          = min(dt_barren * 2^(n_req-k_retry), cap)   otherwise (barren: back-off)
```
When a request is sent, every region of the frame is marked checked (one
inference covers the frame). When its result arrives, region r is
CONFIRMED iff D intersects dilate(cells(r)). Hence:

* a new object is checked at once, even during another object's activity
  (burst handling);
* an object the detector has not yet confirmed is re-checked quickly
  (k_retry times, every dt_retry): the detector may miss on one frame;
* a confirmed object is refreshed slowly (dt_track);
* content that keeps waking the M7 without ever producing a detection
  (swaying vegetation, illumination artefacts, repeated flash spam) is
  backed off exponentially. This is label-free spam suppression: the cost
  of a wake is weighed against its observed utility for that content;
* waking an already-awake M7 is cheaper (no wake transient), so periods are
  shortened by awake_factor.

## 4. Security gate (ugs_secure)

Replay = re-presentation of a STALE observation. With gain normalisation
g(T) = T * 128 / median(T) and the changed-block count
n(A, B) = #{k : |g(A)_k - g(B)_k| > d_abs + d_rel g(B)_k}, every frame (not
only requests) is classified with a session state:
```
n_prev = n(T_t, T_{t-1});  n_old = min over stored LIVE frames h aged [2 s, 60 s] of n(T_t, T_h)
start:     not in session, fg >= fg_min, n_old <= k_match, n_prev >= k_jump, n_old + margin <= n_prev
           -> REPLAY, remember the last live frame R
continue:  in session, n(T_t, R) > k_match, n_old <= k_match -> REPLAY
end:       in session and (n(T_t, R) <= k_match  or  n_old > k_match)
```
A persistent static scene has n_prev ~ 0 and never starts a session (the
R2 FRR source); a moving live object differs from every old frame; returning
to the live scene after a replay matches R and does not start a new session.
Replayed frames are not added to the live history.

Wake budget: a global token bucket (capacity B, refill r) bounds M7
activations under any load; when it is empty only NOVEL content may use a
small reserved novelty budget (capacity E, refill r_e). Together with the
scheduler's barren back-off, repetitive suspicious traffic is limited first
and novel evidence keeps priority.

## 5. Bounded state and cost (M4)

| component | static memory (host check, float features) | worst-case work per frame |
|---|---|---|
| frame features (both front ends, fingerprints) | 76.8 KB | ~1.45 x 10^5 simple ops |
| UGS scheduler | 1.6 KB | median/MAD insertion sort of <= 64 values (2 x 2 k compares), <= 48 component dilations, 8 x 8 region matches |
| UGS gate, history 256 / 64 | 53.6 KB / 13.7 KB | history x 192 block compares (<= 49 k) + 2 medians |

All values are counts or sizes of the compiled host build; no M4 timing has
been measured (see docs/R3_HARDWARE.md).

## 6. What is not used

No ground-truth label, no attack label, no future frame, and no prediction of
the frame being decided reaches the scheduler or the gate (tests:
`tests/test_r3.py::R3Sim::test_blind_to_labels`; the detector output enters
only through the RPC result of an earlier, already processed frame).
