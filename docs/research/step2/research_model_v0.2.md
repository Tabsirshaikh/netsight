# Research model v0.2 vs v0.1 (phase D)

Date: 2026-11-08. v0.2 = v0.1 recipe + SCTD (research-only) + minimum share 0.15 per dataset
(max 4x repeat) + early stopping (patience 3 validations of 250 images per dataset). Stopped at
epoch 19; best mean validation AP50 0.529 at epoch 13 (v0.1: 0.454). Tile mix per epoch: v0.1
mine 5% / GhostVision 32% / AquaScan 31% / SubPipe 32%; v0.2 mine 14% / GhostVision 24% /
AquaScan 24% / SubPipe 24% / SCTD 13% (GhostVision's absolute count unchanged, 2000).

## Paired test comparison (same images, image bootstrap, 1000 draws, 95% CI)

`python -m netsight.detect.compare_run --a calib_v0.1 --b calib_v0.2 --iou X`. Images within a
recording are correlated, so these intervals are optimistic.

| Test set | v0.1 AP50 | v0.2 AP50 | change (95% CI) | change at IoU 0.3 | change at IoU 0.1 |
|---|---|---|---|---|---|
| mine (held-out years) | 0.140 | 0.185 | **+0.045** (+0.019, +0.073) | +0.048 (+0.018, +0.082) | +0.033 |
| ghostvision | 0.345 | 0.353 | +0.008 (-0.022, +0.037) | +0.042 (+0.005, +0.073) | +0.049 |
| ghostvision_shift (Contact) | 0.288 | 0.175 | **-0.113** (-0.138, -0.092) | -0.093 (-0.118, -0.071) | -0.046 |
| aquascan | 0.530 | 0.574 | +0.044 (-0.000, +0.087) | +0.046 (+0.013, +0.082) | +0.018 |
| subpipe | 0.004 | 0.127 | +0.123 (+0.046, +0.220) | -0.063 (-0.162, +0.072) | -0.049 |
| sctd (new in v0.2) | 0.043 | 0.770 | +0.728 | +0.791 | +0.770 |

## Decision

The plan's rule (mean test AP50 rises and no dataset drops by more than ~0.03) is **not met**:
v0.2 is better on mine, AquaScan, GhostVision (at IoU 0.3) and SCTD, but clearly worse on the
GhostVision Contact recording, whose targets are 2.5x smaller than in training. v0.2 is the best
model for in-distribution use; it is not accepted as a strict improvement.

## Why the shifted set regressed

- Ground-truth median side 18 px; v0.2's confident boxes (score >= 0.3) median 34 px (v0.1:
  29.5 px). An 18 px object in a 34 px box has IoU ~0.28: a correct find counted as a miss.
- At IoU 0.1 (finding without box extent) the loss shrinks from -0.113 to -0.046: about 60% of
  the regression is box size, about 40% is objects not found.
- Training had no scale augmentation, so the model learns the training recordings' object sizes;
  SCTD's larger objects and more mine tiles moved that prior up.

Fix under test: **v0.3 = v0.2 + random zoom 0.5-1.5x on training tiles** (only change).

## Flip TTA on v0.2 (hflip + WBF, chosen on v0.1 validation)

mine +0.034 (+0.019, +0.052), AquaScan +0.040 (+0.015, +0.069), GhostVision +0.009, Contact
+0.008, SCTD +0.022, SubPipe -0.025 (-0.055, -0.002). Consistent with v0.1.

## Calibration (fitted on validation, scored on test)

Raw ECE 0.09-0.20 (mine worst at 0.200); own-dataset beta/Platt brings ECE to 0.005-0.028 on all
sets. The pooled calibrator transfers worse for v0.2 on mine (ECE 0.092 vs 0.025 own): with SCTD
in the pool, pooled calibration no longer fits the mine surveys. Per-dataset (or per-sensor)
calibration is needed, and the applicability gate decides which applies.
