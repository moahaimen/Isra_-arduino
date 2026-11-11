"""MDPI-style reference formatting, BibTeX export and verification record."""
from __future__ import annotations

import refs

REFS, ACCESSED, DROPPED = refs.REFS, refs.ACCESSED, refs.DROPPED


def _authors(r):
    """Author list without a trailing period (the formatter adds one)."""
    s = "; ".join(r.get("authors") or [])
    return s[:-1] if s.endswith(".") else s


def link(r):
    if r.get("doi"):
        return "https://doi.org/" + r["doi"]
    return r.get("url")


def markup(key):
    """Reference text with **bold**/*italic* markup (without the trailing link)."""
    r = REFS[key]
    t = r["type"]
    a = _authors(r)
    if t == "article":
        s = f"{a}. {r['title']}. *{r['journal']}* **{r['year']}**"
        if r.get("volume"):
            s += f", *{r['volume']}*"
        if r.get("pages"):
            s += f", {r['pages']}"
        return s + "."
    if t == "book":
        return f"{a}. *{r['title']}*; {r['publisher']}: {r['address']}, {r['year']}."
    if t == "inproceedings":
        s = f"{a}. {r['title']}. In {r['booktitle']}, {r['address']}, {r['dates']}"
        if r.get("pages"):
            s += f"; pp. {r['pages']}"
        return s + "."
    if t == "standard":
        return f"*{r['designation']}*; {r['title']}. {r['publisher']}: {r['address']}, {r['year']}."
    if t == "preprint":
        return f"{a}. {r['title']}. *arXiv* **{r['year']}**, arXiv:{r['arxiv']}."
    if t == "web":
        s = f"{a}. {r['title']}."
        extra = [x for x in (r.get("publisher") if r.get("publisher") and r.get("publisher") != a else None, r.get("note"),
                             str(r["year"]) if r.get("year") and not (r.get("note") and str(r["year"]) in r["note"]) else None) if x]
        if extra:
            s += " " + ", ".join(extra) + "."
        return s
    raise ValueError(t)


def tail(key):
    """(prefix, url, suffix) printed after the reference text."""
    r = REFS[key]
    if r["type"] == "web":
        return "Available online: ", r["url"], f" (accessed on {ACCESSED})."
    if r["type"] == "preprint" or (not r.get("doi") and r.get("url")):
        return "Available online: ", r["url"], f" (accessed on {ACCESSED})."
    return "", link(r), ""


def plain(key):
    import re
    p, u, s = tail(key)
    return re.sub(r"\*+", "", markup(key)) + " " + p + (u or "") + s


def bibtex(order):
    kind = {"article": "article", "book": "book", "inproceedings": "inproceedings", "standard": "techreport", "web": "misc", "preprint": "misc"}
    out = ["% References of the manuscript, in order of first citation.",
           "% Generated from manuscript_submission/build/refs.py; see REFERENCE_VERIFICATION.md for the checks made on each entry.", ""]
    for key in order:
        r = REFS[key]
        f = []
        if r.get("authors"):
            f.append(("author", " and ".join(x.replace("et al.", "others") for x in r["authors"])))
        elif r["type"] == "standard":
            f.append(("institution", r["publisher"]))
        f.append(("title", "{" + r["title"] + "}"))
        if r["type"] == "article":
            f += [("journal", r.get("journal_full") or r["journal"]), ("volume", r.get("volume")), ("pages", (r.get("pages") or "").replace("–", "--"))]
        if r["type"] == "inproceedings":
            f += [("booktitle", r["booktitle"]), ("address", r["address"]), ("pages", (r.get("pages") or "").replace("–", "--"))]
        if r["type"] == "book":
            f += [("publisher", r["publisher"]), ("address", r["address"])]
        if r["type"] == "standard":
            f += [("number", r["designation"]), ("type", "Standard"), ("address", r["address"])]
        if r["type"] == "preprint":
            f += [("eprint", r["arxiv"]), ("archiveprefix", "arXiv")]
        if r["type"] == "web":
            f += [("howpublished", r.get("note") or "Online"), ("note", f"Accessed on {ACCESSED}")]
        f.append(("year", str(r["year"]) if r.get("year") else None))
        f.append(("doi", r.get("doi")))
        if r.get("url") and not r.get("doi"):
            f.append(("url", r["url"]))
        body = ",\n".join(f"  {k} = {{{v}}}" for k, v in f if v)
        out.append(f"@{kind[r['type']]}{{{key},\n{body}\n}}\n")
    return "\n".join(out)
