# Detector score calibration on real held-out detections (research model v0.1)

Date: 2026-11-08. Model `runs/research_v0.1/model` (v0.1 was not trained on SCTD).
Code: `python -m netsight.detect.calibrate_run dump|report|ap`. Detections with score >= 0.05;
a detection is correct if IoU >= 0.5 with an unmatched object. Calibrators are fitted on
validation detections (held-out groups) and scored only on test detections (other held-out
groups). Missed objects have no score; they belong to recall, not calibration.

Few detections are correct (0.4-7%), so ECE alone flatters every method. We therefore also report
**Brier skill** = 1 - Brier / Brier of always predicting the test base rate (> 0 = more useful
than a constant).

| Test set | Correct | Raw ECE | Raw Brier skill | Best (own val) | ECE | Brier skill | Best (pooled val) | ECE | Brier skill |
|---|---|---|---|---|---|---|---|---|---|
| mine (held-out years) | 3.2% | 0.127 | -0.65 | beta | 0.016 | +0.07 | beta | 0.011 | +0.07 |
| ghostvision | 4.9% | 0.111 | -0.12 | beta | 0.004 | +0.22 | isotonic | 0.013 | +0.21 |
| ghostvision_shift (Contact) | 7.3% | 0.085 | +0.11 | temperature | 0.019 | +0.23 | temperature | 0.019 | +0.23 |
| aquascan | 1.5% | 0.111 | -0.92 | beta | 0.005 | +0.35 | platt | 0.011 | +0.30 |
| subpipe | 0.4% | 0.127 | -8.74 | beta | 0.013 | -2.01 | beta | 0.024 | -2.74 |
| sctd (not in v0.1 training) | 0.6% | 0.106 | -2.60 | beta | 0.002 | +0.14 | platt | 0.007 | +0.03 |

## Findings

1. **Raw detector scores are overconfident.** On 5 of 6 test sets they are worse than a constant
   guess. Showing a raw score as "confidence" would mislead a user.
2. **Calibration fixes most of it.** Fitted on other surveys' validation detections, beta/Platt
   calibration gives positive skill on 5 of 6 test sets and ECE <= 0.02.
3. **One pooled calibrator transfers almost as well as a per-dataset one** (same skill on mine,
   GhostVision and its shifted set). A new survey does not need its own labels to get honest
   scores, provided it resembles the pooled data. The applicability gate must catch when it does
   not.
4. **Skill is small where detection is weak** (mine on unseen years +0.07): calibration makes
   scores honest, it cannot make a weak detector strong.
5. **SubPipe remains worse than constant** even after calibration: its labels mark the seabed
   beside the pipe, not the pipe+shadow the model finds (AP at IoU 0.3 = 0.52 vs 0.004 at 0.5).
   This is a label-convention mismatch, so a per-dataset IoU rule or relabelling is needed before
   SubPipe calibration means anything.

Next: repeat on v0.2 once trained; operating point (LTT) at a false-alarm budget on these
calibrated scores.
