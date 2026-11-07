# Flip test-time augmentation (research model v0.1)

Date: 2026-11-08. Code: `netsight.detect.tta`, `calibrate_run dump --tta`. Training already mirrors
tiles across and along track, so flipped views are valid extra looks. Views are merged with
weighted box fusion (WBF: one box per view per cluster, score = sum / number of views) or NMS.

**Choice made on validation only** (mean AP50 over mine, GhostVision, AquaScan, SubPipe):

| Setting | mine | ghostvision | aquascan | subpipe | mean |
|---|---|---|---|---|---|
| none | 0.284 | 0.340 | 0.442 | 0.811 | 0.469 |
| hflip + NMS | 0.305 | 0.336 | 0.457 | 0.789 | 0.472 |
| **hflip + WBF** | 0.349 | 0.356 | 0.500 | 0.796 | **0.500** |
| hflip + vflip + WBF (2x cost) | 0.339 | 0.371 | 0.510 | 0.778 | 0.500 |

**Confirmed once on test** with hflip + WBF (AP50, none -> TTA):

| Test set | none | TTA | change |
|---|---|---|---|
| mine (held-out years) | 0.140 | 0.152 | +0.012 |
| ghostvision | 0.345 | 0.350 | +0.005 |
| ghostvision_shift | 0.288 | 0.301 | +0.013 |
| aquascan | 0.530 | 0.579 | +0.049 |
| subpipe (AP at IoU 0.3) | 0.519 | 0.516 | -0.003 |

Conclusion: hflip + WBF is a small, consistent gain (+0.02 mean on held-out surveys, smaller than
on validation) at 2x inference cost. NMS merging is worse: averaging boxes and down-weighting
boxes seen in one view only is what helps. Use hflip + WBF for reported results, and always
report the no-TTA number next to it.
