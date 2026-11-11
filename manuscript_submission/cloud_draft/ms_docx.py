"""Word helpers: styles, inline markup, three-line tables, equation numbering."""
from __future__ import annotations

import copy
import re

from docx.enum.table import WD_CELL_VERTICAL_ALIGNMENT, WD_TABLE_ALIGNMENT
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.enum.style import WD_STYLE_TYPE
from docx.oxml import OxmlElement
from docx.oxml.ns import qn
from docx.shared import Cm, Pt, RGBColor

FONT = "Palatino Linotype"
TEXT_W = 17.0  # cm
M_NS = "http://schemas.openxmlformats.org/officeDocument/2006/math"


# ------------------------------------------------------------------ styles

def _rfonts(rpr, name):
    rf = rpr.find(qn("w:rFonts"))
    if rf is None:
        rf = OxmlElement("w:rFonts")
        rpr.insert(0, rf)
    for a in list(rf.attrib):
        del rf.attrib[a]
    for a in ("w:ascii", "w:hAnsi", "w:cs", "w:eastAsia"):
        rf.set(qn(a), name)


def force_font(doc, name=FONT):
    styles = doc.styles.element
    for rf in styles.iter(qn("w:rFonts")):
        for a in list(rf.attrib):
            del rf.attrib[a]
        for a in ("w:ascii", "w:hAnsi", "w:cs", "w:eastAsia"):
            rf.set(qn(a), name)
    dd = styles.find(qn("w:docDefaults"))
    rpr = dd.find(qn("w:rPrDefault")).find(qn("w:rPr"))
    _rfonts(rpr, name)


def style(doc, name, base=None):
    try:
        return doc.styles[name]
    except KeyError:
        st = doc.styles.add_style(name, WD_STYLE_TYPE.PARAGRAPH)
        if base:
            st.base_style = doc.styles[base]
        return st


def fmt_style(st, size=None, bold=None, italic=None, align=None, before=None, after=None, first=None, left=None,
              keep_next=None, line=None, color=True):
    f, pf = st.font, st.paragraph_format
    f.name = FONT
    _rfonts(st.element.get_or_add_rPr(), FONT)
    if size is not None:
        f.size = Pt(size)
    if bold is not None:
        f.bold = bold
    if italic is not None:
        f.italic = italic
    if color:
        f.color.rgb = RGBColor(0, 0, 0)
    if align is not None:
        pf.alignment = align
    if before is not None:
        pf.space_before = Pt(before)
    if after is not None:
        pf.space_after = Pt(after)
    if first is not None:
        pf.first_line_indent = Cm(first)
    if left is not None:
        pf.left_indent = Cm(left)
    if keep_next is not None:
        pf.keep_with_next = keep_next
    if line is not None:
        pf.line_spacing = line
    pf.widow_control = True


def setup_styles(doc):
    J, L, C = WD_ALIGN_PARAGRAPH.JUSTIFY, WD_ALIGN_PARAGRAPH.LEFT, WD_ALIGN_PARAGRAPH.CENTER
    force_font(doc)
    doc.styles["Normal"].font.size = Pt(10)
    fmt_style(doc.styles["Normal"], size=10)
    fmt_style(style(doc, "Body Text"), size=10, align=J, before=0, after=2, first=0.75, line=1.08)
    fmt_style(style(doc, "First Paragraph"), size=10, align=J, before=0, after=2, first=0.75, line=1.08)
    fmt_style(style(doc, "Compact"), size=10, align=J, before=0, after=2, line=1.08)
    fmt_style(style(doc, "Heading 1"), size=10.5, bold=True, italic=False, align=L, before=12, after=4, first=0, keep_next=True)
    fmt_style(style(doc, "Heading 2"), size=10, bold=False, italic=True, align=L, before=8, after=3, first=0, keep_next=True)
    fmt_style(style(doc, "MDPI Type", "Normal"), size=10, italic=True, align=L, before=0, after=6, first=0)
    fmt_style(style(doc, "MDPI Title", "Normal"), size=18, bold=True, align=L, before=0, after=10, first=0, line=1.05)
    fmt_style(style(doc, "MDPI Authors", "Normal"), size=10, bold=True, align=L, before=0, after=6, first=0)
    fmt_style(style(doc, "MDPI Affiliation", "Normal"), size=8, align=L, before=0, after=2, first=0, left=0.3)
    fmt_style(style(doc, "MDPI Abstract", "Normal"), size=10, align=J, before=8, after=6, first=0, line=1.08)
    fmt_style(style(doc, "MDPI Keywords", "Normal"), size=10, align=J, before=0, after=10, first=0, line=1.08)
    fmt_style(style(doc, "MDPI Backmatter", "Normal"), size=9, align=J, before=0, after=4, first=0, line=1.05)
    fmt_style(style(doc, "MDPI No Indent", "Normal"), size=10, align=J, before=0, after=2, first=0, line=1.08)
    fmt_style(style(doc, "MDPI Figure", "Normal"), size=10, align=C, before=8, after=3, first=0, keep_next=True)
    fmt_style(style(doc, "MDPI Figure Caption", "Normal"), size=9, align=J, before=0, after=10, first=0, line=1.03)
    fmt_style(style(doc, "MDPI Table Caption", "Normal"), size=9, align=J, before=10, after=3, first=0, keep_next=True, line=1.03)
    fmt_style(style(doc, "MDPI Table Body", "Normal"), size=8.5, align=L, before=1, after=1, first=0, line=1.0)
    fmt_style(style(doc, "MDPI Table Footer", "Normal"), size=8, align=J, before=3, after=10, first=0, line=1.0)
    fmt_style(style(doc, "MDPI References", "Normal"), size=9, align=J, before=0, after=2, first=-0.75, left=0.75, line=1.03)
    fmt_style(style(doc, "MDPI Equation", "Normal"), size=10, align=C, before=3, after=3, first=0)
    for name in ("Heading 1", "Heading 2"):
        rpr = doc.styles[name].element.get_or_add_rPr()
        for tag in ("w:color",):
            for el in rpr.findall(qn(tag)):
                rpr.remove(el)
        doc.styles[name].font.color.rgb = RGBColor(0, 0, 0)


def page_setup(doc, landscape=False):
    for s in doc.sections:
        s.page_width, s.page_height = (Cm(29.7), Cm(21.0)) if landscape else (Cm(21.0), Cm(29.7))
        s.top_margin, s.bottom_margin = Cm(2.5), Cm(2.2)
        s.left_margin = s.right_margin = Cm(2.0)
        s.footer_distance = Cm(1.1)
        fp = s.footer.paragraphs[0] if s.footer.paragraphs else s.footer.add_paragraph()
        fp.alignment = WD_ALIGN_PARAGRAPH.CENTER
        for r in list(fp.runs):
            r._r.getparent().remove(r._r)
        run = fp.add_run()
        run.font.size = Pt(8)
        for kind, text in (("begin", None), (None, "PAGE"), ("end", None)):
            if kind:
                fc = OxmlElement("w:fldChar")
                fc.set(qn("w:fldCharType"), kind)
                run._r.append(fc)
            else:
                it = OxmlElement("w:instrText")
                it.set(qn("xml:space"), "preserve")
                it.text = text
                run._r.append(it)


# ------------------------------------------------------------ inline markup

_TOK = re.compile(r"(\*\*.+?\*\*|\*.+?\*|_\{.+?\}|\^\{.+?\})")


def add_marked(par, text, size=None, bold=False, italic=False):
    """Add text with **bold**, *italic*, _{sub} and ^{sup} markup as runs."""
    for part in _TOK.split(text):
        if not part:
            continue
        b, i, sub, sup = bold, italic, False, False
        if part.startswith("**") and part.endswith("**") and len(part) > 4:
            part, b = part[2:-2], True
        elif part.startswith("*") and part.endswith("*") and len(part) > 2:
            part, i = part[1:-1], True
        elif part.startswith("_{"):
            part, sub = part[2:-1], True
        elif part.startswith("^{"):
            part, sup = part[2:-1], True
        if "_{" in part or "^{" in part:  # nested sub/superscript inside italic or bold
            for sp in re.split(r"(_\{.+?\}|\^\{.+?\})", part):
                if not sp:
                    continue
                s2, p2 = sp.startswith("_{"), sp.startswith("^{")
                _run(par, sp[2:-1] if (s2 or p2) else sp, size, b, i and not (s2 or p2), s2, p2)
            continue
        _run(par, part, size, b, i, sub, sup)
    return par


def _run(par, text, size, b, i, sub, sup):
    r = par.add_run(text)
    r.bold = b or None
    r.italic = i or None
    if size:
        r.font.size = Pt(size)
    if sub:
        r.font.subscript = True
    if sup:
        r.font.superscript = True
    return r


def add_hyperlink(par, url, text=None, size=None):
    rid = par.part.relate_to(url, "http://schemas.openxmlformats.org/officeDocument/2006/relationships/hyperlink", is_external=True)
    h = OxmlElement("w:hyperlink")
    h.set(qn("r:id"), rid)
    r = OxmlElement("w:r")
    rpr = OxmlElement("w:rPr")
    if size:
        for tag in ("w:sz", "w:szCs"):
            sz = OxmlElement(tag)
            sz.set(qn("w:val"), str(int(size * 2)))
            rpr.append(sz)
    r.append(rpr)
    t = OxmlElement("w:t")
    t.text = text or url
    t.set(qn("xml:space"), "preserve")
    r.append(t)
    h.append(r)
    par._p.append(h)


def new_par_before(anchor, doc, style_name, text=None, size=None):
    p = anchor.insert_paragraph_before("", style=doc.styles[style_name])
    if text:
        add_marked(p, text, size)
    return p


# ------------------------------------------------------------------ tables

def _borders(el_parent, tag, edges):
    b = el_parent.find(qn(tag))
    if b is None:
        b = OxmlElement(tag)
        el_parent.append(b)
    for edge, sz in edges.items():
        e = b.find(qn(f"w:{edge}"))
        if e is None:
            e = OxmlElement(f"w:{edge}")
            b.append(e)
        e.set(qn("w:val"), "single" if sz else "nil")
        e.set(qn("w:sz"), str(sz or 0))
        e.set(qn("w:space"), "0")
        e.set(qn("w:color"), "000000")


def _cell_borders(cell, **edges):
    tcpr = cell._tc.get_or_add_tcPr()
    _borders(tcpr, "w:tcBorders", edges)


def _clear_table_style(tbl):
    tblpr = tbl._tbl.tblPr
    for tag in ("w:tblStyle", "w:tblBorders", "w:tblLook"):
        for el in tblpr.findall(qn(tag)):
            tblpr.remove(el)
    _borders(tblpr, "w:tblBorders", dict(top=0, left=0, bottom=0, right=0, insideH=0, insideV=0))
    lay = OxmlElement("w:tblLayout")
    lay.set(qn("w:type"), "fixed")
    tblpr.append(lay)
    mar = OxmlElement("w:tblCellMar")
    for side, w in (("left", 55), ("right", 55), ("top", 15), ("bottom", 15)):
        e = OxmlElement(f"w:{side}")
        e.set(qn("w:w"), str(w))
        e.set(qn("w:type"), "dxa")
        mar.append(e)
    tblpr.append(mar)


def set_widths(tbl, widths_cm):
    tbl.autofit = False
    grid = tbl._tbl.tblGrid
    for gc, w in zip(grid.findall(qn("w:gridCol")), widths_cm):
        gc.set(qn("w:w"), str(int(w * 567)))
    for row in tbl.rows:
        for cell, w in zip(row.cells, widths_cm):
            cell.width = Cm(w)
    tblpr = tbl._tbl.tblPr
    tw = tblpr.find(qn("w:tblW"))
    if tw is None:
        tw = OxmlElement("w:tblW")
        tblpr.append(tw)
    tw.set(qn("w:w"), str(int(sum(widths_cm) * 567)))
    tw.set(qn("w:type"), "dxa")


def add_table(doc, anchor, header, rows, widths, align=None, size=8.5, header_rows=1, rules_after=(), bold_rows=()):
    """Insert a three-line table before the paragraph `anchor`.

    header: list of header rows (each a list of cell texts) or one list.
    rules_after: body-row indices after which a thin rule is drawn.
    """
    if header and not isinstance(header[0], (list, tuple)):
        header = [header]
    ncol = len(widths)
    scale = TEXT_W / sum(widths) if sum(widths) > TEXT_W else 1.0
    widths = [w * scale for w in widths]
    align = align or ["l"] + ["c"] * (ncol - 1)
    tbl = doc.add_table(rows=len(header) + len(rows), cols=ncol)
    _clear_table_style(tbl)
    tbl.alignment = WD_TABLE_ALIGNMENT.CENTER
    set_widths(tbl, widths)
    amap = {"l": WD_ALIGN_PARAGRAPH.LEFT, "c": WD_ALIGN_PARAGRAPH.CENTER, "r": WD_ALIGN_PARAGRAPH.RIGHT}
    nh = len(header)
    all_rows = list(header) + list(rows)
    for ri, cells in enumerate(all_rows):
        row = tbl.rows[ri]
        trpr = row._tr.get_or_add_trPr()
        cs = OxmlElement("w:cantSplit")
        trpr.append(cs)
        if ri < nh:
            th = OxmlElement("w:tblHeader")
            trpr.append(th)
        for ci in range(ncol):
            cell = row.cells[ci]
            cell.vertical_alignment = WD_CELL_VERTICAL_ALIGNMENT.CENTER
            text = "" if ci >= len(cells) or cells[ci] is None else str(cells[ci])
            lines = text.split("\n")
            p = cell.paragraphs[0]
            for li, ln in enumerate(lines):
                if li:
                    p = cell.add_paragraph()
                p.style = doc.styles["MDPI Table Body"]
                p.alignment = amap[align[ci]] if ri >= nh else (WD_ALIGN_PARAGRAPH.LEFT if align[ci] == "l" else WD_ALIGN_PARAGRAPH.CENTER)
                p.paragraph_format.keep_with_next = ri < len(all_rows) - 1
                add_marked(p, ln, size, bold=(ri < nh) or (ri - nh in bold_rows))
            edges = {}
            if ri == 0:
                edges["top"] = 8
            if ri == nh - 1:
                edges["bottom"] = 4
            if ri == len(all_rows) - 1:
                edges["bottom"] = 8
            if ri >= nh and (ri - nh) in rules_after:
                edges["bottom"] = 2
            if edges:
                _cell_borders(cell, **edges)
    anchor._p.addprevious(tbl._tbl)
    return tbl


def merge_header(tbl, row, c0, c1):
    a, b = tbl.cell(row, c0), tbl.cell(row, c1)
    text_pars = [(p.text, p.runs[0].font.size if p.runs else None) for p in a.paragraphs]
    m = a.merge(b)
    # keep only the first paragraph text
    for p in m.paragraphs[1:]:
        p._p.getparent().remove(p._p)
    m.paragraphs[0].alignment = WD_ALIGN_PARAGRAPH.CENTER
    _cell_borders(m, bottom=2)
    return m


# --------------------------------------------------------------- equations

def number_equation(doc, eq_par, marker, number):
    """Wrap a display-equation paragraph in a borderless two-column table with the number at the right."""
    tbl = doc.add_table(rows=1, cols=2)
    _clear_table_style(tbl)
    tbl.alignment = WD_TABLE_ALIGNMENT.CENTER
    set_widths(tbl, [TEXT_W - 1.4, 1.4])
    c0, c1 = tbl.rows[0].cells
    for c in (c0, c1):
        c.vertical_alignment = WD_CELL_VERTICAL_ALIGNMENT.CENTER
    p0 = c0.paragraphs[0]
    p0.style = doc.styles["MDPI Equation"]
    for child in list(eq_par._p):
        if child.tag in (f"{{{M_NS}}}oMathPara", f"{{{M_NS}}}oMath"):
            p0._p.append(copy.deepcopy(child))
    p1 = c1.paragraphs[0]
    p1.style = doc.styles["MDPI Equation"]
    p1.alignment = WD_ALIGN_PARAGRAPH.RIGHT
    p1.add_run(f"({number})")
    marker._p.addprevious(tbl._tbl)
    eq_par._p.getparent().remove(eq_par._p)
    return tbl
