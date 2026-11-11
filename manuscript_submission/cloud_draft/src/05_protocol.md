# Simulation Design, Evaluation Protocol and Statistical Analysis <<sec:protocol>>

## Behavioral Model <<sec:behavioral>>

The behavioral model generates records at 1 kS/s from the operating-condition and fault distributions of {{T:params}} and {{T:faults}}. The first-order AFE is discretized exactly for piecewise-constant inputs. In the sampling interval that contains a reference edge, the state is advanced in two steps, first toward the old input level for the duration $\psi T$ and then toward the new level for the remaining $(1 - \psi)T$:

$$v_\mathrm{mid} = x_{i-1} + \left(v_{i-1} - x_{i-1}\right)\mathrm{e}^{-\psi T/\tau}, \qquad v_i = x_i + \left(v_\mathrm{mid} - x_i\right)\mathrm{e}^{-(1-\psi)T/\tau},$$ <<eq:twostep>>

where $x_{i-1}$ and $x_i$ denote the input levels before and after the edge, including gain and offset. For $\psi = 0$ this reduces to the usual zero-order-hold update. Converter noise of 2.5 mV rms and 12-bit quantization are applied to the output.

## ngspice Model <<sec:ngspice>>

The second domain is a netlist-level model simulated with ngspice [@ngspice]. Every test record is a separate transient simulation of the circuit of {{F:arch}}. The sensor waveform, the reference levels and the switch controls are piecewise-linear sources; the reference and control edges have a duration of 1 µs and are placed at the edge time defined in {{S:sequence}}. The multiplexers are voltage-controlled switches with an on-resistance of 0.5 Ω and an off-resistance of 1 MΩ. The AFE is an RC stage with behavioral gain and offset elements, and a clamp at the ADC input represents the clipping fault. Noise of 0.5 mV rms is added at the amplifier input and on each reference rail, in addition to the converter noise and quantization, which are applied to the ngspice output with the same random stream as in the behavioral model. The two domains are thereby paired record by record: they share the operating condition, the fault, the tolerances, the monitor error and the converter noise.

It is important to be clear about what this second domain is. Both models describe the same idealized circuit, a first-order RC stage followed by an affine converter. Without the additional noise, their outputs agreed to between {{DEV_AGREE_MIN}} and {{DEV_AGREE_MAX}} mV (mean root-mean-square difference per edge phase) on the development seed. The ngspice domain therefore tests whether the method survives a different numerical implementation of the edge timing, finite switch resistances and additional noise sources. It does not contain an operational-amplifier model, charge injection, reference settling, leakage or temperature effects, and it is not a substitute for a hardware experiment.

## Data Sets, Splits and Test Grids <<sec:data>>

{{T:protocol}} summarizes the evaluation protocol. Three data sets were generated with new random seeds. Each contains {{TOTAL_COND}} operating conditions, and each operating condition is simulated with all nine classes. An operating condition fixes the sensor baseline, the signal amplitude and frequency, the sensor noise, the AFE gain and the AFE time constant. The split into training, validation and test data is made by operating condition ({{TRAIN_COND}}, {{VAL_COND}} and {{TEST_COND}} conditions), so that no operating condition contributes records to more than one subset. This grouping matters: records that share an operating condition share most of their waveform, and a random split of records would let the classifier recognize test conditions that it has seen in training. The {{VAL_COND}} validation conditions were set aside by the protocol and were not used by any model.

The training data use the nominal reference amplitude and contain no component tolerances. The test data differ from the training data in three respects. They contain the component tolerances of {{T:params}}, drawn anew for every record. The reference amplitude is scaled by a common factor of 0.8, 0.9, 1.0, 1.1 or 1.2 in the behavioral domain and of 0.8, 1.0 or 1.2 in the ngspice domain. Finally, every amplitude is tested at five edge phases, $\psi$ = 0, 0.25, 0.5, 0.75 and 0.999. A test cell, that is, one combination of domain, amplitude and phase, contains {{TEST_ROWS}} records per data set. The ngspice domain required {{SPICE_RUNS_SEED}} simulations per data set and {{SPICE_RUNS_TOTAL}} in total.

Because the two domains use different amplitude grids, scores pooled over all amplitudes of a domain are not directly comparable between domains. Comparisons between the domains are made only on the matched grid of the three amplitudes that both domains contain.

[[TAB:protocol]]

## Compared Variants and Controls <<sec:variants>>

{{T:variants}} lists the variants. The proposed method, PRr, combines the phase-robust descriptors of {{S:transient}} with training data in which each record has a random edge phase. It was designated as the primary method in the protocol. Three variants isolate the two ingredients: R1 uses the fixed-sample transient descriptors and is trained at $\psi = 0$; R1r uses the same descriptors with randomized training phases; and PR uses the phase-robust descriptors but is trained at $\psi = 0$. A0 is the descriptor set of the first stage of the project and serves, together with passive and one-point versions of the test, as a baseline.

PRrM adds ngspice records to the training data of PRr. It is a secondary variant. It was included to see whether exposure to the second domain helps, and its results are reported, but the protocol did not allow it to decide the outcome of the validation.

Every variant is trained separately for each reference condition: with the true reference levels ("known reference") and with monitored levels for each error bound $E$ of 0, ±1%, ±2% and ±5%, where the training data contain monitor errors drawn from the same bound as the test data. The bound is a specification of the monitor hardware and is known when the classifier is designed, so this matched training does not use information from the test set. The no-monitor control takes the PRr classifier trained with known reference levels and gives it, at test time, the nominal levels although the amplitude has changed. It was evaluated in the behavioral domain only.

[[TAB:variants]]

## Performance Measures <<sec:measures>>

The primary measure is the macro-averaged F1 score of the four-class layer classifier (layer macro-F1), the unweighted mean of the per-class F1 scores [@sokolova2009]. The fault macro-F1 is the corresponding score of the nine-class classifier. Balanced accuracy, the unweighted mean of the per-class recalls, is reported as a second summary that is not inflated by unequal class sizes [@brodersen2010]; the layer classes are unequal because one, three, two and three of the nine simulated classes belong to the healthy, sensor, AFE and ADC layers.

Three derived quantities are used. The retention at a given test condition is the layer macro-F1 at that condition divided by $N$, the layer macro-F1 of PRr with known reference levels at nominal amplitude in the same domain; it expresses how much of the nominal performance survives a disturbance. The AFE–ADC cross-confusion is the fraction of all records with an AFE or an ADC fault that the layer classifier assigns to the other of these two layers; it is the direct measure of the property that the two-point test is designed to provide. The phase spread is the difference between the largest and the smallest layer macro-F1 among the five edge phases.

When a score is pooled over phases or amplitudes, the confusion matrices of the pooled cells are summed before the score is computed. Reported scores are means over the three data sets, each of which is the mean over the two initialization seeds.

## Frozen Protocol, Acceptance Criteria and Statistical Analysis <<sec:stats>>

The descriptor definitions, the variants, the test grids, seven acceptance criteria with their thresholds, and the rule that combines them into a decision were written into a protocol file dated 14 October 2026, together with hash values of the source files, before the three validation data sets were generated. Development and debugging used a separate seed ({{DEV_SEED}}), which also provides the illustrative records of {{F:timing}} and {{F:signatures}}. The protocol was fixed internally in this way; it was not deposited in a public registry, and we therefore do not describe the study as preregistered.

The criteria apply to the primary method; they are listed with their outcomes in {{S:res_overall}}. In brief, they require a retention of at least {{A_THRESH}} at reference amplitudes of ×0.8 and ×1.2 (A), superiority over the baselines (B), an AFE–ADC cross-confusion below {{C_THRESH}} (C), a retention of at least {{D_THRESH}} with a monitor error bound of ±5% (D), a loss of at most {{E_THRESH}} in layer macro-F1 from the behavioral to the ngspice domain (E), a confidence interval that excludes zero for every claimed improvement (F), and a phase spread of at most {{G_THRESH}} (G).

Differences between two variants, or between two domains, are evaluated with a paired cluster bootstrap [@efron1993; @field2007]. The resampling unit is the operating condition: the {{TEST_COND}} test conditions of a data set are resampled with replacement, all records of a selected condition are kept together, and both scores of the comparison are recomputed on the same resample, which preserves the pairing. Resampling single records would treat the nine classes, the amplitudes and the phases of one operating condition as independent observations and would produce intervals that are too narrow. For each data set, {{N_BOOT}} resamples are drawn; the reported 95% confidence interval is that of the mean of the three per-data-set differences. The intervals express the uncertainty due to the finite number of test conditions. They do not express the variability between data sets or between training runs, for which only three data sets and two initializations are available.

## Software and Reproducibility <<sec:repro>>

According to the environment record that was generated with the original runs, the simulations and the training used Python 3.12.12, NumPy 2.2.6 [@harris2020], SciPy 1.16.3 [@virtanen2020], scikit-learn 1.7.2 [@pedregosa2011] and ngspice-47 on macOS.

The evidence on which this article rests consists of the frozen protocol, the result files and the predicted class of every test record for every model. All figures, tables and statistics of this article were regenerated from these saved predictions and result files, and {{N_RECOMPUTED}} summary values were recomputed from the predictions and agreed with the stored summaries. This regeneration used a different software environment (Python 3.13, NumPy 2.5.3, pandas 3.0.5 and Matplotlib 3.11.2) and involves no simulation and no training. The simulator, the descriptor extraction and the training code, and the simulated waveforms, are not part of the archived evidence package. Consequently, the simulations and the training could not be rerun for this article, and the implementation details given in {{S:proc}} and in this section are reported from the project documentation.
