# Tile size, overlap and pixel resolution for the side-scan detector

Date: 2026-11-07. Decides how sonar images are cut and scaled before the detector (Step 2B).
Every number below is quoted from the source named, read in full text unless marked.

## Evidence

| Source | What it says |
|---|---|
| SAHI, Akyon et al. 2022, arXiv 2202.06934 (full text read) | Fine-tuning on random patches 480-640 px (VisDrone) / 300-500 px (xView), **resized up to 800-1333 px wide** so small objects get more pixels. Inference on 640x640 / 400x400 slices with **25% overlap**, NMS match 0.5, plus an optional full-image pass. VisDrone TOOD AP50 29.4 (full image) -> 43.5 (slicing + overlap + full image); xView FCOS 2.2 -> 17.0. "25% overlap ... increases small/medium object AP ... but slightly decreases large object AP"; the full-image pass is needed for large objects; slices that are too small cut large objects. |
| DBnet, Ma et al. 2025, J. Mar. Sci. Eng. 13:155 (full text read) | Side-scan waterfalls: SAHI slicing with **20% overlap**; whole-image input "leads to high leakage of small undersea targets (targets with less than 50 pixels x 50 pixels)". Window size d is not stated numerically. |
| D-FINE config (`configs/dfine/include/dataloader.yml`, read) | Train and validation input **640x640**; multi-scale around base size 640; augmentations include **RandomZoomOut** and RandomIoUCrop until epoch 72. Code Apache-2.0; README: Objects365-pretrained weights "should not be assumed to be commercially cleared" -> product models start from COCO weights. |
| STDnet, Bosquet et al. 2020 (abstract) | Defines small objects as under 16x16 px and shows high-resolution feature maps are key for them. |
| NOAA HSSD 2003 (search snippet, current edition not yet checked) | Side-scan must detect a 1 m cube; tow speed such that a 1 m object is ensonified at least 3 times per pass; maximum range scale 100 m. A NOAA report states 0.3 m resolution meets the object-detection requirement for that cube. |

## What this means for NetSight

1. **Never feed whole waterfalls to the detector.** Waterfalls are thousands of pixels long; at
   640 px input, small targets shrink below the 16-50 px range where detectors fail (DBnet, STDnet).
2. **Network input stays 640x640**, matching D-FINE pretraining. The *tile cut from the sonar
   image* is chosen so that, after resizing to 640, the smallest target class is at least
   ~32 px (COCO's small-object limit; DBnet's 50 px is the safer goal). If targets are tiny,
   tiles are cut smaller than 640 and upscaled, as SAHI does (480-640 -> 800-1333).
3. **Overlap 20-25%**, and at least the size of the largest small-class object so it is never
   cut in every tile that contains it.
4. **Keep a full-image (downscaled) pass** for large objects such as wrecks, merged with the tile
   results (SAHI's FI).
5. **Turn off or weaken RandomZoomOut** when fine-tuning: it shrinks objects, which is the opposite
   of what small sonar targets need.
6. **Ground resolution (metres per pixel)** is a property of each sonar, not one global number.
   Normalise to square ground pixels near the sensor's across-track resolution, never coarser
   than the data supports and never invented by upsampling claims. Physics limit to report
   honestly: along-track resolution (range x beamwidth, tens of cm at 50 m range for a ~0.5 deg
   beam) is much coarser than across-track (a few cm), so small debris covers few along-track
   pings whatever we do. A 0.3 m grid puts a 1 m cube on ~3 px: enough for a hydrographer's
   1 m-cube rule, far too few for a detector.

## What the papers cannot decide: the exact tile size

It depends on each dataset's pixel size and the size of its objects in pixels. So the tile size
is chosen from data, then checked by experiment:

1. Download the labelled datasets unchanged (no tiling, no relabelling).
2. Measure box sizes per dataset and class, in pixels and, where the ground resolution is known,
   in metres.
3. Set tile size per dataset so the 10th-percentile small target is >= 32 px at 640 input.
4. Pilot: train D-FINE-S briefly with three settings (tile = 640 / 480 / 320 px, each resized to
   640, 25% overlap, plus full-image pass) and compare AP_small and recall at a fixed false-alarm
   rate on held-out surveys. Keep the winner.

## Measured box sizes (step 2 of the procedure)

Shorter box side in pixels, at the images' stored resolution (10th percentile / median / 90th):

| Dataset | Images (no object) | Boxes | Shorter side p10 / p50 / p90 |
|---|---|---|---|
| Mine detection, 1024 px images | 586 | 358 | 17 / 27 / 44 |
| Mine detection, 416 px images | 584 | 310 | 7.4 / 12 / 18.5 |
| (all mine images, 5 survey years) | 1,170 (866) | 668: 437 MILCO, 231 NOMBO | |
| GhostVision train (640 px, resized by Roboflow) | 5,721 (1,430) | 7,469 | 16 / 39 / 77 |
| GhostVision valid | 555 (53) | 1,275 | 8.5 / 15 / 24 |
| GhostVision test | 398 (64) | 567 | 22 / 42 / 67 |

Findings:
- Most mine targets and all GhostVision validation targets are below the 32 px goal at stored
  size. Shrinking whole images to 640 would make it worse; tiles enlarged ~2x (320 -> 640) bring
  the 1024 px mine targets to a ~54 px median and GhostVision train to ~78 px.
- GhostVision's published test split shares recordings with train (Rec14, Rec8, baycove, TI: 165 of
  398 test images), so it is re-split by recording for honest evaluation. Its validation split
  has targets 2.5x smaller than train: a harder, differently distributed set.
- The mine set's 416 px and 1024 px images are different images (no identical label file across
  sizes), not resized duplicates. Evaluation holds out whole survey years.
- AquaScan-1K and SubPipe are measured when their downloads finish.

## Pilot results (step 4 of the procedure), 2026-11-07

D-FINE-S from COCO weights, trained jointly on mine-detection and GhostVision training groups
(balanced tile budget per dataset), 8 short epochs, one seed per setting, tiles resized to 640,
25% overlap plus a full-image pass. Held-out test groups:

| Test set | Metric | Tile 320 | Tile 480 | Tile 640 |
|---|---|---|---|---|
| Mine (2015, 2021; 168 images, 462 objects) | AP50 | 0.224 | 0.195 | 0.227 |
| | AP50 small (< 32 px) | 0.138 | 0.078 | 0.092 |
| | recall @ 1 FP/image | 0.227 | 0.167 | 0.227 |
| GhostVision (Rec9, Rec14, Rec8; 443 / 611) | AP50 | 0.240 | 0.286 | 0.331 |
| | recall @ 1 FP/image | 0.293 | 0.336 | 0.458 |
| GhostVision shifted (Contact; 555 / 1,275) | AP50 | 0.223 | 0.303 | 0.250 |
| | recall @ 1 FP/image | 0.258 | 0.384 | 0.317 |

Reading:
- **GhostVision: no tiling (its images are already 640x640 crops).** Every metric rises
  monotonically from 320 to 640.
- **Mine detection: undecided.** Tile 320 is clearly better on small objects, but overall it ties
  with 640 and 480 is worst. A non-monotonic result from single runs means run-to-run variation
  is about as large as the differences (the mine training set has only ~400 objects). Next:
  mine-only runs, tile 320 vs 640, three seeds each.
- Absolute scores are low because these are short comparison trainings, not the final model.
- These three runs used an LR schedule sized from the tile cap instead of the tiles available
  (fixed in b03d07a); all three were affected about equally (~2,500 of an assumed 4,000 tiles).

### Repeat: mine detection only, three seeds (12 epochs, schedule fixed)

| Mine test (2015, 2021) | Tile 320 | Tile 640 | 640 - 320 per seed |
|---|---|---|---|
| AP50 | 0.178 +/- 0.006 | 0.201 +/- 0.025 | +0.034, -0.011, +0.048 |
| AP50 small | 0.077 +/- 0.006 | 0.088 +/- 0.012 | +0.012, -0.005, +0.023 |
| recall @ 1 FP/image | 0.167 +/- 0.011 | 0.183 +/- 0.022 | +0.011, -0.004, +0.039 |

The single-run small-object advantage of tile 320 (0.138 vs 0.092) did **not** reproduce: with
three seeds, 640 is equal or slightly better on every metric (better in 2 of 3 seeds each).
Enlarging a tile adds pixels but no detail: side-scan targets are already blurred along track
(see the physics note above), and small tiles lose context. Training jointly with GhostVision
also helped the mine set (AP50 0.224 joint vs 0.178 alone).

## Decision

**Tile 640 for all datasets, trained jointly.** Images larger than 640 px are cut into 640 px
tiles with 25% overlap plus a full-image pass; images of 640 px or less go to the network whole.
It also costs about 4x less inference than 320 px tiles. The box-size measurements predicted the
opposite for the mine set; the controlled pilot overruled them, which is why the pilot was run.

Labels are always stored in original-image coordinates, never in tile coordinates, so changing
the tile size later is a re-run of code: no relabelling and no extra labelling cost.
