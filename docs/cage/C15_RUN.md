# C1.5 Tinyissimo host workload measurement

This is an instrumentation-only branch. It does not change CAGE or interpret modeled C1 results as real measurements.

## Requirements
Use the pinned TinyissimoYOLO environment prepared by `scripts/detector/setup.sh` and a real existing Tinyissimo `.pt` checkpoint. Use **only permitted development/validation images**. Never pass the locked test directory.

## Run
```bash
source /home/claude/ext/tiy/bin/activate
python scripts/cage/c15_tinyissimo_profile.py \
  --checkpoint /ABS/PATH/TO/EXISTING/best.pt \
  --images /ABS/PATH/TO/ALLOWED/VALIDATION/IMAGES \
  --output /tmp/c15_natural.csv --device cpu --warmup 5 --repeats 5
```

The script fails loudly if the installed Ultralytics raw tensor layout does not match `[B, 4+nc, N]`. Inspect the pinned version and adjust only if required; never fabricate or reinterpret the tensor layout. First run a smoke test on one permitted image.

The `.summary.json` file reports **natural-image host** variation only. It cannot establish adversarial amplification, Portenta latency or measured energy. The raw-candidate count is a proxy based on confidence filtering, not an internal NMS comparison count.

## Decision sequence
1. Smoke test the pinned environment on one permitted image.
2. Run on permitted natural validation frames; retain per-image distributions, forward and NMS separately.
3. If postprocessing cost varies materially, separately design candidate-amplifying input tests using the same frozen checkpoint and parameters.
4. Compare measured clean and attack-like distributions. Only then consider whether a new C1 simulation based on measured work is justified.

Do not claim C1.5 GO/NO-GO from a script alone.
