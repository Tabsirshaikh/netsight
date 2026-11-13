# Overnight run 2026-11-13: results and decisions

Plain summary for the morning. Rule followed all night: test cheaply first; spend long GPU runs or
paid model calls only after a test shows a real gain. Detailed logs:
`docs/plan/autonomous_plan_2026-11-13.md`; label study: `relabel_v2.md`.

## 1. Our test scores were too low (phase 1, done)

Every test image of mine (168), GhostVision (441) and Contact (550) was checked by Gemini 3.8 Flash
low (free for the ChatGPT plan), with GPT-6.1-sol re-checking 141 hard images (~25% of one ChatGPT
5-hour window). The published test labels miss many real objects. Scored honestly (conservative
rule: expert labels kept, AI additions ignored rather than trusted):

| Test set | v0.4 as reported | v0.4 on corrected labels | if every AI addition is real |
|---|---|---|---|
| mine | 0.22 | **0.33** | 0.56 |
| GhostVision | 0.36 | **0.56** | 0.71 |
| Contact (other sensor) | 0.26 | **0.39** (GhostVision specialist 0.50) | 0.56 |

The model ranking and every earlier test verdict stay the same.

AI reviewers are good at spotting unlabelled objects (~70% of their additions are clearly real)
but poor at overruling experts (they rejected 21-36% of expert mine labels that look real; Gemini
and sol agreed on only 51% of boxes on hard mine images). A human must make the final call.

**For you this morning:** three CVAT packs in `netsight-data/review_packs/` (mine_test,
ghostvision_test, ghostvision_shift_test): green = original label, blue = AI-proposed object,
yellow = unsure. Keep/delete/relabel, export "CVAT for images 1.1", and the decisions become the
final test labels (`review_pack.read_decisions`).

## 2. Cleaned training labels do not help (phase 2, gate failed)

A 1-hour test training with the mine training labels cleaned (176 originals + 321 AI-added
objects) gave no gain on expert labels (-0.014, CI -0.037 to +0.013) and lost on AquaScan
(-0.053). The +0.06 on "AI-added" labels is circular. So the long GhostVision cleanup and the full
retraining were NOT run (saved ~9 h).

## 3. Geometry from sonar metadata (phase 3, done)

New square-pixel step: along-track rows are resampled from the navigation (distance travelled), so
objects keep their true shape. Verified end to end on a real-format XTF file (293 pings, 0.21 m
along vs 0.05 m across: rows stretched 4.1x). The XTF reader now also accepts single-sided files.
The old mine specialist is still worse on corrected labels (0.30 vs 0.33): not used.

## 4. New data (phase 4)

- No new REAL labelled side-scan surveys with our object types exist publicly (checked again).
- Added and licence-registered: ApertureLab synthetic side-scan (ghost net, rope, tyre,
  container, wreck, pipe, rock; commercial use allowed with attribution, named exclusions) and a
  real boulder chip set (CC-BY-4.0).
- The review packs above are the human-check step of this phase.

## 5. Classes and synthetic data (phase 5, rejected for real use)

- A crop classifier scores 51-100% when tested on the same dataset it trained on, but on held-out
  datasets: wreck 41%, person 11%, synthetic rock -> real boulders 1%, synthetic pipe -> real
  SubPipe 0%. It learns which sonar made the image, not the object. Net, rope and tyre classes
  from simulation would not work on real surveys, so they were not built.
- Adding the synthetic images to detector training: mixed (AquaScan -0.095, Contact +0.038).

## 6. What actually remains to improve the model

1. Human-checked test labels (your review) - then all numbers are trustworthy.
2. More varied REAL surveys with labels (partners, own data) - still the only lever with a
   measured, repeatable gain (+0.05 AP per doubling of recordings).
3. Use the square-pixel step (and the GhostVision specialist for gear surveys) at inference.
4. Bigger detector: the one model change that passed its test (section 7).

## 7. Bigger detector (D-FINE-M): the first real gain

1-hour test training, identical recipe, only the model size changed (D-FINE-S -> D-FINE-M, both
Apache-2.0 COCO weights). Paired comparison on corrected (conservative v2) labels:

| Test set | small | medium | change (95% CI) |
|---|---|---|---|
| mine | 0.218 | 0.266 | **+0.048** (+0.014, +0.087) |
| GhostVision | 0.388 | 0.512 | **+0.124** (+0.079, +0.168) |
| Contact | 0.202 | 0.217 | +0.015 (-0.009, +0.037) |
| SubPipe (original labels, IoU 0.3) | 0.686 | 0.568 | **-0.118** (-0.199, -0.038) |

It passed the gate, so one full training was run: model v0.6 = v0.4 recipe with D-FINE-M
(`runs/research_v0.6`). It did NOT hold up in full training (section 8). Cost: D-FINE paper latency S 3.5 ms vs M 5.6 ms (~1.6x); not yet
measured on our CPU path.

## 8. v0.6 vs v0.4 (full training): rejected, v0.4 stays

v0.6 trained 25 epochs (early stop; best validation epoch 19, ~5 h). On the validation sets it
looked clearly better (mean AP50 0.584 vs 0.525; mine 0.36 vs 0.29). On the held-out test
surveys it is worse. Paired image bootstrap, 1000 resamples, v0.6 minus v0.4:

| Test set | labels | v0.4 | v0.6 | change (95% CI) |
|---|---|---|---|---|
| mine | conservative v2, IoU 0.5 | 0.334 | 0.262 | **-0.071** (-0.111, -0.032) |
| GhostVision | conservative v2, IoU 0.5 | 0.557 | 0.538 | -0.020 (-0.055, +0.020) |
| Contact (other sensor) | conservative v2, IoU 0.5 | 0.388 | 0.293 | **-0.095** (-0.125, -0.068) |
| AquaScan | original, IoU 0.5 | 0.615 | 0.643 | +0.028 (-0.016, +0.075) |
| SCTD | original, IoU 0.5 | 0.817 | 0.776 | -0.041 (-0.091, +0.025) |
| SubPipe | original, IoU 0.3 | 0.669 | 0.707 | +0.038 (-0.069, +0.144) |

(IoU 0.3 on conservative v2: mine -0.106, GhostVision +0.008, Contact -0.124; same verdict.)

Decision: **v0.4 stays the general model**; v0.6 is not used. Lessons:

1. The 1-hour test compared medium vs small at a short budget; at full length the small model
   catches up and the medium one generalises worse to new surveys and sensors (Contact -0.095).
2. The validation sets are too small to pick a model (mine has 30 objects): a +0.07 validation
   gain turned into a -0.07 test loss. Model choice must stay on held-out test surveys with the
   corrected labels, and a proxy win needs a full-length confirmation before it is believed.
3. Model size is not the bottleneck. The remaining levers are those in section 6: human-checked
   test labels and more varied real surveys.
