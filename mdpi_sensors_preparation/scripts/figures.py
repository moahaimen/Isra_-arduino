"""Publication figures for the MDPI Sensors package.

All plotted values are read from the frozen result files (or the registry built
from them). Each figure is written as PNG (600 dpi), PDF and SVG, with the exact
plotted data in figure_source_data/ and an entry in FIGURE_SOURCE_DATA_MAP.csv.
"""
from __future__ import annotations

import csv
import re

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
import numpy as np  # noqa: E402
import pandas as pd  # noqa: E402
from matplotlib.patches import FancyArrowPatch, FancyBboxPatch, Rectangle  # noqa: E402

from common import (AMPS_BH, FAULT_LABELS, FAULTS, LAYER_LABELS, OUT, PHASE_VALUES, PP, RES,  # noqa: E402
                    load_csv, load_json, rel)

FIG = OUT / "figures"
SRC = OUT / "figure_source_data"

# Okabe-Ito-derived categorical palette, validated (adjacent CVD ΔE ≥ 9) with the
# dataviz validator; markers/line styles provide secondary encoding for print.
C = {"PRr": "#2a78d6", "R1": "#eb6834", "PR": "#1baf7a", "R1r": "#eda100", "PRrM": "#6250d6",
     "A0": "#7a7a7a", "nomon": "#e34948", "ink": "#1a1a1a", "muted": "#5a5a5a", "grid": "#d9d9d9",
     "sensor": "#1baf7a", "afe": "#2a78d6", "adc": "#eb6834", "healthy": "#7a7a7a"}
MK = {"A0": "x", "R1": "s", "R1r": "D", "PR": "^", "PRr": "o", "PRrM": "v"}
LS = {"A0": ":", "R1": "--", "R1r": "-.", "PR": (0, (5, 1, 1, 1)), "PRr": "-", "PRrM": (0, (1, 1))}
BLUES = ["#0d366b", "#184f95", "#2a78d6", "#5598e7", "#86b6ef"]  # known, E0..E5 (sequential)
FULL_W = 6.69  # 17 cm, MDPI full text width
HALF_W = 3.35

plt.rcParams.update({
    "font.family": "sans-serif", "font.sans-serif": ["Liberation Sans", "Arial", "DejaVu Sans"],
    "font.size": 8, "axes.titlesize": 8.5, "axes.labelsize": 8, "xtick.labelsize": 7.5,
    "ytick.labelsize": 7.5, "legend.fontsize": 7, "axes.linewidth": 0.6, "xtick.major.width": 0.6,
    "ytick.major.width": 0.6, "lines.linewidth": 1.4, "lines.markersize": 4.5, "axes.spines.top": False,
    "axes.spines.right": False, "axes.grid": True, "grid.color": C["grid"], "grid.linewidth": 0.4,
    "axes.axisbelow": True, "legend.frameon": False, "savefig.dpi": 600, "svg.fonttype": "none",
    "pdf.fonttype": 42, "axes.titleweight": "bold", "axes.titlelocation": "left", "mathtext.default": "regular",
})

MAP_ROWS: list[dict] = []
QC: dict = {}
DIMENSIONLESS = ("macro-F1", "recall", "Recall", "retention", "cross-confusion", "Cross-confusion", "fraction",
                 "Fraction", "Δ layer macro-F1", "Edge phase", "Reference amplitude", "standardized", "Standardised",
                 "Descriptor", "Predicted", "True", "normalized", "Normalized", "σ", "Control", "gain", "Arm",
                 "Reference condition", "Samples after edge")


def panel(ax, letter, title=""):
    ax.set_title(f"({letter}) {title}".strip(), pad=4)


def _poly(t, bb):
    """Rotated rectangle of a text artist (corners in display units)."""
    ang = np.deg2rad(t.get_rotation() % 180)
    c, s_ = abs(np.cos(ang)), abs(np.sin(ang))
    W, H = bb.width, bb.height
    det = c * c - s_ * s_
    if abs(det) < 0.2:  # ~45 deg: fall back to text height from font size
        h = t.get_fontsize() * t.figure.dpi / 72 * 1.15
        w = max((W - h * s_) / max(c, 1e-6), 1.0)
    else:
        w = (W * c - H * s_) / det
        h = (H * c - W * s_) / det
    w, h = max(w, 1.0), max(h, 1.0)
    ang = np.deg2rad(t.get_rotation())
    ux, uy = np.array([np.cos(ang), np.sin(ang)]), np.array([-np.sin(ang), np.cos(ang)])
    ctr = np.array([(bb.x0 + bb.x1) / 2, (bb.y0 + bb.y1) / 2])
    return np.array([ctr + sx * w / 2 * ux + sy * h / 2 * uy for sx, sy in ((-1, -1), (1, -1), (1, 1), (-1, 1))])


def _sat_overlap(p, q, margin=0.8):
    for poly in (p, q):
        for i in range(4):
            e = poly[(i + 1) % 4] - poly[i]
            n = np.array([-e[1], e[0]])
            n /= np.linalg.norm(n) + 1e-12
            a, b = p @ n, q @ n
            if a.max() - margin <= b.min() or b.max() - margin <= a.min():
                return False
    return True


def text_overlaps(fig):
    """Pairs of visible text artists whose rendered (rotated) boxes intersect."""
    fig.canvas.draw()
    r = fig.canvas.get_renderer()
    for ax in fig.axes:
        for axis, lim in ((ax.xaxis, ax.get_xlim()), (ax.yaxis, ax.get_ylim())):
            lo, hi = min(lim), max(lim)
            for tk in axis.get_major_ticks() + axis.get_minor_ticks():
                if not (lo - 1e-9 <= tk.get_loc() <= hi + 1e-9):
                    tk.label1._qc_ignore = True
                    tk.label2._qc_ignore = True
    texts = [t for t in fig.findobj(matplotlib.text.Text) if t.get_visible() and t.get_text().strip()
             and not getattr(t, "_qc_ignore", False)]
    polys = []
    for t in texts:
        try:
            bb = t.get_window_extent(r)
        except Exception:
            continue
        polys.append((t, _poly(t, bb)))
    over = []
    for i in range(len(polys)):
        for j in range(i + 1, len(polys)):
            if _sat_overlap(polys[i][1], polys[j][1]):
                over.append((polys[i][0].get_text(), polys[j][0].get_text()))
    return over, []


def _isnum(x):
    try:
        float(x.replace("−", "-").replace("×", ""))
        return True
    except ValueError:
        return False


def axis_labels(fig):
    labs = []
    for ax in fig.axes:
        if not ax.axison:
            continue
        for lab, kind in ((ax.get_xlabel(), "x"), (ax.get_ylabel(), "y")):
            ticks = ax.get_xticklabels() if kind == "x" else ax.get_yticklabels()
            has_ticks = any(_isnum(t.get_text()) for t in ticks)
            labs.append((lab, has_ticks))
    return labs


def save(fig, name, kind, sources, data: pd.DataFrame | dict, caption):
    FIG.mkdir(parents=True, exist_ok=True)
    SRC.mkdir(parents=True, exist_ok=True)
    over, outside = text_overlaps(fig)
    labs = axis_labels(fig)
    missing_unit = [l for l, ht in labs if ht and l and "(" not in l and not any(d in l for d in DIMENSIONLESS)]
    missing_label = [l for l, ht in labs if ht and not l]
    for ext in ("png", "pdf", "svg"):
        fig.savefig(FIG / f"{name}.{ext}", bbox_inches="tight", pad_inches=0.03)
    plt.close(fig)
    files = []
    if isinstance(data, pd.DataFrame):
        data = {"": data}
    for suffix, df in data.items():
        fn = SRC / f"{name}{('_' + suffix) if suffix else ''}.csv"
        df.to_csv(fn, index=False)
        files.append(rel(fn))
    for s in sources:
        MAP_ROWS.append(dict(figure=name, type=kind, panel=s[0], plotted_data_file="; ".join(files),
                             original_source=s[1], key_or_rows=s[2]))
    QC[name] = dict(type=kind, overlaps=over, outside=outside, missing_unit=missing_unit,
                    missing_label=missing_label, caption=caption)


def box(ax, x, y, w, h, text, fc="#ffffff", ec=C["ink"], fs=7, lw=0.8, bold=False, ls="-"):
    p = FancyBboxPatch((x, y), w, h, boxstyle="round,pad=0.01,rounding_size=0.02", fc=fc, ec=ec, lw=lw, ls=ls)
    ax.add_patch(p)
    ax.text(x + w / 2, y + h / 2, text, ha="center", va="center", fontsize=fs,
            fontweight="bold" if bold else "normal", color=C["ink"], linespacing=1.15)
    return p


def arrow(ax, x0, y0, x1, y1, color=C["ink"], lw=0.9, style="-|>", ls="-"):
    ax.add_patch(FancyArrowPatch((x0, y0), (x1, y1), arrowstyle=style, mutation_scale=7, color=color, lw=lw, ls=ls,
                                 shrinkA=0, shrinkB=0))


# ------------------------------------------------------------------ Figure 1

def fig01(R):
    fig = plt.figure(figsize=(FULL_W, 3.55))
    ax = fig.add_axes([0, 0, 1, 1])
    ax.set_xlim(0, 100)
    ax.set_ylim(0, 54)
    ax.axis("off")
    y0, h = 30, 9
    # analog chain
    box(ax, 1, y0, 11, h, "Sensor\n(physical\nsignal)", fc="#e8f6f0")
    box(ax, 17, y0, 10, h, "MUX 1\nS1/S2", fc="#f2f2f2")
    box(ax, 32, y0, 15, h, "AFE\ngain G, offset,\nRC low-pass τ", fc="#e7f0fb")
    box(ax, 52, y0, 10, h, "MUX 2\nS3/S4", fc="#f2f2f2")
    box(ax, 67, y0, 12, h, "ADC\n12-bit\n1 kS/s", fc="#fdeee6")
    for a, b in ((12, 17), (27, 32), (47, 52), (62, 67)):
        arrow(ax, a, y0 + h / 2, b, y0 + h / 2)
    # references
    box(ax, 15.5, 16, 13, 7, "Reference R1\n(two-level,\nAFE input)", fc="#fff7e0", fs=6.5)
    box(ax, 50.5, 16, 13, 7, "Reference R2\n(two-level,\nbypasses AFE)", fc="#fff7e0", fs=6.5)
    arrow(ax, 22, 23, 22, y0)
    arrow(ax, 57, 23, 57, y0)
    # monitor
    box(ax, 28, 3, 28, 7.5, "Reference monitor: S5 + high-Z buffer\n+ dedicated 12-bit channel (error ±E)",
        fc="#f4f0fd", fs=6.5)
    arrow(ax, 22, 16, 30, 10.5, color=C["muted"], ls="--")
    arrow(ax, 57, 16, 52, 10.5, color=C["muted"], ls="--")
    # digital
    dx = 82
    box(ax, dx, 30.5, 17, 8, "Settled-plateau\ncalibration", fc="#ffffff", fs=6.5)
    box(ax, dx, 20.5, 17, 7, "Phase-robust\ntransient descriptors", fc="#ffffff", fs=6.5)
    box(ax, dx, 11.5, 17, 6.5, f"Compact MLP\n{R.v('ARCH')}", fc="#e7f0fb", fs=6.5, bold=True)
    box(ax, dx, 2.5, 17, 6.5, "Layer (4 classes)\nFault (9 classes)", fc="#ffffff", fs=6.5)
    arrow(ax, 79, y0 + h / 2, dx, y0 + h / 2)
    arrow(ax, dx + 8.5, 30.5, dx + 8.5, 27.5)
    arrow(ax, dx + 8.5, 20.5, dx + 8.5, 18.0)
    arrow(ax, dx + 8.5, 11.5, dx + 8.5, 9.0)
    ax.plot([56, 80.5, 80.5], [6.8, 6.8, 32], color=C["muted"], lw=0.9, ls="--")
    arrow(ax, 80.5, 32, dx, 32, color=C["muted"], ls="--")
    ax.text(68, 7.6, "measured reference levels", fontsize=6.3, color=C["muted"], ha="center", va="bottom")
    # fault markers
    for x, lab, col in ((6.5, "Sensor faults:\nbias, gain, noise", C["sensor"]),
                        (39.5, "AFE faults:\noffset, bandwidth", C["afe"]),
                        (73, "ADC faults:\noffset, gain, clipping", C["adc"])):
        ax.plot([x], [y0 + h + 2.0], marker="*", ms=8, color=col, mec=C["ink"], mew=0.4, clip_on=False)
        ax.text(x, y0 + h + 3.6, lab, ha="center", va="bottom", fontsize=6.5, color=C["ink"])
    # observability brackets
    def bracket(x0, x1, yb, text):
        ax.plot([x0, x0, x1, x1], [yb - 1, yb, yb, yb - 1], color=C["ink"], lw=0.7)
        ax.text((x0 + x1) / 2, yb + 0.7, text, ha="center", va="bottom", fontsize=6.5, style="italic")
    bracket(27, 79, 50.5, "R1 window observes AFE + ADC")
    bracket(62, 79, 46.6, "R2 window: ADC only")
    ax.text(1, 52.6, "AFE transfer = (R1 response) after removing the ADC transfer estimated from R2",
            fontsize=6.3, color=C["muted"], ha="left", va="bottom")
    cap = ("Electronic architecture of the reference-monitored two-point active self-test. During the AFE test "
           "window MUX 1 (S1/S2) replaces the sensor by the two-level reference R1, so the response passes through the "
           "AFE and the ADC; during the ADC test window MUX 2 (S3/S4) injects the two-level reference R2 directly at the "
           "ADC input, so its response depends on the ADC only. The ADC transfer estimated from R2 is removed before the "
           "AFE transfer is estimated from R1, which separates AFE and ADC fault observability. A buffered reference-"
           "monitor channel (S5) measures the actual reference levels (gain error bounded by ±E). The digital back-end "
           "computes settled-plateau calibration and phase-robust transient descriptors and classifies them with a "
           f"compact {R.v('ARCH')} multilayer perceptron into the faulty layer (4 classes) and the fault class (9 classes). "
           "Stars mark the simulated fault locations. Schematic; not a measured result.")
    save(fig, "Fig01_architecture", "schematic", [("all", "phase_robust_final/PROTOCOL_PHASE_ROBUST_FROZEN.md; paper_package/PAPER_TABLES.csv (T1, T10)",
                                                    "architecture description; ARCH token")],
         pd.DataFrame([{"item": "MLP architecture", "value": R.v("ARCH"), "source": R.entries["ARCH"].source_file}]), cap)
    return cap


# ------------------------------------------------------------------ Figure 2

def fig02(R):
    t = load_csv(PP / "figure_data" / "fig02_timing_example.csv")
    edges_afe = t.t_ms[t.afe_ref_V.diff().fillna(0) != 0].tolist()  # 140, 200, 260
    edges_adc = t.t_ms[t.adc_ref_V.diff().fillna(0) != 0].tolist()  # 340, 400, 460
    guard = load_json(RES / "seed_20261026" / "meta.json")["guard"]
    T1 = load_csv(PP / "PAPER_TABLES.csv")
    tau_txt = T1[(T1.table_id == "T1") & (T1.column == "value") & (T1.row == "Operating condition (per group)")].value.iloc[0]
    lo, hi = map(float, re.search(r"AFE tau U\(([\d.]+),([\d.]+)\) ms", tau_txt).groups())
    tau = (lo + hi) / 2
    fig = plt.figure(figsize=(FULL_W, 4.6))
    gs = fig.add_gridspec(3, 2, height_ratios=[0.7, 1.6, 1.6], width_ratios=[1.6, 1], hspace=0.65, wspace=0.28)
    a = fig.add_subplot(gs[0, :])
    a.step(t.t_ms, t.afe_ctrl + 1.4, where="post", color=C["afe"], lw=1.1)
    a.step(t.t_ms, t.adc_ctrl, where="post", color=C["adc"], lw=1.1)
    a.set_yticks([0.5, 1.9], ["MUX 2 (R2)", "MUX 1 (R1)"])
    a.set_ylim(-0.2, 2.6)
    a.set_xlim(0, t.t_ms.max())
    a.grid(False)
    a.set_xlabel("Time (ms)")
    panel(a, "a", "Multiplexer states")
    b = fig.add_subplot(gs[1:, 0])
    b.plot(t.t_ms, t.adc_output_V, color=C["ink"], lw=0.7, marker=".", ms=1.2)
    segs = [("Sensor", 0, edges_afe[0]), ("Sensor", edges_afe[-1], edges_adc[0]), ("Sensor", edges_adc[-1], t.t_ms.max() + 1)]
    for lab, x0, x1 in segs:
        b.axvspan(x0, x1, color=C["sensor"], alpha=0.08, lw=0)
    for e0, e1, col in ((edges_afe[0], edges_afe[1], C["afe"]), (edges_afe[1], edges_afe[2], C["afe"]),
                        (edges_adc[0], edges_adc[1], C["adc"]), (edges_adc[1], edges_adc[2], C["adc"])):
        g = e0 + guard * (e1 - e0)
        b.axvspan(e0, g, color=col, alpha=0.30, lw=0)
        b.axvspan(g, e1, color=col, alpha=0.12, lw=0)
    ylo, yhi = b.get_ylim()
    b.set_ylim(ylo - 0.12 * (yhi - ylo), yhi + 0.35 * (yhi - ylo))
    ytop = yhi + 0.22 * (yhi - ylo)
    b.text((edges_afe[0] + edges_afe[2]) / 2, ytop, "R1 window", ha="center", fontsize=7, color=C["afe"], fontweight="bold")
    b.text((edges_adc[0] + edges_adc[2]) / 2, ytop, "R2 window", ha="center", fontsize=7, color=C["adc"], fontweight="bold")
    b.text(edges_afe[0] / 2, ytop, "sensor", ha="center", fontsize=7, color=C["muted"])
    b.text((edges_afe[2] + edges_adc[0]) / 2, ytop, "sensor", ha="center", fontsize=7, color=C["muted"])
    b.text((edges_adc[2] + t.t_ms.max()) / 2, ytop, "sensor", ha="center", fontsize=7, color=C["muted"])
    b.set_xlim(0, t.t_ms.max())
    b.set_xlabel("Time (ms)")
    b.set_ylabel("ADC output (V)")
    panel(b, "b", "Illustrative ADC record (dev. seed)")
    b.text(0.99, 0.02, f"dark: {int(guard*100)}% settling guard; light: settled plateau", transform=b.transAxes,
           ha="right", va="bottom", fontsize=6.3, color=C["muted"])
    # (c) analytic edge-phase illustration
    c = fig.add_subplot(gs[1:, 1])
    Ts = 1.0
    n = np.arange(0, 9)
    tt = np.linspace(-1, 8, 600)
    rows = []
    for psi, col, mk in ((0.0, C["PR"], "o"), (0.999, C["R1"], "s")):
        te = -Ts + psi * Ts  # edge after sample t_{-1}
        resp = lambda x: np.where(x >= te, 1 - np.exp(-(x - te) / tau), 0.0)
        c.plot(tt, resp(tt), color=col, lw=0.9, alpha=0.8)
        c.plot(n, resp(n), ls="none", marker=mk, ms=4, color=col, mec="white", mew=0.4, label=f"ψ = {psi:g}")
        for k in n:
            rows.append(dict(panel="c", psi=psi, sample=int(k), normalized_response=float(resp(k)), tau_ms=tau))
    k2 = 2
    r0 = 1 - np.exp(-(k2 + 1) / tau)
    r9 = 1 - np.exp(-(k2 + 1 - 0.999) / tau)
    c.annotate("", xy=(k2 + 0.15, r9), xytext=(k2 + 0.15, r0), arrowprops=dict(arrowstyle="<->", lw=0.7, color=C["ink"]))
    c.text(k2 + 0.4, (r0 + r9) / 2, "fixed-sample\nread differs", fontsize=6.3, va="center")
    c.axvspan(0, 8, color=C["PRr"], alpha=0.07, lw=0)
    c.text(4.0, 0.03, "whole-transient fit window\n(free edge time absorbs ψ)", fontsize=6.3, ha="center", color=C["PRr"])
    c.set_xlim(-1, 8)
    c.set_ylim(0, 0.75)
    c.set_xlabel("Samples after edge (T = 1 ms)")
    c.set_ylabel("Normalized AFE response")
    c.legend(loc="upper left", handlelength=1.2)
    panel(c, "c", "Edge phase ψ (analytic)")
    cap = (f"Active self-test timing. (a) Multiplexer states: MUX 1 connects the two-level reference R1 to the AFE input "
           f"({edges_afe[0]:g}–{edges_afe[2]:g} ms) and MUX 2 connects R2 to the ADC input ({edges_adc[0]:g}–{edges_adc[2]:g} ms). "
           f"(b) Illustrative ADC record from development seed {R.v('DEV_SEED')} (not validation data): sensor intervals, "
           f"R1 and R2 reference windows with their {int(guard*100)}% settling guards (dark) and settled plateaus (light); ADC "
           f"samples are taken every 1 ms. (c) Analytic illustration of the edge phase ψ: a reference edge occurring ψT after "
           f"an ADC sample shifts every sampled value of the first-order response (τ = {tau:g} ms, the midpoint of the simulated "
           f"AFE time-constant range), so a descriptor that reads fixed samples after the edge depends on ψ, whereas a fit "
           f"over the whole transient with a free edge time does not. Panels (b) and (c) are illustrative.")
    src = t.copy()
    src.insert(0, "panel", "a,b")
    save(fig, "Fig02_timing", "illustrative", [
        ("a,b", "paper_package/figure_data/fig02_timing_example.csv", "all columns (development seed 20261097)"),
        ("b", "phase_robust_final/phase_robust_results/seed_20261026/meta.json", "guard"),
        ("c", "paper_package/PAPER_TABLES.csv", "T1 'Operating condition' AFE tau range (midpoint used, analytic curve)")],
        {"ab": src, "c": pd.DataFrame(rows)}, cap)
    return cap


# ------------------------------------------------------------------ Figure 3

def fig03(R):
    fig = plt.figure(figsize=(FULL_W, 1.75))
    ax = fig.add_axes([0, 0, 1, 1])
    ax.set_xlim(0, 100)
    ax.set_ylim(5, 30)
    ax.axis("off")
    steps = [
        ("Circuit\nsimulation", "behavioral +\nngspice", "#f2f2f2"),
        ("Fault\ninjection", f"{R.v('N_FAULTS')} classes,\ntolerances, noise", "#fdeee6"),
        ("Active\nreference test", f"two-point,\n5 edge phases ψ", "#fff7e0"),
        ("Reference\nmonitoring", f"E = {R.v('MON_E')}", "#f4f0fd"),
        ("Descriptor\nextraction", "20 phase-robust\ndescriptors", "#e8f6f0"),
        ("MLP\nclassification", f"{R.v('ARCH')}\nlayer / fault", "#e7f0fb"),
        ("Evaluation", f"macro-F1, gates A–G,\n{R.v('N_BOOT')}-resample\nbootstrap", "#ffffff"),
    ]
    w, gap = 12.2, 2.0
    for i, (head, sub, fc) in enumerate(steps):
        x = 0.8 + i * (w + gap)
        box(ax, x, 13, w, 11, head, fc=fc, fs=7, bold=True)
        ax.text(x + w / 2, 11.5, sub, ha="center", va="top", fontsize=6.2, color=C["muted"], linespacing=1.1)
        if i < len(steps) - 1:
            arrow(ax, x + w, 18.5, x + w + gap, 18.5)
    ax.text(50, 27.5, "Training: behavioral, ×1.0 reference, ψ ~ U[0,1) (PRr); PRrM adds ngspice rows. "
                      f"Test: {R.v('N_SEEDS')} unseen seeds × {R.v('TEST_COND')} conditions × {R.v('N_FAULTS')} faults.",
            ha="center", fontsize=6.5, color=C["ink"])
    cap = ("Processing and evaluation pipeline. Behavioral and ngspice circuit simulations generate records with injected "
           f"faults ({R.v('N_FAULTS')} classes), component tolerances, noise and 12-bit quantization; the two-point active "
           "reference test is applied at five edge phases ψ; the reference monitor reports the reference levels with a bounded "
           f"gain error E; 20 phase-robust descriptors are extracted and classified by the compact MLP ({R.v('ARCH')}); "
           f"performance is evaluated with macro-F1, the pre-registered gates A–G and a {R.v('N_BOOT')}-resample paired "
           "condition-level cluster bootstrap. Schematic.")
    save(fig, "Fig03_pipeline", "schematic", [("all", "phase_robust_final/PROTOCOL_PHASE_ROBUST_FROZEN.md; seed_*/meta.json",
                                                "N_FAULTS, PHASES, MON_E, ARCH, N_BOOT, N_SEEDS, TEST_COND tokens")],
         pd.DataFrame([{"token": k, "value": R.v(k)} for k in ("N_FAULTS", "PHASES", "MON_E", "ARCH", "N_BOOT", "N_SEEDS", "TEST_COND")]), cap)
    return cap


# ------------------------------------------------------------------ Figure 4

def fig04(R):
    d = load_csv(PP / "figure_data" / "fig05_fault_signature_descriptors_dev_seed.csv")
    desc = [("g_adc", "ADC gain ĝ_ADC"), ("o_adc", "ADC offset ô_ADC (V)"), ("G_afe", "AFE gain Ĝ_AFE"),
            ("o_afe", "AFE offset ô_AFE (V)"), ("tau_norm", "τ/P (normalized)"), ("sens_hf", "Sensor HF noise (V)")]
    layer_of = dict(zip(FAULTS, ["healthy", "sensor", "sensor", "sensor", "afe", "afe", "adc", "adc", "adc"]))
    fig, axs = plt.subplots(2, 3, figsize=(FULL_W, 4.4), sharex=True)
    rows = []
    for ax, (col, lab), letter in zip(axs.flat, desc, "abcdef"):
        data = [d[d.fault == f][col].values for f in FAULTS]
        bp = ax.boxplot(data, positions=range(9), widths=0.6, patch_artist=True, showfliers=False,
                        medianprops=dict(color=C["ink"], lw=0.9), whiskerprops=dict(lw=0.6), capprops=dict(lw=0.6))
        for patch, f in zip(bp["boxes"], FAULTS):
            patch.set_facecolor(C[layer_of[f]])
            patch.set_alpha(0.55)
            patch.set_linewidth(0.6)
        ax.set_ylabel(lab)
        panel(ax, letter, "")
        ax.set_title(f"({letter})", loc="left", pad=3)
        for f, v in zip(FAULTS, data):
            q = np.percentile(v, [25, 50, 75])
            rows.append(dict(descriptor=col, fault=f, n=len(v), q25=q[0], median=q[1], q75=q[2]))
    for ax in axs[1]:
        ax.set_xticks(range(9), FAULT_LABELS, rotation=55, ha="right")
    from matplotlib.patches import Patch
    fig.legend(handles=[Patch(fc=C[k], alpha=0.55, ec=C["ink"], lw=0.5, label=l) for k, l in
                        (("healthy", "Healthy"), ("sensor", "Sensor fault"), ("afe", "AFE fault"), ("adc", "ADC fault"))],
               loc="upper center", ncol=4, bbox_to_anchor=(0.5, 1.035))
    fig.text(0.5, -0.06, f"ILLUSTRATIVE — development seed {R.v('DEV_SEED')}, 60 records per class; not validation data",
             ha="center", fontsize=6.8, color=C["nomon"], fontweight="bold")
    fig.tight_layout(h_pad=1.0, w_pad=0.8)
    cap = (f"Example fault signatures (illustrative, development seed {R.v('DEV_SEED')}, 60 records per class; not used for "
           "any decision). Box plots (median, interquartile range, whiskers at 1.5 IQR; outliers hidden) of six of the 20 "
           "descriptors for the nine classes, colored by faulty layer. (a) ADC gain and (b) ADC offset, estimated from the R2 "
           "window that bypasses the AFE, separate ADC gain and ADC offset faults and stay flat for sensor and AFE faults. "
           "(c) AFE gain and (d) AFE offset, estimated from the R1 window after ADC calibration, shift for AFE faults: offset "
           "faults widen the offset distribution, while bandwidth faults lower the apparent gain and raise the apparent offset "
           "because the plateaus do not fully settle. (e) The fitted time constant τ/P marks AFE bandwidth faults. (f) "
           "Sensor-domain high-frequency noise marks sensor-noise faults (and, more weakly, AFE bandwidth faults). Sensor bias "
           "and sensor gain faults are not separated by these six descriptors, which is consistent with their low recall "
           "(Figure 10). Raw per-fault waveforms are not included in the evidence package, so descriptor-level signatures are "
           "shown instead of waveforms.")
    save(fig, "Fig04_fault_signatures", "illustrative",
         [("a–f", "paper_package/figure_data/fig05_fault_signature_descriptors_dev_seed.csv", "columns g_adc, o_adc, G_afe, o_afe, tau_norm, sens_hf; grouped by 'fault'")],
         pd.DataFrame(rows), cap)
    return cap


# ------------------------------------------------------------------ Figure 5

def fig05(R):
    arms = load_csv(RES / "attribution_arms.csv")
    dv = load_json(PP / "figure_data" / "dev_seed_verification.json")["descriptor_phase_invariance"]
    fig = plt.figure(figsize=(FULL_W, 2.6))
    gs = fig.add_gridspec(1, 3, width_ratios=[1, 1, 1], wspace=0.42)
    cols = ["layer_f1_p000", "layer_f1_p250", "layer_f1_p500", "layer_f1_p750", "layer_f1_p999"]
    rows = []
    ax0 = None
    for k, dom in enumerate(("bh", "sp")):
        ax = fig.add_subplot(gs[0, k], sharey=ax0)
        ax0 = ax0 or ax
        for arm in ("R1", "R1r", "PR", "PRr", "PRrM"):
            r = arms[(arms.domain == dom) & (arms.arm == arm)]
            if r.empty:
                continue
            y = r[cols].values[0]
            lw = 2.0 if arm in ("R1", "PRr") else 1.0
            al = 1.0 if arm in ("R1", "PRr") else 0.65
            ax.plot(PHASE_VALUES, y, color=C[arm], marker=MK[arm], ls=LS[arm], lw=lw, alpha=al, label=arm)
            for p, v in zip(PHASE_VALUES, y):
                rows.append(dict(panel="a" if dom == "bh" else "b", domain=dom, arm=arm, psi=p, layer_macro_f1=v))
        tR1 = R.v(f"ARM_{dom}_R1_RANGE")
        tPR = R.v(f"ARM_{dom}_PRR_RANGE")
        ax.text(0.98, 0.98, f"phase spread (max−min)\nR1: {tR1}   PRr: {tPR}", transform=ax.transAxes,
                ha="right", va="top", fontsize=6.5, bbox=dict(fc="white", ec=C["grid"], lw=0.5, pad=2))
        ax.set_xticks(PHASE_VALUES, ["0", "0.25", "0.5", "0.75", "0.999"])
        ax.set_xlabel("Edge phase ψ (fraction of T)")
        ax.set_ylabel("Layer macro-F1")
        panel(ax, "ab"[k], f"{'Behavioral' if dom == 'bh' else 'ngspice'}, E = ±2%")
        if k == 0:
            ax.legend(loc="lower left", ncol=2, handlelength=2.2, columnspacing=0.8, fontsize=6.5)
    ax0.set_ylim(0.48, 0.74)
    c = fig.add_subplot(gs[0, 2])
    for name, col, mk in (("rise_2", C["R1"], "s"), ("rise_5", C["R1r"], "D"), ("tau_norm", C["PRr"], "o"),
                          ("area_norm", C["PR"], "^"), ("rt_50_90_norm", C["PRrM"], "v")):
        src = dv["revision1"] if name in dv["revision1"] else dv["phase_robust"]
        c.plot(dv["phases"], src[name], color=col, marker=mk, ls="--" if name.startswith("rise") else "-",
               label=name.replace("_norm", "").replace("_", " "))
        for p, v in zip(dv["phases"], src[name]):
            rows.append(dict(panel="c", descriptor=name, psi=p, shift_sigma=v))
    c.set_xticks(PHASE_VALUES, ["0", "0.25", "0.5", "0.75", "0.999"])
    c.set_xlabel("Edge phase ψ (fraction of T)")
    c.set_ylabel("Descriptor shift (σ units)")
    c.legend(loc="upper left", handlelength=2.0)
    panel(c, "c", "Descriptor shift (dev. seed)")
    cap = (f"Sampling-phase sensitivity. Layer macro-F1 (monitor E = ±2%, pooled over reference amplitudes; mean of "
           f"{R.v('N_SEEDS')} dataset seeds × 2 initializations) versus edge phase ψ in (a) the behavioral and (b) the ngspice "
           f"domain. The fixed-sample Revision-1 descriptors (R1) lose accuracy as ψ grows (phase spread {R.v('ARM_bh_R1_RANGE')} "
           f"behavioral, {R.v('ARM_sp_R1_RANGE')} ngspice), whereas the proposed PRr is nearly flat ({R.v('ARM_bh_PRR_RANGE')} and "
           f"{R.v('ARM_sp_PRR_RANGE')}); over the pre-registered gate-G variants (known reference and E = ±2%, both domains) "
           f"the PRr spread is {R.v('G_PRR_MIN')}–{R.v('G_PRR_MAX')} (threshold {R.v('G_THRESH')}). R1r, PR and PRrM are shown "
           f"for attribution. (c) Illustrative mechanism on development seed {R.v('DEV_SEED')}: mean absolute descriptor shift "
           f"relative to ψ = 0 in units of the across-record standard deviation; the fixed-sample rise fraction rise_2 shifts "
           f"by up to {R.v('DEV_RISE2_SHIFT')} σ, the phase-robust descriptors by at most {R.v('DEV_PR_MAX_SHIFT')} σ.")
    save(fig, "Fig05_phase_sensitivity", "result (a,b); illustrative (c)",
         [("a,b", "phase_robust_final/phase_robust_results/attribution_arms.csv", "columns layer_f1_p000…p999, all arms"),
          ("a,b annotations", "phase_robust_final/phase_robust_results/attribution_arms.csv", "max−min of layer_f1_p*"),
          ("c", "paper_package/figure_data/dev_seed_verification.json", "descriptor_phase_invariance")],
         pd.DataFrame(rows), cap)
    return cap


# ------------------------------------------------------------------ Figure 6

def fig06(R):
    amp = load_csv(RES / "amplitude_curves.csv")
    nm = load_json(RES / "no_monitor_control.json")["no_monitor_control_layer_macro_f1"]
    xs = [0.8, 0.9, 1.0, 1.1, 1.2]
    cols = ["x0.8", "x0.9", "x1.0", "x1.1", "x1.2"]
    fig, axs = plt.subplots(1, 2, figsize=(FULL_W, 2.85), sharey=True)
    rows = []
    series = [("PRr known", "PRr, known reference", BLUES[0], "o", "-"), ("PRr E=0%", "PRr, monitor E = 0%", BLUES[1], "o", "-"),
              ("PRr E=1%", "PRr, monitor E = ±1%", BLUES[2], "o", "-"), ("PRr E=2%", "PRr, monitor E = ±2%", BLUES[3], "o", "-"),
              ("PRr E=5%", "PRr, monitor E = ±5%", BLUES[4], "o", "-"), ("R1 known", "R1, known reference", C["R1"], "s", "--"),
              ("A0 old", "A0 old descriptors", C["A0"], "x", ":")]
    for ax, dom, letter in zip(axs, ("bh", "sp"), "ab"):
        for ser, lab, col, mk, ls in series:
            r = amp[(amp.domain == dom) & (amp.series == ser) & (amp.target == "layer")]
            if r.empty:
                continue
            y = r[cols].values[0].astype(float)
            m = ~np.isnan(y)
            ax.plot(np.array(xs)[m], y[m], color=col, marker=mk, ls=ls, lw=1.2, label=lab, ms=3.8)
            for x, v in zip(np.array(xs)[m], y[m]):
                rows.append(dict(panel=letter, domain=dom, series=ser, amplitude=x, layer_macro_f1=v, source="amplitude_curves.csv"))
        if dom == "bh":
            y = [nm[f"x{x:g}" if x != 1.0 else "x1.0"]["unmonitored"] for x in xs]
            ax.plot(xs, y, color=C["nomon"], marker="P", ls="-.", lw=1.4, label="No monitor (nominal levels assumed)")
            for x, v in zip(xs, y):
                rows.append(dict(panel=letter, domain=dom, series="no monitor", amplitude=x, layer_macro_f1=v, source="no_monitor_control.json"))
            for x in (0.8, 1.2):
                key = "08" if x == 0.8 else "12"
                ax.annotate(f"{R.v('NOMON_U_x' + key)}", (x, R.raw("NOMON_U_x" + key)), textcoords="offset points",
                            xytext=(0, -9), ha="center", fontsize=6.3, color=C["nomon"])
                ax.annotate(f"{R.v('NOMON_K_x' + key)}", (x, R.raw("NOMON_K_x" + key)), textcoords="offset points",
                            xytext=(0, -11), ha="center", fontsize=6.3, color=BLUES[0])
        ax.set_xticks(xs, ["×0.8", "×0.9", "×1.0", "×1.1", "×1.2"])
        ax.set_xlabel("Reference amplitude (× nominal)")
        panel(ax, letter, "Behavioral" if dom == "bh" else "ngspice (×0.8, ×1.0, ×1.2 tested)")
    axs[0].set_ylabel("Layer macro-F1")
    axs[0].set_ylim(0.0, 0.78)
    h, l = axs[0].get_legend_handles_labels()
    fig.legend(h, l, loc="upper center", ncol=4, bbox_to_anchor=(0.5, 1.10), handlelength=2.2, columnspacing=1.0)
    fig.tight_layout()
    cap = ("Reference-amplitude robustness. Layer macro-F1 (pooled over the five edge phases; mean of three dataset seeds) "
           "versus the actual reference amplitude for the primary PRr classifier with a known reference and with the "
           "simulated reference monitor (gain error E = 0, ±1, ±2, ±5%), for the Revision-1 descriptors (R1, known reference) "
           "and the old descriptors (A0), in (a) the behavioral and (b) the ngspice domain. In (a) the no-monitor control "
           "applies the same PRr known-reference classifier with the nominal (assumed) reference levels: at ×0.8 and ×1.2 its "
           f"layer macro-F1 falls to {R.v('NOMON_U_x08')} and {R.v('NOMON_U_x12')}, against {R.v('NOMON_K_x08')} and "
           f"{R.v('NOMON_K_x12')} with the known reference. The no-monitor control was evaluated in the behavioral domain only; "
           "ngspice was simulated at ×0.8, ×1.0 and ×1.2.")
    save(fig, "Fig06_reference_amplitude", "result",
         [("a,b", "phase_robust_final/phase_robust_results/amplitude_curves.csv", "rows target=layer; series PRr known/E=0..5%, R1 known, A0 old"),
          ("a", "phase_robust_final/phase_robust_results/no_monitor_control.json", "no_monitor_control_layer_macro_f1.*.unmonitored/known")],
         pd.DataFrame(rows), cap)
    return cap


# ------------------------------------------------------------------ Figure 7

def fig07(R, extra):
    dr = load_json(RES / "decision_rules.json")["C"]["detail"]
    fig = plt.figure(figsize=(FULL_W, 4.6))
    gs = fig.add_gridspec(2, 4, height_ratios=[1, 1.05], hspace=0.42, wspace=0.5)
    rows = []
    for k, (var, a, title) in enumerate((("known", 80, "Known ref., ×0.8"), ("known", 120, "Known ref., ×1.2"),
                                         ("assumed", 80, "No monitor, ×0.8"), ("assumed", 120, "No monitor, ×1.2"))):
        ax = fig.add_subplot(gs[0, k])
        m = extra[f"cm_bh_{var}_a{a}"]
        mn = m / m.sum(1, keepdims=True)
        ax.imshow(mn, cmap="Blues", vmin=0, vmax=1)
        for i in range(4):
            for j in range(4):
                ax.text(j, i, f"{mn[i, j]:.2f}", ha="center", va="center", fontsize=6,
                        color="white" if mn[i, j] > 0.55 else C["ink"])
                rows.append(dict(panel="abcd"[k], variant=var, amplitude=a / 100, true=LAYER_LABELS[i],
                                 predicted=LAYER_LABELS[j], row_normalized=mn[i, j], mean_count=m[i, j]))
        for (i, j) in ((2, 3), (3, 2)):
            ax.add_patch(Rectangle((j - 0.5, i - 0.5), 1, 1, fill=False, ec=C["nomon"], lw=1.1))
        ax.set_xticks(range(4), ["H", "S", "AFE", "ADC"], fontsize=6.5)
        ax.set_yticks(range(4), ["H", "S", "AFE", "ADC"] if k == 0 else [""] * 4)
        ax.set_xlabel("Predicted layer")
        if k == 0:
            ax.set_ylabel("True layer")
        ax.grid(False)
        panel(ax, "abcd"[k], title)
    ax = fig.add_subplot(gs[1, :])
    conds = [("known", "Known"), ("mon0", "E 0%"), ("mon1", "E ±1%"), ("mon2", "E ±2%"), ("mon5", "E ±5%"), ("assumed", "No mon.")]
    groups = []
    for a in (80, 120):
        for v, lab in conds:
            if v == "assumed":
                afe, adc, xc = (R.raw(f"SEPX_bh_assumed_a{a}_AFE"), R.raw(f"SEPX_bh_assumed_a{a}_ADC"), R.raw(f"SEPX_bh_assumed_a{a}_X"))
                src = "predictions.npz (assumed)"
            else:
                d = dr[f"bh|{v}|a{a}"]
                afe, adc, xc = d["afe_recall"], d["adc_recall"], d["cross_confusion"]
                src = f"decision_rules.json C.detail['bh|{v}|a{a}']"
            groups.append((f"{lab}\n×{a/100:g}", afe, adc, xc))
            rows.append(dict(panel="e", domain="bh", amplitude=a / 100, condition=lab, afe_recall=afe, adc_recall=adc,
                             cross_confusion=xc, source=src))
    x = np.arange(len(groups))
    wb = 0.26
    ax.bar(x - wb, [g[1] for g in groups], wb, color=C["afe"], label="AFE recall", ec="white", lw=0.5)
    ax.bar(x, [g[2] for g in groups], wb, color=C["adc"], label="ADC recall", ec="white", lw=0.5)
    ax.bar(x + wb, [g[3] for g in groups], wb, color=C["A0"], label="AFE–ADC cross-confusion", ec="white", lw=0.5,
           hatch="////")
    ax.axhline(R.raw("C_THRESH"), color=C["ink"], ls="--", lw=0.8, label=f"Gate C limit ({R.v('C_THRESH')})")
    ax.axvline(5.5, color=C["grid"], lw=0.8)
    ax.set_xticks(x, [g[0] for g in groups], fontsize=6.5)
    ax.set_ylim(0, 1.08)
    ax.set_ylabel("Recall / cross-confusion")
    ax.legend(loc="upper left", ncol=4, bbox_to_anchor=(0.0, 1.0), fontsize=6.5)
    ax.set_ylim(0, 1.18)
    panel(ax, "e", "Behavioral, PRr, pooled over phases")
    cap = ("AFE/ADC fault separation of the primary PRr classifier in the behavioral domain (pooled over the five edge phases; "
           "mean of three dataset seeds × two initializations). (a,b) Row-normalized layer confusion matrices with the known "
           "reference at ×0.8 and ×1.2 reference amplitude; (c,d) the same classifier without reference monitoring (nominal "
           "levels assumed). H = healthy, S = sensor; red boxes mark the AFE↔ADC cells. (e) AFE recall, ADC recall and AFE–ADC "
           "cross-confusion for the known reference, the monitor with E = 0 to ±5% and the no-monitor control at ×0.8 and ×1.2. "
           f"With a known or monitored reference the cross-confusion stays at or below {R.v('C_MAX')} (gate C limit "
           f"{R.v('C_THRESH')}); without monitoring it rises to {R.v('SEPX_bh_assumed_a80_X')} (×0.8) and "
           f"{R.v('SEPX_bh_assumed_a120_X')} (×1.2). Panels (a–d) and the no-monitor bars in (e) are computed from the saved "
           "per-sample predictions; the other bars are read from decision_rules.json. The ngspice values are listed in Table 10.")
    save(fig, "Fig07_afe_adc_separation", "result",
         [("a–d", "phase_robust_final/phase_robust_results/seed_*/predictions.npz", "keys bh_a{80,120}_p*_{known,assumed}|two_point_mlp@PRr_k|{11,22}|layer"),
          ("e", "phase_robust_final/phase_robust_results/decision_rules.json", "C.detail['bh|*|a80/a120']"),
          ("e (no monitor)", "phase_robust_final/phase_robust_results/seed_*/predictions.npz", "keys bh_a{80,120}_p*_assumed|two_point_mlp@PRr_k|*|layer")],
         pd.DataFrame(rows), cap)
    return cap


# ------------------------------------------------------------------ Figure 8

def fig08(R):
    E = load_json(RES / "decision_rules.json")["E"]["all"]
    arms = load_csv(RES / "attribution_arms.csv")
    fig = plt.figure(figsize=(FULL_W, 2.9))
    gs = fig.add_gridspec(1, 3, width_ratios=[1.35, 1.1, 1.0], wspace=0.45)
    rows = []
    vars_ = ["known", "mon0", "mon1", "mon2", "mon5"]
    labs = ["Known", "E 0%", "E ±1%", "E ±2%", "E ±5%"]
    ax = fig.add_subplot(gs[0, 0])
    x = np.arange(5)
    w = 0.27
    for off, key, lab, col, hatch in ((-w, "BB", "PRr behavioral", C["PRr"], ""), (0, "BS", "PRr ngspice", "#86b6ef", ""),
                                      (w, "MS", "PRrM ngspice (secondary)", C["PRrM"], "////")):
        vals = [E[v][key] for v in vars_]
        ax.bar(x + off, vals, w, color=col, label=lab, ec="white", lw=0.5, hatch=hatch)
        for v, val in zip(vars_, vals):
            rows.append(dict(panel="a", variant=v, quantity=key, value=val, source=f"decision_rules.json E.all.{v}.{key}"))
    ax.set_xticks(x, labs, rotation=45, ha="right")
    ax.set_ylim(0.55, 0.75)
    ax.set_ylabel("Layer macro-F1")
    ax.legend(loc="upper left", ncol=1, handlelength=1.4, fontsize=6.5)
    panel(ax, "a", "Matched ngspice grid")
    b = fig.add_subplot(gs[0, 1])
    ys = [E[v]["drop"] for v in vars_]
    lo = [E[v]["drop"] - E[v]["drop_ci"][0] for v in vars_]
    hi = [E[v]["drop_ci"][1] - E[v]["drop"] for v in vars_]
    b.errorbar(range(5), ys, yerr=[lo, hi], fmt="o", color=C["PRr"], capsize=2.5, lw=1.0, ms=4, label="PRr (this stage)")
    for v, y_, l_, h_ in zip(vars_, ys, lo, hi):
        rows.append(dict(panel="b", variant=v, quantity="BB-BS", value=y_, ci_low=y_ - l_, ci_high=y_ + h_,
                         source=f"decision_rules.json E.all.{v}.drop/drop_ci"))
    pv, pl, ph = R.raw("PREV_DROP"), R.raw("PREV_DROP_LO"), R.raw("PREV_DROP_HI")
    b.errorbar([5.3], [pv], yerr=[[pv - pl], [ph - pv]], fmt="s", color=C["R1"], capsize=2.5, lw=1.0, ms=4,
               label="Previous stage (E ±2%)")
    rows.append(dict(panel="b", variant="previous stage mon2", quantity="BB-BS", value=pv, ci_low=pl, ci_high=ph,
                     source="paper_package/NUMBER_PROVENANCE.csv PREV_E_* (previous-stage)"))
    b.axhline(R.raw("E_THRESH"), color=C["ink"], ls="--", lw=0.8)
    b.text(2.0, R.raw("E_THRESH") - 0.009, f"gate E limit {R.v('E_THRESH')}", fontsize=6.3, ha="center")
    b.axhline(0, color=C["muted"], lw=0.5)
    b.set_xticks(list(range(5)) + [5.3], labs + ["Prev."], rotation=45, ha="right")
    b.set_ylim(-0.02, 0.14)
    b.set_ylabel("Transfer loss BB − BS (Δ layer macro-F1)")
    b.legend(loc="center left", bbox_to_anchor=(0.0, 0.55), handlelength=1.0, fontsize=6.5)
    panel(b, "b", "Transfer loss, 95% CI")
    c = fig.add_subplot(gs[0, 2])
    cols = ["layer_f1_p000", "layer_f1_p250", "layer_f1_p500", "layer_f1_p750", "layer_f1_p999"]
    for arm in ("PRr", "PRrM"):
        for dom, ls in (("bh", "-"), ("sp", "--")):
            r = arms[(arms.domain == dom) & (arms.arm == arm)][cols].values[0]
            c.plot(PHASE_VALUES, r, color=C[arm], ls=ls, marker=MK[arm], ms=3.5,
                   label=f"{arm} {'behav.' if dom == 'bh' else 'ngspice'}")
            for p, v in zip(PHASE_VALUES, r):
                rows.append(dict(panel="c", arm=arm, domain=dom, psi=p, value=v, source="attribution_arms.csv"))
    c.set_xticks(PHASE_VALUES, ["0", ".25", ".5", ".75", ".999"])
    c.set_xlabel("Edge phase ψ")
    c.set_ylabel("Layer macro-F1")
    c.set_ylim(0.62, 0.70)
    c.legend(loc="lower left", ncol=2, handlelength=1.8, columnspacing=0.6, fontsize=6.3)
    panel(c, "c", "Per phase, E = ±2%")
    cap = (f"Behavioral-to-ngspice transfer. (a) Layer macro-F1 on the ngspice test grid (×0.8, ×1.0, ×1.2 × five phases) "
           f"of the behavioral-trained PRr classifier on behavioral (BB) and ngspice (BS) data and of the mixed-domain "
           f"secondary variant PRrM on ngspice data (MS), for each reference condition. (b) Transfer loss BB − BS with paired "
           f"{R.v('N_BOOT')}-resample cluster-bootstrap 95% CIs; for the pre-registered primary case (E = ±2%) the loss is "
           f"{R.v('E_DROP')} {R.ci('E_DROP_LO', 'E_DROP_HI')}, against {R.v('PREV_DROP')} "
           f"{R.ci('PREV_DROP_LO', 'PREV_DROP_HI')} in the previous, failed validation stage (previous-stage value, shown for "
           f"context only); dashed line: gate E limit {R.v('E_THRESH')}. (c) Layer macro-F1 per edge phase (E = ±2%, pooled "
           "over amplitudes) of PRr and PRrM in both domains. PRrM is a secondary mixed-training variant, not the "
           "pre-registered primary method.")
    save(fig, "Fig08_domain_transfer", "result (previous-stage point marked)",
         [("a,b", "phase_robust_final/phase_robust_results/decision_rules.json", "E.all.*.BB/BS/MS/drop/drop_ci"),
          ("b (previous stage)", "paper_package/NUMBER_PROVENANCE.csv", "tokens PREV_E_DROP, PREV_E_LO, PREV_E_HI"),
          ("c", "phase_robust_final/phase_robust_results/attribution_arms.csv", "PRr, PRrM rows, layer_f1_p*")],
         pd.DataFrame(rows), cap)
    return cap


# ------------------------------------------------------------------ Figure 9

def fig09(R):
    arms = load_csv(RES / "attribution_arms.csv")
    att = load_csv(RES / "attribution_comparisons.csv")
    fig = plt.figure(figsize=(FULL_W, 4.9))
    gtop = fig.add_gridspec(1, 2, left=0.08, right=0.98, top=0.97, bottom=0.62, wspace=0.32)
    gbot = fig.add_gridspec(1, 1, left=0.36, right=0.98, top=0.47, bottom=0.08)
    rows = []
    order = ["A0", "R1", "R1r", "PR", "PRr", "PRrM"]
    x = np.arange(len(order))
    w = 0.38
    ax = fig.add_subplot(gtop[0, 0])
    bx = fig.add_subplot(gtop[0, 1])
    cols = ["layer_f1_p000", "layer_f1_p250", "layer_f1_p500", "layer_f1_p750", "layer_f1_p999"]
    for off, dom, hatch in ((-w / 2, "bh", ""), (w / 2, "sp", "////")):
        vals, rng = [], []
        for a in order:
            r = arms[(arms.domain == dom) & (arms.arm == a)]
            vals.append(r.layer_macro_f1.values[0] if not r.empty else np.nan)
            rng.append((r[cols].values[0].max() - r[cols].values[0].min()) if not r.empty else np.nan)
            rows.append(dict(panel="a,b", domain=dom, arm=a, layer_macro_f1=vals[-1], phase_range=rng[-1]))
        colors = [C[a] for a in order]
        ax.bar(x + off, vals, w, color=colors, ec="white", lw=0.5, hatch=hatch, alpha=1.0 if dom == "bh" else 0.75)
        bx.bar(x + off, rng, w, color=colors, ec="white", lw=0.5, hatch=hatch, alpha=1.0 if dom == "bh" else 0.75)
    for xi, a in zip(x, order):
        if a == "A0":
            ax.text(xi + w / 2, 0.02, "n/a", ha="center", fontsize=6, rotation=90, color=C["muted"])
            bx.text(xi + w / 2, 0.002, "n/a", ha="center", fontsize=6, rotation=90, color=C["muted"])
    from matplotlib.patches import Patch
    hd = [Patch(fc="#9a9a9a", label="Behavioral"), Patch(fc="#9a9a9a", hatch="////", ec="white", label="ngspice")]
    ax.legend(handles=hd, loc="upper left", ncol=2)
    ax.set_xticks(x, order)
    ax.set_ylim(0, 0.8)
    ax.set_ylabel("Layer macro-F1")
    panel(ax, "a", "Layer macro-F1, E = ±2%")
    bx.axhline(R.raw("G_THRESH"), color=C["ink"], ls="--", lw=0.8)
    bx.text(5.6, R.raw("G_THRESH") + 0.002, f"gate G limit {R.v('G_THRESH')}", ha="right", fontsize=6.3)
    bx.set_xticks(x, order)
    bx.set_ylim(0, 0.095)
    bx.set_ylabel("Phase spread (Δ layer macro-F1)")
    panel(bx, "b", "Phase spread, max−min over ψ")
    c = fig.add_subplot(gbot[0, 0])
    from registry_build import ATT_KEYS, ATT_LABEL
    keys = ["DESC", "RAND", "DESC_GIVEN_RAND", "RAND_GIVEN_DESC", "COMB", "MIXED"]
    yl = []
    for i, k in enumerate(keys):
        for dom, dy, mk, col in (("bh", -0.15, "o", C["PRr"]), ("sp", 0.15, "s", "#86b6ef")):
            r = att[(att.domain == dom) & (att.comparison == ATT_KEYS[k])].iloc[0]
            c.errorbar(r["diff"], i + dy, xerr=[[r["diff"] - r.ci_low], [r.ci_high - r["diff"]]], fmt=mk, color=col,
                       capsize=2, ms=4, lw=1.0, label=("Behavioral" if dom == "bh" else "ngspice") if i == 0 else None)
            rows.append(dict(panel="c", domain=dom, comparison=ATT_KEYS[k], diff=r["diff"], ci_low=r.ci_low, ci_high=r.ci_high))
        yl.append(ATT_LABEL[k])
    c.axvline(0, color=C["ink"], lw=0.7)
    c.set_yticks(range(len(keys)), yl)
    c.invert_yaxis()
    c.set_xlabel("Δ layer macro-F1 (paired bootstrap 95% CI)")
    c.legend(loc="lower right")
    panel(c, "c", "Attribution (E = ±2%, pooled over amplitudes and phases)")
    cap = ("Ablation study. (a) Layer macro-F1 (monitor E = ±2%, pooled over amplitudes and phases) of the old descriptors (A0), "
           "the fixed-sample Revision-1 descriptors (R1), R1 with phase-randomized training (R1r), the phase-robust descriptors "
           "(PR), the proposed PRr and the mixed-domain secondary variant PRrM; solid bars behavioral, hatched bars ngspice (A0 "
           f"was not simulated in ngspice). (b) Phase spread (max − min over the five edge phases); dashed line: gate G limit "
           f"{R.v('G_THRESH')}. (c) Paired-bootstrap differences with 95% CIs: descriptors alone (PR − R1) "
           f"{R.v('ATT_bh_DESC')} behavioral / {R.v('ATT_sp_DESC')} ngspice; randomisation alone (R1r − R1) {R.v('ATT_bh_RAND')} / "
           f"{R.v('ATT_sp_RAND')}; descriptors given randomisation (PRr − R1r) {R.v('ATT_bh_DESC_GIVEN_RAND')} / "
           f"{R.v('ATT_sp_DESC_GIVEN_RAND')}; randomisation given robust descriptors (PRr − PR) {R.v('ATT_bh_RAND_GIVEN_DESC')} "
           f"{R.ci('ATT_bh_RAND_GIVEN_DESC_LO', 'ATT_bh_RAND_GIVEN_DESC_HI')} / {R.v('ATT_sp_RAND_GIVEN_DESC')} "
           f"{R.ci('ATT_sp_RAND_GIVEN_DESC_LO', 'ATT_sp_RAND_GIVEN_DESC_HI')} (not resolvable); mixed-domain training (PRrM − PRr) "
           f"{R.v('ATT_bh_MIXED')} / {R.v('ATT_sp_MIXED')}.")
    save(fig, "Fig09_ablation", "result",
         [("a,b", "phase_robust_final/phase_robust_results/attribution_arms.csv", "layer_macro_f1; max−min of layer_f1_p*"),
          ("c", "phase_robust_final/phase_robust_results/attribution_comparisons.csv", "diff, ci_low, ci_high")],
         pd.DataFrame(rows), cap)
    return cap


# ------------------------------------------------------------------ Figure 10

def fig10(R):
    rf = load_csv(RES / "per_class_recall_fault.csv")
    rl = load_csv(RES / "per_class_recall_layer.csv")
    weak = 0.5
    fig = plt.figure(figsize=(FULL_W, 4.7))
    gs = fig.add_gridspec(2, 2, height_ratios=[1, 0.85], width_ratios=[2.6, 1.0], hspace=0.35, wspace=0.12)
    rows = []
    for k, dom in enumerate(("bh", "sp")):
        ax = fig.add_subplot(gs[k, 0])
        sub = rf[rf.domain == dom].set_index("arm")
        order = [a for a in ("A0", "R1", "R1r", "PR", "PRr", "PRrM") if a in sub.index]
        M = sub.loc[order, list(FAULTS)].values
        ax.imshow(M, cmap="Blues", vmin=0, vmax=1, aspect="auto")
        for i, a in enumerate(order):
            for j, f in enumerate(FAULTS):
                v = M[i, j]
                ax.text(j, i, f"{v:.2f}", ha="center", va="center", fontsize=6,
                        color="white" if v > 0.6 else C["ink"], fontweight="bold" if a == "PRr" else "normal")
                if v < weak:
                    ax.add_patch(Rectangle((j - 0.5, i - 0.5), 1, 1, fill=False, ec=C["nomon"], lw=0.9))
                rows.append(dict(panel="ab"[k], domain=dom, arm=a, class_=f, recall=v, weak=v < weak))
        ax.set_yticks(range(len(order)), [f"{a} (primary)" if a == "PRr" else a for a in order])
        ax.set_xticks(range(9), FAULT_LABELS if k == 1 else [""] * 9, rotation=40, ha="right")
        ax.grid(False)
        panel(ax, "ab"[k], f"Fine-fault recall, {'behavioral' if dom == 'bh' else 'ngspice'} (E = ±2%)")
        ax.set_ylabel("Arm")
        if k == 1:
            ax.set_xlabel("True fault class")
    ax = fig.add_subplot(gs[:, 1])
    sub = rl.copy()
    sub["label"] = [("no-mon. ×0.8/×1.2" if "no monitor" in a else a) + (" (bh)" if d == "bh" else " (sp)")
                    for a, d in zip(sub.arm, sub.domain)]
    keep = sub[sub.arm.isin(["R1", "PRr", "PRrM"]) | sub.arm.str.contains("no monitor")]
    M = keep[list(("healthy", "sensor", "afe", "adc"))].values
    ax.imshow(M, cmap="Blues", vmin=0, vmax=1, aspect="auto")
    for i in range(M.shape[0]):
        for j in range(4):
            v = M[i, j]
            ax.text(j, i, f"{v:.2f}", ha="center", va="center", fontsize=6, color="white" if v > 0.6 else C["ink"])
            if v < weak:
                ax.add_patch(Rectangle((j - 0.5, i - 0.5), 1, 1, fill=False, ec=C["nomon"], lw=0.9))
            rows.append(dict(panel="c", domain=keep.domain.iloc[i], arm=keep.arm.iloc[i], class_=("healthy", "sensor", "afe", "adc")[j],
                             recall=v, weak=v < weak))
    ax.set_yticks(range(M.shape[0]), keep.label)
    ax.yaxis.tick_right()
    ax.set_xticks(range(4), LAYER_LABELS, rotation=40, ha="right")
    ax.set_xlabel("True layer")
    ax.grid(False)
    panel(ax, "c", "Layer recall")
    weak_prr = [FAULT_LABELS[j] for j, f in enumerate(FAULTS) if R.raw(f"RF_bh_PRR_{f.upper()}") < weak]
    cap = ("Per-class recall (monitor E = ±2%, pooled over amplitudes and phases; mean of three dataset seeds). (a,b) "
           "Fine-fault recall of every arm in the behavioral and ngspice domains (PRr, the primary method, in bold). (c) Layer "
           "recall of R1, PRr and PRrM in both domains and of the no-monitor control (behavioral, ×0.8/×1.2). Red outlines mark "
           f"weak classes with recall below {weak:.2f} (display threshold chosen for this figure, not a pre-registered "
           f"criterion). For PRr the weak fine classes are {', '.join(weak_prr).lower()}; healthy-layer recall is "
           f"{R.v('RL_bh_PRR_HEALTHY')} (behavioral) and {R.v('RL_sp_PRR_HEALTHY')} (ngspice), so the classifier is a "
           "fault-localisation aid rather than a healthy/faulty detector.")
    save(fig, "Fig10_per_class_recall", "result",
         [("a,b", "phase_robust_final/phase_robust_results/per_class_recall_fault.csv", "all rows"),
          ("c", "phase_robust_final/phase_robust_results/per_class_recall_layer.csv", "rows R1, PRr, PRrM, no-monitor control")],
         pd.DataFrame(rows), cap)
    return cap, weak_prr


def build_all(R, extra):
    MAP_ROWS.clear()
    QC.clear()
    caps = {}
    caps["Fig01_architecture"] = fig01(R)
    caps["Fig02_timing"] = fig02(R)
    caps["Fig03_pipeline"] = fig03(R)
    caps["Fig04_fault_signatures"] = fig04(R)
    caps["Fig05_phase_sensitivity"] = fig05(R)
    caps["Fig06_reference_amplitude"] = fig06(R)
    caps["Fig07_afe_adc_separation"] = fig07(R, extra)
    caps["Fig08_domain_transfer"] = fig08(R)
    caps["Fig09_ablation"] = fig09(R)
    caps["Fig10_per_class_recall"], weak = fig10(R)
    with open(FIG / "FIGURE_SOURCE_DATA_MAP.csv", "w", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=list(MAP_ROWS[0].keys()))
        w.writeheader()
        w.writerows(MAP_ROWS)
    lines = ["# Figure captions (MDPI Sensors)", "",
             "Generated by `scripts/build_all.py`; every number in a caption is filled from `NUMBER_PROVENANCE_MDPI.csv`.",
             "Figures are in `figures/` as PNG (600 dpi), PDF and SVG. Type: result, illustrative or schematic.", ""]
    for i, (name, cap) in enumerate(caps.items(), 1):
        lines += [f"**Figure {i}.** {cap}", "", f"*File:* `figures/{name}.png|.pdf|.svg` · *Type:* {QC[name]['type']}", ""]
    (FIG / "FIGURE_CAPTIONS.md").write_text("\n".join(lines))
    return caps, dict(QC), weak


if __name__ == "__main__":
    from registry_build import build
    R, extra = build()
    caps, qc, _ = build_all(R, extra)
    for k, v in qc.items():
        print(k, "overlaps:", v["overlaps"], "outside:", v["outside"], "unit:", v["missing_unit"], "nolabel:", v["missing_label"])
