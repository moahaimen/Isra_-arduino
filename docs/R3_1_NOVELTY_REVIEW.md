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

## What this implies for the claims
* Dual-stage "cheap trigger → expensive detector" designs and battery-drain / denial-of-sleep attacks with rate-limiting defences
  **already exist as general ideas**; the paper must not present the architecture or the idea of wake-up spam as new.
* We found **no snippet** describing the specific combination studied here (content-aware gate against replay *and* spam for a
  vision-triggered dual-core MCU, evaluated with availability preserved). Absence from a handful of snippets is **not** evidence of absence.
* The defensible framing is therefore: an *evaluation-driven study* of whether simple rate limiting suffices, and which additional state
  (content-aware budgets, stale-frame detection) buys availability under replay/spam, with negative results reported.

## Searches still to run (not done)
"denial of sleep" × vision/camera; "wake-up attack" × always-on camera; "sponge/energy-latency attack" × cascade detectors;
"replay attack" × surveillance camera video injection; "adaptive sampling"/"smart trigger" × object detection MCU;
"utility-gated"/"value of information" scheduling for detector invocation; token-bucket baselines for IoT admission control.
