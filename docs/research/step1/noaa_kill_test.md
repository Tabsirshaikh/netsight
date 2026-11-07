# NOAA ground-truth kill test (Step 1B)

Date: 2026-11-07. Data: NOAA NCEI H-survey Descriptive Reports (CC0). Tool:
`netsight noaa contacts SURVEY... --features F.csv --summary S.csv`.

## Question

Do public NOAA survey reports contain enough investigated objects with a recorded outcome
(real object / not real) to calibrate NetSight's P(real)? Kill criterion set in Step 1:
**at least 10 surveys with usable outcomes.**

## Sample

Every third survey number from H12300 to H12417 (40 numbers), downloaded one at a time with a
pause. 9 numbers do not exist on NCEI (404), 1 download failed part-way (H12342), so
**29 surveys** were parsed. No survey was chosen by looking at it first.

## Result: passed

**15 of 29 surveys (52%) have usable outcomes.** 14 surveys have none: their DRs either keep
contacts in separate deliverables (Separates, S-57 files) that are not public, or the survey
investigated no items.

| Source format | Surveys | Items | Decided | Real | Not real |
|---|---|---|---|---|---|
| Contact-outcome tables (older DRs) | 2 | 41 | 36 | 32 | 4 |
| Pydro Feature Reports (AWOIS, DTON, new features) | 15 | 160 | 135 | 98 | 37 |

The first parser read only contact-outcome tables and found 2 surveys, which would have
failed the test. Reading the Pydro Feature Reports changed the answer. The two formats can
describe the same object in H12330 and H12333; the counts above are not de-duplicated across
formats.

Feature Report outcomes: 98 verified, 26 disproved, 11 reclassified as seabed (sand waves,
"not a rock"), 2 inconclusive, 19 retained without new evidence, 2 bare deletions, 2 unknown.
Only the first three count as decided. 104 of 160 items were developed with multibeam (least
depth measured or multibeam named); none mention divers or ROVs, so **none are physical
verification**. They are expert dispositions backed by sonar evidence.

## Cases that show the trust problem in the reports themselves

- H12333: "Charted wreck PA ... disproved by 200% sidescan sonar."
- H12381: "Not a rock as determined during office processing." (four items)
- H12357 1.2: the field team found "No evidence of wreck ... in 200% SSS" and recommended
  deletion; the office replied "Do not concur. SSS shows evidence of a feature at the location."
- H12357 1.17: "Shadow analysis indicates 0.6m height ... Survey data is inadequate to disprove
  this item."
- H12357 1.14: "A 20 cm contact can be seen in the sss coverage", but "The compiler did not see
  the 20 cm. contact".

## What this data can and cannot do

Can:
- Give a few hundred expert-decided outcomes with positions, least depths and S-57 classes from
  CC0 data, enough to build and test the calibration and reporting pipeline in Step 2.
- Supply realistic disagreement cases (field vs office) for the applicability gate.

Cannot, and must not be claimed:
- **Selection bias.** Items are charting-significant objects (rocks, wrecks, obstructions) that
  someone chose to investigate, not every detector output. Calibration fitted here is
  "indicative" until checked on full detector output.
- **Negatives are mostly "charted item not found again".** That is a different event from "a new
  sonar contact was a false alarm". The two must be kept apart (`item_kind` = awois vs dton).
- **Class balance:** 98 real vs 37 not real. Real-world detector output is dominated by false
  alarms.
- **No image chips yet.** Reports give positions; public mosaics are 1 m/pixel, too coarse for
  small debris. Raw XTF must be requested (see `docs/outreach/data_requests.md`).
- Outcome wording is parsed by rules tuned on these 29 surveys and regression-tested
  (`tests/test_noaa_features.py`). A larger sample needs another spot-check before use.

## Next

1. Scale to a few hundred surveys (throttled) for a larger outcome table, then spot-check a
   fresh random sample of parsed items by hand.
2. Request raw XTF and the Separates contact listings from NOAA for surveys with many decided
   items (H12357, H12381, H12411, H12315).
3. Step 2 uses this table to build and test calibration metrics and the claim levels.
