"""Build the manuscript, the supplementary document and the support files.

    python3 manuscript_submission/build/build_manuscript.py

Sources: src/*.md (text with tokens), refs.py (verified references), the number
registry of the evidence package and the figures in mdpi_sensors_preparation/.
Outputs are written to manuscript_submission/.
"""
from __future__ import annotations

import csv
import json
import re
import shutil
import subprocess
import sys
from pathlib import Path

from docx import Document
from docx.enum.text import WD_ALIGN_PARAGRAPH, WD_BREAK
from docx.oxml import OxmlElement
from docx.oxml.ns import qn
from docx.shared import Cm, Pt

BUILD = Path(__file__).resolve().parent
OUT = BUILD.parent
sys.path.insert(0, str(BUILD))

import ms_docx as D  # noqa: E402
import ms_refs  # noqa: E402
import ms_tables  # noqa: E402
import ms_tokens  # noqa: E402

PREP = ms_tokens.PREP
SRC = sorted((BUILD / "src").glob("*.md"))
WORK = BUILD / "_work"
NB = " "
FIG_FILES = {"arch": "Fig01_architecture", "timing": "Fig02_timing", "pipeline": "Fig03_pipeline", "signatures": "Fig04_fault_signatures",
             "phase": "Fig05_phase_sensitivity", "refamp": "Fig06_reference_amplitude", "separation": "Fig07_afe_adc_separation",
             "transfer": "Fig08_domain_transfer", "ablation": "Fig09_ablation", "recall": "Fig10_per_class_recall"}
FIG_WIDTH = {"arch": 16.0, "timing": 15.5, "pipeline": 17.0, "signatures": 15.5, "phase": 17.0, "refamp": 16.5, "separation": 15.0,
             "transfer": 17.0, "ablation": 15.0, "recall": 16.5}
CAPTION_FIX = [("adc clipping", "ADC clipping"), ("dataset", "data-set"), ("The fixed-sample rise fraction rise_2 moves", "The fixed-sample step fraction at two samples moves"),
               ("3 data-set seeds", "three data sets"), ("three data-set seeds", "three data sets"), ("development seed", "development data set, seed"),
               ("Revision-1", "fixed-sample")]


def mn(s):
    return re.sub(r"(?<![\w.])-(?=\d)", "−", str(s))


# ---------------------------------------------------------------- captions

def figure_captions():
    text = (PREP / "figures" / "FIGURE_CAPTIONS.md").read_text()
    caps = {}
    inv = {v: k for k, v in FIG_FILES.items()}
    for m in re.finditer(r"\*\*Figure (\d+)\.\*\* (.+?)\n\n\*File:\* `figures/(\w+)\.png", text, re.S):
        cap = m.group(2).strip()
        for a, b in CAPTION_FIX:
            cap = cap.replace(a, b)
        caps[inv[m.group(3)]] = mn(cap)
    assert len(caps) == 10, len(caps)
    return caps


# ------------------------------------------------------------- preprocessor

class Pre:
    def __init__(self, R, authors=None):
        self.R = R
        self.authors = authors
        self.sec, self.eq, self.fig, self.tab, self.cite = {}, {}, [], [], []
        self.used_tokens = set()

    # numbering pass over the raw text
    def scan(self, text):
        h1 = h2 = 0
        for line in text.split("\n"):
            m = re.match(r"^(#+) (.+?) <<sec:(\w+)>>\s*$", line)
            if m:
                if len(m.group(1)) == 1:
                    h1, h2 = h1 + 1, 0
                    self.sec[m.group(3)] = str(h1)
                else:
                    h2 += 1
                    self.sec[m.group(3)] = f"{h1}.{h2}"
            m = re.match(r"^\$\$(.+)\$\$\s*<<eq:(\w+)>>\s*$", line)
            if m:
                self.eq[m.group(2)] = len(self.eq) + 1
        self.fig = re.findall(r"\[\[FIG:(\w+)\]\]", text)
        self.tab = re.findall(r"\[\[TAB:(\w+)\]\]", text)
        self.atab = re.findall(r"\[\[ATAB:(\w+)\]\]", text)
        # first-citation order must equal placement order
        first = []
        for m in re.finditer(r"\{\{F:(\w+)\}\}", text):
            if m.group(1) not in first:
                first.append(m.group(1))
        assert first == self.fig, (first, self.fig)
        first = []
        for m in re.finditer(r"\{\{T:(\w+)\}\}", text):
            if m.group(1) not in first:
                first.append(m.group(1))
        assert first == self.tab, (first, self.tab)
        for m in re.finditer(r"\[@([^\]]+)\]", text):
            for k in re.split(r";\s*", m.group(1)):
                k = k.strip().lstrip("@")
                assert k in ms_refs.REFS, k
                if k not in self.cite:
                    self.cite.append(k)

    def ref(self, kind, key):
        if kind == "S":
            return f"Section{NB}{self.sec[key]}"
        if kind == "F":
            return f"Figure{NB}{self.fig.index(key) + 1}"
        if kind == "T":
            return f"Table{NB}{self.tab.index(key) + 1}"
        if kind == "AT":
            return f"Table{NB}A{self.atab.index(key) + 1}"
        if kind == "EQ":
            return f"Equation{NB}({self.eq[key]})"
        if kind == "EQN":
            return f"({self.eq[key]})"
        raise KeyError(kind)

    def cites(self, m):
        nums = sorted(self.cite.index(k.strip().lstrip("@")) + 1 for k in re.split(r";\s*", m.group(1)))
        out, i = [], 0
        while i < len(nums):
            j = i
            while j + 1 < len(nums) and nums[j + 1] == nums[j] + 1:
                j += 1
            out.append(str(nums[i]) if j == i else (f"{nums[i]},{nums[j]}" if j == i + 1 else f"{nums[i]}–{nums[j]}"))
            i = j + 1
        return "[" + ",".join(out) + "]"

    def token(self, m):
        t = m.group(1)
        R = self.R
        if ":" in t:
            kind, rest = t.split(":", 1)
            if kind in ("S", "F", "T", "AT", "EQ", "EQN"):
                return self.ref(kind, rest)
            if kind == "CI":
                lo, hi = rest.split(":")
                self.used_tokens.update((lo, hi))
                return mn(f"[{R.v(lo)}, {R.v(hi)}]")
            if kind == "PCT":
                self.used_tokens.add(rest)
                return f"{float(R.raw(rest)) * 100:.1f}%"
            if kind == "U":
                self.used_tokens.add(rest)
                return mn(R.v(rest).lstrip("+"))
            raise KeyError(t)
        self.used_tokens.add(t)
        return mn(R.v(t))

    def inline(self, text):
        text = re.sub(r"\{\{([^{}]+)\}\}", self.token, text)
        text = re.sub(r"\[@([^\]]+)\]", self.cites, text)
        return text

    def body(self, text):
        out = []
        for line in text.split("\n"):
            m = re.match(r"^(#+) (.+?) <<sec:(\w+)>>\s*$", line)
            if m:
                out.append(f"{m.group(1)} {self.sec[m.group(3)]}. {m.group(2)}")
                continue
            m = re.match(r"^\$\$(.+)\$\$\s*<<eq:(\w+)>>\s*$", line)
            if m:
                out += [f"$${m.group(1)}$$", "", f"ZZMARK:EQ:{self.eq[m.group(2)]}:ZZ"]
                continue
            m = re.match(r"^\[\[(FIG|TAB|ATAB):(\w+)\]\]\s*$", line)
            if m:
                out.append(f"ZZMARK:{m.group(1)}:{m.group(2)}:ZZ")
                continue
            out.append(self.inline(line))
        return "\n".join(out)


def div(style, text):
    return f'::: {{custom-style="{style}"}}\n{text}\n:::\n'


def assemble(pre, raw, authors):
    """Return pandoc markdown for the manuscript."""
    title = re.search(r"^%%TITLE (.+)$", raw, re.M).group(1).strip()
    abstract = re.search(r"^%%ABSTRACT\n(.+?)\n\n", raw, re.M | re.S).group(1).strip()
    keywords = re.search(r"^%%KEYWORDS (.+)$", raw, re.M).group(1).strip()
    main_raw = raw.split("# Introduction", 1)[1]
    main_raw, back_raw = ("# Introduction" + main_raw).split("%%BACKMATTER", 1)
    md = [div("MDPI Type", "Article"), div("MDPI Title", title)]
    if authors:
        md.append(div("MDPI Authors", authors["author_line"]))
        for a in authors["affiliations"]:
            md.append(div("MDPI Affiliation", a))
        if authors.get("correspondence"):
            md.append(div("MDPI Affiliation", authors["correspondence"]))
    abstract_txt = pre.inline(abstract)
    md.append(div("MDPI Abstract", "**Abstract:** " + abstract_txt))
    md.append(div("MDPI Keywords", "**Keywords:** " + keywords))
    md.append(pre.body(main_raw))
    # back matter
    decl = {1: [], 2: [], 3: []}
    if authors:
        decl[1] = [f"**Author Contributions:** {authors['contributions']}", f"**Funding:** {authors['funding']}"]
        decl[2] = [f"**Data Availability Statement:** {authors['data_availability']}"]
        decl[3] = [f"**Conflicts of Interest:** {authors['conflicts']}"]
    blocks = [b.strip() for b in re.split(r"\n\s*\n", back_raw) if b.strip()]
    for b in blocks:
        m = re.match(r"^%%AUTHOR_DECLARATIONS_(\d)$", b)
        if m:
            for p in decl[int(m.group(1))]:
                md.append(div("MDPI Backmatter", p))
        elif b.startswith("%%ABBREVIATIONS"):
            pre.abbrev = [tuple(x.strip() for x in ln.split("|")) for ln in b.split("\n")[1:]]
            md.append(div("MDPI Backmatter", "**Abbreviations**"))
            md.append(div("MDPI Backmatter", "The following abbreviations are used in this manuscript:"))
            md.append("ZZMARK:ABBREV:x:ZZ\n")
        elif b.startswith("%%APPENDIX"):
            md.append("# Appendix A. Descriptor Vector\n")
        else:
            body = pre.body(b)
            md.append(body + "\n" if body.startswith("ZZMARK") or not body.startswith("**") else div("MDPI Backmatter", body))
    md.append("# References\n")
    md.append("ZZMARK:REFERENCES:x:ZZ\n")
    return title, abstract_txt, keywords, "\n".join(md)


# ------------------------------------------------------------ post-process

def pandoc(md_text, out_path):
    WORK.mkdir(exist_ok=True)
    src = WORK / (out_path.stem + ".md")
    src.write_text(md_text)
    subprocess.run(["pandoc", str(src), "-f", "markdown+smart-citations-implicit_figures", "-t", "docx", "-o", str(out_path)], check=True)


def insert_table(doc, anchor, spec, label):
    cap = D.new_par_before(anchor, doc, "MDPI Table Caption")
    D.add_marked(cap, f"**{label}.** {spec['title']}", 9)
    tbl = D.add_table(doc, anchor, spec["header"], spec["rows"], spec["widths"], spec.get("align"), spec.get("size", 8.5),
                      rules_after=spec.get("rules_after", ()), bold_rows=spec.get("bold_rows", ()))
    for row, c0, c1 in spec.get("merges", ()):
        D.merge_header(tbl, row, c0, c1)
    foot = D.new_par_before(anchor, doc, "MDPI Table Footer")
    if spec.get("note"):
        D.add_marked(foot, spec["note"], 8)
    else:
        foot.paragraph_format.space_before = Pt(0)
        foot.paragraph_format.space_after = Pt(6)
    return tbl


def remove(par):
    par._p.getparent().remove(par._p)


def postprocess(path, pre, tables, caps, cite_order, landscape=False, supp=None):
    doc = Document(str(path))
    D.setup_styles(doc)
    D.page_setup(doc, landscape)
    pars = list(doc.paragraphs)
    after_eq = []
    for p in pars:
        txt = p.text.strip()
        m = re.match(r"^ZZMARK:(\w+):(\w+):ZZ$", txt)
        if not m:
            continue
        kind, key = m.groups()
        if kind == "EQ":
            prev = p._p.getprevious()
            eq_par = next(q for q in pars if q._p is prev)
            assert eq_par._p.findall(f"{{{D.M_NS}}}oMathPara") or eq_par._p.findall(f"{{{D.M_NS}}}oMath"), key
            D.number_equation(doc, eq_par, p, key)
            nxt = p._p.getnext()
            if nxt is not None and nxt.tag == qn("w:p"):
                after_eq.append(nxt)
        elif kind == "FIG":
            n = pre.fig.index(key) + 1
            fp = D.new_par_before(p, doc, "MDPI Figure")
            fp.add_run().add_picture(str(PREP / "figures" / f"{FIG_FILES[key]}.png"), width=Cm(FIG_WIDTH[key]))
            cp = D.new_par_before(p, doc, "MDPI Figure Caption")
            D.add_marked(cp, f"**Figure {n}.** {caps[key]}", 9)
        elif kind in ("TAB", "ATAB"):
            label = f"Table {pre.tab.index(key) + 1}" if kind == "TAB" else f"Table A{pre.atab.index(key) + 1}"
            insert_table(doc, p, tables[key], label)
        elif kind == "STAB":
            if key == "S3":
                cap = D.new_par_before(p, doc, "MDPI Table Caption")
                D.add_marked(cap, f"**Table S3.** {supp['S3_title']}", 9)
                for i, sp in enumerate(supp["S3"]):
                    lab = D.new_par_before(p, doc, "MDPI Table Caption")
                    lab.paragraph_format.space_before = Pt(6)
                    D.add_marked(lab, f"({'abcd'[i]}) {sp['label']}", 9)
                    tbl = D.add_table(doc, p, sp["header"], sp["rows"], sp["widths"], None, sp["size"])
                    for row, c0, c1 in sp["merges"]:
                        D.merge_header(tbl, row, c0, c1)
                    D.new_par_before(p, doc, "MDPI Table Footer")
            else:
                insert_table(doc, p, supp[key], f"Table {key}")
        elif kind == "ABBREV":
            tbl = doc.add_table(rows=len(pre.abbrev), cols=2)
            D._clear_table_style(tbl)
            D.set_widths(tbl, [2.2, 10.0])
            for row, (a, b) in zip(tbl.rows, pre.abbrev):
                for cell, t in zip(row.cells, (a, b)):
                    cell.paragraphs[0].style = doc.styles["MDPI Table Body"]
                    D.add_marked(cell.paragraphs[0], t, 9)
            p._p.addprevious(tbl._tbl)
            D.new_par_before(p, doc, "MDPI Table Footer")
        elif kind == "REFERENCES":
            for n, k in enumerate(cite_order, 1):
                rp = D.new_par_before(p, doc, "MDPI References")
                rp.paragraph_format.tab_stops.add_tab_stop(Cm(0.75))
                rp.add_run(f"{n}.\t").font.size = Pt(9)
                D.add_marked(rp, ms_refs.markup(k) + " ", 9)
                pre_t, url, suf = ms_refs.tail(k)
                if pre_t:
                    rp.add_run(pre_t).font.size = Pt(9)
                if url:
                    D.add_hyperlink(rp, url, size=9)
                if suf:
                    rp.add_run(suf).font.size = Pt(9)
                rp.alignment = WD_ALIGN_PARAGRAPH.LEFT
        elif kind == "PAGEBREAK":
            bp = D.new_par_before(p, doc, "MDPI No Indent")
            bp.add_run().add_break(WD_BREAK.PAGE)
        remove(p)
    # continuation paragraphs after an equation start flush left
    for el in after_eq:
        q = next((x for x in doc.paragraphs if x._p is el), None)
        if q is not None and q.text[:1].islower():
            q.style = doc.styles["MDPI No Indent"]
    # thin rule under the keywords, as in the journal layout
    for q in doc.paragraphs:
        if q.style.name == "MDPI Keywords":
            ppr = q._p.get_or_add_pPr()
            D._borders(ppr, "w:pBdr", dict(bottom=4))
            ppr.find(qn("w:pBdr")).find(qn("w:bottom")).set(qn("w:space"), "6")
    # the abstract and keywords labels are bold already; make list paragraphs justified
    core = doc.core_properties
    core.author, core.comments, core.keywords = "", "", ""
    doc.save(str(path))
    return doc


def to_pdf(docx_path):
    subprocess.run(["soffice", "--headless", "--convert-to", "pdf", "--outdir", str(docx_path.parent), str(docx_path)], check=True,
                   stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)


# --------------------------------------------------------------------- main

def main():
    R, extra, prep, X = ms_tokens.load()
    authors = None
    if (BUILD / "authors.json").exists():
        authors = json.loads((BUILD / "authors.json").read_text())
    raw = "\n\n".join(p.read_text() for p in SRC)
    pre = Pre(R, authors)
    pre.scan(raw)
    title, abstract, keywords, md = assemble(pre, raw, authors)
    assert "{{" not in md and "[[" not in md and "[@" not in md, re.findall(r".{20}(?:\{\{|\[\[|\[@).{30}", md)[:5]
    n_abs = len(re.findall(r"\S+", abstract))
    assert n_abs <= 200, n_abs
    assert len(keywords.split(";")) == 6
    tables = ms_tables.main_tables(R, prep, pre.ref)
    supp = ms_tables.supp_tables(R, prep, X)
    caps = figure_captions()
    assert R.v("B_MIN_CI_WHERE") == "known reference, ×1.2, vs AFE-only PRr"

    ms = OUT / "Phase_Robust_Sensors_Manuscript.docx"
    pandoc(md, ms)
    core_title = title
    doc = postprocess(ms, pre, tables, caps, pre.cite)
    doc.core_properties.title = core_title
    doc.save(str(ms))

    # ---- supplementary document
    smd = [div("MDPI Type", "Supplementary Materials"), div("MDPI Title", title),
           div("MDPI No Indent", "This document contains the supplementary tables that are cited in the article. All values are simulation results and were "
                                 "computed from the same saved result files and per-record predictions as the tables of the article. PRr denotes the primary "
                                 "method, E the gain-error bound of the reference monitor, and ×0.8 to ×1.2 the actual reference amplitude relative to nominal.")]
    for k in ("S1", "S2", "S3", "S4", "S5", "S6", "S7"):
        if k in ("S3", "S4"):
            smd.append("ZZMARK:PAGEBREAK:x:ZZ\n")
        smd.append(f"ZZMARK:STAB:{k}:ZZ\n")
    sp = OUT / "Phase_Robust_Sensors_Supplementary.docx"
    pandoc("\n".join(smd), sp)
    sdoc = postprocess(sp, pre, tables, caps, pre.cite, supp=supp)
    sdoc.core_properties.title = "Supplementary Materials: " + title
    sdoc.save(str(sp))

    to_pdf(ms)
    to_pdf(sp)

    # ---- support files
    (OUT / "references.bib").write_text(ms_refs.bibtex(pre.cite))
    used = sorted(pre.used_tokens)
    with open(OUT / "MANUSCRIPT_NUMBER_PROVENANCE.csv", "w", newline="") as fh:
        w = csv.writer(fh)
        w.writerow(["token", "printed_value", "raw_value", "status", "source_file", "key_or_row", "calculation"])
        for t in sorted(R.entries):
            e = R.entries[t]
            w.writerow([t, mn(e.value), e.raw, e.status, e.source_file, e.key, e.calculation])
    state = dict(title=title, abstract=abstract, abstract_words=n_abs, keywords=keywords, sections=pre.sec, equations=pre.eq, figures=pre.fig,
                 tables=pre.tab, appendix_tables=pre.atab, citations=pre.cite, text_tokens=used, authors_supplied=bool(authors))
    (WORK / "state.json").write_text(json.dumps(state, indent=1, ensure_ascii=False))
    print(f"abstract words: {n_abs}; sections: {len(pre.sec)}; equations: {len(pre.eq)}; figures: {len(pre.fig)}; tables: {len(pre.tab)}+{len(pre.atab)}; "
          f"references: {len(pre.cite)} of {len(ms_refs.REFS)}; text tokens: {len(used)}")
    uncited = [k for k in ms_refs.REFS if k not in pre.cite]
    print("uncited references:", uncited)


if __name__ == "__main__":
    main()
