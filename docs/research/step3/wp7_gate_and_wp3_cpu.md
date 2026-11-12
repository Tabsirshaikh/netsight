# WP7 applicability gate measurement, and WP3 CPU/ONNX check

Date: 2026-11-12. Research model v0.4, dump `runs/calib_v0.4`.

## WP7: does the gate flag the blocks where claims fail?

Code: `netsight.trust.withdrawal_eval`, `python -m netsight.detect.withdrawal_run`.
Result: `runs/withdrawal_v0.4.json`.

Units: 32 blocks of 50 consecutive images from held-out test surveys (6 test sets). Per block the
geometry gate (envelope from validation surveys of the same kind of data) gives *calibrated* or
*indicative* plus a continuous out-of-envelope distance. A block's claims **failed** when, fixed
before looking: calibrated-probability ECE > 0.10, or recall at 1 false alarm per image below
the lower end of the validation recall interval (blocks with at least 10 objects).

| | blocks | claims failed | rate (95% CI) |
|---|---|---|---|
| gate flagged (indicative) | 15 | 14 | 0.93 (0.68-1.00) |
| gate passed (calibrated) | 17 | 6 | 0.35 (0.14-0.62) |

AUROC of the out-of-envelope distance for "claims failed": **0.71**.

- Every failure was a recall shortfall; no block's calibration error exceeded 0.10 (largest 0.065,
  all on the sensor-shifted Contact recording).
- All Contact (other sensor) and mine (2015, 2021) blocks were flagged, correctly.
- Missed failures: four GhostVision blocks (recordings Rec14 and Rec9) with recall 0.18-0.29,
  same sensor and same geometry, so a geometry check cannot see them; and both SubPipe blocks
  (label convention problem). Recall dips within one sensor need a different signal (WP13
  seeded targets, or the per-survey completeness map).
- One false flag: one AquaScan block (recall 0.54, fine).

Plan acceptance ("flagged surveys measurably worse"): met, flagged blocks fail 93% vs 35%.
Not yet met: a withdrawal test on a truly held-out *sensor family* (only one other-sensor
recording exists in the public data).

## WP3: ONNX export and CPU inference

Code: `netsight.detect.onnx_export` (export, CPU predictor, benchmark), `netsight.detect.onnx_parity`.
Model: `runs/onnx_v0.4/model.onnx` (41 MB, opset 17) with a sidecar JSON (model id, hashes).

| | PyTorch, CPU | ONNX Runtime, CPU |
|---|---|---|
| seconds per image (8 test images, 0.6-2 MP, tiled 640 px) | 1.15 | **0.70** |
| megapixels per second | | 1.21 |

Laptop CPU: AMD Ryzen (16 threads), no GPU. Detection counts at score 0.3 were identical on all
8 images; the largest top-score difference was 0.000003.

At 5 cm pixels a 100 m swath by 100 m of track is about 4 MP, i.e. roughly 3.3 s per 100 m of
track on this laptop (without flip TTA; TTA doubles it). Offline: the ONNX path needs no network
and no GPU.
