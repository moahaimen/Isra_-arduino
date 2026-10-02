#!/usr/bin/env python3
"""Leave-one-group-out selection (validation/development data only). For each held-out group: choose, per family, the config that
maximises pooled UR_timely on the other groups subject to pooled duty <= 0.25 (fallback: lowest duty); report that config on the held-out group.
Input: result CSVs of exp_sched.py / exp_baselines.py (all configs evaluated once on all groups)."""
import sys, os
import pandas as pd
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import lib31
out = sys.argv[1]
df = pd.concat([pd.read_csv(sys.argv[2]), pd.read_csv(sys.argv[3]).query("mode != 'always_on'")])
df["family"] = df["mode"].str.split("|").str[0]
g = lib31.pool(df, ["mode", "group"]); g["family"] = g["mode"].str.split("|").str[0]
ao = g[g["mode"] == "always_on"].set_index("group"); g = g[g["mode"] != "always_on"]
groups = sorted(g.group.unique()); rows = []
for fam, gf in g.groupby("family"):
    for h in groups:
        tr = gf[gf.group != h].groupby("mode")[["tracks_timely", "m7_active_ms", "seconds_ms"]].sum()
        aot = ao.loc[[x for x in groups if x != h], "tracks_timely"].sum()
        tr["UR"] = tr.tracks_timely / aot; tr["duty"] = tr.m7_active_ms / tr.seconds_ms
        ok = tr[tr.duty <= 0.25]
        pick = (ok.sort_values("UR", ascending=False).index[0] if len(ok) else tr.sort_values("duty").index[0])
        r = gf[(gf["mode"] == pick) & (gf.group == h)].iloc[0]
        rows.append({"family": fam, "heldout": h, "selected": pick, "constraint_met": bool(len(ok)), "UR_heldout": r.tracks_timely / ao.loc[h, "tracks_timely"] if ao.loc[h, "tracks_timely"] else float("nan"),
                     "duty_heldout": r.m7_active_ms / r.seconds_ms, "moving_tracks": ao.loc[h, "moving_tracks"]})
t = pd.DataFrame(rows); t.to_csv(out, index=False)
s = t.groupby("family").agg(UR_mean=("UR_heldout", "mean"), UR_min=("UR_heldout", "min"), duty_mean=("duty_heldout", "mean"), duty_max=("duty_heldout", "max"),
                            constraint_met=("constraint_met", "mean")).round(3)
print(s.to_string())
