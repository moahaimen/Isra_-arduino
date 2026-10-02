#!/usr/bin/env python3
"""Shared machinery for simulation campaigns (main, ablation, sensitivity).

A campaign is a list of run specifications. For each distinct
(scenario, seed, seconds, workload parameters) one workload is generated and
saved first; every run that shares that key replays the SAME workload file.
Each run then writes raw outputs, per-run metrics and a validation report.

Directory layout (never overwritten; an existing campaign id is refused):

    results/campaigns/<campaign_id>/
        config/      copies of every configuration file + campaign.json metadata
        workloads/   generated workload JSONL (+ .meta.json)
        raw/         per-run simulator outputs (events.jsonl.gz, observations.csv.gz, ...)
        per_run/     per-run metrics (metrics.csv, one JSON per run)
        aggregate/   aggregated CSV, statistics and tables
        figures/     PNG + PDF figures
        logs/        validation results and runner logs
"""
from __future__ import annotations

import concurrent.futures as cf
import datetime as dt
import gzip
import hashlib
import json
import os
import platform
import shutil
import subprocess
import sys
from typing import Dict, List, Optional

import pandas as pd

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.abspath(os.path.join(HERE, "..", ".."))
sys.path.insert(0, HERE)
from metrics import compute_run_metrics  # noqa: E402
from validate_run import validate_run  # noqa: E402

DEFAULT_BIN = os.path.join(REPO, "build", "edge_sim")
DEFAULT_CONFIG = os.path.join(REPO, "config", "default_config.json")
ALL_SCENARIOS = ["quiet", "normal", "busy", "burst", "noisy", "trigger_spam", "replay", "mixed"]
ALL_MODES = ["always_on", "motion_only", "fixed_threshold", "event", "event_no_early_exit", "secure"]


def parse_seeds(text: str) -> List[int]:
    """'1:10' -> [1..10]; '1,3,5' -> [1,3,5]; '7' -> [7]."""
    out: List[int] = []
    for part in text.split(","):
        part = part.strip()
        if ":" in part:
            a, b = part.split(":")
            out.extend(range(int(a), int(b) + 1))
        elif part:
            out.append(int(part))
    return out


def sha256_file(path: str) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as fh:
        for chunk in iter(lambda: fh.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def git_info() -> Dict[str, str]:
    def run(args):
        try:
            return subprocess.check_output(args, cwd=REPO, stderr=subprocess.DEVNULL).decode().strip()
        except Exception:
            return ""
    return {
        "commit": run(["git", "rev-parse", "HEAD"]),
        "branch": run(["git", "rev-parse", "--abbrev-ref", "HEAD"]),
        "dirty": bool(run(["git", "status", "--porcelain", "--untracked-files=no"])),
    }


def env_info() -> Dict[str, str]:
    info = {"python": sys.version.split()[0], "platform": platform.platform()}
    for mod in ("numpy", "pandas", "scipy", "matplotlib"):
        try:
            info[mod] = __import__(mod).__version__
        except Exception:
            info[mod] = "missing"
    try:
        info["compiler"] = subprocess.check_output(["c++", "--version"]).decode().splitlines()[0]
    except Exception:
        info["compiler"] = "unknown"
    return info


def workload_key(spec: Dict) -> str:
    wa = spec.get("workload_args", {})
    tag = json.dumps(wa, sort_keys=True)
    h = hashlib.sha1(tag.encode()).hexdigest()[:8] if wa else "default"
    return f"{spec['scenario']}__s{spec['seed']}__{int(spec['seconds'])}s__{h}"


def create_campaign_dir(root: str, campaign_id: str) -> str:
    path = os.path.join(root, campaign_id)
    if os.path.exists(path):
        raise SystemExit(f"refusing to overwrite existing campaign: {path}")
    for sub in ("config", "workloads", "raw", "per_run", "aggregate", "figures", "logs"):
        os.makedirs(os.path.join(path, sub))
    return path


def _gzip_inplace(path: str) -> None:
    if not os.path.exists(path):
        return
    with open(path, "rb") as src, gzip.open(path + ".gz", "wb", compresslevel=6) as dst:
        shutil.copyfileobj(src, dst)
    os.remove(path)


def generate_workload(binary: str, cfg_path: str, spec: Dict, out_path: str) -> str:
    cmd = [binary, "--config", cfg_path, "--scenario", spec["scenario"], "--seed", str(spec["seed"]),
           "--seconds", str(spec["seconds"]), "--save-workload", out_path, "--generate-only"]
    for k, v in sorted(spec.get("workload_args", {}).items()):
        cmd += [f"--{k.replace('_', '-')}", str(v)]
    subprocess.run(cmd, check=True, stdout=subprocess.DEVNULL)
    return out_path


def execute_run(binary: str, cfg_path: str, spec: Dict, wl_path: str, out_dir: str, log_level: str,
                compress: bool) -> Dict:
    cmd = [binary, "--config", cfg_path, "--mode", spec["mode"], "--workload", wl_path,
           "--out-dir", out_dir, "--log-level", log_level] + list(spec.get("sim_args", []))
    proc = subprocess.run(cmd, capture_output=True, text=True)
    if proc.returncode != 0:
        return {"run_id": spec["run_id"], "error": proc.stderr.strip(), "command": " ".join(cmd)}
    with open(os.path.join(out_dir, "command.txt"), "w") as fh:
        fh.write(" ".join(cmd) + "\n")
    if compress:
        _gzip_inplace(os.path.join(out_dir, "events.jsonl"))
        _gzip_inplace(os.path.join(out_dir, "observations.csv"))
    metrics = compute_run_metrics(out_dir)
    val = validate_run(out_dir)
    metrics.update({k: spec[k] for k in ("run_id", "label", "group") if k in spec})
    metrics["sweep_param"] = spec.get("sweep_param", "")
    metrics["sweep_value"] = spec.get("sweep_value", "")
    metrics["validation_pass"] = all(v[0] for v in val.values())
    metrics["validation_failures"] = "|".join(k for k, v in val.items() if not v[0])
    with open(os.path.join(out_dir, "metrics.json"), "w") as fh:
        json.dump(metrics, fh, indent=1, default=str)
    return metrics


def run_campaign(specs: List[Dict], campaign_root: str, campaign_id: str, binary: str = DEFAULT_BIN,
                 config: str = DEFAULT_CONFIG, jobs: int = 4, log_level: str = "full", compress: bool = True,
                 meta: Optional[Dict] = None) -> str:
    """Run every spec and return the campaign directory."""
    if not os.path.exists(binary):
        raise SystemExit(f"simulator binary not found: {binary} (build with cmake first)")
    cdir = create_campaign_dir(campaign_root, campaign_id)
    cfg_copy = os.path.join(cdir, "config", "default_config.json")
    shutil.copy(config, cfg_copy)
    with open(config) as fh:
        pm_rel = json.load(fh).get("power_model", "config/power_model.json")
    shutil.copy(os.path.join(REPO, pm_rel), os.path.join(cdir, "config", "power_model.json"))
    # The copied config must point at the copied power model.
    with open(cfg_copy) as fh:
        cfgj = json.load(fh)
    cfgj["power_model"] = os.path.join(cdir, "config", "power_model.json")
    with open(cfg_copy, "w") as fh:
        json.dump(cfgj, fh, indent=2)

    metadata = {
        "campaign_id": campaign_id,
        "created_utc": dt.datetime.now(dt.timezone.utc).isoformat(),
        "command": " ".join(sys.argv),
        "git": git_info(),
        "environment": env_info(),
        "simulator_binary_sha256": sha256_file(binary),
        "num_runs": len(specs),
        "log_level": log_level,
        "note": "All energy values are MODELED from simulation-assumption power states (uncalibrated).",
    }
    metadata.update(meta or {})
    with open(os.path.join(cdir, "config", "campaign.json"), "w") as fh:
        json.dump(metadata, fh, indent=2)
    with open(os.path.join(cdir, "config", "run_specs.json"), "w") as fh:
        json.dump(specs, fh, indent=1)

    # 1) Generate each shared workload exactly once.
    wl_paths: Dict[str, str] = {}
    for spec in specs:
        key = workload_key(spec)
        if key not in wl_paths:
            wl_paths[key] = os.path.join(cdir, "workloads", key + ".jsonl")
    keyed_specs = {workload_key(s): s for s in specs}
    with cf.ThreadPoolExecutor(max_workers=jobs) as ex:
        list(ex.map(lambda k: generate_workload(binary, cfg_copy, keyed_specs[k], wl_paths[k]), list(wl_paths)))

    # 2) Run every spec on its shared workload.
    results: List[Dict] = []
    errors: List[Dict] = []
    with cf.ProcessPoolExecutor(max_workers=jobs) as ex:
        futs = {}
        for spec in specs:
            out_dir = os.path.join(cdir, "raw", spec["run_id"])
            fut = ex.submit(execute_run, binary, cfg_copy, spec, wl_paths[workload_key(spec)], out_dir, log_level,
                            compress)
            futs[fut] = spec
        for i, fut in enumerate(cf.as_completed(futs), 1):
            r = fut.result()
            (errors if "error" in r else results).append(r)
            if i % 50 == 0 or i == len(futs):
                print(f"  [{campaign_id}] {i}/{len(futs)} runs done", flush=True)
    df = pd.DataFrame(results).sort_values("run_id")
    df.to_csv(os.path.join(cdir, "per_run", "metrics.csv"), index=False)
    val_cols = ["run_id", "scenario", "seed", "mode", "label", "validation_pass", "validation_failures"]
    df[[c for c in val_cols if c in df.columns]].to_csv(os.path.join(cdir, "logs", "validation.csv"), index=False)
    with open(os.path.join(cdir, "logs", "errors.json"), "w") as fh:
        json.dump(errors, fh, indent=1)
    # 3) Workload-equality audit: every run of a (scenario, seed, wl args)
    #    must carry the hash of the shared workload file.
    audit = []
    rid_key = {s["run_id"]: workload_key(s) for s in specs}
    wl_of_run = df["run_id"].map(rid_key)
    for key, path in wl_paths.items():
        with open(path + ".meta.json") as fh:
            h = json.load(fh)["workload_hash_fnv1a64"]
        sub = df[wl_of_run == key]
        audit.append({"workload": key, "file_hash": h, "runs": len(sub),
                      "all_runs_match": bool((sub["workload_hash"] == h).all())})
    pd.DataFrame(audit).to_csv(os.path.join(cdir, "logs", "workload_equality.csv"), index=False)
    print(f"campaign {campaign_id}: {len(results)} runs ok, {len(errors)} errors, "
          f"validation failures: {int((~df['validation_pass']).sum())}, "
          f"workload mismatches: {sum(1 for a in audit if not a['all_runs_match'])}")
    return cdir
