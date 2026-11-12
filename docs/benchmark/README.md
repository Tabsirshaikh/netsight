# NetSight benchmark v0 (side-scan sonar, public data)

A protocol for scoring sonar object detectors **and the trust claims made about them** on
surveys the model has never seen. Built with `python -m netsight.benchmark --out benchmark_v0`
(writes `splits.json`, the NOAA outcome tables, `results_v0.4.json` and file hashes into the data
folder).

## Why another benchmark

Published sonar detectors report 75-99% because they test on random images from surveys they
trained on. Scored that way NetSight's pipeline matches them (0.72 vs 75% on the mine dataset);
on unseen survey years the same model scores 0.21. This benchmark therefore splits **by survey
recording**, never by image.

## Splits

`splits.json` lists, per dataset and split, the survey groups (recordings, years, sites), image
and object counts, and a SHA-256 of the sorted image list. Test groups:

| Dataset | Licence | Test groups | Notes |
|---|---|---|---|
| mine_detection_sss | see licence register | years 2015, 2021 | validation 2017 |
| ghostvision_crabpot | see licence register | Rec8, Rec9, Rec14 | validation Rec2, Rec13 |
| ghostvision Contact | see licence register | Contact recording | other sensor geometry (shift test) |
| aquascan_1k | see licence register | 2 survey days | |
| subpipe_mini2 | see licence register | 3 time windows | label convention marks seabed beside the pipe |
| ai4shipwrecks | see licence register | 13 wreck sites (official split) | not in model v0.4 training (v0.5 rejected) |
| sctd | research only | official test | not usable for a product model |

Licences: `licences/` in the repository. Research-only data never enters a product model.

## What is scored

| Claim | Metric | Script |
|---|---|---|
| detection | AP50 per test set, paired image-bootstrap CI between models | `netsight.detect.compare_run` |
| calibrated P(real) | ECE, Brier, log loss, reliability; vs B0 raw score and B1 temperature scaling | `netsight.trust.detector_calibration`, `netsight.detect.fusion_run` |
| false-alarm budget | false alarms per image held on each test survey; recall with CI | `netsight.detect.operating_run` |
| search completeness | injected-target Pd per survey, seabed stratum and range band; realism check vs real recall; vs B2 hand-set Pd | `netsight.detect.injection_run` |
| applicability gate | failure rate of flagged vs passed 50-image blocks, AUROC | `netsight.detect.withdrawal_run` |
| evidence features | fusion vs score-only on held-out log loss, ablation per feature group; vs B3 shadow-required | `netsight.detect.fusion_run` |
| position | ellipse coverage on known targets | `netsight.geo.locate.ellipse_coverage` |
| CPU | seconds per image, ONNX vs PyTorch parity | `netsight.detect.onnx_parity` |

Fixed in advance: IoU 0.5 for AP and calibration labels, IoU 0.3 for injected-target hits,
budget 1 false alarm per image, ECE limit 0.10 for "claims failed", 50-image gate blocks,
90% one-sided Clopper-Pearson lower bounds for Pd.

## NOAA contact-outcome table (CC0)

`noaa_features.csv`: expert dispositions (verified, disproved, seabed) parsed from public NOAA
Descriptive Reports, 93 surveys, about 250 decided items. They are expert decisions backed by
sonar and multibeam, not diver checks, and the not-real items are mostly "charted item not found
again". Use them for indicative calibration studies only.

## Results v0.4

See `docs/research/step2/` and `docs/research/step3/` for the numbers and their limits.
