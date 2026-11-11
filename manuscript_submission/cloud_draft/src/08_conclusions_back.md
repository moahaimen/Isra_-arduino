# Conclusions <<sec:conclusions>>

This article examined, by simulation, a two-point active self-test for a sensor interface that consists of a sensor, an analog front-end and an analog-to-digital converter. A two-level reference at the AFE input and a second one at the ADC input make the static parameters of the two stages separately identifiable, which a passive observation of the output cannot do. Two conditions have to be met for this to work in practice, and the study quantified both. The reference levels must be measured, because an unmonitored amplitude error is read as an ADC gain fault; with a monitor channel, a gain error of the monitor of up to ±5% was tolerated. The transient must be described independently of the sampling phase; a first-order fit with a free edge time reduced the phase spread of the layer macro-F1 from {{ARM_bh_R1_RANGE}} to at most {{G_PRR_MAX}}, and the ablation attributed this to the descriptors and not to training with randomized phases.

Under a protocol that was frozen before the validation data were generated, the layer macro-F1 of the primary method was {{ARM_bh_PRR_L}} in the behavioral domain and {{ARM_sp_PRR_L}} in the ngspice domain, the loss between the domains on a matched grid was {{E_DROP}} (95% CI {{CI:E_DROP_LO:E_DROP_HI}}), and the AFE–ADC cross-confusion stayed below {{C_MAX}} at reference amplitudes of ±20%. These scores describe a method that localizes faults of the electronics and is insensitive to two nuisance variables. They do not describe a fault detector: most healthy records were assigned to a fault layer, and sensor bias and sensor gain faults, which the references do not excite, were not recognized.

The next step is a hardware experiment, which is needed to establish whether the first-order description of the transient, the assumed monitor and the tolerance of the classifier hold for a real circuit. Further work should also train with component tolerances and several reference amplitudes, add a detection stage with thresholds on the physical descriptors, and examine reference levels that exercise the upper range of the converter.

%%BACKMATTER

**Supplementary Materials:** The following supporting information is provided with this article: Table S1: AFE and ADC recall and AFE–ADC cross-confusion for all reference conditions; Table S2: Per-class recall of all variants; Table S3: Pooled confusion matrices of the primary method; Table S4: Paired comparisons of the primary method with the baselines; Table S5: Scores of the primary method for each data set; Table S6: Layer macro-F1 and retention at reference amplitudes of ×0.8 and ×1.2; Table S7: Simulation counts, run times and software versions.

%%AUTHOR_DECLARATIONS_1

**Institutional Review Board Statement:** Not applicable.

**Informed Consent Statement:** Not applicable.

%%AUTHOR_DECLARATIONS_2

**Acknowledgments:** During the preparation of this manuscript, the authors used Claude (Anthropic) for the purposes of drafting and editing the text, searching and checking the literature, regenerating the figures and tables from the saved result files, and assembling the document. The authors have reviewed and edited the output and take full responsibility for the content of this publication.

%%AUTHOR_DECLARATIONS_3

%%ABBREVIATIONS
ADC | Analog-to-digital converter
AFE | Analog front-end
BIST | Built-in self-test
CI | Confidence interval
MLP | Multilayer perceptron
MUX | Multiplexer
RSS | Residual sum of squares

%%APPENDIX A

The 20 entries of the descriptor vector are listed in {{AT:descriptors}}. The variant R1 replaces entries 16–20 by the fractions of the step that are reached 2, 5, 10, 20 and 30 samples after the nominal edge.

[[ATAB:descriptors]]
