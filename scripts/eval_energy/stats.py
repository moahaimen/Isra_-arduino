#!/usr/bin/env python3
"""Statistical helpers.

* Descriptive: mean, std (ddof=1), median, 95 % CI of the mean using the
  Student t distribution (runs are independent seeds).
* Paired comparison: two modes evaluated on the SAME workload (same scenario
  and seed) form a matched pair. We use the two-sided Wilcoxon signed-rank
  test on the paired differences (no normality assumption). Zero differences
  are discarded (Wilcoxon's original treatment) and the number of non-zero
  pairs is reported; with fewer than 6 non-zero pairs a two-sided test at
  alpha = 0.05 cannot reach significance, so no p-value is reported.
* Effect size: matched-pairs rank-biserial correlation
  r_rb = (R+ - R-) / (R+ + R-), in [-1, 1], plus the median paired difference.
* Multiplicity: Holm-Bonferroni step-down correction over the whole family of
  tests that is reported together.
"""
from __future__ import annotations

import math
from typing import Dict, List, Sequence

import numpy as np
from scipy import stats as sps

MIN_NONZERO_PAIRS = 6


def describe(values: Sequence[float]) -> Dict[str, float]:
    v = np.asarray([x for x in values if x is not None and not (isinstance(x, float) and math.isnan(x))], float)
    n = int(v.size)
    if n == 0:
        return {"n": 0, "mean": math.nan, "std": math.nan, "median": math.nan, "ci95_low": math.nan,
                "ci95_high": math.nan}
    mean = float(v.mean())
    std = float(v.std(ddof=1)) if n > 1 else 0.0
    half = float(sps.t.ppf(0.975, n - 1) * std / math.sqrt(n)) if n > 1 else math.nan
    return {"n": n, "mean": mean, "std": std, "median": float(np.median(v)),
            "ci95_low": mean - half if n > 1 else math.nan, "ci95_high": mean + half if n > 1 else math.nan}


def rank_biserial(diffs: np.ndarray) -> float:
    d = diffs[diffs != 0]
    if d.size == 0:
        return 0.0
    ranks = sps.rankdata(np.abs(d))
    r_plus = ranks[d > 0].sum()
    r_minus = ranks[d < 0].sum()
    return float((r_plus - r_minus) / (r_plus + r_minus))


def paired_test(a: Sequence[float], b: Sequence[float]) -> Dict[str, float]:
    """Wilcoxon signed-rank test of a vs b (paired, two-sided). diff = a - b."""
    a = np.asarray(a, float)
    b = np.asarray(b, float)
    ok = ~(np.isnan(a) | np.isnan(b))
    d = a[ok] - b[ok]
    nz = d[np.abs(d) > 1e-12]
    out = {"n_pairs": int(d.size), "n_nonzero": int(nz.size),
           "mean_a": float(a[ok].mean()) if d.size else math.nan,
           "mean_b": float(b[ok].mean()) if d.size else math.nan,
           "median_diff": float(np.median(d)) if d.size else math.nan,
           "mean_diff": float(d.mean()) if d.size else math.nan,
           "rank_biserial": rank_biserial(d) if d.size else math.nan,
           "W": math.nan, "p_value": math.nan, "test": "wilcoxon_signed_rank"}
    if nz.size >= MIN_NONZERO_PAIRS:
        res = sps.wilcoxon(nz, zero_method="wilcox", alternative="two-sided", method="auto")
        out["W"] = float(res.statistic)
        out["p_value"] = float(res.pvalue)
    else:
        out["test"] = "not_tested_insufficient_nonzero_pairs"
    return out


def holm(pvalues: List[float]) -> List[float]:
    """Holm-Bonferroni adjusted p-values (NaN entries are left as NaN)."""
    idx = [i for i, p in enumerate(pvalues) if p is not None and not math.isnan(p)]
    m = len(idx)
    adj = [math.nan] * len(pvalues)
    order = sorted(idx, key=lambda i: pvalues[i])
    running = 0.0
    for rank, i in enumerate(order):
        val = min(1.0, (m - rank) * pvalues[i])
        running = max(running, val)
        adj[i] = running
    return adj
