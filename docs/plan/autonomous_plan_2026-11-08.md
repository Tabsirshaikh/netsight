# Autonomous work plan, 2026-11-08 (~10 hours, user away)

Goal set by the user: the **research model** must be as good as possible and trained as fast as
possible; research it myself, improve everything, use GPT / Gemini via OmniRoute when useful,
watch usage limits. The product model stays deferred (memory: netsight-product-model-deferred).

## State at start (03:45)

- Branch `step-2a-trust` (pushed). Research model v0.1 done: `netsight-data/runs/research_v0.1`
  (best epoch 12; results in `docs/research/step2/research_model_v0.1.md`).
- Running: replication `netsight-data/runs/replicate_mine/{random,years}` (module
  `netsight.detect.replicate`), literature survey (scratchpad `hunt/paper_survey.py`, output
  `hunt/survey2/papers.jsonl`, model cx/gpt-6-luna-medium, quote-checked).
- Pixel cache built: `netsight-data/cache/pixels` (11,152 images, 8.5 GB), class `PixelCache` in
  `netsight.detect.pixel_cache`; not yet used by `netsight.detect.pilot`.
- Datasets: mine, ghostvision, aquascan, subpipe, sctd (research-only) in `pilot.build_splits`.
  SWDD inspected and excluded (test-only).

## Phase A: read the running experiments (until ~04:30)

1. **Replication.** Rule: random-split mine AP50 >= ~0.70 -> pipeline competitive, the gap is the
   test protocol; continue. Clearly below -> find the pipeline weakness first (compare with the
   survey's best pipelines: input size, epochs, model size, augmentation; quick mine-only runs).
2. **Survey.** Spot-check 5 records against their quoted pages (especially split protocol: all
   18 said "unclear"). Write `docs/research/step2/literature_pipelines.md`: table of verified
   papers + comparison with our pipeline + techniques worth testing. GPT-6-luna may draft from
   the verified JSON; I check every number against the record.

## Phase B: v0.2 code, test-first (~04:30-06:00)

1. Use `PixelCache` in `pilot` when the cache exists (faster, same pixels).
2. Early stopping: patience of 3 validations; larger validation sets (~250 images per dataset).
3. Minimum share per dataset in `balanced_tiles` (repeat tiles with new augmentation seeds) so a
   small dataset (mine) gets >= ~15% of each epoch.
4. Report AP at IoU 0.3 as well as 0.5 (elongated pipelines have ambiguous extents).
5. Apply any pipeline fix found in phase A.

## Phase C: train v0.2 (~06:00-10:00)

`--datasets mine,ghostvision,aquascan,subpipe,sctd --tile 640`, early stopping, model id
`netsight-dfine-s-research-v0.2`. While it trains (CPU only, new files): connect detector scores
to the trust layer: fit calibrators (Platt/beta/isotonic) on validation predictions, report
reliability, ECE / D-ECE and Brier per dataset on test predictions.

## Phase D: compare and decide (~10:00-13:00)

v0.2 vs v0.1 on the **same test sets**. Call v0.2 better only if the mean test AP50 rises and no
dataset drops by more than ~0.03 (noise). Write `docs/research/step2/research_model_v0.2.md`.
If time remains: per-dataset short fine-tune from the joint model; repeat the comparison.
End with a progress summary for the user.

## Working rules

- Never: train the product model, delete raw data, commit data or secrets, edit code that a
  running training imports in a way that breaks importing (Windows workers re-import each epoch;
  prefer new files while a run is active).
- Every change test-first; full suite + ruff before each commit; push after each commit.
- Usage: short tool outputs, background jobs with notifications instead of polling, no large
  file reads. If a usage-limit message appears, stop cleanly; this file is the place to resume.
- Log progress below as it happens.

## Budget and delegation (user, 03:50)

- Claude weekly usage was at 78%: keep my own token use low.
- **Model work (anything that makes the detector better: training, data balance, evaluation,
  pipeline fixes) I do myself.** Everything else goes to other agents: web app / dashboard and
  other self-contained code to `cx/gpt-6.1-sol-medium`; literature, data surveys and drafting to
  `cx/gpt-6-luna-medium`; web-heavy hunts to Gemini. I review what they produce.
- If phases A-D finish early, continue with the next work packages of `docs/plan/final.md`
  (WP4 evidence features, WP5 calibration + operating point on real detector output, WP7 gate,
  WP9 evidence pack), in that order.

## Progress log

- 03:45 plan written; replication and survey running.
- 04:05 Replication (mine set, one recipe): scored on its own training images 0.721 AP50 (paper:
  "mAP of 75%" on its 1,170 images) -> pipeline competitive; random held-out images 0.528;
  held-out survey years ~0.2 (final "years" run pending). Decision: GO, continue to v0.2.
  Minor: replicate.py does not save the image processor; to fix.
- 04:30 Replication complete: training images 0.721 / random held-out 0.528 / held-out years
  0.209 (docs/research/step2/replication.md). Phase B code done: shared balanced_tiles with a
  minimum share (0.15, max 4x repeat), EarlyStopper (patience 3 validations), val 250 images per
  dataset, PixelCache in training, AP at IoU 0.3 reported. Next: train v0.2.
- 05:10 Phase A done. Literature survey: 21 quote-verified papers (docs/research/step2/
  literature_pipelines.md); every split found is a random/ratio image split, none held-out.
  v0.2 training started (5 datasets, ~14 tiles/s, ~10 min/epoch, early stopping).
  Phase C side task: detector -> trust-layer calibration module delegated to GPT-6.1-sol.
- 05:40 Calibration module reviewed and committed (best_method may now keep raw scores when no
  calibrator beats them). calibrate_run.py: dump val/test predictions per dataset, report
  calibration fitted on own-dataset val and on pooled val. v0.1 dump running. WP4 classical
  evidence features (shadow/height, mesh FFT/Gabor, ridge+Hough lines, ripple structure tensor,
  background-statistics anomaly baseline) delegated to GPT-6.1-sol.
- 06:50 v0.1 calibration on real held-out detections (detector_calibration_v0.1.md): raw scores
  overconfident (worse than constant on 5/6 test sets); beta/Platt calibration gives positive
  Brier skill on 5/6; pooled calibrator ~ per-dataset. Flip TTA chosen on val (hflip+WBF),
  confirmed on test +0.02 mean AP50 (tta_v0.1.md). WP4 evidence features committed.
  v0.2 at epoch 3 (val after epoch 2: mine 0.232, gv 0.162, aq 0.255, sp 0.790, sctd 0.788).
