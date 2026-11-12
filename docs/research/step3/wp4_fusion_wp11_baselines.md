# WP4 evidence fusion and WP11 baselines B0, B1, B3 (research model v0.4)

Date: 2026-11-12. Code: `netsight.trust.fusion`, `netsight.trust.baselines`,
`python -m netsight.detect.fusion_run`. Result: `runs/fusion_v0.4/results.json`.

Detections with raw score >= 0.1 from the v0.4 dump, labelled real/false by IoU >= 0.5, up to 800
per set (seeded sample). Evidence features measured on the image for every detection (shadow,
texture, lines, ripple, anomaly, box size/aspect). Everything fitted on validation surveys,
scored on held-out test surveys. Pooled: 4,263 test detections, 467 real.

## Calibration: NetSight vs baselines (lower is better except AUROC)

| Test set | B0 raw ECE | B1 temperature ECE | NetSight beta ECE | beta log loss vs B0 |
|---|---|---|---|---|
| pooled | 0.173 | 0.085 | **0.042** | 0.259 vs 0.371 |
| aquascan | 0.190 | 0.077 | **0.013** | 0.080 vs 0.265 |
| ghostvision | 0.171 | 0.044 | **0.020** | 0.244 vs 0.363 |
| ghostvision_shift | 0.116 | 0.056 | 0.062 | 0.375 vs 0.393 |
| mine | 0.217 | 0.161 | **0.041** | 0.290 vs 0.451 |
| sctd | 0.153 | 0.134 | **0.052** | 0.333 vs 0.422 |
| subpipe | 0.198 | 0.123 | **0.056** | 0.209 vs 0.361 |

The calibrated probability beats the raw score (B0, "a typical SIH project") on every set and
temperature scaling (B1) on all but the sensor-shifted Contact recording, where the two are
equal within noise (that recording is the one the applicability gate marks indicative).

## WP4: fusing evidence features into P(real): rejected

| Test set | score-only log loss | fusion log loss | AUROC score-only / fusion |
|---|---|---|---|
| pooled | **0.259** | 0.288 | 0.864 / 0.858 |
| aquascan | **0.080** | 0.242 | 0.956 / 0.923 |
| ghostvision | **0.244** | 0.264 | 0.858 / 0.856 |
| ghostvision_shift | **0.375** | 0.494 | 0.808 / 0.741 |
| mine | **0.290** | 0.363 | 0.796 / 0.814 |
| sctd | **0.333** | 0.901 | 0.923 / 0.840 |
| subpipe | **0.209** | 0.550 | 0.884 / 0.897 |

Fusion is worse on held-out surveys everywhere. The ablation (change in held-out log loss when a
group is removed) is negative for most groups, i.e. removing them helps: texture (-0.015 pooled,
-0.42 on SCTD), size (-0.010), shadow (-0.006). Only ripple deviation helps slightly (+0.002
pooled). The features carry survey-specific patterns that do not transfer between surveys.

Decision: the fusion model is not used. Evidence features stay what the plan says they are:
measurements shown to the expert, never inputs that change P(real) or drop a contact. Revisit
with more surveys (the learning curve showed more recordings pay off) and per-feature
normalisation by survey.

## B3: shadow-required filter

| Test set | real detections dropped by B3 | AUROC with B3 |
|---|---|---|
| pooled | 412 of 467 (88%) | 0.49 |
| ghostvision | 80 of 81 (99%) | 0.49 |
| mine | 76 of 80 (95%) | 0.46 |
| sctd | 75 of 105 (71%) | 0.57 |

Requiring a measurable shadow throws away most real objects and ranks no better than chance.
Caveat: shadow is searched on one assumed range side (to the right); on waterfalls with a centre
nadir, half of the objects cast their shadow to the left, so this overstates B3's loss. Even
halved, B3 would drop about 40% of real objects, matching the plan's rule that shadow is a soft
feature, never a gate.
