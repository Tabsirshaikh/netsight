# Autonomous plan, part 2 (2026-11-08, from ~15:00, ~10 hours, user away)

Read this first after any context reset. Progress log at the bottom; append after every step.
Earlier plan and log: `autonomous_plan_2026-11-08.md`. Results so far: `docs/research/step2/`.

## Where we are

- **Research model = v0.4** (`runs/research_v0.4/model`): v0.2 recipe + weight EMA 0.9998.
  Test AP50: mine 0.223, GhostVision 0.361, Contact 0.256, AquaScan 0.615, SubPipe 0.231,
  SCTD 0.817 (research_model_v0.4.md). Product model stays deferred: never train it.
- Test B done: per-survey pixel-geometry correction recovers sensor shift (Contact 0.175 ->
  0.368); no global zoom works (test_b_resampling.md).
- Test A (learning curve, GhostVision 2/5/10/21 recordings, 10 epochs, EMA) running:
  `runs/curve_gv_k{2,5,10,21}`, background job writes one line per k.
- Trust layer on real detections (v0.1): calibration works (positive Brier skill 5/6), label-free
  count threshold holds the FA budget 12/12, validation-frozen thresholds do not.
- We have NOAA descriptive reports + parsed contacts for ~100 surveys
  (`netsight-data/raw/noaa/*/contacts.csv`), but **no raw side-scan files (XTF) yet**.

## Rules (unchanged)

- Model work: Claude. Non-model code: GPT-6.1-sol (`cx/gpt-6.1-sol-medium` via
  scratchpad `gemini_ask.py`, env GEMINI_MODEL); research/surveys: GPT-6-luna
  (`cx/gpt-6-luna-medium`) or Gemini. Review every GPT file: run tests + ruff, read the logic.
- Choose settings on validation only; test sets are measured once per decision. Compare models
  with `compare_run` (paired bootstrap). Accept a model only if mean test AP50 rises and no test
  set drops by more than ~0.03 (the Contact sensor-shift set is reported but judged with test B).
- Never: train the product model, delete raw data, commit data or secrets, put the OmniRoute key
  anywhere but the env var, mix research_only data into product paths, edit a module a running
  training imports (pilot.py, dfine.py, ema.py, training_tiles.py, pixel_cache.py) - new files only.
- Commit + push after each step; plain, honest docs (state what failed).
- Usage: keep own outputs short, background jobs + notifications, no big file reads. If usage
  runs low, do steps in priority order P1 > P2 > P3 > P4 > P8 and stop the rest.

## Steps

### P1. Finish test A (0-1.5 h)
1. When the job finishes: table of test AP50/AP30 (GhostVision held-out + Contact) vs number of
   recordings and images. Write `docs/research/step2/test_a_learning_curve.md`.
2. Decision: **rising** (k=21 clearly above k=10, i.e. > ~0.02) -> more surveys pay off: do P6 at
   full effort. **Flat** -> more of the same data won't help: P6 only as the data-check part;
   spend effort on P5 (geometry gate) and P7.
3. One seed only: say so; if time allows at the end, rerun k=10 and k=21 with group-seed 1.

### P2. Per-dataset fine-tune of v0.4 (GPU, ~1.5 h) - Claude
1. For mine and GhostVision (weakest / most important): `pilot --init-from runs/research_v0.4/model
   --datasets <one> --lr 5e-5 --ema 0.9998 --epochs 8 --eval-every 2 --patience 2`.
2. Dump test predictions, `compare_run` vs v0.4 on that dataset. Keep a fine-tuned model only if
   its own test set improves with CI above zero; it is a per-dataset specialist, v0.4 stays the
   general model. Manifest inherits v0.4's datasets (already implemented).
3. Doc: `docs/research/step2/finetune_v0.4.md`.

### P3. Trust layer on v0.4 (GPU ~45 min + CPU) - Claude
1. `calibrate_run dump` (val+test, no TTA exists as `calib_v0.4`; add val if missing) and
   `--tta hflip` dump; `report` for calibration; `operating_run` (frozen vs label-free count
   threshold, survey-level bound).
2. Doc: `docs/research/step2/trust_v0.4.md` (calibration, TTA gain, FA budget held, recall).

### P4. End-to-end demo evidence pack (CPU + short GPU) - Claude integrates, GPT drafts glue
1. Script `src/netsight/demo/run_survey.py` (new): images of one held-out survey -> v0.4 + flip
   TTA -> calibrated probabilities (beta fitted on validation) -> label-free count threshold at
   1 FA/image -> evidence features per contact -> claim level from the applicability gate
   (box-aspect / pixel-geometry check vs training envelope, see P5) -> `build_pack` +
   `write_pack` + ledger.
2. Run on AquaScan test (calibrated case) and Contact (should come out indicative/withdrawn).
3. Commit the code; outputs stay in netsight-data (no data in git).

### P5. Geometry check for the applicability gate (CPU) - GPT drafts, Claude reviews
- New `src/netsight/trust/geometry_gate.py`: per survey, pixel size and aspect (from metadata
  when present; otherwise estimated from detection-box aspect statistics, marked "estimated"),
  compared with the training envelope -> soft/hard reasons for `decide_claim_level`.
- Test on GhostVision recordings: Contact must be flagged, training-like recordings not.

### P6. NOAA raw data -> labelled training data (Track 1) - GPT-luna/Gemini + GPT-sol + Claude
1. (luna/Gemini, web) For the surveys with the most confirmed contacts in our contacts.csv files,
   find the raw side-scan files on NOAA NCEI (survey id -> XTF/JSF links, sizes). Output a table.
   Pick 1-2 surveys < ~5 GB total. Download with `netsight data fetch` (resumable, 8 connections).
2. (GPT-sol) `src/netsight/datasets/noaa_chips.py`: XTF -> existing normaliser
   (`netsight.normalise.swath.normalise_record`, fixed ground resolution) -> project each contact
   (lat/lon) to (ping, sample) using navigation -> image chips + YOLO boxes flagged
   "position from NOAA, extent unchecked". Tests on synthetic records.
3. (Claude) Run on the downloaded survey; visually check 10 chips; write
   `docs/research/step2/noaa_chips.md`. Do not train on them until boxes are reviewed (P6 gives
   candidates for the team's review, not finished labels).
4. (luna, cheap) Bodine dataset (Zenodo 10119320): read README / file list only - does it have
   object boxes? Add to `docs/research/step2/dataset_hunt.md`.

### P7. Label consistency (CPU)
- SubPipe and Contact: document the box convention per dataset in `docs/labelling_guide.md`
  (object only, shadow excluded) and list which datasets break it. Report SubPipe at IoU 0.3.

### P8. Final summary for the user (last 30 min)
- `docs/research/step2/summary_2026-11-08.md`: plain language: what was done, numbers, what
  worked, what failed, decisions, next steps (v5 plan with the A/B evidence). Update memory.

## Order

GPU queue: test A -> P2 -> P3 -> P4 runs. CPU/agents in parallel: P5 and P6 (GPT/luna) while the
GPU works; P7 anytime; P8 last.

## Progress log

- 15:00 Plan written. Test A running.
- 15:20 P6 changed: NCEI has no raw XTF for our top surveys, but has georeferenced side-scan
  mosaics (GeoTIFF + .tfw, 1 m pixels, 455 kHz) for H12330 (23 confirmed contacts), H12357 (18),
  H12890 (16), 40-70 MB each; downloading to raw/noaa/<survey>/TIFF. 1 m pixels suit large objects
  (wrecks, obstructions), not crab-pot scale. GPT-6.1-sol drafting noaa_chips.py (contact lat/lon
  -> pixel via mosaic CRS -> chips + candidate boxes) and geometry_gate.py (label-free pixel
  aspect/size check from the detector's own boxes).
- 16:20 P5+P4 done (GPT-drafted, Claude-reviewed): noaa_chips.py, geometry_gate.py,
  demo/run_survey.py. Demo packs for v0.4 in runs/demo_v0.4 (ledger verifies). Found and fixed:
  the geometry envelope must be per dataset (box aspect depends on object type); with it Contact
  (aspect 1.25 vs 0.87-1.11) and mine 2015 (2.08 vs 1.49-1.74) come out indicative, normal
  recordings calibrated. Pack text now states the count-threshold FA bound plainly; recall comes
  from the same dataset's validation surveys. User: weekly usage 86%; use GPT-6.1-sol (high for
  complex), verify, redo myself if not good enough.
- 17:30 P1 done (test_a_learning_curve.md): RISING. GhostVision test AP50 0.269/0.251/0.332/0.369
  for 2/5/10/21 recordings; Contact 0.074 -> 0.224. More surveys pay off -> Track 1 full effort.
  P6 done (noaa_chips.md): 60 candidate chips from 3 NOAA mosaics (48 confirmed real); 1 m
  pixels -> large objects only, human review required. Starting P2 (fine-tunes) on the GPU.
- 18:40 P2 done (finetune_v0.4.md): GhostVision fine-tune kept as specialist (Contact 0.256 ->
  0.398, CI > 0; GhostVision +0.014 n.s.; forgets other sets). Mine fine-tune rejected (own test
  -0.022, CI < 0, while validation rose). P3 (trust_v0.4.md) and P7 (labelling guide 4.1) done.
  Next: test A second seed (k=10, 21) on GPU, then P8 summary.
