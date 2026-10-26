"""Shared paths, loaders, rounding and the number-provenance registry.

Every number that appears in a figure annotation, table cell or manuscript draft
is registered here with its source file, key, calculation and rounding rule.
Nothing downstream types a result value by hand.
"""
from __future__ import annotations

import csv
import json
import math
from dataclasses import dataclass, field
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[2]
EVID = ROOT / "evidence_package_2026-10-26"
PRF = EVID / "phase_robust_final"
RES = PRF / "phase_robust_results"
PP = EVID / "paper_package"
OUT = ROOT / "mdpi_sensors_preparation"

SEEDS = (20261026, 20261027, 20261028)
INITS = (11, 22)
PHASES = ("000", "250", "500", "750", "999")
PHASE_VALUES = (0.0, 0.25, 0.5, 0.75, 0.999)
AMPS_BH = (80, 90, 100, 110, 120)
AMPS_SP = (80, 100, 120)
LAYERS = ("healthy", "sensor", "afe", "adc")
FAULTS = ("healthy", "sensor_bias", "sensor_gain", "sensor_noise", "afe_offset",
          "afe_bandwidth", "adc_offset", "adc_gain", "adc_clipping")
FAULT_LABELS = ("Healthy", "Sensor bias", "Sensor gain", "Sensor noise", "AFE offset",
                "AFE bandwidth", "ADC offset", "ADC gain", "ADC clipping")
LAYER_LABELS = ("Healthy", "Sensor", "AFE", "ADC")
FAULT_TO_LAYER = (0, 1, 1, 1, 2, 2, 3, 3, 3)
ARMS = ("A0", "R1", "R1r", "PR", "PRr", "PRrM")
DOMAIN_LABEL = {"bh": "Behavioral", "sp": "ngspice"}
VARIANTS = ("known", "mon0", "mon1", "mon2", "mon5")
VARIANT_LABEL = {"known": "Known reference", "mon0": "Monitor E = 0%", "mon1": "Monitor E = ±1%",
                 "mon2": "Monitor E = ±2%", "mon5": "Monitor E = ±5%"}

ROUNDING_RULE = ("Python format() to the stated number of decimals (round-half-to-even on the "
                 "stored binary value); signed differences carry an explicit '+'.")


def rel(p: Path) -> str:
    """Path relative to the evidence package root (or repo root) for provenance."""
    p = Path(p)
    for base in (EVID, ROOT):
        try:
            return str(p.relative_to(base))
        except ValueError:
            continue
    return str(p)


def load_json(p: Path):
    with open(p) as fh:
        return json.load(fh)


def load_csv(p: Path) -> pd.DataFrame:
    return pd.read_csv(p)


def fmt(x: float, decimals: int = 3, signed: bool = False) -> str:
    if x is None or (isinstance(x, float) and math.isnan(x)):
        return "—"
    s = format(float(x), f".{decimals}f")
    if s.startswith("-") and float(s) == 0.0:
        s = s[1:]
    if signed and not s.startswith("-"):
        s = "+" + s
    return s.replace("-", "−") if False else s


@dataclass
class Entry:
    token: str
    raw: object
    decimals: int | None
    signed: bool
    source_file: str
    key: str
    calculation: str
    status: str  # primary | secondary | previous-stage | illustrative | protocol | derived
    note: str = ""

    @property
    def value(self) -> str:
        if isinstance(self.raw, (int, np.integer)) and self.decimals is None:
            return f"{int(self.raw):,}" if abs(int(self.raw)) >= 10000 else str(int(self.raw))
        if isinstance(self.raw, str):
            return self.raw
        if self.decimals is None:
            return str(self.raw)
        return fmt(float(self.raw), self.decimals, self.signed)


@dataclass
class Registry:
    entries: dict = field(default_factory=dict)

    def add(self, token, raw, source_file, key, calculation="direct read", decimals=3,
            signed=False, status="primary", note=""):
        if token in self.entries:
            raise KeyError(f"duplicate token {token}")
        if isinstance(raw, (np.floating,)):
            raw = float(raw)
        self.entries[token] = Entry(token, raw, decimals, signed, rel(source_file) if isinstance(source_file, Path) else source_file,
                                    key, calculation, status, note)
        return self.entries[token]

    def v(self, token) -> str:
        return self.entries[token].value

    def raw(self, token):
        return self.entries[token].raw

    def ci(self, lo, hi) -> str:
        return f"[{self.v(lo)}, {self.v(hi)}]"

    def to_csv(self, path: Path):
        path.parent.mkdir(parents=True, exist_ok=True)
        with open(path, "w", newline="") as fh:
            w = csv.writer(fh)
            w.writerow(["token", "value", "raw_value", "status", "source_file", "key_or_row",
                        "calculation", "rounding", "note"])
            for e in self.entries.values():
                rnd = ("integer / text, no rounding" if e.decimals is None
                       else f"{e.decimals} decimals" + (", signed" if e.signed else ""))
                w.writerow([e.token, e.value, e.raw, e.status, e.source_file, e.key,
                            e.calculation, rnd, e.note])


# ---------------------------------------------------------------- metrics from predictions

def confusion(y, p, k):
    m = np.zeros((k, k))
    np.add.at(m, (np.asarray(y, int), np.asarray(p, int)), 1)
    return m


def macro_f1(m):
    tp = np.diag(m)
    prec = np.divide(tp, m.sum(0), out=np.zeros_like(tp), where=m.sum(0) > 0)
    rec = np.divide(tp, m.sum(1), out=np.zeros_like(tp), where=m.sum(1) > 0)
    den = prec + rec
    f = np.divide(2 * prec * rec, den, out=np.zeros_like(tp), where=den > 0)
    return float(f.mean())


def recall(m):
    return np.diag(m) / m.sum(1)


def cross_confusion(m):
    """Fraction of AFE- and ADC-fault samples assigned to the other of the two layers."""
    return float((m[2, 3] + m[3, 2]) / (m[2].sum() + m[3].sum()))


_PRED_CACHE: dict = {}


def predictions(seed):
    if seed not in _PRED_CACHE:
        z = np.load(RES / f"seed_{seed}" / "predictions.npz")
        _PRED_CACHE[seed] = {k: z[k] for k in z.files}
    return _PRED_CACHE[seed]


def pooled_confusion(seed, init, domain, variant, model, target, amps, phases=PHASES):
    z = predictions(seed)
    y = z["y_layer"] if target == "layer" else z["y_fault"]
    k = 4 if target == "layer" else 9
    m = np.zeros((k, k))
    for a in amps:
        for p in phases:
            m += confusion(y, z[f"{domain}_a{a}_p{p}_{variant}|{model}|{init}|{target}"], k)
    return m


def mean_metric(fn, domain, variant, model, target, amps, phases=PHASES):
    """Mean over 3 dataset seeds x 2 init seeds of fn(pooled confusion)."""
    vals = [fn(pooled_confusion(s, i, domain, variant, model, target, amps, phases))
            for s in SEEDS for i in INITS]
    return float(np.mean(vals, axis=0)) if np.ndim(vals[0]) == 0 else np.mean(vals, axis=0)


def model_for(arm, variant):
    suffix = "k" if variant in ("known", "assumed") else "e" + variant[-1]
    return f"two_point_mlp@{arm}_{suffix}" if arm != "A0" else "two_point_mlp@A0"
