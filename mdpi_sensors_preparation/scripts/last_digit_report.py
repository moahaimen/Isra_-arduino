"""List every registered value whose three-decimal print changes when it is rounded from full precision.

Several result CSVs store four decimals. Rounding such a stored value again to three decimals can differ in the
last digit from the correctly rounded full-precision value (0.6585 -> 0.658, although the underlying 0.658502
rounds to 0.659). registry_build.refine_full_precision() recomputes these values from the saved per-record
predictions; this script writes the cases in which the printed value changes,
and the two interval bounds whose stored fourth decimal is 5.

    python3 mdpi_sensors_preparation/scripts/last_digit_report.py
"""
import contextlib
import csv
import io
import re

import registry_build
from common import OUT, fmt

with contextlib.redirect_stdout(io.StringIO()):
    R, extra = registry_build.build()
rows = []
for t, e in R.entries.items():
    m = re.search(r"the CSV stores ([-\d.e]+)$", e.calculation or "")
    if m and e.decimals is not None:
        old = fmt(float(m.group(1)), e.decimals, e.signed)
        if old != e.value:
            rows.append([t, e.key, m.group(1), old, f"{e.raw:.6f}", e.value, "point estimate recomputed from predictions"])
for t in extra["refined"]["ci_ties_recomputed"]:
    e = R.entries[t]
    stored = re.search(r"stored bound ([-\d.]+)", e.calculation).group(1)
    rows.append([t, e.key, stored, "ambiguous (fourth decimal is 5)", f"{e.raw:.6f}", e.value,
                 "interval bound recomputed with the original code on the author's computer"])
path = OUT / "verification" / "LAST_DIGIT_DIFFERENCES.csv"
with open(path, "w", newline="") as fh:
    w = csv.writer(fh)
    w.writerow(["token", "source_key", "stored_four_decimal_value", "print_from_stored_value", "full_precision_value", "correct_print", "note"])
    w.writerows(rows)
print(len(rows), "rows ->", path)
