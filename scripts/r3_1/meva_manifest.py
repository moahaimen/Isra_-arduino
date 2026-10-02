#!/usr/bin/env python3
"""Create the immutable MEVA (public S3 bucket mevadata-public-01) split manifest
BY METADATA ONLY (file names): no frame has been decoded when this runs.

Selection rule (fixed here, seed 20261002):
  * candidates: drops-123-r13 clips with duration >= 290 s (start/end time in the name);
  * cameras (G-numbers) are the sequence groups; splits are disjoint BY CAMERA
    (a camera never appears in two splits), which is stricter than disjoint clips;
  * per site (school, bus, hospital, admin) the cameras are shuffled with the seed and
    assigned test, then validation, then development:
        school: 1 test, 3 val, 1 dev;  bus: 1 test, 2 val, 1 dev;
        hospital: 1 test, 2 val;       admin: 1 test, 1 val
  * per camera one clip, drawn with the same seed among its candidate clips;
  * segment: seconds 15-105 of the clip (90 s), decimated 30 fps -> 10 fps (every 3rd frame).
"""
import hashlib, json, os, random, re, sys, urllib.request

B = "https://mevadata-public-01.s3.amazonaws.com"
ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
ALLOC = {"school": (1, 3, 1), "bus": (1, 2, 1), "hospital": (1, 2, 0), "admin": (1, 1, 0)}  # test, val, dev
SEED = 20261002


def ls(prefix, delim="/"):
    keys, token = [], None
    while True:
        u = f"{B}/?list-type=2&prefix={prefix}&delimiter={delim}&max-keys=1000" + (f"&continuation-token={urllib.parse.quote(token)}" if token else "")
        d = urllib.request.urlopen(u, timeout=60).read().decode()
        keys += list(zip(re.findall("<Key>([^<]*)</Key>", d), map(int, re.findall("<Size>([^<]*)</Size>", d))))
        pre = re.findall("<Prefix>([^<]*)</Prefix>", d)[1:]
        if "<IsTruncated>true" in d:
            token = re.search("<NextContinuationToken>([^<]*)", d).group(1)
        else:
            return pre, keys


def secs(h, m, s): return int(h) * 3600 + int(m) * 60 + int(s)


def main():
    import urllib.parse
    days, _ = ls("drops-123-r13/")
    clips = []
    for day in days:
        hours, k0 = ls(day)
        for hp in hours:
            _, ks = ls(hp)
            for name, size in ks:
                m = re.search(r"\.(\d\d)-(\d\d)-(\d\d)\.(\d\d)-(\d\d)-(\d\d)\.(\w+)\.(G\d+)\.r13\.avi$", name)
                if not m:
                    continue
                dur = secs(*m.group(4, 5, 6)) - secs(*m.group(1, 2, 3))
                if dur >= 290:
                    clips.append({"key": name, "site": m.group(7), "camera": m.group(8), "duration_s": dur, "bytes": size})
    rng = random.Random(SEED)
    by = {}
    for c in clips:
        by.setdefault((c["site"], c["camera"]), []).append(c)
    segs = []
    for site, (nt, nv, nd) in ALLOC.items():
        cams = sorted(cam for (s, cam) in by if s == site)
        rng.shuffle(cams)
        assign = ["test"] * nt + ["validation"] * nv + ["development"] * nd
        if len(cams) < len(assign):
            raise SystemExit(f"{site}: only {len(cams)} cameras with >= 290 s clips")
        for cam, split in zip(cams, assign):
            c = sorted(by[(site, cam)], key=lambda x: x["key"])
            clip = c[rng.randrange(len(c))]
            segs.append({"split": split, "site": site, "camera": cam, "group": f"{site}_{cam}", "key": clip["key"],
                         "bytes": clip["bytes"], "start_s": 15, "end_s": 105, "src_fps": 30, "fps": 10})
    out = {"name": "R3.1 MEVA splits", "source": B, "seed": SEED, "rule": __doc__, "candidates": len(clips),
           "segments": sorted(segs, key=lambda s: (s["split"], s["group"])),
           "license_note": "MEVA public data: licence reported by the project as CC BY 4.0; NOT verifiable from this container (mevadata.org blocked). Verify before publication.",
           "annotation_note": "No exhaustive box annotations are accessible from this container; evaluation is detector-referenced."}
    p = os.path.join(ROOT, "data", "splits", "r3_1_meva_splits.json")
    json.dump(out, open(p, "w"), indent=1)
    open(p.replace(".json", ".sha256"), "w").write(hashlib.sha256(open(p, "rb").read()).hexdigest() + "  data/splits/r3_1_meva_splits.json\n")
    for s in out["segments"]:
        print(s["split"], s["group"], s["key"].split("/")[-1], round(s["bytes"] / 1e6), "MB")


if __name__ == "__main__":
    import urllib.parse
    main()
