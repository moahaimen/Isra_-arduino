"""M4-class watcher features computed from REAL frames (reference
implementation). The C++ port is simulation/watcher/frame_features.h; the
two are checked against each other by tests/test_r2.py.

Input per frame: an 8-bit grayscale low-resolution image L_t (LOWRES_W x
LOWRES_H = 96 x 32, box-averaged from the camera frame) and a 17 x 16
grayscale fingerprint image F_t. No ground truth, no detector output.

Two sensing front ends are computed from the same frames; every method
receives both, and the operating mode decides which one its decision rule
reads (so front end and decision rule can be ablated separately):

BASIC front end (no illumination compensation; used by the R1-derived
legacy methods by default). State: L_{t-1}, edge map E_{t-1}, background B.

  D_t        = |L_t - L_{t-1}|
  motion     m_raw = mean(D_t > DELTA_D)                (frame-difference foreground fraction)
  temporal   tau_raw = mean(|L_t - B_{t-1}| > DELTA_B)   (change w.r.t. slow background)
  edges      G_t = |dx L_t| + |dy L_t|,  E_t = G_t > K_EDGE * mean(G_t)   (scale invariant)
             e_raw = |E_t xor E_{t-1}| / (|E_t or E_{t-1}| + 1)          (Jaccard distance)
  visual     v_raw = fraction of 8x8 cells whose mean |L_t - B_{t-1}| > DELTA_V
  noise      Immerkaer (1996) sigma estimate on L_t, / NOISE_REF
  B_t        = B_{t-1} + ALPHA_B (L_t - B_{t-1})

GAIN-COMPENSATED front end (R2). A global gain is estimated robustly from
the 48 cells and applied before differencing, so automatic-exposure hunting
and global illumination flicker do not look like motion:

  g_t        = median_cells( mean_cell(B'_{t-1}) / mean_cell(L_t) ), clipped to [0.5, 2]
  L'_t       = clip(g_t L_t, 0, 255)
  D'_t       = |L'_t - L'_{t-1}|,  m2 = mean(D'_t > DELTA_D)
  tau2       = mean(|L'_t - B'_{t-1}| > DELTA_B)
  v2         = fraction of cells with mean |L'_t - B'_{t-1}| > DELTA_V
  cells      motion_cells bit k (k = cy*12 + cx) = mean(D'_t > DELTA_D in cell) >= CELL_FRAC
  fg mask    FG_t = |L'_t - B'_{t-1}| > DELTA_B, OR-pooled 2x2 -> 48 x 16 = 768 bits
  B'_t       = B'_{t-1} + ALPHA_B (L'_t - B'_{t-1})

Normalised features (clipped to [0,1]): m = m_raw/M_REF, tau = tau_raw/T_REF,
v = v_raw/V_REF, e = e_raw/E_REF; consistency c = 1 - |m - e| when
max(m, e) > 0.05, else 1. The same normalisation applies to m2, tau2, v2
(consistency c2 uses m2).

Fingerprints:
  dhash256  bit(y, x) = F[y, x+1] > F[y, x], y < 16, x < 16, packed row-major
            into 4 uint64 words (word k holds rows 4k..4k+3)
  dhash64   classic 64-bit difference hash on a 9 x 8 box-downsample of L_t
            (the "perceptual content signature" read by the legacy gate)
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, Tuple

import numpy as np

LOWRES_W, LOWRES_H = 96, 32
FP_W, FP_H = 17, 16
CELL = 8
NCX, NCY = LOWRES_W // CELL, LOWRES_H // CELL  # 12 x 4 = 48 cells
FG_W, FG_H = LOWRES_W // 2, LOWRES_H // 2      # 48 x 16 foreground mask
DELTA_D, DELTA_B, DELTA_V = 15, 20, 12.0
K_EDGE = 2.0
CELL_FRAC = 0.10
ALPHA_B = 0.02
M_REF, T_REF, V_REF, E_REF = 0.05, 0.15, 0.25, 0.30  # set on the development split
NOISE_REF = 16.0  # set on the development split
GAIN_MIN, GAIN_MAX = 0.5, 2.0


def to_gray(rgb: np.ndarray) -> np.ndarray:
    r, g, b = rgb[..., 0].astype(np.uint32), rgb[..., 1].astype(np.uint32), rgb[..., 2].astype(np.uint32)
    return ((77 * r + 150 * g + 29 * b) >> 8).astype(np.uint8)


def box_resize(gray: np.ndarray, w: int, h: int) -> np.ndarray:
    """Area-average downsample (PIL BOX filter). The camera-side downsample
    is not part of the M4 feature code (the camera can deliver a binned
    frame); the C++ port starts from this low-res image."""
    from PIL import Image
    return np.asarray(Image.fromarray(gray).resize((w, h), Image.BOX))


def lowres_and_fp(rgb: np.ndarray) -> Tuple[np.ndarray, np.ndarray]:
    g = to_gray(rgb)
    return box_resize(g, LOWRES_W, LOWRES_H), box_resize(g, FP_W, FP_H)


def dhash256(fp: np.ndarray) -> Tuple[int, int, int, int]:
    bits = (fp[:, 1:] > fp[:, :-1]).astype(np.uint8)  # 16 x 16
    words = []
    for k in range(4):
        v = 0
        for b in bits[4 * k:4 * k + 4].reshape(-1):
            v = (v << 1) | int(b)
        words.append(v)
    return tuple(words)


def lowres_9x8(L: np.ndarray) -> np.ndarray:
    """Integer box downsample 96x32 -> 9x8 used by dhash64 (column k covers
    pixels [floor(96k/9), floor(96(k+1)/9)), rows cover 4 pixels each)."""
    Li = L.astype(np.int32)
    out = np.zeros((8, 9), np.int32)
    for y in range(8):
        for x in range(9):
            x0, x1 = (LOWRES_W * x) // 9, (LOWRES_W * (x + 1)) // 9
            blk = Li[4 * y:4 * y + 4, x0:x1]
            out[y, x] = int(blk.sum()) // blk.size
    return out


def dhash64(L: np.ndarray) -> int:
    s = lowres_9x8(L)
    v = 0
    for b in (s[:, 1:] > s[:, :-1]).reshape(-1):
        v = (v << 1) | int(b)
    return v


def hamming256(a, b) -> int:
    return sum(bin(x ^ y).count("1") for x, y in zip(a, b))


def edge_map(L: np.ndarray) -> np.ndarray:
    Li = L.astype(np.int32)
    G = np.zeros_like(Li)
    G[:, :-1] += np.abs(Li[:, 1:] - Li[:, :-1])
    G[:-1, :] += np.abs(Li[1:, :] - Li[:-1, :])
    s = int(G.sum())
    # integer form of G > K_EDGE * mean(G): G * N > K_EDGE * sum(G)
    return (G * G.size * 2 > int(2 * K_EDGE) * s) if s > 0 else np.zeros(G.shape, bool)


def noise_sigma(L: np.ndarray) -> float:
    Li = L.astype(np.int32)
    c = (Li[:-2, :-2] - 2 * Li[:-2, 1:-1] + Li[:-2, 2:] - 2 * Li[1:-1, :-2] + 4 * Li[1:-1, 1:-1]
         - 2 * Li[1:-1, 2:] + Li[2:, :-2] - 2 * Li[2:, 1:-1] + Li[2:, 2:])
    H, W = L.shape
    return float(np.sqrt(np.pi / 2.0) * np.abs(c).sum() / (6.0 * (W - 2) * (H - 2)))


def clip01(x: float) -> float:
    return 0.0 if x < 0 else (1.0 if x > 1 else float(x))


def cell_means(A: np.ndarray) -> np.ndarray:
    return A.reshape(NCY, CELL, NCX, CELL).mean(axis=(1, 3))


@dataclass
class FeatureState:
    prev: np.ndarray | None = None       # basic: previous low-res frame (uint8)
    prev_edges: np.ndarray | None = None
    bg: np.ndarray | None = None         # basic background (float64)
    prev_c: np.ndarray | None = None     # compensated previous frame (float64)
    bg_c: np.ndarray | None = None       # compensated background (float64)


def _consistency(m: float, e: float) -> float:
    return 1.0 - abs(m - e) if max(m, e) > 0.05 else 1.0


def step(state: FeatureState, L: np.ndarray, fp: np.ndarray) -> Dict:
    """Features of the current frame; updates `state`."""
    Lf = L.astype(np.float64)
    E = edge_map(L)
    if state.prev is None:
        state.prev, state.prev_edges, state.bg = L.copy(), E, Lf.copy()
        state.prev_c, state.bg_c = Lf.copy(), Lf.copy()
    # ---- basic front end ----------------------------------------------------
    D = np.abs(L.astype(np.int32) - state.prev.astype(np.int32))
    dmask = D > DELTA_D
    m_raw = float(dmask.mean())
    dev = np.abs(Lf - state.bg)
    t_raw = float((dev > DELTA_B).mean())
    inter_or = np.logical_or(E, state.prev_edges).sum()
    e_raw = float(np.logical_xor(E, state.prev_edges).sum() / (inter_or + 1.0))
    v_raw = float((cell_means(dev) > DELTA_V).mean())
    m, t, v, e = clip01(m_raw / M_REF), clip01(t_raw / T_REF), clip01(v_raw / V_REF), clip01(e_raw / E_REF)
    c = _consistency(m, e)
    n = clip01(noise_sigma(L) / NOISE_REF)
    # ---- gain-compensated front end ------------------------------------------
    cl = cell_means(Lf)
    cb = cell_means(state.bg_c)
    ratios = cb[cl > 0.5] / cl[cl > 0.5]
    g = float(np.median(ratios)) if ratios.size else 1.0
    g = min(GAIN_MAX, max(GAIN_MIN, g))
    Lc = np.clip(Lf * g, 0.0, 255.0)
    Dc = np.abs(Lc - state.prev_c)
    dmask_c = Dc > DELTA_D
    m2_raw = float(dmask_c.mean())
    dev_c = np.abs(Lc - state.bg_c)
    fgm = dev_c > DELTA_B
    t2_raw = float(fgm.mean())
    v2_raw = float((cell_means(dev_c) > DELTA_V).mean())
    cell_frac = cell_means(dmask_c.astype(np.float64))
    cells = 0
    for cy in range(NCY):
        for cx in range(NCX):
            if cell_frac[cy, cx] >= CELL_FRAC:
                cells |= 1 << (cy * NCX + cx)
    fg_pooled = fgm.reshape(FG_H, 2, FG_W, 2).any(axis=(1, 3))  # 16 x 48
    fg_bits = fg_pooled.reshape(-1)
    fg_words = []
    for k in range(12):
        w = 0
        for b in fg_bits[64 * k:64 * (k + 1)]:
            w = (w << 1) | int(b)
        fg_words.append(w)
    m2, t2, v2 = clip01(m2_raw / M_REF), clip01(t2_raw / T_REF), clip01(v2_raw / V_REF)
    c2 = _consistency(m2, e)
    # ---- state update -----------------------------------------------------------
    state.bg = state.bg + ALPHA_B * (Lf - state.bg)
    state.bg_c = state.bg_c + ALPHA_B * (Lc - state.bg_c)
    state.prev, state.prev_edges, state.prev_c = L.copy(), E, Lc
    fpw = dhash256(fp)
    return {"motion_score": m, "temporal_change_score": t, "visual_score": v, "edge_change_score": e,
            "sensor_consistency_score": c, "noise_score": n,
            "r2_motion": m2, "r2_temporal": t2, "r2_visual": v2, "r2_consistency": c2, "gain": g,
            "motion_cells": cells, "fg_count": int(fg_bits.sum()), "fg": fg_words,
            "m_raw": m_raw, "tau_raw": t_raw, "v_raw": v_raw, "e_raw": e_raw, "m2_raw": m2_raw,
            "fp": list(fpw), "sig64": dhash64(L)}


def op_count_per_frame() -> Dict[str, int]:
    """Approximate integer/float operations per frame on the M4 (excluding the
    camera-side box downsample), both front ends."""
    n = LOWRES_W * LOWRES_H
    ops = {
        "basic_frame_difference_threshold": 3 * n,
        "basic_background_deviation_and_update": 5 * n,
        "gradient_and_edge_map": 7 * n,
        "edge_xor_or": 3 * n,
        "cell_statistics": 4 * n,
        "noise_laplacian": 12 * n,
        "gain_estimate_cell_means_median": 2 * n + 48 * 6,
        "compensated_difference_background_fg": 9 * n,
        "fg_mask_pooling": n,
        "dhash256": FP_H * (FP_W - 1),
        "dhash64": n + 64,
    }
    ops["total"] = sum(ops.values())
    return ops
