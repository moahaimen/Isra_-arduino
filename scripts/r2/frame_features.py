"""M4-class watcher features computed from REAL frames (reference
implementation; the C++ port is simulation/watcher/frame_features.h and the
two are checked against each other by tests/test_r2.py).

Input per frame: an 8-bit grayscale low-resolution image L_t (LOWRES_W x
LOWRES_H, box-averaged from the camera frame) and a 17 x 16 grayscale
fingerprint image F_t. No ground truth, no detector output.

State carried between frames: L_{t-1}, binary edge map E_{t-1}, background
B (float, exponential moving average).

  D_t        = |L_t - L_{t-1}|
  motion     m_raw = mean(D_t > DELTA_D)                (frame-difference foreground fraction)
  temporal   tau_raw = mean(|L_t - B_{t-1}| > DELTA_B)   (change w.r.t. slow background)
  edges      G_t = |dx L_t| + |dy L_t|,  E_t = G_t > K_EDGE * mean(G_t)   (scale invariant)
             e_raw = |E_t xor E_{t-1}| / (|E_t or E_{t-1}| + 1)          (Jaccard distance)
  cells      8x8-pixel cells; cell active if mean(D_t > DELTA_D) >= CELL_FRAC; motion_cells = bitmask
  visual     v_raw = fraction of cells whose mean |L_t - B_{t-1}| > DELTA_V   (block-level activity)
  noise      Immerkaer (1996) estimate on L_t, sigma / NOISE_REF
  B_t        = B_{t-1} + ALPHA_B (L_t - B_{t-1})

Normalised features (clipped to [0,1]): m = m_raw/M_REF, tau = tau_raw/T_REF,
v = v_raw/V_REF, e = e_raw/E_REF; consistency c = 1 - |m - e| when
max(m, e) > 0.05, else 1 (both cues agree there is no change). Global
illumination flicker raises m but leaves the scale-invariant edge map
nearly unchanged, so c drops; real object motion raises both.

Fingerprint: 256-bit difference hash, bit(y, x) = F[y, x+1] > F[y, x],
y < 16, x < 16, packed row-major into 4 uint64 words (word k holds rows 4k..4k+3).
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, Tuple

import numpy as np

LOWRES_W, LOWRES_H = 96, 32
FP_W, FP_H = 17, 16
CELL = 8
DELTA_D, DELTA_B, DELTA_V = 15, 20, 12.0
K_EDGE = 2.0
CELL_FRAC = 0.10
ALPHA_B = 0.02
M_REF, T_REF, V_REF, E_REF = 0.05, 0.15, 0.25, 0.30  # set on the development split
NOISE_REF = 16.0  # set on the development split


def to_gray(rgb: np.ndarray) -> np.ndarray:
    r, g, b = rgb[..., 0].astype(np.uint32), rgb[..., 1].astype(np.uint32), rgb[..., 2].astype(np.uint32)
    return ((77 * r + 150 * g + 29 * b) >> 8).astype(np.uint8)


def box_resize(gray: np.ndarray, w: int, h: int) -> np.ndarray:
    """Area-average downsample (PIL BOX filter). The camera-side downsample
    is not part of the M4 feature code (the Portenta camera driver can
    deliver a binned frame); the C++ port starts from this low-res image."""
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


def hamming256(a, b) -> int:
    return sum(bin(x ^ y).count("1") for x, y in zip(a, b))


def edge_map(L: np.ndarray) -> np.ndarray:
    Li = L.astype(np.int32)
    G = np.zeros_like(Li)
    G[:, :-1] += np.abs(Li[:, 1:] - Li[:, :-1])
    G[:-1, :] += np.abs(Li[1:, :] - Li[:-1, :])
    m = G.mean()
    return G > K_EDGE * m if m > 0 else np.zeros(G.shape, bool)


def noise_sigma(L: np.ndarray) -> float:
    Li = L.astype(np.int32)
    c = (Li[:-2, :-2] - 2 * Li[:-2, 1:-1] + Li[:-2, 2:] - 2 * Li[1:-1, :-2] + 4 * Li[1:-1, 1:-1]
         - 2 * Li[1:-1, 2:] + Li[2:, :-2] - 2 * Li[2:, 1:-1] + Li[2:, 2:])
    H, W = L.shape
    return float(np.sqrt(np.pi / 2.0) * np.abs(c).sum() / (6.0 * (W - 2) * (H - 2)))


@dataclass
class FeatureState:
    prev: np.ndarray | None = None
    prev_edges: np.ndarray | None = None
    bg: np.ndarray | None = None
    extra: Dict = field(default_factory=dict)


def clip01(x: float) -> float:
    return 0.0 if x < 0 else (1.0 if x > 1 else float(x))


def step(state: FeatureState, L: np.ndarray, fp: np.ndarray) -> Dict:
    """Features of the current frame; updates `state`."""
    E = edge_map(L)
    if state.prev is None:
        state.prev, state.prev_edges, state.bg = L.copy(), E, L.astype(np.float64)
    D = np.abs(L.astype(np.int32) - state.prev.astype(np.int32))
    dmask = D > DELTA_D
    m_raw = float(dmask.mean())
    dev = np.abs(L.astype(np.float64) - state.bg)
    t_raw = float((dev > DELTA_B).mean())
    inter_or = np.logical_or(E, state.prev_edges).sum()
    e_raw = float(np.logical_xor(E, state.prev_edges).sum() / (inter_or + 1.0))
    H, W = L.shape
    nc_y, nc_x = H // CELL, W // CELL
    cells = 0
    v_cnt = 0
    for cy in range(nc_y):
        for cx in range(nc_x):
            sl = (slice(cy * CELL, (cy + 1) * CELL), slice(cx * CELL, (cx + 1) * CELL))
            if dmask[sl].mean() >= CELL_FRAC:
                cells |= 1 << (cy * nc_x + cx)
            if dev[sl].mean() > DELTA_V:
                v_cnt += 1
    v_raw = v_cnt / float(nc_y * nc_x)
    m, t, v, e = clip01(m_raw / M_REF), clip01(t_raw / T_REF), clip01(v_raw / V_REF), clip01(e_raw / E_REF)
    c = 1.0 - abs(m - e) if max(m, e) > 0.05 else 1.0
    n = clip01(noise_sigma(L) / NOISE_REF)
    state.bg = state.bg + ALPHA_B * (L.astype(np.float64) - state.bg)
    state.prev, state.prev_edges = L.copy(), E
    fpw = dhash256(fp)
    return {"motion_score": m, "temporal_change_score": t, "visual_score": v, "edge_change_score": e,
            "sensor_consistency_score": c, "noise_score": n, "motion_cells": cells,
            "m_raw": m_raw, "tau_raw": t_raw, "v_raw": v_raw, "e_raw": e_raw,
            "fp0": fpw[0], "fp1": fpw[1], "fp2": fpw[2], "fp3": fpw[3]}


def op_count_per_frame() -> Dict[str, int]:
    """Approximate integer operations per frame on the M4 (excluding the
    camera-side box downsample)."""
    n = LOWRES_W * LOWRES_H
    ops = {
        "frame_difference_threshold": 3 * n,
        "background_deviation_and_update": 5 * n,
        "gradient_and_edge_map": 7 * n,
        "edge_xor_or": 3 * n,
        "cell_statistics": 2 * n,
        "noise_laplacian": 12 * n,
        "dhash256": FP_H * (FP_W - 1),
    }
    ops["total"] = sum(ops.values())
    return ops
