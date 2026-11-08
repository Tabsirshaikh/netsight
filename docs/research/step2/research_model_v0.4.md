# Research model v0.4 (accepted): v0.2 + weight EMA

Date: 2026-11-08. Only change from v0.2: exponential moving average of the weights (decay 0.9998,
warmup 1000 steps; the official D-FINE recipe uses weight EMA, ours did not). Validation rose
smoothly (0.414, 0.442, 0.500, 0.507, 0.512, 0.525, 0.520, 0.509); early stop at epoch 17, best
0.525 at epoch 11. Model: `runs/research_v0.4/model` (research model: trained on SCTD,
research-only).

## Paired test comparison (image bootstrap, 1000 draws, 95% CI, AP50, no TTA)

| Test set | v0.1 | v0.2 | **v0.4** | v0.4 - v0.2 (CI) | v0.4 - v0.1 (CI) |
|---|---|---|---|---|---|
| mine (held-out years) | 0.140 | 0.185 | **0.223** | +0.037 (+0.008, +0.065) | +0.082 (+0.053, +0.112) |
| ghostvision | 0.345 | 0.353 | **0.361** | +0.008 (-0.018, +0.030) | +0.016 (-0.010, +0.039) |
| ghostvision_shift (Contact) | 0.288 | 0.175 | 0.256 | +0.082 (+0.064, +0.102) | -0.031 (-0.056, -0.007) |
| aquascan | 0.530 | 0.574 | **0.615** | +0.041 (-0.002, +0.084) | +0.085 (+0.044, +0.125) |
| subpipe | 0.004 | 0.127 | **0.231** | +0.104 (+0.004, +0.216) | +0.227 (+0.145, +0.348) |
| sctd | 0.043 | 0.770 | **0.817** | +0.046 (-0.002, +0.093) | +0.774 |

## Decision

Accepted as the current research model. Against v0.2 no test set is worse and three improve with
a CI above zero. Against v0.1 the only drop is the Contact recording (-0.031, at the ~0.03 limit),
which is a sensor-geometry shift (boxes 1.32x wider than tall): test B showed per-survey pixel
correction recovers it (0.175 -> 0.368 for v0.2) and the applicability gate must flag such
surveys. SubPipe at IoU 0.5 is unstable (labels mark the seabed beside the pipe): the in-training
evaluation gave 0.183 and the re-run 0.231 for the same model; tiny box changes flip matches.

Lesson from v0.2-v0.4: with small validation sets, changes that stabilise training (EMA) paid
off; a change judged on noisy validation (zoom augmentation, v0.3) did not.
