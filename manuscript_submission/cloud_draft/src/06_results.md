# Results <<sec:results>>

All results in this section are simulation results. Unless stated otherwise, they refer to the primary method PRr with monitored reference levels and an error bound $E$ of ±2%, which the protocol defines as the main reference condition.

## Overall Performance and Acceptance Criteria <<sec:res_overall>>

{{T:main}} gives the summary scores. Pooled over its own test grid, the layer macro-F1 of PRr is {{ARM_bh_PRR_L}} in the behavioral domain and {{ARM_sp_PRR_L}} in the ngspice domain, and the fault macro-F1 is {{ARM_bh_PRR_F}} and {{ARM_sp_PRR_F}}. The two domains are pooled over different amplitude grids, so the difference between these values is not the transfer loss; that quantity is evaluated on the matched grid in {{S:res_transfer}}. The three data sets agree closely: their layer macro-F1 values are {{X_SEED_bh_1}}, {{X_SEED_bh_2}} and {{X_SEED_bh_3}} in the behavioral domain and {{X_SEED_sp_1}}, {{X_SEED_sp_2}} and {{X_SEED_sp_3}} in the ngspice domain (Table S5).

[[TAB:main]]

A layer macro-F1 near 0.66 is a modest score, and its composition matters more than its value. The per-class F1 scores of the layer classifier in the behavioral domain are {{X_F1L_bh_AFE}} for the AFE, {{X_F1L_bh_ADC}} for the ADC, {{X_F1L_bh_SENSOR}} for the sensor and {{X_F1L_bh_HEALTHY}} for the healthy class. The macro average gives the healthy class a weight of one quarter, and its low score pulls the average down. This also explains why the fault macro-F1 is slightly higher than the layer macro-F1 although the fault classifier solves a finer task: among the nine fault classes, five have F1 scores between {{X_F1F_bh_STRONG_MIN}} and {{X_F1F_bh_STRONG_MAX}}, so that the poorly recognized classes carry a smaller share of the average. The per-class behavior is examined in {{S:res_classes}}.

All acceptance criteria of the frozen protocol were met ({{T:criteria}}), and the outcome defined by the protocol's decision rule was therefore positive. The criteria are thresholds that were fixed in advance to guard against a favorable reading of the results after the fact. Meeting them means that the robustness properties hold to the stated degree in the simulated conditions; it does not mean that the diagnosis is accurate in an absolute sense.

[[TAB:criteria]]

## Sensitivity to the Sampling Phase <<sec:res_phase>>

{{F:phase}} and {{T:perphase}} show the layer macro-F1 as a function of the edge phase. With the fixed-sample descriptors (R1), which were trained at $\psi = 0$, the score falls steadily as the edge moves away from the sampling instant, from {{ARM_bh_R1_P000}} at $\psi = 0$ to {{ARM_bh_R1_P999}} at $\psi = 0.999$ in the behavioral domain and from {{ARM_sp_R1_P000}} to {{ARM_sp_R1_P999}} in the ngspice domain. The phase spread is {{ARM_bh_R1_RANGE}} and {{ARM_sp_R1_RANGE}}. With PRr the corresponding spreads are {{ARM_bh_PRR_RANGE}} and {{ARM_sp_PRR_RANGE}}, and over the four cases that criterion G covers (known and monitored reference in both domains) the spread lies between {{G_PRR_MIN}} and {{G_PRR_MAX}}.

Two observations help to interpret these numbers. At $\psi = 0$, where the test phase equals the training phase of R1, the two descriptor sets perform similarly ({{ARM_bh_R1_P000}} against {{ARM_bh_PRR_P000}} in the behavioral domain). The fixed-sample descriptors are therefore not much poorer descriptors as such; they describe a quantity that changes with the phase. Second, the loss of R1 is nearly the same in both domains, which indicates that it is a property of the descriptors and not of one simulator. The residual trend of PRr, a decrease of about {{ARM_bh_PRR_RANGE}} from the first to the last phase in the behavioral domain, shows that the descriptors are not perfectly phase-independent in the presence of noise and quantization, as expected from the assumptions listed in {{S:transient}}. Panel (c) of {{F:phase}} shows the mechanism at the level of the descriptors, on records of the development seed: the fixed-sample descriptors shift with the phase by a large fraction of their spread across records, and the proposed descriptors do not.

[[FIG:phase]]

[[TAB:perphase]]

## Ablation: Descriptors versus Phase-Randomized Training <<sec:res_ablation>>

Robustness to the edge phase can be sought in two ways: by measuring quantities that do not depend on the phase, or by showing the classifier many phases during training and letting it learn the dependence. The four variants R1, R1r, PR and PRr separate these two routes ({{F:ablation}}, {{T:ablation}}).

Replacing the descriptors alone (PR against R1) raises the pooled layer macro-F1 by {{ATT_bh_DESC}} in the behavioral domain and by {{ATT_sp_DESC}} in the ngspice domain. Randomizing the training phase alone (R1r against R1) raises it by {{ATT_bh_RAND}} and {{ATT_sp_RAND}}. Randomization thus recovers a large part of the loss, but not all of it: the phase spread of R1r is still {{ARM_bh_R1R_RANGE}} in the behavioral domain, against {{ARM_bh_PR_RANGE}} for PR, and the phase-robust descriptors retain an advantage of {{ATT_bh_DESC_GIVEN_RAND}} (95% CI {{CI:ATT_bh_DESC_GIVEN_RAND_LO:ATT_bh_DESC_GIVEN_RAND_HI}}) over the fixed-sample descriptors when both are trained with random phases. Once the descriptors are phase-robust, randomizing the training phase adds nothing that the data can resolve: the difference between PRr and PR is {{ATT_bh_RAND_GIVEN_DESC}} (95% CI {{CI:ATT_bh_RAND_GIVEN_DESC_LO:ATT_bh_RAND_GIVEN_DESC_HI}}) in the behavioral domain and {{ATT_sp_RAND_GIVEN_DESC}} (95% CI {{CI:ATT_sp_RAND_GIVEN_DESC_LO:ATT_sp_RAND_GIVEN_DESC_HI}}) in the ngspice domain, and both intervals include zero.

The conclusion is that the robustness of the proposed method comes from the measurement and not from the training procedure. The protocol had designated PRr, with randomized training, as the primary method before this was known, and it is reported as such. On the evidence of the ablation, the simpler variant PR, trained at a single phase, performs equally well.

The mixed-domain variant PRrM scores {{ATT_bh_MIXED}} (95% CI {{CI:ATT_bh_MIXED_LO:ATT_bh_MIXED_HI}}) higher than PRr in the behavioral domain and {{ATT_sp_MIXED}} (95% CI {{CI:ATT_sp_MIXED_LO:ATT_sp_MIXED_HI}}) higher in the ngspice domain. This gain should not be attributed to the circuit-level data as such. The ngspice training records contain component tolerances and the additional noise, which the behavioral training records do not, so the comparison confounds the simulation domain with exposure to tolerances during training. The improvement appears in both test domains, which suggests that the exposure to tolerances is the more likely cause, but the experiment does not separate the two.

[[FIG:ablation]]

[[TAB:ablation]]

## Reference Amplitude and Monitor Error <<sec:res_amp>>

{{F:refamp}} and {{T:refamp}} show the layer macro-F1 against the actual reference amplitude. With known reference levels, PRr scores {{AMP_bh_PRr_known_layer_x10}} at nominal amplitude, {{AMP_bh_PRr_known_layer_x08}} at ×0.8 and {{AMP_bh_PRr_known_layer_x12}} at ×1.2 in the behavioral domain. The classifiers were trained at nominal amplitude only, so the amplitudes away from nominal are an extrapolation, and the decrease at ×0.8 is the largest effect in the table. The smallest retention among the cases of criterion A is {{A_MIN_RET}} ({{A_MIN_RET_WHERE}}), against a threshold of {{A_THRESH}} (Table S6).

Replacing the known levels with monitored levels changes little. With an error bound of ±5%, the retention is at least {{D_MIN_RET}} ({{D_MIN_RET_WHERE}}), against a threshold of {{D_THRESH}}. This is consistent with the analysis of {{S:monitor}}: a monitor gain error of this size displaces the apparent ADC gain by less than the smallest simulated ADC gain fault, and the classifier, which is trained with the same error bound, has seen the resulting spread. The variant with $E$ = ±2% scores somewhat higher than the variant with known levels at several amplitudes. The monitored variants are separately trained models whose training data contain the monitor noise, and a regularizing effect of that noise is a possible explanation, but it was not tested and we do not draw a conclusion from this difference.

The no-monitor control shows what the monitor is for. The same PRr classifier that scores {{NOMON_K_x08}} at ×0.8 and {{NOMON_K_x12}} at ×1.2 with known levels scores {{NOMON_U_x08}} and {{NOMON_U_x12}} when it is given the nominal levels instead. At nominal amplitude the two coincide by construction. The mechanism is the one predicted by {{EQ:mapping}}: the amplitude change appears as a change of the ADC gain, and the classifier assigns the records to the ADC layer. At ×0.8 and ×1.2 taken together, the recall of the healthy class falls to {{RL_bh_UNMON_HEALTHY}} and that of the sensor layer to {{RL_bh_UNMON_SENSOR}} in this control, while the recall of the ADC layer is {{RL_bh_UNMON_ADC}}, because most records are called ADC faults. The control was run in the behavioral domain only.

[[FIG:refamp]]

[[TAB:refamp]]

## Separation of AFE and ADC Faults and Per-Class Behavior <<sec:res_classes>>

The purpose of the two-point test is to separate faults of the AFE from faults of the ADC. {{F:separation}} shows that it does so within the simulated conditions. With known or monitored reference levels, at ×0.8 and ×1.2, the AFE–ADC cross-confusion does not exceed {{C_MAX}} ({{C_MAX_WHERE}}), against a limit of {{C_THRESH}}; the AFE recall is at least {{C_MIN_AFE}} and the ADC recall at least {{C_MIN_ADC}} over all these cases in both domains (Table S1). The cross-confusion is larger at ×1.2 than at ×0.8 in every case, which again reflects the extrapolation away from the training amplitude. Without monitoring, the cross-confusion rises to {{SEPX_bh_assumed_a80_X}} at ×0.8 and {{SEPX_bh_assumed_a120_X}} at ×1.2, and the AFE recall falls to {{SEPX_bh_assumed_a80_AFE}} and {{SEPX_bh_assumed_a120_AFE}}.

[[FIG:separation]]

The per-class recall of the fault classifier ({{F:recall}}; Table S2) divides the nine classes into two groups. Five classes are recognized reliably in the behavioral domain: ADC offset ({{RF_bh_PRR_ADC_OFFSET}}), sensor noise ({{RF_bh_PRR_SENSOR_NOISE}}), AFE bandwidth ({{RF_bh_PRR_AFE_BANDWIDTH}}), ADC gain ({{RF_bh_PRR_ADC_GAIN}}) and AFE offset ({{RF_bh_PRR_AFE_OFFSET}}). Four classes are not: ADC clipping ({{RF_bh_PRR_ADC_CLIPPING}}), sensor gain ({{RF_bh_PRR_SENSOR_GAIN}}), healthy ({{RF_bh_PRR_HEALTHY}}) and sensor bias ({{RF_bh_PRR_SENSOR_BIAS}}). The ngspice values follow the same pattern.

The four weak classes are confused mainly with one another. In the behavioral domain, healthy records are assigned to the ADC clipping class in {{PCT:X_FH2CLIP_bh}} of the cases, to the sensor gain class in {{PCT:X_FH2SG_bh}} and to the sensor bias class in {{PCT:X_FH2SB_bh}}, and ADC clipping records are assigned to the healthy class in {{PCT:X_FCLIP2H_bh}} of the cases (Table S3). This pattern has a physical reading that follows from {{S:twopoint}}. Sensor bias and sensor gain faults are not excited by either reference. They change the level and the amplitude of the sensor signal by amounts that lie within the spread of these quantities across the simulated operating conditions ({{T:params}} and {{T:faults}}), so that a record with such a fault resembles a healthy record under a different operating condition. A clipping fault is visible only if the signal reaches the clipping level. For the simulated gain range the second AFE plateau reaches about 2.1 to 2.7 V, whereas the clipping level lies between about 2.4 and 3.1 V, so that in a part of the records the fault is not exercised by the test. This reading is consistent with the confusion pattern and with {{F:signatures}}, but it was not verified by a dedicated experiment.

At the layer level the consequence is severe for one class. The recall of the healthy layer is {{RL_bh_PRR_HEALTHY}} in the behavioral and {{RL_sp_PRR_HEALTHY}} in the ngspice domain: of the healthy records, {{PCT:X_H2S_bh}} are assigned to the sensor layer and {{PCT:X_H2D_bh}} to the ADC layer in the behavioral domain. Conversely, {{PCT:X_MISS_bh}} of the faulty records are called healthy. The layer classifier therefore cannot be used to decide whether a fault is present. Its output is informative about the location of a fault of the electronics: the recall is {{RL_bh_PRR_AFE}} for the AFE layer and {{RL_bh_PRR_ADC}} for the ADC layer, with the low cross-confusion reported above. The assignment of healthy records shifts with the reference amplitude. With known levels, {{PCT:X_K80_H2D}} of the healthy records are assigned to the ADC layer at ×0.8, and {{PCT:X_K120_H2S}} to the sensor layer at ×1.2.

[[FIG:recall]]

## Comparison with Baselines <<sec:res_baselines>>

{{T:baselines}} compares PRr with simpler forms of the test at the two extreme amplitudes. A passive observation of the sensor signal reaches a layer macro-F1 of {{BASEF1_passive_a80}}, which is close to the value of about 0.24 that a uniformly random assignment would give for the class proportions of this study; this is the empirical counterpart of the identifiability argument of {{S:observability}}. A one-point test with the proposed descriptors, using only the AFE reference or only the ADC reference, reaches {{BASEF1_afe_only_PRr_a80}} and {{BASEF1_adc_only_PRr_a80}} at ×0.8. Each single reference localizes the faults that it excites and leaves the others ambiguous, and the two-point test exceeds both by more than 0.1 with intervals that exclude zero. The baselines that use the descriptor set A0 are far lower away from nominal amplitude. Over the 70 comparisons that criterion B prescribes, the smallest lower confidence bound of the difference in favor of PRr is {{B_MIN_CI}} ({{B_MIN_CI_WHERE}}; Table S4).

[[TAB:baselines]]

## Transfer from the Behavioral Model to ngspice <<sec:res_transfer>>

The transfer test asks whether a classifier that was trained on behavioral data works on ngspice data. On the matched grid, the behavioral-trained PRr classifier scores {{E_PRIMARY_BB}} on behavioral data and {{E_PRIMARY_BS}} on ngspice data. The difference, computed from the unrounded scores, is {{E_DROP}} with a 95% confidence interval of {{CI:E_DROP_LO:E_DROP_HI}}, against a limit of {{E_THRESH}}. The interval includes zero, and the same holds for every other reference condition ({{T:transfer}}, {{F:transfer}}).

This result needs to be read together with the description of the ngspice domain in {{S:ngspice}}. The two models implement the same idealized circuit and agree closely without noise, so a small loss is what should be expected once the descriptors no longer depend on the numerical handling of the edge. The test confirms that they do not. It does not show that the classifier would transfer to hardware.

In an earlier stage of this project, a version of the method with the fixed-sample descriptors had lost {{PREV_DROP}} (95% CI {{CI:PREV_DROP_LO:PREV_DROP_HI}}) between the two domains. That stage used a single edge placement in each simulator, a different amplitude grid and different random seeds, and its result files are not part of the evidence package of this article. The value is therefore reported as the historical motivation for the present work, and the difference between the two stages is not a controlled estimate of the effect of the descriptors. The controlled evidence is the phase sensitivity of R1 within the present protocol ({{S:res_phase}}) and the ablation ({{S:res_ablation}}).

[[TAB:transfer]]

[[FIG:transfer]]

## Model Size and Computation <<sec:res_cost>>

{{T:cost}} lists the size and the measured computation times. The descriptor extraction took {{DESC_MS_PR}} ms per record for the phase-robust descriptors, against {{DESC_MS_R1}} ms for the fixed-sample descriptors, and the classification {{MLP_US}} µs per record in batched evaluation. These times were measured in Python on a desktop computer (Table S7) and say nothing quantitative about a microcontroller. What carries over is the operation count: one classification requires {{MACS_LAYER}} multiply–accumulate operations for the layer network, and the grid search evaluates a fixed number of candidate parameter pairs on 60 samples. No measurement of execution time, memory or energy on an embedded target was made.

[[TAB:cost]]
