# Test labels v2: AI-assisted review of the mine, GhostVision and Contact test sets

Date: 2026-11-13. Code: `netsight.datasets.llm_review`, `netsight.datasets.relabel`,
`python -m netsight.detect.rescore`. Reviews: `runs/relabel_gemini_*`, `runs/relabel_sol_*`.

## Method

Every test image with a candidate box was reviewed: 168 mine, 441 GhostVision, 550 Contact.
Candidates = the published labels plus confident v0.4 detections that no label covers. The
reviewer sees the image with numbered boxes and zoomed crops, is NOT told which boxes are labels,
and answers per box object / not_object / unsure, plus objects nobody marked.

- Reviewer 1: Gemini 3.8 Flash low (all images; no cost to the ChatGPT plan).
- Reviewer 2: GPT-6.1-sol-medium on images Gemini was unsure about plus 10 random images per set
  (33 mine, 68 GhostVision, 40 Contact); it overrides Gemini where it ran.
- Cost measured beforehand: Astra 10 images = 4% of the ChatGPT 5-hour window, sol 2%; Gemini
  free for the plan. On 10 GhostVision control images Gemini Flash low matched Astra on 29 of 34
  boxes, as did sol; Gemini boxes are slightly looser.

## How reliable are the AI reviewers?

- Gemini rejected 21% of the mine-like (MILCO) and 36% of the non-mine object (NOMBO) expert
  labels; in a visual spot-check most rejected labels look like real objects (the prompt asked
  about "mine-like" objects, NOMBO are labelled non-mine objects).
- About 10 of 15 sampled Gemini additions are clearly objects with shadows; 4-5 uncertain.
- On 33 hard mine images Gemini and sol gave the same verdict on 141 of 275 boxes (51%).

So the reviewers are good at finding unlabelled objects and poor at overruling expert labels.
Two label versions are scored (rules fixed before scoring):

- **conservative v2 (main result)**: every published label kept; every reviewer addition or
  doubt becomes an ignore region (a detection there is neither a hit nor a false alarm);
- **generous v2 (upper bound)**: reviewer additions count as objects, doubted labels ignored.

## Results (AP50 on held-out test surveys)

| Test set | v0.4 original labels | v0.4 conservative v2 | v0.4 generous v2 | best model, conservative |
|---|---|---|---|---|
| mine | 0.223 | **0.337** | 0.570 | v0.4 |
| GhostVision | 0.361 | **0.557** | 0.713 | v0.4 (GhostVision specialist 0.547) |
| Contact (other sensor) | 0.256 | **0.390** | 0.564 | GhostVision specialist 0.496 |

(All sets include the sol re-check.)

1. The published test labels miss many real objects: v0.4 is about 50% better than reported on
   every set, even under the conservative rule.
2. Model ranking does not change (mine: v0.4 > v0.2 > v0.3 > v0.1) and the earlier proxy verdicts
   (class per dataset, sonar augmentation, synthetic data) keep their direction.
3. Caveat: added candidates came from v0.4's own detections, which favours v0.4 when compared
   with older models; comparisons between two new models are not affected.

## Human check

CVAT packs with original (green), proposed (blue) and unsure (yellow) boxes:
`review_packs/<set>_test/` (images, annotations.xml, README). Team decisions read back with
`netsight.datasets.review_pack.read_decisions` become the final test labels v3.
