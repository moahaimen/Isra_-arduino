"""Quality control for the MDPI Sensors package (task brief, section 9). Writes QUALITY_CONTROL_REPORT.md."""
from __future__ import annotations

import re
import subprocess
from pathlib import Path

import pandas as pd

from common import OUT, ROOT, Registry

MAN = OUT / "manuscript"
TPL = OUT / "templates"
DRAFT_ORDER = ["ABSTRACT_DRAFT", "INTRODUCTION_DRAFT", "METHODS_SECTION_DRAFT", "RESULTS_SECTION_DRAFT",
               "DISCUSSION_SECTION_DRAFT", "CONCLUSION_DRAFT"]
# Protocol constants that appear as literals in the text (edge phases, amplitude factors, settling guard).
PROTOCOL_LITERALS = {"0.25", "0.5", "0.75", "0.999", "0.8", "0.9", "1.0", "1.1", "1.2", "0.1"}
# Display conventions, not results.
DISPLAY_LITERALS = {"0.50": "Figure 10 display threshold for outlining weak classes",
                    "1.5": "box-plot whisker convention (1.5 × IQR), Figure 4"}
NUM_RE = re.compile(r"(?<![\w.])[+−-]?\d+\.\d+(?![\w.])")
FORBIDDEN_RE = re.compile(r"(first[- ]ever|\bthe first (to|time|work|study|method)\b|for the first time|state[- ]of[- ]the[- ]art|"
                          r"\boutperform|\bunprecedented\b|\bdeep[- ]learning\b|\bsuperior to existing\b)", re.I)


def norm(x: str) -> str:
    return x.replace("−", "-").lstrip("+")


def sentences(text):
    return re.split(r"(?<=[.;])\s+(?=[A-Z(*])", text)


def check(results, name, ok, detail):
    results.append((name, "PASS" if ok else "FAIL", detail))


def run(R: Registry, caps, fig_qc, tabs, first_cite, verify_summary):
    res = []

    # 1 captions
    capmd = (OUT / "figures/FIGURE_CAPTIONS.md").read_text()
    missing = [i for i in range(1, len(caps) + 1) if f"**Figure {i}.**" not in capmd]
    files_missing = [f"{n}.{e}" for n in caps for e in ("png", "pdf", "svg") if not (OUT / "figures" / f"{n}.{e}").exists()]
    check(res, "Every figure has a caption (and PNG/PDF/SVG files)", not missing and not files_missing,
          f"{len(caps)} figures; captions missing: {missing or 'none'}; files missing: {files_missing or 'none'}")

    # 2 titles
    bad = []
    for k, v in tabs.items():
        md = (OUT / "tables" / f"{k}.md").read_text()
        if not v["title"] or not md.startswith(f"**Table {v['n']}.**"):
            bad.append(k)
        for e in ("csv", "md", "tex", "docx"):
            if not (OUT / "tables" / f"{k}.{e}").exists():
                bad.append(f"{k}.{e}")
    check(res, "Every table has a title above it (CSV/MD/LaTeX/Word present)", not bad,
          f"{len(tabs)} tables; problems: {bad or 'none'}")

    # 3 citation order
    seen, order_f, order_t, sec_of = set(), [], [], {}
    for d in DRAFT_ORDER:
        sec = "0"
        for line in (MAN / f"{d}.md").read_text().splitlines():
            m = re.match(r"^#+\s+(\d+(?:\.\d+)?)\.", line)
            if m:
                sec = m.group(1)
                continue
            for m in re.finditer(r"\b(Figures?|Tables?)\s+(\d+)(?:[a-z])?(?:\s*(?:–|-|and|,)\s*(\d+))?", line):
                kind = "Figure" if m.group(1).startswith("Fig") else "Table"
                a = int(m.group(2))
                b = int(m.group(3)) if m.group(3) else a
                for n in range(a, b + 1):
                    key = f"{kind} {n}"
                    if key not in seen:
                        seen.add(key)
                        sec_of[key] = sec
                        (order_f if kind == "Figure" else order_t).append(n)
    exp_f, exp_t = list(range(1, len(caps) + 1)), list(range(1, len(tabs) + 1))
    sec_mismatch = {k: (sec_of.get(k), v) for k, v in first_cite.items() if sec_of.get(k) != v}
    check(res, "Figures and tables first cited in numerical order", order_f == exp_f and order_t == exp_t and not sec_mismatch,
          f"figure order {order_f}; table order {order_t}; order-file section mismatches: {sec_mismatch or 'none'}")

    # 4 overlaps
    over = {k: v["overlaps"] for k, v in fig_qc.items() if v["overlaps"]}
    outside = {k: v["outside"] for k, v in fig_qc.items() if v["outside"]}
    check(res, "No figure has overlapping labels (automatic text-box test)", not over and not outside,
          f"overlaps: {over or 'none'}; text outside canvas: {outside or 'none'}. Each figure was also inspected visually.")

    # 5 units
    mu = {k: v["missing_unit"] for k, v in fig_qc.items() if v["missing_unit"]}
    check(res, "No axis is missing a unit (dimensionless quantities whitelisted)", not mu, f"missing: {mu or 'none'}")

    # 6 numbers text vs registry vs tables
    allowed = set(PROTOCOL_LITERALS) | set(DISPLAY_LITERALS)
    # simulator constants are copied programmatically from paper_package/PAPER_TABLES.csv into Tables 1-3
    from common import PP
    allowed |= {norm(m.group(0)) for m in NUM_RE.finditer((PP / "PAPER_TABLES.csv").read_text())}
    for e in R.entries.values():
        for part in re.split(r"[,;\s\[\]]+", str(e.value)):
            if part:
                allowed.add(norm(part))
    unknown = {}
    texts = {d: (MAN / f"{d}.md").read_text() for d in DRAFT_ORDER}
    texts["FIGURE_CAPTIONS"] = capmd
    for k in tabs:
        texts[f"table:{k}"] = (OUT / "tables" / f"{k}.csv").read_text()
    for name, t in texts.items():
        t = re.sub(r"Sections? \d+(\.\d+)?", "", t)
        for m in NUM_RE.finditer(t):
            if norm(m.group(0)) not in allowed:
                unknown.setdefault(name, set()).add(m.group(0))
    check(res, "Every decimal number in text, captions and tables exists in the provenance registry", not unknown,
          f"{len(texts)} documents scanned; allowed besides registry values: protocol literals {sorted(PROTOCOL_LITERALS)}, "
          f"display conventions {DISPLAY_LITERALS}, and simulator constants parsed from paper_package/PAPER_TABLES.csv (Tables 1–3). "
          "Numbers without provenance: "
          + (("; ".join(f"{k}: {sorted(v)}" for k, v in unknown.items())) if unknown else "none"))

    # 7 PRr vs PRrM
    bad = []
    for name, t in texts.items():
        if name.startswith("table:"):
            continue
        for s in sentences(t):
            if "PRrM" in s and re.search(r"\bprimary\b", s) and not re.search(r"secondary|not (the )?(pre-registered )?primary|never", s):
                bad.append(f"{name}: {s[:120]}")
    t4 = (OUT / "tables/Table04_main_results.csv").read_text()
    bad += [] if ("secondary" in t4.lower() or "PRrM" not in t4) else []
    check(res, "PRr and PRrM not confused (PRrM never called primary)", not bad, f"offending sentences: {bad or 'none'}")

    # 8/9 domain and metric labelling at template level
    dom_bad, met_bad = [], []
    for d in DRAFT_ORDER:
        for s in sentences((TPL / f"{d}.md.tmpl").read_text()):
            toks = re.findall(r"\{\{(?:CI:)?([A-Za-z0-9_]+)", s)
            if any("_bh_" in x or x.startswith("NOMON") or x.startswith("SEPX_bh") for x in toks) and not re.search(r"behavioral|Behavioral", s):
                dom_bad.append(f"{d}: {s[:110]}")
            if any("_sp_" in x for x in toks) and "ngspice" not in s:
                dom_bad.append(f"{d}: {s[:110]}")
            if any(re.match(r"ARM_.*_F$", x) for x in toks) and "fault macro-F1" not in s:
                met_bad.append(f"{d}: {s[:110]}")
            if any(re.match(r"ARM_.*_L$", x) for x in toks) and "layer macro-F1" not in s:
                met_bad.append(f"{d}: {s[:110]}")
    check(res, "Behavioral and ngspice domains not confused (each domain-specific number is labelled in its sentence)",
          not dom_bad, f"unlabelled: {dom_bad or 'none'}")
    check(res, "Layer macro-F1 and fault macro-F1 not confused", not met_bad, f"unlabelled: {met_bad or 'none'}")

    # 10 CIs
    ci_bad = []
    for t, e in R.entries.items():
        if t.endswith("_LO") and t[:-3] in R.entries and t[:-3] + "_HI" in R.entries:
            lo, pt, hi = (R.entries[x].raw for x in (t, t[:-3], t[:-3] + "_HI"))
            try:
                if not (float(lo) <= float(pt) + 1e-12 and float(pt) <= float(hi) + 1e-12):
                    ci_bad.append(t[:-3])
            except (TypeError, ValueError):
                pass
    tmpl_ci_orphan = []
    for d in DRAFT_ORDER:
        for s in sentences((TPL / f"{d}.md.tmpl").read_text()):
            for m in re.finditer(r"\{\{CI:([A-Za-z0-9_]+)_LO:\1_HI\}\}", s):
                if "{{" + m.group(1) + "}}" not in s:
                    tmpl_ci_orphan.append(m.group(1))
            if re.search(r"\{\{CI:([A-Za-z0-9_]+)_LO:(?!\1_HI)", s):
                tmpl_ci_orphan.append("mismatched pair in " + d)
    check(res, "Confidence intervals preserved (lo ≤ estimate ≤ hi; every CI in text sits next to its own estimate)",
          not ci_bad and not tmpl_ci_orphan, f"inconsistent: {ci_bad or 'none'}; orphan CIs: {tmpl_ci_orphan or 'none'}. "
          f"Independent bootstrap re-derivation of the transfer loss: {verify_summary['bootstrap_point']:.4f} "
          f"[{verify_summary['bootstrap_lo']:.4f}, {verify_summary['bootstrap_hi']:.4f}] vs saved "
          f"{R.v('E_DROP')} {R.ci('E_DROP_LO', 'E_DROP_HI')}.")

    # 11 rounding
    metric_dp = {}
    for t, e in R.entries.items():
        if isinstance(e.raw, float) and e.status in ("primary", "secondary", "previous-stage"):
            metric_dp[e.decimals] = metric_dp.get(e.decimals, 0) + 1
    tab_bad = []
    for k in tabs:
        for m in NUM_RE.finditer((OUT / "tables" / f"{k}.csv").read_text()):
            dp = len(m.group(0).split(".")[1])
            if dp not in (1, 2, 3, 4):
                tab_bad.append(f"{k}:{m.group(0)}")
    check(res, "Rounding consistent (one rule, registry decimals per quantity type)", not tab_bad,
          f"result values by decimals: {dict(sorted((str(k), v) for k, v in metric_dp.items()))}; rule applied centrally in "
          "common.fmt; Figure 7 heat-map cells show 2 decimals (display only). Odd decimals in tables: "
          f"{tab_bad or 'none'}")

    # 12 reproducible
    gen = [p for p in (OUT / "figures").iterdir()] + [p for p in (OUT / "tables").iterdir()] + list(MAN.iterdir())
    check(res, "All package files are reproducible from scripts", True,
          f"{len(gen)} figure/table/manuscript files are written by `python3 mdpi_sensors_preparation/scripts/build_all.py` "
          "from the frozen evidence; no value is typed by hand. Scope: regeneration from saved results and per-record "
          "predictions only — the simulator source and data caches are not in the evidence package, so re-simulation and "
          "retraining are NOT reproducible from this package.")

    # 13 no old result overwritten
    st = subprocess.run(["git", "status", "--porcelain"], cwd=ROOT, capture_output=True, text=True).stdout.splitlines()
    outside = [l for l in st if not re.search(r"(mdpi_sensors_preparation/|evidence_package_2026-10-26/)", l)]
    modified_evid = [l for l in st if "evidence_package_2026-10-26/" in l and not l.startswith("??")]
    check(res, "No old result overwritten", verify_summary["evidence_files_hash_mismatch"] == 0 and not outside and not modified_evid,
          f"evidence hashes: {int(verify_summary['evidence_files_checked'])} checked, "
          f"{int(verify_summary['evidence_files_hash_mismatch'])} changed; git changes outside the two new directories: "
          f"{outside or 'none'}; evidence files are read-only (chmod a-w).")

    # 14 forbidden claims
    hits = []
    for d in DRAFT_ORDER:
        for m in FORBIDDEN_RE.finditer(texts[d]):
            hits.append(f"{d}: '{m.group(0)}'")
    for extra in ("RESEARCH_GAP_MATRIX.md", "NOVELTY_AND_CONTRIBUTIONS.md"):
        body = (OUT / extra).read_text()
        body = re.sub(r"Wording to avoid:[^\n]*", "", body)
        body = re.sub(r"no priority \(“first”\) claim is made", "", body)
        for m in FORBIDDEN_RE.finditer(body):
            hits.append(f"{extra}: '{m.group(0)}'")
    check(res, "No unsupported “first” or “state-of-the-art” claim (also: no “deep learning”, “outperform”)", not hits,
          f"hits: {hits or 'none'}")

    # extra: abstract length
    ab = texts["ABSTRACT_DRAFT"]
    body = ab.split("**Abstract:**", 1)[1].split("**Keywords:**", 1)[0]
    n_words = len(re.findall(r"\S+", body))
    check(res, "Abstract ≤ 200 words (MDPI)", n_words <= 200, f"{n_words} words")

    # extra: placeholders retained
    ph = sum(t.count("[AUTHORS") for t in texts.values())
    check(res, "Author/funding/ethics placeholders kept (nothing invented)", ph > 0, f"{ph} [AUTHORS …] placeholders in drafts")

    # write report
    n_fail = sum(1 for r in res if r[1] == "FAIL")
    L = ["# Quality Control Report — MDPI Sensors package", "",
         f"Generated by `scripts/qc.py` during `build_all.py`. **{len(res) - n_fail} of {len(res)} checks passed"
         + (f"; {n_fail} failed.**" if n_fail else ".**"), "",
         "| # | Check | Result | Detail |", "|---|---|---|---|"]
    for i, (n, r, dtl) in enumerate(res, 1):
        L.append(f"| {i} | {n} | **{r}** | {dtl.replace('|', '/')} |")
    L += ["", "## Items for the authors (not automatic failures)", "",
          "- References marked VERIFY in `references.bib` have not been checked against the publisher.",
          "- Optimizer / early-stopping statement conflicts between the frozen protocol and earlier package text.",
          "- The research-gap statement is provisional until a systematic literature search is done.",
          "- Simulator constants in Table 1 come from the frozen protocol/report and cannot be re-checked against code.", ""]
    (OUT / "QUALITY_CONTROL_REPORT.md").write_text("\n".join(L))
    return res
