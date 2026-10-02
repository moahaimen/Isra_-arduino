# R3 M4 computational complexity

Source: `firmware/host_check_r3.cpp` (compiled host build with the float feature extractor; sizes are
`sizeof` of the actual classes, i.e. static RAM before stack) and `frame_features.op_count_per_frame()`.
**No M4 execution time, power or cycle count has been measured.**

| component | static memory | worst-case work per frame |
|---|---|---|
| frame features (basic + gain-compensated front end, 256-bit dHash, 64-bit dHash, motion cells, foreground mask) | 76,804 B (float state) | about 1.45 x 10^5 simple integer/float operations (`op_count_per_frame`) |
| thumbnail 24x8 | 192 B per stored frame | 3,072 additions |
| UGS scheduler (accumulator, 64-sample background window, 8 content regions) | 1,640 B | one insertion-sorted median and one MAD (<= 2 x 64^2/2 compares), <= 8 connected components (iterated 1-cell dilation of a 48-bit mask), 8 x 8 popcount overlaps |
| UGS gate history 256 / 64 frames | 53,616 B / 13,680 B | per frame: 1 median (histogram, 192 + 256 ops) + up to history x 192 block compares (49,152 for 256; the cached median avoids recomputation) + previous-frame compare |
| total, history 64 | about 92 KB | dominated by the feature state |

Whether this fits the M4's usable RAM on the Portenta H7 has NOT been checked against the actual
linker memory map (the M4 shares RAM regions with the M7 and the camera buffers); this must be done
before any deployment claim. The Gate-C parameters were tuned with history 256; a history-64 equivalent
(6.4 s at 10 Hz) has NOT been evaluated and could change the replay window.
Hash cost: dHash-256 = 256 comparisons; thumbnail = 3,072 adds; replay check = block-compare loop above.
C++ / Python parity: `tests/test_r2.py::FrameFeatureTests` (features, bit-identical in double) and
`tests/test_r3.py::ThumbParity` (thumbnail). Scheduler and gate have C++ unit tests
(`tests/cpp/unit_tests.cpp`, `firmware/host_check_r3.cpp`); there is no separate Python reference
implementation of the scheduler or gate (single C++ implementation used by both simulator and firmware).
