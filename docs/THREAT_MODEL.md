# Threat model

## Asset and goal

The asset is the M7 detector's time and energy budget and the integrity of
the detection results. The defender's goal is that only legitimate stimuli
wake the M7, without rejecting real objects.

## Attacker capabilities (modelled)

| attack | capability | effect if successful | ground-truth label |
|---|---|---|---|
| trigger_spam | inject fake trigger stimuli on the M4 sensing path (e.g. a spoofed PIR/motion line or light flicker), in sessions of exponential length at Poisson rate 3/s × session rate scaled by attack intensity; 30 % of injections are sophisticated and make all sensing channels agree | repeated M7 wake-ups (energy drain), consumption of the cooldown window (legitimate objects suppressed) | `attack_type=trigger_spam`, `is_legitimate=false`, `ground_truth_action=block` |
| replay | record legitimate camera frames and replay them later with the original relative timing; 30 % of replayed frames are perturbed to change the perceptual hash | false detections of objects that are not present, M7 energy use | `attack_type=replay`, `replay_id=<original event_id>` |
| mixed | both of the above at half rate, plus legitimate bursts | combined | as above |

Not modelled: compromise of either core's firmware, attacks on the RPC
channel itself, physical tampering, adaptive attackers that probe and learn
the thresholds, adversarial examples against the CNN, denial of service on
the M4 itself (it is assumed to keep up with the observation rate).

## Defences (algorithmic, M4 side, before any M7 wake)

| defence | rule (defaults) | attacks addressed | expected false rejections |
|---|---|---|---|
| cooldown (watcher) | ≥ 1.5 s between triggers | caps spam wake rate | concurrent legitimate objects |
| consistency check | min(consistency, 1 − |motion − temporal|) ≥ 0.5 | naive spam | noisy legitimate frames |
| duplicate detection | same perceptual hash within 2 s | frame re-injection | static legitimate scenes |
| replay detection | same hash or L∞ feature distance < 0.01, age 2–600 s, 512-frame history | exact and near-exact replays | rare |
| burst anomaly | > 10 watcher-positive candidates in 5 s | sustained spam | legitimate crowds/bursts |
| rate limit | < 20 accepted triggers per 60 s | sustained spam | very busy scenes |

The gate never sees ground-truth labels (separate data structures; verified
statically and by a label-scrambling experiment in
`scripts/audit_scientific.py`). Effectiveness is measured from labeled
attacks against these algorithmic decisions. Probability-based blocking is
not part of the defence; it exists only as a debug flag whose runs are marked
`research_valid: false`.

## Known limitations of the defences (visible in the results)

* Replays older than the replay window, or evicted from the 512-frame
  history, or perturbed beyond ε, pass the gate; detection then depends on
  other checks.
* Sophisticated spam that keeps sensors consistent is only caught by the
  burst and rate checks.
* Burst detection and the global cooldown reject or suppress legitimate
  objects in genuine bursts; the ablation and `burst_threshold` sweep
  quantify this trade-off.
