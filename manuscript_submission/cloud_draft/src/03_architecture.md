# Self-Test Architecture and Diagnostic Observability <<sec:arch>>

## Measurement Chain and Fault Model <<sec:chain>>

{{F:arch}} shows the simulated interface. The sensor delivers a voltage $x(t)$. The AFE is modeled as a first-order low-pass stage with time constant $\tau$, gain $G_\mathrm{AFE}$ and offset $o_\mathrm{AFE}$, so that its output $v(t)$ obeys

$$\tau\,\frac{\mathrm{d}v}{\mathrm{d}t} + v = G_\mathrm{AFE}\,x(t) + o_\mathrm{AFE}.$$ <<eq:afe>>

The ADC samples $v$ with period $T = 1$ ms and resolution of 12 bits over a range of 0 to 3.3 V. Its static transfer is described by a gain $g_\mathrm{ADC}$ and an offset $o_\mathrm{ADC}$, nominally one and zero, so that a sample is $y[n] = Q\!\left(g_\mathrm{ADC}\,v(nT) + o_\mathrm{ADC} + w[n]\right)$, where $w$ is the converter noise and $Q$ the quantizer. The parameters of the model are listed in {{T:params}}.

[[FIG:arch]]

[[TAB:params]]

Nine classes are simulated ({{T:faults}}): the healthy interface and eight single faults, three in the sensor, two in the AFE and three in the ADC. For the layer-level diagnosis they are grouped into four classes (healthy, sensor, AFE and ADC). The severity of each fault is drawn at random from the range given in the table, and every record also contains the tolerances and noise of {{T:params}}, so that a healthy interface is not a nominal one.

[[TAB:faults]]

## Observability of the Chain from Its Output <<sec:observability>>

In steady state the chain reduces to

$$y = g_\mathrm{ADC}\left(G_\mathrm{AFE}\,x + o_\mathrm{AFE}\right) + o_\mathrm{ADC} = g_\mathrm{ADC}G_\mathrm{AFE}\,x + \left(g_\mathrm{ADC}\,o_\mathrm{AFE} + o_\mathrm{ADC}\right).$$ <<eq:chain>>

Only the product of the two gains and one combined offset appear in {{EQ:chain}}. Even if the sensor signal $x$ were known exactly, the output would determine no more than these two combinations, and the individual parameters $g_\mathrm{ADC}$, $G_\mathrm{AFE}$, $o_\mathrm{AFE}$ and $o_\mathrm{ADC}$ would remain unidentifiable in the structural sense [@bellman1970]. With an unknown $x$, a change of the sensor sensitivity is in addition indistinguishable from a change of either gain. This is the reason why a passive observation of the output cannot localize a parametric fault, whatever classifier is applied to it, and it is the engineering motivation for injecting references at two points of the chain.

## Two-Point Reference Test <<sec:twopoint>>

During the AFE test window a multiplexer (MUX 1 in {{F:arch}}) disconnects the sensor and applies a two-level reference, $r^\mathrm{AFE}_1$ followed by $r^\mathrm{AFE}_2$, to the AFE input. During the ADC test window a second multiplexer (MUX 2) applies another two-level reference, $r^\mathrm{ADC}_1$ followed by $r^\mathrm{ADC}_2$, directly to the ADC input. Let $m_1$ and $m_2$ denote the settled ADC outputs on the two plateaus of the ADC window. Because the AFE is bypassed, $m_k = g_\mathrm{ADC}\,r^\mathrm{ADC}_k + o_\mathrm{ADC}$, and the two unknowns follow from the two plateaus:

$$\hat{g}_\mathrm{ADC} = \frac{m_2 - m_1}{r^\mathrm{ADC}_2 - r^\mathrm{ADC}_1}, \qquad \hat{o}_\mathrm{ADC} = m_1 - \hat{g}_\mathrm{ADC}\,r^\mathrm{ADC}_1 .$$ <<eq:adc>>

The whole record is then referred to the ADC input,

$$y_\mathrm{c}[n] = \frac{y[n] - \hat{o}_\mathrm{ADC}}{\hat{g}_\mathrm{ADC}},$$ <<eq:cal>>

and the settled values $a_1$ and $a_2$ of $y_\mathrm{c}$ on the two plateaus of the AFE window give the AFE parameters in the same way:

$$\hat{G}_\mathrm{AFE} = \frac{a_2 - a_1}{r^\mathrm{AFE}_2 - r^\mathrm{AFE}_1}, \qquad \hat{o}_\mathrm{AFE} = a_1 - \hat{G}_\mathrm{AFE}\,r^\mathrm{AFE}_1 .$$ <<eq:afeest>>

Four settled plateau values thus determine the four static parameters, provided that the four reference levels are known, that the two levels of each reference differ, and that the plateaus have settled. The time constant $\tau$ is the fifth parameter of the model and is observable only in the transient of the AFE window ({{S:transient}}). Two levels per reference are the minimum that separates a gain from an offset; a single level would again leave one combination of the two.

The sensor is not excited by either reference. Sensor faults are visible only in the intervals in which the sensor is connected, after the record has been referred back to the AFE input with the estimated parameters, $\hat{x}[n] = (y_\mathrm{c}[n] - \hat{o}_\mathrm{AFE})/\hat{G}_\mathrm{AFE}$. This removes the static errors of the electronics from the sensor signal, but it cannot separate a bias or a sensitivity change of the sensor from a genuine change of the measured quantity. The test is consequently an active test for the electronics and a passive one for the sensor, a distinction that reappears in the results.

## Reference Monitoring and the Effect of Reference Errors <<sec:monitor>>

Equations {{EQN:adc}} and {{EQN:afeest}} contain the reference levels. It is instructive to work out what happens when the levels used in the calculation differ from the levels that were applied. Suppose that all four applied levels are a common factor $c$ times their nominal values, as happens when the reference source drifts, and that the nominal values are used. Substituting into Equations {{EQN:adc}}–{{EQN:afeest}} for settled, noise-free plateaus gives

$$\hat{g}_\mathrm{ADC} = c\,g_\mathrm{ADC}, \qquad \hat{o}_\mathrm{ADC} = o_\mathrm{ADC}, \qquad \hat{G}_\mathrm{AFE} = G_\mathrm{AFE}, \qquad \hat{o}_\mathrm{AFE} = \frac{o_\mathrm{AFE}}{c}.$$ <<eq:mapping>>

A drift of the reference amplitude is therefore read as a change of the ADC gain by the same factor, accompanied by a change of the apparent AFE offset and, through $\hat{x}$, by a rescaling of the sensor signal by $1/c$. A reference that is 20% low looks like an ADC whose gain is 20% low, which lies inside the range of the simulated ADC gain faults ({{T:faults}}). No processing of the output record can undo this, because $c$ and $g_\mathrm{ADC}$ enter the ADC window only through their product. The reference amplitude has to be known from another source.

That source is a monitor channel ({{F:arch}}). It taps the reference nodes through a switch and a high-impedance buffer and digitizes each level with a converter that is independent of the ADC under test. The independence is essential: if the reference were measured with the ADC under test, a gain fault of that ADC would scale the measured levels and the measured response alike and would cancel in {{EQ:adc}}. The monitor is modeled as

$$\hat{r} = Q_\mathrm{m}\!\left(r\,(1 + e) + n\right), \qquad e \sim \mathcal{U}(-E, E), \qquad n \sim \mathcal{N}\!\left(0, \sigma_\mathrm{m}^2\right),$$ <<eq:monitormodel>>

where $r$ is the applied level, $e$ is a gain error that is common to the four levels of one test and bounded by $E$, $n$ is the noise that remains after averaging 16 samples ($\sigma_\mathrm{m} = 0.25$ mV), and $Q_\mathrm{m}$ is a 12-bit quantizer over 0 to 3.3 V. The offset of the monitor is assumed to be trimmed. The measured levels $\hat{r}$ replace the reference levels in {{EQ:adc}} and {{EQ:afeest}}. Repeating the substitution with $\hat{r} = (1 + e)\,r$ shows that the monitor error acts like a reference drift with $c = 1/(1 + e)$: it leaves $\hat{o}_\mathrm{ADC}$ and $\hat{G}_\mathrm{AFE}$ unchanged, scales $\hat{g}_\mathrm{ADC}$ by $1/(1 + e)$ and scales $\hat{o}_\mathrm{AFE}$ by $1 + e$.

The monitor thus does not remove the need for an accurate quantity in the system; it moves that need from the test stimulus, which must be switched quickly and may be loaded by the circuit under test, to a slow measurement of a static level, where accuracy is cheaper to obtain. The residual sensitivity is to the monitor's own gain error, and the bound $E$ expresses the uncertainty of the monitored level in the sense of [@jcgm100]. With $E$ of 5% the apparent ADC gain moves by about 5% at most, slightly less than the smallest simulated ADC gain fault of 6%. These relations are analytical properties of the estimator under the stated assumptions (a gain error common to all levels, settled plateaus, no noise). Whether the classifier tolerates monitor errors of this size in the presence of tolerances and noise is an empirical question, which {{S:res_amp}} answers for the simulated conditions. The monitor was simulated and not built.

## Test Sequence and Sampling Phase <<sec:sequence>>

Each record contains 512 samples ({{F:timing}}). The sensor is connected from 0 to 140 ms, from 260 to 340 ms and from 460 ms to the end. The AFE window extends from 140 to 260 ms and the ADC window from 340 to 460 ms; each consists of two plateaus of 60 ms. The sensor is thus disconnected for 240 ms per test.

The reference and multiplexer edges are produced by a sequencer whose clock is not assumed to be locked to the ADC clock. An edge occurs a fraction $\psi \in [0, 1)$ of a sampling period after the preceding ADC sample, at $t_\mathrm{edge} = t_{i-1} + \psi T$. The first sample on the new level has then settled for $(1 - \psi)T$, and every later sample of the transient is shifted by the same amount ({{F:timing}}c). We call $\psi$ the edge phase. It is constant within a record in this study and is the same for all edges of the record. In the ADC window the edge phase has no effect in the model, because the bypassed path has no dynamics and the first sample after the edge already shows the new level.

[[FIG:timing]]
