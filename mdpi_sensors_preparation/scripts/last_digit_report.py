"""Report every registered value whose stored four-decimal value does not determine its three-decimal rounding.

Several result CSVs store four decimals. When the fourth decimal is 5, the stored value is a tie at three decimals
and the correct print depends on the full-precision value. registry_build.refine_full_precision() recomputes these
values from the saved per-record predictions. Ratios of counts can be exact ties even at full precision (for example
1287/13200 = 0.0975); common.round_exact() rounds those half-to-even in decimal arithmetic, because the binary float
nearest to 0.0975 lies below the tie and format(x, ".3f") would print 0.097.

    python3 mdpi_sensors_preparation/scripts/last_digit_report.py
"""
import contextlib
import csv
import io
import re
from fractions import Fraction

import registry_build
from common import OUT, fmt

with contextlib.redirect_stdout(io.StringIO()):
    R, extra = registry_build.build()


def legacy(x, e):
    s = format(float(x), f".{e.decimals}f")
    return ("+" + s) if e.signed and not s.startswith("-") else s


rows = []
for t, e in R.entries.items():
    m = re.search(r"the CSV stores ([-\d.e]+)$", e.calculation or "")
    if not (m and e.decimals is not None):
        continue
    stored = m.group(1)
    if not re.fullmatch(r"-?\d+\.\d{3}5", stored):
        continue
    frac = ""
    if t.startswith(("RL_", "RF_", "SEP_")):  # ratios of record counts
        f = Fraction(e.raw).limit_denominator(100000)
        if abs(float(f) - e.raw) < 1e-13:
            frac = f"{f.numerator}/{f.denominator}"
    tie = bool(re.fullmatch(r"-?\d+\.\d{3}5", format(e.raw, ".12g")))
    old = legacy(float(stored), e)
    rows.append([t, e.key, stored, format(e.raw, ".12g"), frac, "yes" if tie else "no", e.value, old, "yes" if old != e.value else "no",
                 "point estimate recomputed from predictions"])
for t in extra["refined"]["ci_ties_recomputed"]:
    e = R.entries[t]
    stored = re.search(r"stored bound ([-\d.]+)", e.calculation).group(1)
    old = legacy(float(stored), e)
    rows.append([t, e.key, stored, format(e.raw, ".12g"), "", "no", e.value, old, "yes" if old != e.value else "no",
                 "interval bound recomputed with the original code on the author's computer"])
path = OUT / "verification" / "LAST_DIGIT_DIFFERENCES.csv"
with open(path, "w", newline="") as fh:
    w = csv.writer(fh)
    w.writerow(["token", "source_key", "stored_four_decimal_value", "full_precision_value", "exact_fraction_of_counts",
                "exact_tie_at_full_precision", "correct_print", "print_by_float_format_of_stored_value", "differs", "note"])
    w.writerows(rows)
print(len(rows), "rows,", sum(r[8] == "yes" for r in rows), "differ ->", path)
for r in rows:
    if r[5] == "yes":
        print("exact tie:", r[0], r[3], r[4], "->", r[6])
