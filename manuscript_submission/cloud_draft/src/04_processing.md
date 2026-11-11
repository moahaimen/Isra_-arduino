# Calibration, Transient Descriptors and Classification <<sec:proc>>

{{F:pipeline}} summarizes the processing of a record. The design follows from the analysis of {{S:arch}}: the static parameters are estimated from the settled plateaus with the monitored levels, the dynamic parameter is estimated from the transient in a way that does not depend on the edge phase, and only then is a classifier applied.

[[FIG:pipeline]]

## Settled-Plateau Calibration <<sec:plateau>>

Each plateau contains $L = 60$ samples. The first 30% of every plateau, a guard of 18 samples that was fixed before the validation, is discarded, and the remaining samples are averaged. For a plateau that starts at sample $n_k$,

$$m_k = \frac{1}{L - L_\mathrm{g}} \sum_{n = n_k + L_\mathrm{g}}^{n_k + L - 1} y[n], \qquad L_\mathrm{g} = \lceil 0.3\,L \rceil = 18,$$ <<eq:plateau>>

and the values $a_k$ are obtained in the same way from $y_\mathrm{c}$. The guard has two purposes. It keeps the samples that are most affected by the transient, and therefore by the edge phase, out of the static estimates, and it makes these estimates independent of the transient descriptors that are computed separately.

The guard does not guarantee that the plateau has settled. For a first-order response, the average over the retained samples still contains a fraction of the step that depends on $\tau$; for the slowest healthy AFE in the simulation ($\tau$ near 16 ms) this fraction is roughly one tenth. The gain estimate of {{EQ:afeest}} is therefore biased toward lower values by an amount that grows with $\tau$, and an AFE with reduced bandwidth shows a lower apparent gain and a higher apparent offset. Two additional descriptors make this visible to the classifier. The settling error of plateau $k$ compares the mean of its last six samples, $\bar{y}_{k}^\mathrm{tail}$, with the plateau value,

$$\varepsilon_k = \frac{\bar{y}_{k}^\mathrm{tail} - a_k}{\left| a_2 - a_1 \right|}, \qquad k = 1, 2,$$ <<eq:settle>>

and the residual noise of the plateaus is taken as the standard deviation of the retained samples after removal of a linear trend.

## Phase-Robust Transient Descriptors <<sec:transient>>

The transient of the second AFE plateau carries the information about the AFE bandwidth. The obvious descriptors, the fractions of the step reached 2, 5, 10, 20 and 30 samples after the edge, were used in an earlier stage of this project and are retained here as the comparison variant R1. They depend on the edge phase, because a fixed sample index corresponds to a settling time that varies by up to one sampling period, and for a time constant of about ten sampling periods this is a large part of the early response.

The proposed descriptors are estimated from the whole plateau. Let $n_2$ be the first sample of the second plateau, and let

$$d_j = y[n_2 - 1 + j] - y[n_2 - 1], \qquad j = 1, \dots, L,$$ <<eq:dj>>

be the response relative to the last sample before the step, at the times $u_j = jT$. The response is modeled as

$$d(u) = S\left(1 - \mathrm{e}^{-(u - t_\mathrm{e})/\tau}\right) \quad \text{for } u \ge t_\mathrm{e}, \qquad d(u) = 0 \quad \text{for } u < t_\mathrm{e},$$ <<eq:model>>

with three parameters: the span $S$, the time constant $\tau$ and the edge time $t_\mathrm{e}$. The edge time is the element that matters. An edge that occurs at phase $\psi$ corresponds to $t_\mathrm{e} = \psi T$, so that for a first-order AFE and an ideal step the model contains the true response for every phase, and the values of $S$ and $\tau$ that describe it do not depend on $\psi$.

The model is linear in $S$. For given $\tau$ and $t_\mathrm{e}$, with $g_j$ denoting the model response of unit span at $u_j$, the least-squares span and the residual sum of squares are available in closed form,

$$S^{\star} = \frac{\sum_j g_j d_j}{\sum_j g_j^2}, \qquad \mathrm{RSS} = \sum_j d_j^2 - S^{\star} \sum_j g_j d_j ,$$ <<eq:span>>

which is the variable projection approach to separable least-squares problems [@golub1973; @golub2003; @oleary2013]. The remaining two parameters are found by an exhaustive search over a fixed grid of 56 logarithmically spaced values of $\tau$ between 1 and 400 ms and seven values of $t_\mathrm{e}$ between $-0.25\,T$ and $1.25\,T$, followed by one local refinement on a 9 × 9 grid ($\tau$ within ±10% and $t_\mathrm{e}$ within ±0.2 $T$ of the best grid point). An exhaustive search was preferred to an iterative optimizer because it needs no starting value and no convergence test and has a fixed, data-independent cost. Its limitations are equally clear. The estimate is restricted to the range and the resolution of the grid, and when the fitted span is close to zero the normalization below is undefined. For that case ($|S^{\star}| < 10^{-4}$) a fallback is defined that replaces the fitted quantities by a multi-sample window area and sets the rise-time descriptors to zero. In {{DEV_FALLBACK_N}} records of the development seed the fallback was used {{DEV_FALLBACK_COUNT}} times; its use on the validation records was not logged.

With the normalized response $\rho_j = d_j / S^{\star}$ and the plateau duration $P = LT$, five descriptors are formed:

$$\frac{\tau}{P}, \qquad \frac{t_{50} - t_{10}}{P}, \qquad \frac{t_{90} - t_{50}}{P}, \qquad A = \frac{T}{P}\sum_{j=1}^{L}\left(1 - \rho_j\right), \qquad \eta = \frac{\sqrt{\mathrm{RSS}/L}}{\left|S^{\star}\right|},$$ <<eq:descr>>

where $t_q$ is the time at which the monotone envelope of $\rho_j$ crosses $q$ percent, obtained by linear interpolation and capped at the end of the window. The first descriptor is the fitted time constant. The two rise-time differences and the normalized area $A$ describe the shape of the measured response without assuming that it is first-order, and $\eta$ measures how well the first-order model fits, so that a response that is not first-order is flagged instead of being silently misdescribed. The fitted edge time itself is not used as a descriptor, because it encodes only the phase.

Two invariance properties follow from the construction, under assumptions that should be stated. First, all five descriptors are unchanged when $y$ is replaced by $\alpha y + \beta$, because $d_j$ removes $\beta$ and the normalization by $S^{\star}$ removes $\alpha$. They are therefore independent of the ADC gain and offset and of the reference levels, as long as the ADC is not clipping and quantization is neglected. Second, a shift of the edge within the sampling interval is absorbed by $t_\mathrm{e}$ in the fit and cancels in the rise-time differences, exactly for the continuous first-order response and approximately for its sampled, interpolated version. These are properties of the noise-free model. Their practical value was checked empirically before the validation: on the development seed, moving $\psi$ from 0 to 0.999 shifted the fixed-sample descriptor at two samples by up to {{DEV_RISE2_SHIFT}} standard deviations of its distribution across records, and none of the five proposed descriptors by more than {{DEV_PR_MAX_SHIFT}}. These shifts are shown together with the validation results in {{S:res_phase}}.

## Descriptor Vector <<sec:vector>>

The complete descriptor vector has 20 entries, which are listed in {{AT:descriptors}}: the ADC gain, offset and plateau noise; the AFE gain, offset, two settling errors and plateau noise; the five transient descriptors; five statistics of the sensor signal $\hat{x}$ in the intervals in which the sensor is connected (mean, standard deviation, high-frequency noise, peak-to-peak value and slope); and two saturation indicators (the maximum level and the fraction of samples at the top of the range). The variant R1 differs only in the five transient entries.

{{F:signatures}} shows how six of the descriptors respond to the nine classes in a set of illustrative records. The ADC gain and offset estimates react to ADC gain and offset faults and to nothing else, the AFE estimates react to AFE faults, the fitted time constant isolates the bandwidth fault, and the high-frequency noise of the sensor intervals isolates the sensor noise fault. The same figure also shows what the descriptors cannot do: the healthy class, the sensor bias fault and the sensor gain fault have nearly identical distributions in every panel.

[[FIG:signatures]]

## Neural-Network Classifiers <<sec:classifier>>

Two classifiers are trained on the descriptor vector, one for the four layers and one for the nine fault classes. They are separate networks with the same hidden structure and different output layers, and their results must not be confused: the layer macro-F1 and the fault macro-F1 reported below are the scores of different models on different label sets. Each network is a fully connected MLP with 20 inputs, two hidden layers of 96 and 48 rectified linear units, and a softmax output. The layer network has four outputs and {{PARAMS_LAYER}} parameters ({{MACS_LAYER}} multiply–accumulate operations per inference), and the fault network has nine outputs and {{PARAMS_FAULT}} parameters ({{MACS_FAULT}} operations).

The networks were implemented with scikit-learn [@pedregosa2011] and trained with the Adam optimizer [@kingma2015]. According to the project documentation, the settings were a learning rate of $8 \times 10^{-4}$, a batch size of 64, an L2 penalty of $10^{-4}$, at most 700 epochs, and early stopping on an internal split of 15% of the training records; the inputs were standardized with statistics of the training data only. The training code is not part of the archived evidence package, so these settings are reported as documented and could not be re-verified for this article ({{S:repro}}). Every model was trained twice, with two initialization seeds, and all reported scores are averages over the two.

A small network on physically motivated descriptors was chosen deliberately. The descriptors already separate the influences that the analysis of {{S:arch}} identified, so that the classifier is left with a low-dimensional problem, and a network of this size can run on a microcontroller with existing inference kernels [@lai2018]. No measurement on an embedded target was made.
