#!/usr/bin/env bash
# Download every external input of the R2 study into $DATA (default
# /home/claude/data_r2). Nothing here is stored in git; all inputs are pinned
# by SHA-256 (models) or by the official dataset release.
#
#   models  MediaPipe object detectors (Apache-2.0), Google public bucket
#   voc     PASCAL VOC 2007 (fast.ai S3 mirror of the official release,
#           COCO-format json; train/valid/test = official VOC07 splits)
#   kitti   KITTI tracking labels + OXTS + the 1,189 static-segment frames
#           (CC BY-NC-SA 3.0, official avg-kitti bucket, HTTP range requests)
set -euo pipefail
DATA=${DATA:-/home/claude/data_r2}
HERE="$(cd "$(dirname "$0")" && pwd)"
mkdir -p "$DATA/models" "$DATA/voc" "$DATA/kitti"

python3 - "$DATA/models" <<'EOF'
import os, sys, urllib.request, hashlib
sys.path.insert(0, os.path.join(os.environ.get("HERE", "scripts/r2"), "..", "detector"))
sys.path.insert(0, "scripts/detector")
import models
d = sys.argv[1]
for name, s in models.MODELS.items():
    p = os.path.join(d, s["file"])
    if not os.path.exists(p):
        urllib.request.urlretrieve(s["url"], p)
    h = hashlib.sha256(open(p, "rb").read()).hexdigest()
    assert h == s["sha256"], (name, h)
    print("model ok", name, os.path.getsize(p))
EOF

if [ ! -d "$DATA/voc/pascal_2007" ]; then
  curl -sSL --retry 4 -o "$DATA/voc/pascal_2007.tgz" https://s3.amazonaws.com/fast-ai-imagelocal/pascal_2007.tgz
  tar -xzf "$DATA/voc/pascal_2007.tgz" -C "$DATA/voc"
  rm -f "$DATA/voc/pascal_2007.tgz"
fi
echo "voc ok: $(ls "$DATA/voc/pascal_2007/test" | wc -l) test images"

K="$DATA/kitti"
for z in data_tracking_label_2 data_tracking_oxts; do
  if [ ! -d "$K/training/$( [ $z = data_tracking_label_2 ] && echo label_02 || echo oxts )" ]; then
    curl -sSL --retry 4 -o "$K/$z.zip" "https://s3.eu-central-1.amazonaws.com/avg-kitti/$z.zip"
    (cd "$K" && python3 -m zipfile -e "$z.zip" . && rm -f "$z.zip")
  fi
done
python3 - "$K" <<'EOF'
import sys, os
sys.path.insert(0, "scripts/detector")
import kitti
root = sys.argv[1]
for split in ("development", "validation", "test"):
    d = kitti.load(root, split)
    print("kitti", split, len(d["frames"]), "frames", len(d["gt"]), "gt rows")
EOF
