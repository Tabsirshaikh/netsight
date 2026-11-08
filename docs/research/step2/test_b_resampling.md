# Test B: does correcting pixel geometry recover sensor shift? (research v0.2)

Date: 2026-11-08. Code: `python -m netsight.detect.resample_check`. Inference only: each image is
resampled (rows x row_scale, both axes x scale) before tiled detection; boxes are mapped back
and scored on the original labels.

## GhostVision Contact recording (test, sensor-shifted: boxes 1.32x wider than tall)

| row_scale | scale | AP50 | AP30 | recall @ 1 FA/image |
|---|---|---|---|---|
| 1.0 | 1.0 | 0.175 | 0.301 | 0.25 |
| 1.0 | 1.5 | 0.293 | 0.441 | 0.36 |
| 1.32 | 1.0 | 0.250 | 0.411 | 0.33 |
| **1.32** | **1.5** | **0.368** | **0.478** | **0.42** |
| 0.76 (wrong way, control) | 1.0 | 0.205 | 0.372 | 0.27 |
| 0.76 (wrong way, control) | 1.5 | 0.218 | 0.366 | 0.30 |

Un-stretching in the right direction plus enlarging more than doubles AP50 (above v0.1's 0.288);
the wrong-way control barely moves. Caveat: 1.32 comes from the test labels' box aspect and six
settings were tried on this test set, so 0.368 is optimistic.

## Same x1.5 enlargement on every validation set (fair check, no test data)

| Validation set | x1.0 | x1.5 | change |
|---|---|---|---|
| mine | 0.302 | 0.158 | -0.14 |
| ghostvision | 0.344 | 0.270 | -0.07 |
| aquascan | 0.476 | 0.446 | -0.03 |
| sctd | 0.827 | 0.593 | -0.23 |
| subpipe | 0.682 | 0.832 | +0.15 |

## Conclusion

Pixel geometry matters a lot, but there is no single global correction: enlarging helps the
shifted recording and SubPipe and hurts the others. The rule must be **per survey: resample each
survey to the pixel size and aspect the model was trained on**, with the factors taken from the
sonar metadata (range, samples per ping, ping rate, vessel speed), never from labels. Surveys
whose geometry cannot be determined, or falls outside the training range, go to the applicability
gate (indicative / withdrawn). This makes Track 2 (resampling module) worth building.
