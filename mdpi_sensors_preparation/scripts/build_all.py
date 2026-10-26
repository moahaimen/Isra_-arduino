"""Regenerate the complete MDPI Sensors package from the frozen evidence.

    python3 mdpi_sensors_preparation/scripts/build_all.py

Order: number registry -> verification -> figures -> tables -> documents/drafts -> quality control.
Nothing is retrained or re-simulated; all values come from evidence_package_2026-10-26/.
"""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

import docs  # noqa: E402
import figures  # noqa: E402
import qc  # noqa: E402
import tables  # noqa: E402
import verify  # noqa: E402
from common import OUT  # noqa: E402
from registry_build import build  # noqa: E402


def main():
    print("[1/6] building number registry")
    R, extra = build()
    print(f"      {len(R.entries)} numbers registered")
    print("[2/6] verifying evidence (hashes, recomputation from predictions, frozen facts)")
    summary, ff, rec = verify.main(R)
    if summary["evidence_files_hash_mismatch"] or summary["recomputed_mismatches"] or summary["facts_mismatch"]:
        raise SystemExit(f"verification failed: {summary}")
    print(f"      {summary['recomputed_quantities']} quantities recomputed, 0 mismatches")
    print("[3/6] figures")
    caps, fig_qc, _ = figures.build_all(R, extra)
    print("[4/6] tables")
    tabs = tables.build_all(R)
    print("[5/6] documents and manuscript drafts")
    _, first_cite = docs.build_all(R, caps, tabs, ff, summary)
    R.to_csv(OUT / "NUMBER_PROVENANCE_MDPI.csv")  # after tables/docs so table-derived tokens are included
    print(f"      NUMBER_PROVENANCE_MDPI.csv: {len(R.entries)} rows")
    print("[6/6] quality control")
    res = qc.run(R, caps, fig_qc, tabs, first_cite, summary)
    for name, r, _ in res:
        print(f"      {r:4s}  {name}")
    n_fail = sum(1 for x in res if x[1] == "FAIL")
    print("done" if not n_fail else f"done with {n_fail} QC failure(s); see QUALITY_CONTROL_REPORT.md")
    return 1 if n_fail else 0


if __name__ == "__main__":
    sys.exit(main())
