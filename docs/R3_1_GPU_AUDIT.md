# R3.1 Gate A1 — GPU / detector-ceiling audit

**Status: BLOCKED (no GPU). No full TinyissimoYOLO training was run. No detector-ceiling claim is made.**

## What was checked
* `nvidia-smi` is absent; `torch.cuda.is_available()` is false; the container has 4 CPU cores, 15 GB RAM.
  (`read_documentation environment.*` pages describe CPU-only environments; no GPU option is configured for this session.)
* `scripts/detector/tinyissimo/train_full_gpu.sh` was audited against the upstream recipe
  (ETH-PBL/TinyissimoYOLO @ 19bea4b, `a_train_export.py`): tinyissimo-v8 scale `b` (839,392 parameters at nc=20), 256x256, SGD,
  1000 epochs, batch 512, Ultralytics 8.1.29 default hyper-parameters. The script was corrected (R3.1) to:
  two stages (VOC07+12 pretraining with checkpoint selection on VOC07 *val*; KITTI-tile adaptation selected on the detector-validation
  sequences 0013/0018), a CUDA guard that refuses a knowingly inadequate CPU run, and a provenance record (GPU, CUDA/torch versions,
  upstream commit, checkpoint hashes, wall time).
  VOC07 *test* is never used for any choice; no R3 validation or test frame enters training.
* The code path was exercised with `SMOKE=1` (CPU, 1 epoch, 1 % of the data, `*_smoke` directories):
  both stages ran end-to-end including validation and checkpoint hashing (`results/r3_1/detector/smoke_train_record.json`).
  Stage 1 took 656 s wall on the shared 4-core CPU for 1 epoch of 1 % of the data (plus a full validation pass). This verifies the
  code path only; **the smoke weights carry no accuracy information and are not used anywhere.**

## Why no CPU rerun
The prescribed schedule is 1000 epochs over 11,540 images (stage 1) plus a 200-epoch stage 2. From the measurement above, a single epoch
over the full data is of the order of hours on this CPU, i.e. the schedule would need months. A shortened CPU schedule would produce the
same inadequate detector as R3's 30/80-epoch CPU checkpoints, which is exactly what the task forbids rerunning knowingly.

## Consequence for the paper
* The MCU-feasible detector ceiling (O1) is **unresolved**. The R3 MCU-class detector (EfficientDet-Lite0 INT8 tiles / cascade) and the
  CPU-trained TinyissimoYOLO checkpoints remain the only evidence; the latter are documented as inadequate (R2/R3 reports).
* All system-level results in R3.1 are therefore "given the Lite0/Lite2 tiled cascade as M7 detector", not claims about TinyissimoYOLO.
* Remaining experiment: run `SMOKE=0 bash scripts/detector/tinyissimo/train_full_gpu.sh` on a CUDA GPU (est. a few GPU-hours on a
  single modern GPU; not measured here), then evaluate on the KITTI detector-validation sequences before any pipeline use.
