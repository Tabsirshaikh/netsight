# NetSight — editorial decisions

Written before implementation. This document defines the implemented sequence.

The site now follows the video's problem → questions → method → operational meaning → evidence → next step storyline. The video is a narrative reference, not the authority for current detector, calibration or threshold claims.

## Candidate decisions

| Candidate | Decision | Reason |
|---|---|---|
| S01 Hero | Keep | Preserve the cinematic descent and existing R3F introduction; establish the project before presenting evidence. |
| S02 Side-scan explainer | Keep, reorder | Place after the real-world problem so judges first understand why learning to read sonar matters. |
| S03 Exploded pipeline | Merge | Replace the six-operation presentation with a new, explicitly proposed eight-stage architecture using D-FINE-S and 640 px tiles. |
| S04 Papers vs reality | Merge | Retain the measured split comparison inside validation, but remove the broad papers-versus-practice framing. |
| S05 Real results | Merge | Present the supplied target-specific results as readable evidence, beside their evaluation limits rather than illustrative target images. |
| S06 Trust | Merge | Keep measured calibration and budget results; replace empty gate boxes and the schematic reliability chart with plain-language claim conditions and a measured survey tally. |
| S07 Geometry correction | Merge | Explain geometry inside ingest; remove the oversized before/after numbers because they distract from operational meaning. |
| S08 More surveys | Merge | Keep the recording-count experiment as supporting validation evidence, not another standalone chart. |
| S09 Evidence pack / ledger | Merge | Explain the inspectable record in a contact walkthrough; remove illustrative hashes and the hash-manipulation demonstration. |
| S10 CTA | Merge | Replace the placeholder-dashboard invitation with a downloadable pilot discussion brief and explicit evidence requests. |
| Videos section | Cut | No playable asset is supplied; the supplied summary also contains superseded technical claims. Do not invent a video URL or repeat those claims. |
| Sourced problem statistics | New | Give judges and funders a reason to care, with a visible source line for every statistic. |
| Today's search workflow | New | Explain survey → human review → suspect list → diver check before introducing automation. |
| Hidden gaps / “all clear” map | Merge | Combine with the proposed search-completeness map to contrast surveyed area with evidence of effective search. |
| Three questions + three pillars | New | Distinguish finding a contact, trusting that contact and assessing the search itself. |
| Offline preparation | Merge | Include synthetic injection, detection-probability study and dataset-specific calibration in the questions section; separate design from measured evidence. |
| Synthetic net injection | Merge | Describe its proposed role without inventing rendered training examples or performance. |
| Probability-of-detection curve | Cut | There is no supplied measured curve; explain the proposed study without drawing an apparently quantitative result. |
| Eight online stages | New | Make the architecture legible and traceable to the operational questions. |
| Search-completeness map | New | Provide the strongest operational distinction, labelled design / illustrative until measured beside the visual. |
| One contact's journey / contact #17 | New | Show what an operator should inspect without assigning invented scores, locations or position errors. |
| Requirements-to-stages matrix | Merge | Include an architecture traceability table in the contact handoff, explicitly not a verified compliance claim. |
| Data, tools and honesty | New | End with measured versus proposed boundaries, unresolved data/licensing needs and a useful pilot request. |

## Final order

1. **S01Hero** — existing cinematic introduction.
2. **ProblemSection** — sourced problem, current workflow and the cost of checking suspects.
3. **S02SideScan** — existing acoustic explainer.
4. **QuestionsSection** — three questions/pillars and offline preparation.
5. **EightStagesSection** — proposed eight-stage online architecture.
6. **CompletenessSection** — illustrative hidden-gap / effective-search map.
7. **ValidationSection** — measured split comparison, target results, calibration, budget tally and recording experiment.
8. **ContactSection** — illustrative contact #17, evidence handoff and requirements traceability.
9. **NextSection** — data honesty, pilot discussion brief and CTA.

## Implementation boundaries

- Existing S01 and S02 remain unchanged. Existing R3F, GSAP and Lenis infrastructure remains in use.
- App.tsx changes composition and navigation. All replacement sections are new files.
- All new editorial copy lives in `src/content.partC.ts`; measured values are read from the supplied `content.ts`.
- Old, unmounted sections and assets remain in place.
- New animation is scoped through `useGSAP`, uses top-level ScrollTrigger timelines, linear scrubbed easing, transforms/autoAlpha, reduced-motion fallbacks and matchMedia cleanup.
- Tall/mobile sections flow normally; only the compact desktop map is pinned.
- Sources supplied in the prompt are identified visibly. No paper URLs, video assets, survey imagery or external validation records are invented.
- The downloaded brief is a discussion document, not an evidence export or operational dashboard.
