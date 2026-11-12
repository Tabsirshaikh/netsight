# WP6: measured detection probability by target injection (research model v0.4)

Date: 2026-11-12. Code: `netsight.trust.injection`, `netsight.trust.pd_report`,
`python -m netsight.detect.injection_run`. Runs: `runs/injection_v0.4` (seed 0) and
`runs/injection_v0.4_s1` (seed 1), up to 300 test images per dataset.

## Method

Per held-out test image, two targets are pasted where the detector saw nothing before and no
labelled object lies, on insonified seabed only (seabed mask: local mean at least half the
image's 75th-percentile brightness):

- **transplant**: a real labelled object (with a padded, feathered margin that keeps its shadow)
  cut from *another* image of the same test survey, scaled to the local seabed level;
- **parametric**: a block with highlight and acoustic shadow, or a flat textured patch, at the
  dataset's median object size.

The detector runs once on the modified image. A target counts as detected when a detection with
IoU >= 0.3 scores at or above **the survey's own operating threshold** (label-free count
threshold, 1 false alarm per image), i.e. the same rule the reported contacts use. A pre-existing
detection can never be credited (positions overlapping base detections are excluded).

A bug found on the way: the first smoke run placed targets uniformly over the image, including
the dark water column at nadir; transplants were then found 5% of the time against 64% real
recall. Restricting placement to seabed fixed it (50% vs 64%).

## Realism check: transplant Pd vs recall on real objects (same threshold, IoU 0.3)

| Test set | real recall (95% CI) | transplant Pd seed 0 | seed 1 | verdict |
|---|---|---|---|---|
| mine | 0.19 (0.16-0.23) | 0.29 (0.22-0.36) | 0.32 | consistent / slightly optimistic |
| ghostvision | 0.40 (0.36-0.44) | 0.47 (0.41-0.53) | 0.45 | consistent |
| ghostvision_shift (Contact) | 0.25 (0.23-0.28) | 0.31 (0.26-0.37) | 0.35 | consistent / slightly optimistic |
| aquascan | 0.64 (0.58-0.70) | 0.52 (0.45-0.58) | 0.55 | consistent |
| subpipe | 0.72 (0.58-0.83) | 0.23 (n=30) | 0.31 | pessimistic |
| sctd | 0.76 (0.67-0.84) | 0.26 (n=23) | 0.37 | pessimistic |

On four datasets transplant Pd is within about 0.1 of real recall (two of them up to 0.13 above
it in one seed). On SubPipe and SCTD it is far too low: pipelines and wrecks fill most of the
image and depend on context, and few free seabed positions exist (23-37 trials).

**Parametric targets were never detected: 0 of about 1,000 in each seed, on every dataset.** The
detector learned what real objects look like, not "bright patch with a shadow". Simple reference
shapes therefore cannot stand in for S-44-style reference targets with this detector: Pd for a
"1 m cube" needs either realistic rendering or the seeded-target trial (WP13). The dashboard's
completeness map uses transplanted real objects from validation surveys for this reason.

## Pd depends on the seabed

Transplant Pd by local seabed texture (tertiles of the coefficient of variation around the
target), seed 0:

| Test set | smooth | medium | rough |
|---|---|---|---|
| aquascan | 0.74 | 0.55 | 0.34 |
| ghostvision | 0.59 | 0.46 | 0.38 |
| mine | 0.35 | 0.22 | 0.30 |
| ghostvision_shift | 0.36 | 0.35 | 0.24 |

## Baseline B2 (hand-set Pd curve, max over passes) vs measured Pd

B2 = 0.95 / (1 + exp(12 (r - 0.85))), zero inside a 5% nadir gap, r = relative range from a
centre nadir (verified for AquaScan; assumed for the others). Both seeds pooled, transplants:

| Test set | near (0-0.33) B2 / measured [95% CI] | middle (0.33-0.66) | far (0.66-1) |
|---|---|---|---|
| aquascan | 0.95 / 0.43 [0.28-0.58] | 0.93 / 0.59 [0.53-0.64] | 0.69 / 0.47 [0.38-0.55] |
| ghostvision | 0.82 / 0.47 [0.41-0.53] | 0.93 / 0.41 [0.35-0.48] | 0.70 / 0.54 [0.44-0.63] |
| mine | 0.94 / 0.39 [0.29-0.51] | 0.93 / 0.28 [0.21-0.34] | 0.72 / 0.24 [0.12-0.41] |
| ghostvision_shift | 0.87 / 0.29 [0.23-0.36] | 0.93 / 0.36 [0.30-0.43] | 0.60 / 0.33 [0.26-0.40] |

Every B2 value lies above the measured 95% interval: a hand-set Pd grid overstates search
completeness by 0.2-0.65 on every dataset and range band. This is the pitch line for WP6.

## Limits

- Transplants come from the same test survey (other images), so they match that survey's
  sensor and objects; Pd for other object types needs other donors.
- Pasting cannot reproduce the object-seabed interaction (burial, scour, true shadow geometry
  on the new slope); the realism check is the guard, and SubPipe/SCTD fail it.
- Per-survey completeness maps (dashboard) have few trials per cell; cells under 5 trials are
  reported as insufficient, never filled in.
