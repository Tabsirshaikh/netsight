# Research model v0.1: results and findings

Date: 2026-11-08. D-FINE-S from COCO weights, tile 640 (25% overlap; whole-image pass only for
aspect <= 2), trained jointly on mine detection, GhostVision, AquaScan-1K and SubPipe (balanced
tile budget), 30 epochs, validation every 3 epochs. Label: research model (GhostVision's licence
is unresolved). Best checkpoint: epoch 12 by mean validation AP50.

## Validation curve

| Epoch | 3 | 6 | 9 | 12 | 15 | 18 | 21 | 24 | 27 | 30 |
|---|---|---|---|---|---|---|---|---|---|---|
| Mean val AP50 | 0.323 | 0.377 | 0.434 | **0.454** | 0.431 | 0.429 | 0.441 | 0.425 | 0.413 | 0.408 |

After epoch 12 the model overfits; more epochs make it worse. v0.2 should stop early (and use
larger validation sets, ~100 images per dataset is noisy).

## Held-out test (groups never seen in training)

| Test set | Images | Objects | AP50 | Recall @ 1 FP/image |
|---|---|---|---|---|
| Mine (2015, 2021) | 168 | 462 | 0.140 | 0.149 |
| GhostVision (Rec9, Rec14, Rec8) | 443 | 611 | 0.345 | 0.430 |
| GhostVision shifted (Contact) | 555 | 1,275 | 0.287 | 0.341 |
| AquaScan-1K (2 sessions) | 243 | 243 | 0.529 | 0.621 |
| SubPipe (last 3 time windows) | 79 | 57 | 0.002 at IoU 0.5; **0.519 at IoU 0.3** | 0.018 / 0.509 |

## SubPipe: an annotation-convention shift, not a detector failure

Validation windows score 0.93-0.95 AP50, the test windows ~0. Looking at the images: in the test
window the label box covers the seabed left of the pipe plus the pipe, while the model (and the
training labels) cover the pipe plus its acoustic shadow. The model finds the pipe but at IoU
~0.4, so a strict IoU 0.5 count rejects it. At IoU 0.3 the test AP is 0.519. The late windows
(52 minutes later in the mission) are also genuinely harder (low model confidence). Elongated
objects such as pipelines have ambiguous extents; report a looser IoU for them alongside 0.5.

## Weaknesses to fix in v0.2

1. Overfitting after ~12 epochs: early stopping; more data (SCTD added).
2. Mine set is weakest (0.140): it gets <5% of the training tiles and has 12-27 px targets.
3. Validation sets too small to choose epochs reliably.
4. Data loading limits GPU use (fixed by the raw-pixel cache).
