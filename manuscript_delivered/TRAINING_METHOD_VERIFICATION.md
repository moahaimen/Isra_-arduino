# Training-method verification

This document compares the frozen protocol with the training code that the protocol froze. All sources are included in this package (`source_code/active_sensor_diagnosis/src/`), so the comparison can be repeated.

## 1. Source and hash comparison

`python3 source_code/verify_source_hashes.py` compares every source file with `evidence_package_2026-10-26/phase_robust_final/phase_robust_results/source_hashes_at_freeze.txt`. Result: **38 of 38 frozen files match; none differ and none are missing.** Eight files were added after the freeze (report, figure and literature scripts); the validation run does not import them.

| File | SHA-256 at freeze | SHA-256 of the included file |
|---|---|---|
| src/run_feasibility.py | f994d9499ebd659779835d9266ea36927687122602525524c02cc0e1e3175d15 | f994d9499ebd659779835d9266ea36927687122602525524c02cc0e1e3175d15 |
| src/run_phase_robust.py | a16a6a4587ba190a250de748bef8b61745e87fab5ebc21fc03428cc04baa637e | a16a6a4587ba190a250de748bef8b61745e87fab5ebc21fc03428cc04baa637e |

What this shows: the included code is byte-identical to the code that was hashed when the protocol was frozen, before the validation data were generated. What it does not show: the run logs record neither the code hash nor the fitted iteration count, so the link between this code and the saved predictions rests on the freeze record and the file timestamps (protocol 14 Oct 2026 20:25, predictions 20:44), not on a log entry.

## 2. What the protocol says

`PROTOCOL_PHASE_ROBUST_FROZEN.md`, section 3:

> * New validation dataset seeds **20261026, 20261027, 20261028**; 350 conditions x 9 faults; test 25 % (`random_state = S+1`), validation 15 % of the rest (`S+2`, unused: no early-stopped model), train = remaining 222 conditions, no overlap asserted. Two initialisation seeds (11, 22), averaged. Same MLP (`_classifier`, 96-48).

The same parenthesis ("unused here because no early-stopped model is trained") appears in the earlier reference-monitor protocol, from which the text was carried over.

## 3. What the code does

The validation run (`run_phase_robust.py`) builds every classifier with `_classifier` from `run_feasibility.py` (import on line 23; calls on lines 176 and 238):

```python
  30  def _classifier(seed: int) -> Pipeline:
  31      return Pipeline(
  32          [
  33              ("scale", StandardScaler()),
  34              (
  35                  "mlp",
  36                  MLPClassifier(
  37                      hidden_layer_sizes=(96, 48),
  38                      activation="relu",
  39                      solver="adam",
  40                      alpha=1e-4,
  41                      batch_size=64,
  42                      learning_rate_init=8e-4,
  43                      max_iter=700,
  44                      early_stopping=True,
  45                      validation_fraction=0.15,
  46                      n_iter_no_change=35,
  47                      random_state=seed,
  48                  ),
  49              ),
  50          ]
  51      )
```

The condition-level split in `run_phase_robust.py`:

```python
  77      dev, test = next(GroupShuffleSplit(1, test_size=0.25, random_state=seed + 1).split(np.zeros(n_rows), groups=groups))
  78      sub = next(GroupShuffleSplit(1, test_size=0.15, random_state=seed + 2).split(dev, groups=groups[dev]))
  79      train, val = dev[sub[0]], dev[sub[1]]
  80      train_set, test_set = set(train.tolist()), set(test.tolist())
```

Rows of the 40 validation conditions are skipped when the training and test sets are built (`if r not in train_set and r not in test_set: continue`), so they are never simulated, used for training or used for model selection.

With scikit-learn 1.7.2 (the version recorded for the run), `MLPClassifier.fit` with `early_stopping=True` executes the following. The quoted line numbers are from `sklearn/neural_network/_multilayer_perceptron.py` of the installed 1.7.2, which matches https://github.com/scikit-learn/scikit-learn/blob/1.7.2/sklearn/neural_network/_multilayer_perceptron.py.

**Internal hold-out: random, not stratified, for these networks.**

```python
 642          if early_stopping:
 643              # don't stratify in multilabel classification
 644              should_stratify = is_classifier(self) and self.n_outputs_ == 1
 645              stratify = y if should_stratify else None
 646              if sample_weight is None:
 647                  X_train, X_val, y_train, y_val = train_test_split(
 648                      X,
 649                      y,
 650                      random_state=self._random_state,
 651                      test_size=self.validation_fraction,
 652                      stratify=stratify,
 653                  )
```

Stratification applies only when `self.n_outputs_ == 1`. For a multiclass target, `MLPClassifier` one-hot encodes the labels, so `n_outputs_` equals the number of classes: 4 for the layer network and 9 for the fault network. I confirmed this with the installed 1.7.2 on synthetic 4-class and 9-class data (`n_outputs_` = 4 and 9). The split was therefore a **plain random 15% of the training rows**, drawn by row and not by operating condition, with `random_state` equal to the network's initialization seed (11 or 22).

**Stopping criterion.** After every epoch the hold-out accuracy is computed (`_score` with `accuracy_score`):

```python
 809              if last_valid_score < (self.best_validation_score_ + self.tol):
 810                  self._no_improvement_count += 1
 811              else:
 812                  self._no_improvement_count = 0
 813  
 814              if last_valid_score > self.best_validation_score_:
 815                  self.best_validation_score_ = last_valid_score
 816                  self._best_coefs = [c.copy() for c in self.coefs_]
 817                  self._best_intercepts = [i.copy() for i in self.intercepts_]
```

```python
 755                  if self._no_improvement_count > self.n_iter_no_change:
 756                      # not better than last `n_iter_no_change` iterations by tol
 757                      # stop or decrease learning rate
 758                      if early_stopping:
```

The counter increases whenever the accuracy fails to exceed the best value so far by at least `tol` = 1e-4, and resets otherwise. Training stops when the counter exceeds `n_iter_no_change` = 35, that is after 36 consecutive epochs without such an improvement, or after `max_iter` = 700 epochs.

**Restoration of the best weights.** At the end of training, whether it stopped early or reached `max_iter`, the weights and intercepts with the highest hold-out accuracy are restored:

```python
 790          if early_stopping:
 791              # restore best weights
 792              self.coefs_ = self._best_coefs
 793              self.intercepts_ = self._best_intercepts
```

**Other settings that executed:** Adam, constant initial learning rate 8e-4, mini-batches of 64, L2 penalty 1e-4, shuffling on (the default). `StandardScaler` is fitted on all training rows, including the internal hold-out.

## 4. Discrepancy

The frozen protocol states that no early-stopped model is trained. **This is not what the frozen code does:** every MLP in the validation run, primary method included, was trained with scikit-learn's internal early stopping on a random (not class-stratified) 15% row-level hold-out of its own training rows. The protocol's statement that the 40-condition validation split is unused is correct; its statement about early stopping is not.

The discrepancy is in the protocol text, not in the executed procedure. The code was frozen and hashed before the validation data existed, and the reported results are those of the code. It cannot be resolved retrospectively by reinterpreting the protocol. The manuscript therefore reports the procedure as implemented and states the discrepancy explicitly (Section 5). Consequences:

- **No test leakage.** The 88 test conditions are disjoint from all training conditions, and the hold-out is drawn only from training rows.
- **Possibly optimistic stopping.** The hold-out is not condition-disjoint from the remaining training rows, so the stopping point may be chosen somewhat optimistically. This affects all arms in the same way.
- **Not recorded.** The number of epochs actually run per model was not saved, so it cannot be reported.

Resolving the discrepancy completely would require retraining with a documented procedure, which was not done.
