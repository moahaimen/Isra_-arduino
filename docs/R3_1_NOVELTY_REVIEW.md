# R3.1 literature / novelty check (snippet-level, UNVERIFIED)

**Method and limits.** Web search returned titles and short snippets only; arXiv, ResearchGate, Semantic Scholar and publisher pages
were not retrievable in this environment, so no paper was read in full. Every entry below is therefore *a lead*, not a verified
characterisation. Authors/venues/years are deliberately not stated where the snippet did not show them. **This review cannot establish
novelty, and the words "first", "novel" and "unique" are not used anywhere in the R3.1 documents.** A proper systematic search
(Google Scholar / IEEE Xplore / ACM DL with the queries below) is required before submission.

## Leads found (snippets)
| Topic | Lead (title as returned) | What the snippet suggests | Status |
|---|---|---|---|
| Always-on visual trigger on a node | "A sub-mW IoT-endnode for always-on visual monitoring and smart triggering" (arXiv 1705.00221) | low-power front end triggers a bigger processor | not read |
| Context-aware vision node | "An Energy-Proportional Multimodal and Context-Aware Vision IoT Node" (arXiv 2608.23192) | multimodal wake-up, battery-life estimates at 1 % activity | not read |
| Event-driven smart sensor | "An Event-Driven Ultra-Low-Power Smart Visual Sensor" | triggering with 193–277 µW average | not read |
| Tiered wake-up | "tiered-wakeup-visual-classification" (GitHub) | cheap tier gates an expensive classifier | not read |
| Uncertainty-triggered wake-up | arXiv 2605.29533 | wake decision from front-end uncertainty | not read |
| MCU detectors | TinyissimoYOLO family | MCU object detection networks | referenced in R2 |
| Battery-drain / denial-of-sleep | "Battery Drain Denial-of-Service Attacks and Defenses in the IoT"; "Battery draining attacks against edge computing nodes in IoT networks" (arXiv 2002.00069); "Denial-of-service attacks on battery-powered mobile computers"; wake-up-radio denial-of-sleep patent | attacker prevents sleeping / forces wake-ups; defences include rate limiting and IDS | not read |

## Additional leads (second search round; snippets only, none read in full)
| Topic | Lead (title as returned) | What the snippet suggests | Relevance |
|---|---|---|---|
| Denial of sleep, sensor networks | "Wireless sensor network denial of sleep attack" (IEEE Workshop on Information Assurance and Security 2005, per the result title); "Effects of Denial of Sleep Attacks on Wireless Sensor Network MAC Protocols" | attacks keep nodes awake; a general, established threat class | prior art for the threat model |
| Denial of sleep in wake-up systems | "Counteracting Denial-of-Sleep Attacks in Wake-up-based Sensing Systems" | defences for wake-up *radios*/sensing front ends (changing wake-up tokens, anomaly detection of wake-up rate) | closest defence-side prior art found; modality is radio/sensing, not vision content |
| Battery drain, IoT/Wi-Fi | "Secure Triggering Frame-Based Dynamic Power Saving Mechanism against Battery Draining Attack in Wi-Fi-Enabled Sensor Networks" (Sensors 2024, per DOI 10.3390/s24165131) | secure trigger frames against battery-draining | prior art for secured wake triggers |
| Replay / false frame injection on cameras | "Detecting Malicious False Frame Injection Attacks on Surveillance Systems at the Edge Using ENF Signals" (Sensors 2019); "A Study on Smart Online Frame Forging Attacks against Video Surveillance System" (arXiv 1903.03473) | replayed video masks live scenes; detection via power-grid-frequency signatures, duplication/temporal checks | prior art for replay detection in surveillance (but for *security monitoring*, not wake-gating, and with a physical-side-channel method) |
| Energy-latency attacks on detectors | "Sponge Examples: Energy-Latency Attacks on Neural Networks"; "Phantom Sponges" (NMS); multi-exit/early-exit attacks; "Can't Slow me Down … Object Detectors against Latency Attacks for Edge Devices" (arXiv 2412.02171) | adversarial inputs raise inference energy/latency | a different (input-crafted, post-wake) availability threat to the same cascade; must be discussed and not conflated |
| Dual-core MCU inference | ST AN5557 (STM32H745/747 dual-core architecture); ETRI "Dual-Core-Based Microcontrollers Inference Design" | M4/M7 division of labour, separate power domains | architecture background |
| Cascaded TinyML wake-up | wake-word cascades; "Uncertainty-triggered wake-up … memristor front ends" (arXiv 2605.29533); "Smart sensor for always-on operation" (patent) | staged wake-up is standard practice | prior art for the dual-stage idea |

## Can an availability-preserving pre-wake security mechanism be the main contribution?
Assessment (from snippets only): the *threat* (denial of sleep / wake-up spam), the *defence class* (rate limiting, anomaly detection on wake rate, non-reusable wake tokens), replay detection on camera streams, and the *staged wake-up architecture* each have prior art. The snippets did **not** reveal a work that gates the wake-up of a heterogeneous MCU vision pipeline with a content-level stale-frame check evaluated for availability (FRR) and modeled energy, but this absence is not evidence of novelty (no systematic search, no full texts).
**Verdict: a novelty claim is not defensible with the current evidence.** What is defensible, with measurements, is an empirical statement: in our simulation a global cooldown already provides most of the spam protection (it is also the trigger design), a plain rate limiter alone destroys availability (FRR 0.79) and adds nothing behind the cooldown, and a gradient-tolerant stale-frame gate adds a measurable but partial reduction in replay success at FRR ≈ 0.007. That is a useful, honestly-scoped result, but by itself it reads as a design study; whether it is a sufficient *main* contribution for a Q1 venue is doubtful and depends on a systematic literature search and on on-device evidence.

## What this implies for the claims
* Dual-stage "cheap trigger → expensive detector" designs and battery-drain / denial-of-sleep attacks with rate-limiting defences
  **already exist as general ideas**; the paper must not present the architecture or the idea of wake-up spam as new.
* We found **no snippet** describing the specific combination studied here (content-aware gate against replay *and* spam for a
  vision-triggered dual-core MCU, evaluated with availability preserved). Absence from a handful of snippets is **not** evidence of absence.
* The defensible framing is therefore: an *evaluation-driven study* of whether simple rate limiting suffices, and which additional state
  (content-aware budgets, stale-frame detection) buys availability under replay/spam, with negative results reported.

## Searches still to run (not done; the two rounds above covered a subset)
"denial of sleep" × vision/camera; "wake-up attack" × always-on camera; "sponge/energy-latency attack" × cascade detectors;
"replay attack" × surveillance camera video injection; "adaptive sampling"/"smart trigger" × object detection MCU;
"utility-gated"/"value of information" scheduling for detector invocation; token-bucket baselines for IoT admission control.
