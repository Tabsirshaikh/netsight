# Improving the detector: diagnosis, data audit, literature and ranked plan

Date: 2026-11-13. Model: research v0.4 (D-FINE-S, COCO start, 640 px tiles, five datasets,
weight EMA). Goal: real gains on **unseen surveys**, not +0.01 on a random split.

## 1. What was already tried (docs/research/step2)

| Change | Result on held-out surveys |
|---|---|
| tile 320 / 480 / 640 (3 seeds) | 640 best; smaller tiles add pixels, not detail |
| balanced dataset shares (v0.2) | real gain (mine +0.045, AquaScan +0.044) |
| weight EMA (v0.4) | real gain on 3 sets, none worse |
| random zoom 0.5-1.5x (v0.3) | worse on 4 sets |
| + AI4Shipwrecks (v0.5) | worse on 5 sets |
| per-dataset fine-tune | helps its own data only (Contact 0.26 -> 0.40) |
| flip test-time augmentation | +0.02-0.04 |
| per-survey pixel-geometry resampling | large when geometry is known (Contact 0.18 -> 0.37) |
| more training recordings | still rising: ~+0.05 AP50 per doubling |

## 2. Where v0.4 actually fails (new)

Code: `netsight.detect.error_breakdown`, `netsight.detect.rank_check`.

**The detector sees the objects; it ranks them below clutter.** A proposal with IoU >= 0.3 exists
for 91-100% of test objects, versus 0.4-13% for the same box moved to a random place (control);
the object's best proposal is usually ranked 1st-5th in its image (median rank 0-4).

| Test set | objects/image | recall @ 1 true FA/image | recall at any score (IoU 0.5) | cap of the count rule (1 flag/image) |
|---|---|---|---|---|
| mine | 2.75 | 0.21 | 0.78 | 0.36 |
| GhostVision | 1.38 | 0.47 | 0.94 | 0.73 |
| Contact (other sensor) | 2.30 | 0.32 | 0.71 | 0.44 |
| AquaScan | 1.00 | 0.69 | 0.94 | 1.00 |
| SubPipe | 0.72 | 0.42 | 0.81 | 1.00 |
| SCTD | 1.10 | 0.92 | 0.96 | 0.91 |

Visual audit of the 20 highest-scoring false alarms per set:
- **mine**: all 20 are mine-like objects with shadows, visually identical to labelled ones, with no
  label. The 2015 test images hold many such objects; training-year "empty" images really are
  plain seabed. Either the test labels are incomplete or only some object types were labelled:
  mine AP and recall are understated by an unknown amount. Needs an expert relabel of the test years.
- **GhostVision / Contact**: the model draws object **plus shadow**; GhostVision labels are
  object-only (median aspect 0.9-1.1 in every recording). Mine and SubPipe labels include the
  shadow. One class trained on two box conventions mixes them. Upper bound of fixing it
  (AP at IoU 0.3 vs 0.5): GhostVision 0.36 -> 0.48, Contact 0.26 -> 0.38.
- The count rule (flag at most 1 per image) caps recall when surveys are dense: mine can never
  exceed 0.36. This is a trust-layer choice, not a model limit.

## 3. Data audit (new)

Code: `netsight.datasets.quality_check` (difference hash, confirmed by thumbnail correlation >= 0.97).

| Dataset | test images duplicating training | note |
|---|---|---|
| mine, GhostVision, Contact, AI4Shipwrecks | 0 | honest test |
| AquaScan | 2 of 243 | negligible |
| SubPipe | 11 of 79 (val 40 of 229) | adjacent video frames across the time split |
| **SCTD** | **22 of 100** (val 6 of 40) | official split leaks: SCTD 0.82 is inflated |

Label sanity: no duplicate boxes; a handful of degenerate or negative-coordinate boxes. Mine
training years hold only 176 boxes (909 images); the test years hold 462: most mine objects are
in the test set.

Ensembles of existing models (v0.4 with v0.2, v0.3, fine-tunes; WBF): mixed, small (-0.075 to
+0.045 per set). Variance between models is not the bottleneck.

## 4. New data (verified from official pages)

| Dataset | What | Licence | Use |
|---|---|---|---|
| ApertureLab synthetic SSS v1.0 (HF idg101/...) | 250 simulated EdgeTech 4125i swaths, COCO masks: ghost_net 194, rope_line 144, container 103, wreck 91, tire 392, pipe 118, natural (rock) 512; raw XTF, shadow polygons | ALSD-1.0: commercial use allowed with attribution, except named excluded parties (some US Navy offices, Kitware) | the only source for net / rope / tyre / container classes; synthetic, no electronic noise |
| Side-scan boulder recognition (Zenodo 15167183) | ~2,000 boulder images, boxes (boulder, shadow, boulder+shadow) | CC-BY-4.0 | hard negatives or a rock class |
| PANGAEA PS124 OFOBS side-scan; NOAA NCEI / USGS raw XTF | large unlabelled archives | CC-BY / public domain | self-supervised pretraining, self-training |

No public **real** side-scan labels exist for nets, ropes or tyres (Stolte et al. 2022 data
unreleased). Classes possible from public real data: pot/trap (GhostVision), wreck (SCTD,
AI4Shipwrecks), aircraft and person (SCTD, AquaScan), mine-like (mine dataset), pipe (SubPipe),
rock (boulders), wall/structure (SWDD).

## 5. Literature (quote-checked; method_run, method_run2)

Large measured gains when the test domain differs, little labelled data:
- self-training / mean teacher on unlabelled target images: Probabilistic Teacher Cityscapes ->
  Foggy 31 -> 47.1, KITTI -> Cityscapes 46.4 -> 60.2, Sim10k -> Cityscapes 44.5 -> 55.1;
- diversity augmentation for single-domain generalisation: Clipart 25.7 -> 38.9, Comic 18.9 -> 33.2;
- diffusion-generated side-scan images: AP50 0.74 -> 0.86 (random split only, YOLOv8n);
- bigger D-FINE: S -> L +5.5 COCO AP, Objects365 pretraining +2.2 (in-domain, 2.3x slower);
- generic self-supervised pretraining: modest (+0.5 to +4 points) and costly.
All natural-image or random-split evidence; each must be verified on our held-out surveys.

## 6. Experiments running / planned

See section 7 (filled in as results arrive).
