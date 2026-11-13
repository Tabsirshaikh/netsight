# Trust-layer drawbacks 6-12: research and fixes (2026-11-13)

The model is frozen (v0.4). This note takes the trust-layer drawbacks one by one: find the
cause, test a fix cheaply, keep it only if it holds on held-out test surveys. Scripts used for
the experiments: `C:\Users\524ta\netsight-agents\trust\` (outside the repo); results in
`netsight-data/runs/trust_*`.

## Summary

| # | Drawback | Cause found | Result |
|---|---|---|---|
| 6 | No Pd for a standard "1 m cube" target | the detector learned real objects, not shapes | drawn targets rejected for good; Pd by size band from real objects |
| 7 | Transplant Pd realistic on only 4 of 6 datasets | extended objects need context; other-sensor optimism | refused for pipelines/wrecks; upper bound on gate-flagged surveys |
| 8 | Gate misses recall drops within one sensor | the drop is not visible without labels | 30-image recall audit: catches 82% of drops, 2% false flags |
| 9 | Calibration on another sensor = baseline | scores of real objects shift; prior methods cannot see it | 50-contact random audit: ECE 0.083 -> 0.043 |
| 10 | Evidence fusion makes P(real) worse | survey-specific feature levels | normalising per survey removes blow-ups, still no gain: stays off |
| 11 | Completeness far too low on small uploads | mixed / cross-survey donor library, not the threshold | donors = objects the operator marks in 30 audit images: matched real recall in 10 of 14 audits |
| 12 | False-alarm budget per image, not per km2 | no area | per-km2 budget over insonified seabed for georeferenced surveys (built) |

## 6. Reference targets ("1 m cube")

Test: 150 held-out test images per dataset, same-survey threshold (1 false alarm per image),
detection = IoU >= 0.3 at or above it.

- Data-driven rendered targets: highlight and shadow strength sampled from real labelled
  objects, near-edge brightness gradient, blur, host-matched speckle, shadow on the far-range
  side: detected 0/149 (AquaScan), 3/149 (GhostVision), 2/148 (mine), 0/148 (Contact). Together
  with the 0/~2,000 of the simple blocks in WP6, drawn targets are rejected for good. The DRDC
  augmented-reality method (Defence R&D Canada 2017, three CMRE trial sites) works for
  hand-crafted ATR; a learned detector does not respond to drawn shapes.
- Real objects rescaled: 0.5x gives Pd 0.28 / 0.15 / 0.03 / 0.08 against real recall of the
  smallest third of objects 0.40 / 0.36 / 0.16 / 0.06 (pessimistic, same direction); 2x is not
  reliable (up-sampling blurs: 0.60 / 0.33 / 0.22 / 0.70 against 0.81 / 0.48 / 0.29 / 0.46).

Decision: Pd for a target size is reported from real objects of that size band (no
up-scaling). A "1 m cube" figure is never produced from a drawn shape.

## 8. Recall drops the gate cannot see

The six blocks that pass the gate yet fail are real failures (one-sided binomial against
validation recall: GhostVision Rec14 both blocks p <= 0.002, Rec9 block 3 p = 0.009; SubPipe
two blocks = label convention; one SCTD block borderline). Label-free signals tested, AUROC for
"failed" among gate-passed blocks:

| signal | AUROC |
|---|---|
| self-donor Pd (survey's own confident detections pasted elsewhere) | 0.23 |
| mean top score per image | 0.70 (mostly dataset differences) |
| seabed texture | 0.31 |
| image statistics (coverage, level, speckle contrast, sharpness) | 0.59-0.68 |
| geometry gate distance | 0.35 |

Rec14 looks like the GhostVision recordings that work on every image measure. Garg et al. 2022
(ATC) prove that accuracy under shift cannot be estimated from unlabelled data in general
without assumptions on the shift; our failures fit that.

Fix: recall audit. The operator marks every object in a few random images; a one-sided
binomial test compares recall there with validation recall. Simulated on the test blocks
(SubPipe excluded, label convention), 300 draws each:

| images audited | catches failing blocks | false flags on fine blocks |
|---|---|---|
| 5 | 0.29 | 0.01 |
| 10 | 0.46 | 0.02 |
| 20 | 0.67 | 0.02 |
| 30 | **0.82** | 0.02 |

Code: `netsight.trust.audit.recall_audit` (default 30 images, at least 10 objects).

## 9. Calibration on another sensor

Measured on all detections with score >= 0.1 (IoU 0.5 labels): Contact ECE beta 0.083,
temperature 0.037.

- Label-free prior adjustment (Saerens EM per survey): rejected. It overestimates the real rate
  on mine (0.26 vs 0.09) and SCTD (0.52 vs 0.31) and goes the wrong way on Contact (0.066 vs
  0.151): on the other sensor real objects score lower (a change in p(score | real)), which no
  prior adjustment can see.
- Corrected (conservative v2) labels: the deployed calibrator underestimates P(real) (Contact
  mean 0.056 vs 0.187 real), because the validation labels it was fitted on also miss objects.
  Refitting on corrected labels of the other two sets helps GhostVision and Contact a little
  (beta ECE 0.122 -> 0.091 on Contact) but hurts mine: calibration does not transfer cleanly
  between datasets with any labels.
- Operator audit: refit a logit slope and intercept (penalised towards no change) on N
  decisions from the new survey. Contact: random 50 -> ECE 0.044, random 100 -> 0.035; the
  operator's top 100 -> 0.178 (worse: a top-ranked sample only covers the easy end). On surveys
  that pass the gate the update adds nothing (GhostVision 0.028 -> 0.032).

Fix: `netsight.trust.audit` - a random 50-contact audit, asked for only when the gate says
indicative; `calibration_check` tells whether the shown probabilities held (it flagged Contact
in 11 of 20 audits, GhostVision in 3 of 20). Verified with the module on real data: Contact
0.083 -> 0.043.

## 10. Evidence fusion

Held-out log loss (lower is better), fusion fitted on validation:

| test set | score only | fusion, raw features | fusion, features normalised per survey |
|---|---|---|---|
| AquaScan | 0.085 | 0.131 | 0.085 |
| GhostVision | 0.277 | 0.290 | 0.289 |
| mine | 0.279 | 0.288 | 0.288 |
| SubPipe | 0.201 | 0.331 | **0.187** |
| SCTD | 0.337 | 1.160 | 0.357 |
| Contact | 0.448 | 0.464 | 0.476 |

Normalising removes the large failures but fusion still wins on 1 of 6 sets. Decision
unchanged: evidence features are measurements for the expert, never inputs to P(real).

## 11. Completeness on small uploads

The 0.19-vs-0.64 gap is not the threshold: on random 8-image uploads the count threshold is
within 0.01 of the whole-survey threshold and real recall stays 0.64. It is the donor library.
Pd of pasted objects by donor source (AquaScan / GhostVision / mine / Contact):

| donors | AquaScan | GhostVision | mine | Contact |
|---|---|---|---|---|
| same survey, labelled (WP6) | 0.51 | 0.44 | 0.22 | 0.25 |
| validation surveys, same dataset | 0.33 | 0.19 | 0.16 | 0.20 |
| other datasets (what the "general" library mixed in, incl. synthetic) | 0.15 | 0.22 | 0.02 | 0.30 |
| real recall | 0.64 | 0.40 | 0.19 | 0.25 |

Validation objects are not harder where they were recorded (validation recall 0.59 AquaScan,
0.46 GhostVision): they lose detectability when moved to another survey. Tried and rejected:

- self donors (the survey's own flagged detections): too optimistic (mine 0.42 vs 0.19,
  Contact 0.56 vs 0.25) because they are the easy objects;
- matching donor contrast to the host seabed: +0.03 to +0.08 on three sets, -0.06 on Contact,
  still far below real recall;
- anchoring the level to validation recall and keeping only the injected pattern: mean error
  against real recall per range/texture band 0.220 vs 0.197 raw (validation recall does not
  carry over: mine 0.60 validation vs 0.19 test).

## 12. Budget per km2

Built: `netsight.trust.area_budget`, dashboard `budget_unit=km2`. When every image is a GeoTIFF
in a projected CRS, the count rule flags at most floor(budget x insonified seabed km2); other
uploads get a clear refusal. Georeferenced per-image runs also report flagged contacts per km2.
The validation recall shown is taken at the equivalent per-image budget (validation images have
no pixel size) and says so.

### The fix: donors from the survey's own audit (sections 7 and 11)

The recall audit (section 8) already has the operator mark every object in 30 random images.
Those objects are used as the donors, pasted into the survey's other images. Two random audits
per test survey (surveys with at least 60 images), Pd at the survey threshold vs real recall on
the other images:

| survey | Pd (two audits) | real recall | |
|---|---|---|---|
| AquaScan 2025-11-23 | 0.65, 0.54 | 0.66, 0.69 | agrees |
| GhostVision Rec8 | 0.48, 0.57 | 0.50, 0.48 | agrees |
| GhostVision Rec9 | 0.39, 0.54 | 0.44, 0.45 | agrees |
| GhostVision Rec14 (the hard recording) | 0.39, 0.41 | 0.30, 0.29 | real value inside the 95% interval, slightly high |
| mine 2015 | 0.13, 0.11 | 0.16, 0.15 | agrees |
| Contact (other sensor, gate-flagged) | 0.47, 0.41 | 0.26, 0.25 | about 0.2 too high |
| SCTD (wrecks; only 9-14 placements) | 0.21, 0.22 | 0.76, 0.74 | fails |

Decisions (built in the dashboard, `POST /api/packs/{id}/audit`):

- completeness is measured from the operator's audit objects; without an audit, a single-profile
  validation library is used and labelled a pessimistic estimate; the mixed "general" library
  and synthetic objects are no longer used;
- completeness is refused for pipeline and wreck profiles (section 7: pasted extended objects
  lose their context);
- on gate-flagged surveys completeness is labelled an upper bound (Contact: +0.2).

## What is still open

- Absolute Pd for a standard reference target ("1 m cube") is not available from drawn shapes
  with this detector; size-banded Pd from real objects is the honest substitute.
- No label-free signal sees a within-sensor recall drop (Rec14); the audit needs an operator.
- Calibration on a new sensor needs a 50-contact audit; there is no label-free repair.
- Audit sizes (50 contacts, 30 images) were chosen from simulations on public test surveys;
  they need checking on the first real customer survey.
