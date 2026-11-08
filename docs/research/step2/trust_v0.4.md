# Trust layer on research model v0.4 (P3)

Date: 2026-11-08. Dump `runs/calib_v0.4` (no TTA), same code as for v0.1
(`calibrate_run report`, `operating_run`). Budget = false alarms per image.

## Calibration (fitted on own-dataset validation detections, scored on test)

| Test set | raw ECE | best method | ECE | raw Brier | Brier |
|---|---|---|---|---|---|
| mine | 0.150 | beta | 0.018 | 0.081 | 0.044 |
| ghostvision | 0.110 | beta | 0.004 | 0.049 | 0.034 |
| ghostvision_shift | 0.083 | temperature | 0.035 | 0.074 | 0.069 |
| aquascan | 0.118 | platt | 0.004 | 0.029 | 0.007 |
| subpipe | 0.112 | beta | 0.022 | 0.041 | 0.022 |
| sctd | 0.108 | isotonic | 0.028 | 0.062 | 0.046 |

Raw scores stay overconfident; calibration fixes them on every set. The sensor-shifted Contact set
calibrates worst (ECE 0.035): the geometry gate marks it indicative (demo packs).

## False-alarm budget 1 per image

| Test set | threshold from own validation: FA/image, held? | recall | label-free count: FA/image | recall (95% CI) |
|---|---|---|---|---|
| mine | 4.06, **no** | 0.468 | 0.57 | 0.154 (0.122-0.190) |
| ghostvision | 1.35, **no** | 0.545 | 0.55 | 0.313 (0.276-0.351) |
| ghostvision_shift | 0.66, yes | 0.264 | 0.49 | 0.219 (0.196-0.243) |
| aquascan | 1.00, yes | 0.687 | 0.39 | 0.605 (0.540-0.667) |
| subpipe | 1.14, **no** | 0.491 | 0.70 | 0.404 (0.276-0.542) |
| sctd | 0.82, yes | 0.891 | 0.18 | 0.736 (0.644-0.816) |

Same conclusion as v0.1: a validation-frozen threshold breaks the budget on new surveys (3/6
here; survey-level conformal: 8/12 surveys at 1 FA/image), the label-free count threshold holds it
on 6/6. Recall at a held budget improved over v0.1 on mine (0.110 -> 0.154, v0.1 numbers with
flip TTA) and AquaScan (0.547 -> 0.605); TTA would add a little more.
