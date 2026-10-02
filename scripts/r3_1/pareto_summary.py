#!/usr/bin/env python3
"""Pooled (clean+noisy) UR_timely / duty per config from exp_sched / exp_baselines CSVs; best UR under duty<=0.25 per family."""
import sys, os, pandas as pd
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import lib31
def table(path):
    df = pd.read_csv(path); g = lib31.pool(df, ["mode", "scenario"]); ao = g[g["mode"] == "always_on"].set_index("scenario")
    rows = []
    for m, x in g[g["mode"] != "always_on"].groupby("mode"):
        r = {"mode": m, "family": m.split("|")[0]}
        for sc in ["clean", "noisy"]:
            y = x[x.scenario == sc].iloc[0]
            r[sc + "_UR"] = y.tracks_timely / ao.loc[sc, "tracks_timely"]; r[sc + "_duty"] = y.m7_active_ms / y.seconds_ms
            r[sc + "_energy"] = y.energy_per_min_mJ
        rows.append(r)
    t = pd.DataFrame(rows); t["UR"] = (t.clean_UR + t.noisy_UR) / 2; t["duty"] = (t.clean_duty + t.noisy_duty) / 2
    return t
if __name__ == "__main__":
    t = pd.concat([table(p) for p in sys.argv[2:]], ignore_index=True); t.to_csv(sys.argv[1], index=False)
    ok = t[t.duty <= 0.25]
    print("best UR with duty<=0.25 per family (mean of clean/noisy):")
    print(ok.sort_values("UR", ascending=False).groupby("family").head(1)[["mode", "clean_UR", "noisy_UR", "UR", "clean_duty", "noisy_duty", "duty"]].round(3).to_string())
    print("overall min duty per family:"); print(t.groupby("family").duty.min().round(3).to_string())
