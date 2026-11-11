# Review handoff — 2026-10-26

## Result

The package was rebuilt from the included frozen evidence package and passes all
16 automatic quality-control checks. The rebuild recomputed 475 quantities from
saved per-record predictions with 0 mismatches, and the evidence hash check
reported 85 files with 0 mismatches.

The package remains a manuscript-preparation package, not a submission-ready
paper. Author metadata, the optimizer/early-stopping confirmation, the ngspice
version, and the systematic literature search/reference verification are still
explicitly marked as author tasks.

## Fixes made during review

1. The compiled DOCX generator no longer carries repeated Markdown `---`
   separators into the single Pandoc stream. This prevents Pandoc from turning
   the intervening manuscript prose into a one-column table. The rendered DOCX
   is now 27 pages and was visually checked at the beginning, middle, and end.
2. Figure 8 now leaves the top y-axis label of its phase panel clear of the
   neighboring panel title. The automatic label-overlap check passes, and the
   regenerated PNG was visually checked.

## Frozen headline values retained

The rebuild did not change the evidence values. In particular, the primary PRr
values remain 0.656 on the behavioral grid and 0.649 on the ngspice grid; the
matched-grid transfer loss remains 0.002 with 95% CI [-0.003, +0.006]. These
are not to be subtracted across the different five-amplitude versus
three-amplitude grids.

The evidence package is regenerated from saved results and predictions only;
it does not claim end-to-end simulator rerun or retraining reproducibility.
