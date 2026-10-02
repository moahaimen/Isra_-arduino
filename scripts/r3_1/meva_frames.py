#!/usr/bin/env python3
"""Download MEVA clips and extract 10 fps frames (seconds 15-105, every 3rd frame)
resized to 1280x720 and stored as JPEG q95 under $R31_DATA/meva/<group>/%05d.jpg.
Refuses the test split unless --allow-test (locked until the R3.1 freeze)."""
import argparse, json, os, sys, urllib.request
import cv2
ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
DATA = os.environ.get("R31_DATA", "/home/claude/data_r3_1")
B = "https://mevadata-public-01.s3.amazonaws.com"


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--splits", default="development,validation")
    ap.add_argument("--allow-test", action="store_true")
    a = ap.parse_args()
    want = a.splits.split(",")
    if "test" in want and not a.allow_test:
        raise SystemExit("MEVA test split is locked until config/r3_1_frozen.json is committed")
    m = json.load(open(os.path.join(ROOT, "data", "splits", "r3_1_meva_splits.json")))
    for s in m["segments"]:
        if s["split"] not in want:
            continue
        out = os.path.join(DATA, "meva", s["group"])
        if os.path.exists(os.path.join(out, "DONE")):
            continue
        os.makedirs(out, exist_ok=True)
        clip = os.path.join(DATA, "meva_raw", os.path.basename(s["key"]))
        os.makedirs(os.path.dirname(clip), exist_ok=True)
        if not os.path.exists(clip):
            urllib.request.urlretrieve(f"{B}/{s['key']}", clip + ".part")
            os.replace(clip + ".part", clip)
        c = cv2.VideoCapture(clip)
        fps = c.get(cv2.CAP_PROP_FPS)
        step = int(round(fps / s["fps"]))
        f0, f1 = int(s["start_s"] * fps), int(s["end_s"] * fps)
        c.set(cv2.CAP_PROP_POS_FRAMES, f0)
        n = 0
        for f in range(f0, f1):
            ok, img = c.read()
            if not ok:
                break
            if (f - f0) % step == 0:
                cv2.imwrite(os.path.join(out, f"{n:05d}.jpg"), cv2.resize(img, (1280, 720), interpolation=cv2.INTER_AREA),
                            [cv2.IMWRITE_JPEG_QUALITY, 95])
                n += 1
        open(os.path.join(out, "DONE"), "w").write(f"{n} frames from {s['key']} fps_src={fps}\n")
        os.remove(clip)
        print(s["split"], s["group"], n, "frames", flush=True)


if __name__ == "__main__":
    main()
