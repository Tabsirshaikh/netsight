# Label-free per-survey geometry correction (step 3), research v0.4

Date: 2026-11-08. Code: `netsight.detect.adaptive_resample` (GPT-6.1-sol draft, reviewed;
41 tests) and `python -m netsight.detect.adaptive_eval`. Two passes per test survey: detect;
estimate pixel aspect/size from the detector's own confident boxes; if outside the envelope of the
same dataset's validation surveys, resample and detect again; boxes mapped back. No labels used.

| Test set | correction chosen per survey | AP50 before -> after | AP30 before -> after |
|---|---|---|---|
| GhostVision (normal recordings) | none, none, none | 0.361 -> 0.361 | 0.482 -> 0.482 |
| **Contact (stretched sensor)** | rows x1.28 (true ~1.32) | **0.256 -> 0.333** | **0.377 -> 0.481** |
| AquaScan | rows x0.63, x1.10 | 0.614 -> 0.589 | 0.673 -> 0.645 |
| mine | rows x1.29, x0.79 | 0.223 -> 0.171 | 0.351 -> 0.282 |

## Conclusion

The estimate reads pixel stretch from the shape of detected boxes. That is valid for roughly
square targets (traps/pots: Contact +0.077 AP50 with no labels), and wrong when the targets'
shape or orientation varies (people in AquaScan, mine-like shapes): it mistakes object pose for
pixel geometry and hurts.

Rule adopted:
- Resample automatically only with **sonar metadata** (exact pixel spacing) or for **validated
  roughly-square target types** (ghost-gear traps/pots).
- Otherwise the estimate only feeds the applicability gate (claim "indicative", with the
  suggested resampling in the reasons); detections are not changed.
