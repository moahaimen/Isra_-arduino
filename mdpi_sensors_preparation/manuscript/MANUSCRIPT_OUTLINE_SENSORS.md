# MDPI Sensors — Manuscript Outline

Article type: Article. Section numbering follows the MDPI template (Introduction = 1). The 21-item structure requested for this package maps onto the MDPI sections as shown. Placeholders in [AUTHORS: …] must be completed by the authors.

| # | Item | MDPI section | Draft file | Status |
|---|---|---|---|---|
| 1 | Title | Front matter | `manuscript/ABSTRACT_DRAFT.md` | drafted |
| 2 | Abstract (≤ 200 words) | Front matter | `manuscript/ABSTRACT_DRAFT.md` | drafted; word count checked by QC |
| 3 | Keywords | Front matter | `manuscript/ABSTRACT_DRAFT.md` | drafted |
| 4 | Introduction | 1 | `manuscript/INTRODUCTION_DRAFT.md` | drafted |
| 5 | Related Work and Research Gap | 2 | `manuscript/INTRODUCTION_DRAFT.md`, `RESEARCH_GAP_MATRIX.md` | drafted; literature search pending |
| 6 | Proposed Electronic Architecture | 3 | `manuscript/METHODS_SECTION_DRAFT.md` | drafted |
| 7 | Phase-Robust Descriptor Method | 4 | `manuscript/METHODS_SECTION_DRAFT.md` | drafted |
| 8 | Neural-Network Classifier | 5 | `manuscript/METHODS_SECTION_DRAFT.md` | drafted; optimizer/early-stopping to confirm |
| 9 | Simulation and Validation Protocol | 6 | `manuscript/METHODS_SECTION_DRAFT.md` | drafted |
| 10 | Results | 7 | `manuscript/RESULTS_SECTION_DRAFT.md` | drafted |
| 11 | Discussion | 8 | `manuscript/DISCUSSION_SECTION_DRAFT.md` | drafted |
| 12 | Limitations | 9 | `manuscript/DISCUSSION_SECTION_DRAFT.md` | drafted |
| 13 | Conclusions | 10 | `manuscript/CONCLUSION_DRAFT.md` | drafted |
| 14 | Data Availability Statement | Back matter | `manuscript/CONCLUSION_DRAFT.md` | placeholder (repository URL/DOI) |
| 15 | Author Contributions | Back matter | `manuscript/CONCLUSION_DRAFT.md` | placeholder |
| 16 | Funding | Back matter | `manuscript/CONCLUSION_DRAFT.md` | placeholder |
| 17 | Institutional Review Board Statement | Back matter | `manuscript/CONCLUSION_DRAFT.md` | “Not applicable” (to confirm) |
| 18 | Informed Consent Statement | Back matter | `manuscript/CONCLUSION_DRAFT.md` | “Not applicable” (to confirm) |
| 19 | Data Availability (archive/DOI details) | Back matter | `manuscript/CONCLUSION_DRAFT.md` | placeholder; MDPI uses one Data Availability Statement — items 14 and 19 are merged there |
| 20 | Conflicts of Interest | Back matter | `manuscript/CONCLUSION_DRAFT.md` | placeholder |
| 21 | References | Back matter | `references.bib` | entries marked VERIFY must be checked |

## Section content plan

- **1 Introduction** — why fault location matters; identifiability argument; the two practical problems (reference drift: 0.237 without monitor at ×1.2; phase-sensitive transfer: 0.119 previous-stage loss); contributions.
- **2 Related work** — four literature categories + gap (Research Gap Matrix).
- **3 Architecture** — Figure 1, Figure 2, Tables 1–2; Equations (1)–(2); monitor model.
- **4 Descriptors** — Figure 3 pipeline, Figure 4 illustrative signatures; Equation (3).
- **5 Classifier** — 20–96–48 MLP; 6,868/7,113 parameters.
- **6 Protocol** — Table 3; gates A–G.
- **7 Results** — 7.1 decision (Tables 4–5); 7.2 phase (Fig. 5, Table 8); 7.3 amplitude/monitor (Fig. 6, Table 7); 7.4 baselines & separation (Table 6, Fig. 7, Table 10); 7.5 transfer (Fig. 8, Table 9); 7.6 ablation (Fig. 9); 7.7 per-class (Fig. 10, Table 11); 7.8 cost (Table 12).
- **8–9 Discussion & limitations**; **10 Conclusions**; back matter.

## Author information still needed

- Authors, affiliations, ORCIDs, corresponding author [AUTHORS]
- Funding, acknowledgments, conflicts of interest [AUTHORS]
- Data/code repository URL or DOI; whether simulator source will be released [AUTHORS]
- Optimizer settings and early-stopping statement (protocol vs earlier package text conflict) [AUTHORS]
- ngspice version used; Python/package versions of the original runs [AUTHORS]
- Completed systematic literature search; verification of references marked VERIFY [AUTHORS]
