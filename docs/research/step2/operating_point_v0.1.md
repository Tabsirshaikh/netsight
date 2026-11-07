# Operating point on real detector output (research v0.1 + flip TTA)

Date: 2026-11-08. Code: `python -m netsight.detect.operating_run`. Budgets are false alarms per
image (public sets have no swath geometry; with navigation the unit becomes km2). Recall counts
every object, including ones never detected.

## Findings

1. **A threshold certified on validation surveys does not hold on new surveys.** Learn-then-Test
   at delta 0.05 assumes Poisson false alarms with no survey-to-survey over-dispersion. On the
   held-out surveys the budget is broken on 8 of 12 (pooled) cases; the mine held-out years see
   1.8-3.2 false alarms per image against budgets of 0.5-1.0. False-alarm rates vary by survey.
   A validation-frozen FA/km2 promise is therefore **not** honest for a new survey.
2. **A label-free, survey-adaptive threshold does hold.** On the new survey, set the threshold so
   that at most budget x area detections are flagged. False alarms can never exceed flagged
   detections, so the budget holds without labels: 12 of 12 cases. The price is recall (real
   objects use up part of the budget): e.g. AquaScan at 1 FA/image 0.72 -> 0.55, mine 0.33 ->
   0.11.
3. **So the product should promise the false-alarm budget (guaranteed by counting) and report
   recall as an estimate with its interval and applicability level**, not the reverse.
4. **The detector remains the bottleneck**: on unseen mine-survey years, a guaranteed 1 FA/image
   leaves 11% recall.

Next: survey-cluster bounds (negative-binomial or cluster bootstrap) for the frozen threshold,
so the validation route states an honest, wider bound; repeat on v0.2.

## Survey-level conformal threshold (second route tried)

Threshold = lowest score at which **every** validation survey stays within budget (split-conformal
over surveys: coverage n/(n+1) if a new survey is exchangeable with them).

Survey-level bound: 8 validation surveys -> guaranteed coverage 8/9 = 89% for an exchangeable new survey.

| Budget FA/image | Threshold | Test surveys within budget | Pooled test recall |
|---|---|---|---|
| 0.5 | 0.756 | 11/12 | 0.038 |
| 1.0 | 0.466 | 8/12 | 0.306 |

| Test survey | FA/img @ 0.5 | FA/img @ 1.0 |
|---|---|---|
| aquascan/13SEP25 | 0.14 | 0.92 |
| aquascan/2025-11-23 | 0.05 | 1.18 |
| ghostvision/Rec14 | 0.00 | 1.23 |
| ghostvision/Rec8 | 0.01 | 0.73 |
| ghostvision/Rec9 | 0.00 | 0.89 |
| ghostvision_shift/Contact | 0.00 | 0.43 |
| mine/2015 | 0.17 | 2.72 |
| mine/2021 | 0.04 | 0.85 |
| sctd/test | 0.05 | 0.37 |
| subpipe/t28226170 | 1.00 | 2.03 |
| subpipe/t28226222 | 0.00 | 0.31 |
| subpipe/t28226223 | 0.00 | 0.00 |

It does not rescue the frozen route: at 0.5 FA/image it holds 11/12 but recall collapses to 0.04
(the worst validation survey sets the threshold); at 1.0 only 8/12 = 67% of test surveys stay in
budget, below the 89% the method promises. New surveys are not exchangeable with 8 calibration
surveys from other sites and sensors. With the data we have, **the label-free count threshold is
the only route that held the budget on every held-out survey.** (SubPipe false alarms are inflated
by its label convention at IoU 0.5.)

## Full table

| Test set | Fitted on | Budget FA/image | Threshold | Test FA/image | Budget held | Test recall | 95% CI |
|---|---|---|---|---|---|---|---|
| aquascan | own validation | 0.5 | 0.598 | 0.58 | **no** | 0.601 | 0.536-0.663 |
| aquascan | own validation | 1.0 | 0.471 | 1.10 | **no** | 0.667 | 0.604-0.726 |
| aquascan | pooled validation | 0.5 | 0.491 | 0.98 | **no** | 0.654 | 0.591-0.714 |
| aquascan | pooled validation | 1.0 | 0.404 | 1.63 | **no** | 0.716 | 0.655-0.772 |
| aquascan | label-free count on the test survey | 0.5 | 0.748 | 0.10 | yes | 0.391 | 0.329-0.455 |
| aquascan | label-free count on the test survey | 1.0 | 0.637 | 0.44 | yes | 0.547 | 0.482-0.611 |
| ghostvision | own validation | 0.5 | 0.494 | 0.69 | **no** | 0.365 | 0.327-0.405 |
| ghostvision | own validation | 1.0 | 0.425 | 1.44 | **no** | 0.534 | 0.493-0.574 |
| ghostvision | pooled validation | 0.5 | 0.491 | 0.72 | **no** | 0.375 | 0.336-0.415 |
| ghostvision | pooled validation | 1.0 | 0.404 | 1.67 | **no** | 0.589 | 0.549-0.629 |
| ghostvision | label-free count on the test survey | 0.5 | 0.572 | 0.25 | yes | 0.170 | 0.141-0.202 |
| ghostvision | label-free count on the test survey | 1.0 | 0.514 | 0.57 | yes | 0.313 | 0.276-0.351 |
| ghostvision_shift | own validation | 0.5 | 0.494 | 0.31 | yes | 0.181 | 0.160-0.203 |
| ghostvision_shift | own validation | 1.0 | 0.425 | 0.61 | yes | 0.289 | 0.264-0.314 |
| ghostvision_shift | pooled validation | 0.5 | 0.491 | 0.32 | yes | 0.187 | 0.166-0.209 |
| ghostvision_shift | pooled validation | 1.0 | 0.404 | 0.73 | yes | 0.311 | 0.285-0.337 |
| ghostvision_shift | label-free count on the test survey | 0.5 | 0.527 | 0.19 | yes | 0.132 | 0.114-0.152 |
| ghostvision_shift | label-free count on the test survey | 1.0 | 0.459 | 0.45 | yes | 0.239 | 0.216-0.264 |
| mine | own validation | 0.5 | 0.449 | 2.41 | **no** | 0.271 | 0.231-0.314 |
| mine | own validation | 1.0 | 0.360 | 4.45 | **no** | 0.377 | 0.332-0.423 |
| mine | pooled validation | 0.5 | 0.491 | 1.84 | **no** | 0.234 | 0.196-0.275 |
| mine | pooled validation | 1.0 | 0.404 | 3.23 | **no** | 0.325 | 0.282-0.369 |
| mine | label-free count on the test survey | 0.5 | 0.676 | 0.31 | yes | 0.069 | 0.048-0.096 |
| mine | label-free count on the test survey | 1.0 | 0.609 | 0.69 | yes | 0.110 | 0.083-0.143 |
| sctd | own validation | 0.5 | 0.529 | 0.21 | yes | 0.045 | 0.015-0.103 |
| sctd | own validation | 1.0 | 0.396 | 0.78 | yes | 0.073 | 0.032-0.138 |
| sctd | pooled validation | 0.5 | 0.491 | 0.31 | yes | 0.045 | 0.015-0.103 |
| sctd | pooled validation | 1.0 | 0.404 | 0.70 | yes | 0.073 | 0.032-0.138 |
| sctd | label-free count on the test survey | 0.5 | 0.442 | 0.43 | yes | 0.055 | 0.020-0.115 |
| sctd | label-free count on the test survey | 1.0 | 0.362 | 0.90 | yes | 0.082 | 0.038-0.150 |
| subpipe | own validation | 0.5 | 0.531 | 0.63 | **no** | 0.035 | 0.004-0.121 |
| subpipe | own validation | 1.0 | 0.334 | 1.75 | **no** | 0.035 | 0.004-0.121 |
| subpipe | pooled validation | 0.5 | 0.491 | 0.81 | **no** | 0.035 | 0.004-0.121 |
| subpipe | pooled validation | 1.0 | 0.404 | 1.15 | **no** | 0.035 | 0.004-0.121 |
| subpipe | label-free count on the test survey | 0.5 | 0.672 | 0.47 | yes | 0.035 | 0.004-0.121 |
| subpipe | label-free count on the test survey | 1.0 | 0.435 | 0.96 | yes | 0.035 | 0.004-0.121 |
