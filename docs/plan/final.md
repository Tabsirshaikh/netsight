# NetSight — Final Project Plan (v2)

**Independent, sensor-neutral assurance for sonar survey contacts: how much to trust each find, and how well each patch of seabed was really searched.**

SIH26057 origin (MoES / NIOT, side-scan sonar debris detection) · Plan date: 6 November 2026 · Replaces `NetSight_Solution.md` (v1) as the working plan · Status: **plan only, nothing built or measured yet**

---

## 0. How to read this plan

**Evidence tags** (every claim carries one):

| Tag | Meaning |
|---|---|
| **[V]** | Verified: a researcher opened the primary page or paper and read the claim |
| **[S]** | Secondary: rests on a search summary, a vendor claim or a page that could not be opened. Check before it goes on a slide |
| **[P]** | Proposed: our design decision or opinion, built on the evidence but not itself evidence |
| **[H]** | Hypothesis: something we believe and must test |
| **[E]** | Estimate: a planning number, not a measurement |
| **[I]** | Illustrative: example values that show a format, not results |

**How this plan was built.** It merges v1 (`NetSight_Solution.md`), three research reports in `reports/`, sixteen research-note files in `research_notes/` (problem validity, market and buyers, moat and multi-sonar AI, and four final-plan input notes on the unified model, trust-layer methods, data acquisition, and targets/standards), and a static audit of 120 competitor repositories for SIH26057. Every number below traces to one of those files; the full source trails live there.

**What changed from v1, in one line:** NetSight is no longer "a better side-scan debris detector". It is a **trust layer** (calibrated contact probabilities, an empirically validated probability-of-detection map, honest applicability limits and a provenance record) that runs on any sonar through one shared model family, built in two steps, and sold first as an independent review service. Section 25 lists every change.

---

## 1. One-page summary

| | |
|---|---|
| **Problem** | After a sonar survey (port channel, post-disaster area, wreck site, wind-farm route, ghost-gear search), a person or an AI marks suspect objects. Two things stay unknown: **which suspects are real**, and **how well each patch of seabed was actually searched**. In the best-documented ghost-gear campaign, divers checked 176 of 549 sonar suspects and 94 were real (about half) [V, Stolte et al. 2022]. In offshore-wind UXO work only about 3–8% of investigated targets turn out to be real UXO [S]. Survey standards themselves say "no single survey system can guarantee detection of all features" [V, IHO S-44]. |
| **What exists** | AI detection is common and increasingly free inside vendor software (Kongsberg, Chesapeake SonarWiz, Coda Octopus, Ocean Geophysics) [S]. Pieces of the trust idea exist: temperature-scaled scores and a hand-set Pd grid in a few SIH repos [V, audit], terrain-aware Pd maps from target insertion in naval mine hunting [V, SeeByte/Guerneve et al.]. |
| **Gap** | We found no civilian tool, product or SIH project that **validates** its contact probabilities on held-out surveys, **fits** its Pd map from experiments and checks it against real targets, **withdraws** its claims on an unfamiliar sonar, and keeps an auditable record of every decision [S, limited search]. |
| **NetSight** | A software layer on top of existing survey data that outputs, for every survey: (1) contacts with a **calibrated probability of being real** and class probabilities, (2) a per-cell **Pd lower bound** for stated reference targets, (3) an operating point set by a **false-alarm budget per km²**, (4) a **claim level** (calibrated / indicative / withdrawn) from an applicability gate, (5) **position ellipses** that are tested, (6) a **hash-chained provenance record**, (7) a ranked verification plan and re-survey polygons [P]. |
| **One AI for all sonars** | One NetSight model family: a shared, sensor-conditioned backbone ("NetSight Core") with small heads per sonar family, fed by physics normalisation, and one shared trust layer. Built in two steps: Stage A ships per-family detectors with the shared trust layer; Stage B replaces them with the shared backbone only if a pre-registered test shows it wins [P]. |
| **Why it can't be copied easily** | Accuracy and methods are copyable. What a sonar maker or survey contractor cannot credibly offer is an **independent** grade of its own output. NetSight's moat stack is neutrality paid for by the risk owner, an open method and benchmark, and a growing ledger of verified outcomes [P, with analogues in testing/inspection and credit rating]. |
| **Business** | Services-first "assurance desk": fixed-price independent reviews of target lists and coverage, then a product after 10–20 labelled jobs [P]. Best-evidenced first niche is global (offshore wind and cable target lists, search-and-recovery contractors); India is the base for grants, data partnerships and building [S/P]. |
| **Honest status** | Demand is unproven: no buyer has been shown to pay for calibrated confidence or coverage maps [S]. Every stage of the roadmap has a kill criterion, and the first two months are customer interviews and a free retrospective study on public data. |

---

## 2. The problem, with verified facts

### 2.1 How sonar search works today

Survey vessel, AUV, USV or ROV → sonar (side-scan, multibeam, synthetic aperture, imaging) → **a person scrolls through the imagery and marks contacts** (AI increasingly pre-marks them) → divers or ROV verify selected contacts → removal, charting, or "area searched" decision [V, NOAA HSSD; S, vendor sources].

### 2.2 Evidence that contacts are often wrong

| Evidence | Detail | Tag |
|---|---|---|
| Baltic ghost-gear campaign (Stolte et al. 2022, Frontiers in Marine Science 9:981840) | 549 sonar suspects over 5,820 ha (58.2 km²) in 45 days; 176 diver-verified; 94 confirmed lost gear (≈53%, reported as 52%). Schleswig-Holstein: 53 of 93 verified suspects were not lost gear (57%). Bay of Lübeck test: "22 of 49 sonar positions verified during 5 diving days were confirmed as ALDFG, a success rate of 45%" | [V] |
| Why the false suspects happened | Soft sediment gives "a similar reflectivity signal as a larger lost trawl net"; "edges and reefs" and "rich underwater flora" complicate interpretation. No per-suspect breakdown | [V] |
| Cost of checking by diver | Authors' estimate for a scooter-equipped diving team (14.4 ha/day, €2,000–4,000/day): "at least 140 Euros per hectar"; sonar search "8 Euros per hectar"; sonar "12 times more efficient in time and 17 times more efficient in cost than the diver search". Without scooters divers cover "less than 2 hectares" per day | [V] (an estimate inside the paper, not a measured cost) |
| Offshore-wind UXO | Real-UXO share of investigated targets: Dudgeon 20 of 243 (≈8%), a Boskalis Baltic cable route 25 of 773 (≈3%), SeaTerra ≈6%, ALM Geophysics ≈4% across 18 campaigns. A GEOMAR paper says false-positive targets "drive costs and efforts" | [S] (GEOMAR [V]) |
| Famous misreads | Deep Sea Vision's "Earhart plane" sonar image (Jan 2024) was reported as "a natural rock formation" by the company in Nov 2024; an MH370 contact cluster (May 2015) turned out to be an unrelated uncharted wreck; the Baltic Sea Anomaly is widely attributed to a natural feature or instrument artefact | [V]/[S] |
| India | Shirur landslide search (Karnataka, 2024): the lorry was announced "located" on 24 July from radar/sonar signals but recovered only on 25 September, 72 days after the landslide; no source says which July signal was the truck. Treat as a premature announcement, not a proven sonar false positive | [S] |

**Correct wording:** "About half of the suspects divers checked were real gear (94 of 176)." Not "experts are right only half the time": only 32% of suspects were checked, and no miss rate was reported [V].

### 2.3 Evidence that "nothing found" is not "nothing there"

| Evidence | Detail | Tag |
|---|---|---|
| IHO S-44 | "No single survey system can guarantee detection of all features." Feature detection is defined for **cubes** (Order 1a: > 2 m; Special: > 1 m; Exclusive: > 0.5 m), not nets or ropes | [V] (Edition 6 Preview; check against 6.2.0) |
| NOAA HSSD | "100% side scan sonar is insufficient to disprove a feature"; 200% is sufficient. Contacts are picked when shadow-derived height is ≥ 1 m (≤ 20 m depth) or ≥ 5% of depth (deeper); other contacts "may be picked if the sonargram signature (e.g., size, shape, or pattern qualities) is notable" | [V] (HSSD 2022 and 2026.0.02) |
| Why low-relief objects are at risk | A shadow-height picking rule favours tall objects. A flat net plausibly casts little or no shadow, so it depends on pattern-based picking. **No published study confirms the "collapsed net, no shadow" signature**, and Stolte's Figure 2 shows a trawl bundle casting "extended sonar shadows" | [V] facts, [H] for flat nets |
| Blind areas | Nadir gap, far range, acoustic shadows behind tall objects, attitude dropouts, narrow-view imaging sonars. Deep Trekker's operator rule of thumb (altitude at 10% of range) gives "around 70% seabed coverage" | [S]/[V] Deep Trekker |
| False all-clear cases | We found **no documented case** of a side-scan "clear" declaration followed by a missed hazard. Known groundings (USS San Francisco 2005, USS Connecticut 2021) were charting/coverage failures | [S]. Do not imply such a case exists |

### 2.4 India context, corrected

| Claim | Status |
|---|---|
| INS Sarvekshak: 807 miles of side-scan, 54 underwater debris, one wreck after MV X-Press Pearl (2 July 2021) | [V] — but the survey was in **Sri Lankan waters, at Sri Lanka's request**, a Navy hard-object search |
| Ghost gear in India | Found and removed **by divers** on shallow reefs (Gulf of Mannar); no sonar-based ghost-net programme found; India has no systematic tracking of lost gear (Mongabay, June 2026) [V/S] |
| Gear loss | Global ≈1.82% of gear per year (95% CI 1.62–2.03%, Richardson et al. 2022) [V]; a Kerala study of 390 fishers found ≈21% lost, abandoned or discarded per year, 11.6% lost [V] |
| Gulf of Mannar | Abandoned nets were **43.17 ± 5.48% of reef debris** (Edward et al. 2020) [S]. v1's "37.9%" was not found; drop it unless the MARESSOL report is checked |
| Indian sonar users | Navy survey ships (side-scan, multibeam, AUV incl. Kongsberg HUGIN, ROV) [S]; NIOT (multibeam + SAS; found the IAF An-32 wreck at ≈3,400 m in Jan 2024) [S]; GSI (side-scan and SAS on survey ships) [S]; Planys (ROV + side-scan, e.g. post-Cyclone Vardah jetty survey) [V]; ports via contractors; Cochin Port's own team found a sunken vessel in its channel in 2017 [S] |

---

## 3. Who has the problem and who would pay

The market research (`reports/Sonar survey market and buyers.md`) is not re-argued here; this section states only what it means for the plan.

| Rank | Segment | Why it matters | Who pays | Plan implication |
|---|---|---|---|---|
| 1 | Offshore-wind and subsea-cable target lists (UXO, boulders, debris) — global | Only quantified false-alarm pain (3–8% hit rate; vessel days per target) [S] | Developers, transmission operators, UXO consultants, marine warranty surveyors | First paid-pilot target; needs UXO mode and the Cenos-style contact fields (§13) |
| 2 | Search and recovery (wrecks, aircraft, vehicles, people) | "How well was each area searched" is the core question; outcome contracts (MH370 $70M only on a find) [V/S] | Contractors carrying coverage risk | Second segment; strong demo value |
| 3 | Hydrographic and port survey QA | Assurance already bought as a human service: New Mangalore Port pays Rs 32,87,847 over three years for third-party witnessing of dredging surveys [V] | Ports, dredging clients | Indian pilot candidate; small budgets |
| 4 | Ghost gear | Most mission-aligned, best demo story; funded by grants (NOAA awards $0.13–8M; GhostNetBusters €221k) [S] | NGOs, governments, CSR | Demo and partnerships, not the revenue base |
| 5 | Defence mine countermeasures | Strongest technical fit, closed procurement [S] | Navies via primes | Separate, firewalled track (iDEX) only |

**What would have to be true for a company** [P, from the market report]: a buyer owns a budget for target-list QA or coverage proof; calibrated probabilities change a decision they already make; they will share anonymised outcome data; a file-in/report-out workflow is acceptable; a price of at least a few thousand dollars per survey or a five-figure annual licence is realistic. **None of these has direct evidence yet**, so Stage 0 of the roadmap tests them first.

---

## 4. What already exists, and what does not

### 4.1 Vendors and funded projects

| Who | What they do | What they don't show | Tag |
|---|---|---|---|
| Kongsberg SAS Target Assistant (with Cathx) | Detects and measures objects, list "for review/confirmation" | Confidence, Pd, false-alarm rate | [S] |
| Chesapeake SonarWiz | CNN-based ATR; says future detections will "carry probability estimates" and aims to cut false-alarm review "by an order of magnitude" | Calibration method or validation | [S] |
| Coda Octopus, Ocean Geophysics | AI boulder picking (4,600 contacts in 9 minutes vs ≈3 days, vendor claim); Ocean Geophysics "will not be sold as a stand-alone product" | Independent validation | [S]/[V] |
| SeeByte (Guerneve et al., UACE 2023) | Inserts CAD targets into real side-scan via ray tracing + GAN, averages detections into a per-location Pd and false-alarm-density map; 500 ms to 1 min per 1000 pings | **Validation of injected-target Pd against real laid targets** | [V] |
| GhostNetZero (Microsoft, WWF Germany, Accenture) | Ghost-net segmentation on Baltic (239) and Puget Sound (173) images; "~90%" is a validation-set centroid detection rate (0.89–0.93 at 20 px tolerance) | Test set, precision, calibration, coverage; data not public | [V] |
| GhostNetBusters (GEOMAR, sonoware, net-recovery NGO; €221k) | Open-source SidescanTools processing | Performance figures | [S] |
| GhostVision (Univ. of Delaware) | Derelict **crab-pot** detection on Humminbird side-scan; dataset published | Calibration, coverage | [V] |
| HydroSight (Israel, $5M seed, Sep 2026) | Multi-epoch survey change and anomaly AI for ports, energy and cable owners | Outcomes (too new) | [S] |

### 4.2 The 120-repository SIH26057 audit

The audit statically inspected 120 repositories linked to SIH26057 or the same task (many are copies; the 100 problem-linked repos are not 100 teams) [V, audit file].

| Feature | How many have source-code evidence | Who | What's missing |
|---|---|---|---|
| Detector inference | 95 of 120 | Almost all | — |
| Raw XTF handling | 16 | Sagar-Netra, Varuna, KADAL, SONARIS, others | Some parsers assign fixed or default navigation |
| Probability calibration | 3 | Sagar-Netra and Aqua-AI (temperature scaling), DEPTH (fitted thresholds with Clopper-Pearson bounds) | Proof that the **final** score stays calibrated after fusion |
| Pd / coverage assurance | 5 (3 are copies of one AquaSentinel project with hand-set arithmetic) | Sagar-Netra (per-cell grid, **hand-set** logistic coefficients, max-Pd across passes, labels 0.5–0.8 as "clear"), DEPTH (recall promise, withdraws on unfamiliar sonar) | Pd **fitted** from experiments and validated on real targets |
| Expert review / audit | 22 | DeepSight (review state + provenance), others | Separation of reviewer opinion from field verification |
| Not established in any inspected code | — | False-alarm-per-km² operating point; net-state modelling; injection-fitted Pd | These are open, but "not found" is not proof of absence |

**Consequence for our claims:** v1's "we saw no calibration, no Pd map" is **wrong** and must not be repeated. Our defensible claim is the quality of validated, integrated evidence, not that the parts are new (§23).

---

## 5. What NetSight is

**Definition** [P]: NetSight is an independent, sensor-neutral assurance layer for sonar survey contacts. It reads exported survey data, runs one NetSight model family plus a trust layer, and delivers a signed evidence pack. It does not control vehicles, does not certify absence, and does not replace divers.

### 5.1 The seven outputs

| # | Output | Plain meaning |
|---|---|---|
| 1 | **Contacts** with P(real), class probabilities, `unknown`, size, height (if measurable) | "This contact is 0.78 likely to be real; most likely a net bundle" |
| 2 | **Pd map** per reference target (e.g. 1 m cube, 2 m cube, net patch of stated area), as a **lower bound** with interval | "If a 1 m cube were in this cell, we would have flagged it with probability ≥ 0.82" |
| 3 | **Operating point** at a stated false-alarm budget per km² | "At ≤ 2 false alarms/km², expected recall is X (interval)" |
| 4 | **Claim level** per survey and per sensor | Calibrated / indicative / withdrawn, with the reason |
| 5 | **Position ellipse** per contact (95%) | Tested against known targets |
| 6 | **Provenance record** | Every number traceable to data, model, calibrator and reviewer versions |
| 7 | **Action outputs** | Ranked verification (dive/ROV) plan, re-survey polygons, report |

### 5.2 Modes (configuration, not separate products) [P]

| Mode | Classes and rules | When |
|---|---|---|
| Hydrographic / disaster debris | Disaster taxonomy (§8.4); S-57-style fields; "not for navigation" | MVP |
| Ghost gear | Gear taxonomy and net states; class-conditional shadow | MVP |
| UXO / offshore | 1.0 m pick threshold, boulders never auto-discarded (rank only), pUXO wording, Cenos contact fields | After Stage 2 |
| Search & recovery | Single-target class with prior map; Bayesian search wording | After Stage 2 |

---

## 6. Every drawback, and how this plan handles it

| # | Drawback (from the research) | How this plan handles it | Residual risk |
|---|---|---|---|
| 1 | Side-scan only | Format adapters for XTF, JSF, GSF, KMALL, s7k, Oculus and GeoTIFF; physics normalisation; one model family with sensor metadata conditioning; second sensor = multibeam backscatter, third = forward-looking sonar (§7) | A shared backbone across sonar types is unproven; fallback is per-family heads with the same trust layer |
| 2 | Better hardware shrinks the problem | Trust layer is sensor-neutral; SAS contacts still need review (Kongsberg ships a target assistant for its 13 mm SAS) [S]; Pd is target-specific, so it stays useful at any resolution | For premium sensors the false-alarm pain is smaller and unmeasured |
| 3 | Not real-time, not for buried objects | Stated scope: post-survey and near-real-time block processing; buried objects need a sub-bottom profiler or magnetometer; UXO mode accepts magnetometer flags as inputs later | None if worded honestly |
| 4 | Coverage half is weak (mosaics and S-44 already show coverage) | Pd is per target size and seabed condition, a lower bound, validated, and dependence-aware across passes; HSSD itself says 100% coverage cannot disprove a feature [V] | Buyers may still accept binary coverage |
| 5 | Prior art is close (SeeByte insertion, SAS uncertainty, competitor repos) | Claim the closed loop: injected Pd **validated** against real laid targets, final-output calibration on held-out surveys, applicability withdrawal, provenance. Cite prior art first | Novelty is in evidence, so it must actually be produced |
| 6 | Vendors bundle AI and add "probability estimates" | Position as the **independent** grade of anyone's output; support several formats; sell to the risk owner (§17) | A classification society could enter; aim to be the method behind them |
| 7 | Easy to copy | Moat stack: neutrality, open method and benchmark, outcome-label ledger, later accreditation and insurer backing (§17.3) | Ledger depends on contracts |
| 8 | No public ghost-net data | Use real ghost-gear data that exists (GhostVision crab pots, CC BY-SA), our own laid nets in trials, partner data (WWF/GEOMAR-style MoU); injected nets only for Pd sweeps, never for calibration (§11) | Net-specific numbers stay provisional until real nets are verified |
| 9 | Calibration needs many labels per sensor | Parametric calibrators (Platt/beta with covariates) needing hundreds of contacts per condition; binning only with thousands; visible "not validated for this sensor" state (§9) | Honest but slower claims on new sensors |
| 10 | No Indian data | Model-to-data MoU with NIOT, NIO, GSI or IIT Madras (data stays on their premises); request letters in week 1 | Long lead time |
| 11 | Proof of value is long and costly | Free retrospective calibration on public NOAA contacts; cheap seeded-target trial (Omniscan 450 SS ≈ $5.4–6.7k) [S]; services pilots generate labels as they earn | Trial still needs a boat |
| 12 | Proposal facts were wrong or unverified | Corrected throughout; Stolte figures now verified with exact wording (§2) | — |
| 13 | Few Indian buyers; Navy does work in-house | India = grants, data and build base; first revenue sought globally; Navy only via a firewalled defence track | — |
| 14 | Survey spend is small | Target segments where false targets cost vessel-days (UXO, S&R); price per survey, not per seat | Unproven willingness to pay |
| 15 | No buyer shown to pay | Stage 0 interviews and a paid/near-paid pilot ask are kill gates before heavy engineering (§19) | This is the main business risk |

---

## 7. Architecture: one NetSight model family for all sonars

### 7.1 The layers

```
 RAW / EXPORTED DATA: XTF · JSF · GSF · KMALL · s7k · Oculus · GeoTIFF/BAG mosaics (+ nav, attitude)
        │
 L0  FORMAT ADAPTERS ──► common SonarRecord + SensorDescriptor (type, frequency, beamwidths,
        │                 range/along-track resolution, altitude, processing flags)
 L1  QC + PHYSICS NORMALISATION ──► quality mask Q, ground-range geometry, gain/angle correction,
        │                            resolution tiers, geometry channels (range, grazing angle)
 L2  NETSIGHT CORE (one shared backbone, conditioned on SensorDescriptor)
        │   + family heads: side-scan/SAS · multibeam backscatter · forward-looking · (3D later)
 L3  EVIDENCE: shadow/height (soft) · texture/mesh · lines · ripple deviation · local anomaly · context
 L4  ASSOCIATION + FUSION: across pings, passes and sensors → persistent object IDs
 L5  CALIBRATION (final output, per sensor × site group) + OPERATING POINT (false alarms / km²)
 L6  APPLICABILITY GATE (hard + soft + injection canary) ──► claim level
 L7  Pd / SEARCH-COMPLETENESS (injection-fitted, real-target-validated, lower bounds, dependence-aware)
 L8  GEOLOCATION + UNCERTAINTY (propagated covariance, tested ellipses)
 L9  PROVENANCE LEDGER + REVIEW/VERIFICATION WORKFLOW
 L10 OUTPUTS: contacts JSON/CSV (S-57/HSSD-aligned) · Pd GeoTIFF/GeoJSON · re-survey polygons ·
              verification plan · evidence-pack PDF
```

**Routing is not an AI** [P]: L0 reads the file format and metadata and selects the family head and the calibrator. A wrong or unknown descriptor sends the survey to the applicability gate, which withdraws calibrated claims.

### 7.2 "One AI": what is shared and what is per sensor

| Shared (written once) | Fitted per sensor family / site |
|---|---|
| Adapters' common record, normalisation code, NetSight Core backbone (Stage B), evidence features, association, calibration code, Pd framework, provenance, outputs | Detection head weights, calibrator parameters, Pd model parameters (as a random effect), applicability reference banks |

The trust layer is sensor-agnostic **in code but not in fitted parameters**: calibration and conformal guarantees assume deployment data resemble calibration data, so each sensor and site group gets its own fit and its own claim level [V method literature; P design].

### 7.3 Evidence behind the "one model" design

| Finding | Tag |
|---|---|
| No public "universal sonar" model exists, and no sonar paper uses sensor-metadata conditioning | [S] (few queries) |
| BenthicDINO: self-supervised ConvNeXt-v2-T pretrained on ≈1M Klein 3000H (500 kHz) tiles, with a penalty making features independent of incidence angle and slant range. Frozen, it reached 0.423 shipwreck IoU on AI4Shipwrecks (EdgeTech 2205) vs 0.411 for a supervised U-Net, but 0.651 on deep sites vs 0.280 on shallow ones. No code or weights; no controlled cross-sensor test | [V] |
| Mine-JEPA: pretrained on only 1,170 side-scan images, F1 0.935 vs 0.922 for fine-tuned DINOv3; continued self-supervision on top of DINOv3 **hurt** by 10–13 points | [V]/[S] |
| Domain gaps are large: optical→side-scan detection mAP 9.58 source-only vs 58.88 supervised, 48.64 with adaptation (DCBD); GhostNetZero Baltic→Puget Sound mIoU 0.740→0.547, joint training recovers 0.739/0.685 | [V] |
| Remote-sensing "any-sensor" models condition on metadata: DOFA (wavelength hypernetwork; DOFA+ from DINOv2, 8×L40 ≈3 days), Panopticon (channel cross-attention, learned SAR embeddings), Copernicus-FM (Fourier-encoded metadata, learned "missing" token, 0.7 metadata dropout, 512 A100 GPU-hours per run) | [V] |
| Single-domain features can make kNN/Mahalanobis out-of-distribution scores blind to domain shift; distilling from a frozen DINOv2 teacher helps (arXiv 2603.11269, code not released) | [V] |

### 7.4 Stage A (ships first) and Stage B (the one shared backbone)

**Stage A — per-family detectors + shared trust layer** [P]
- Detector: **D-FINE-S/N or DEIM-S/N** (Apache-2.0) per sonar family; RF-DETR Nano–Large (Apache-2.0) as an alternative. Avoid Ultralytics YOLO (AGPL-3.0) and Objects365-derived checkpoints [V licences].
- Backbone init: **DINOv2 ViT-S/14** (Apache-2.0 reported; verify in repo in WP0). DINOv3 is **not** used: its custom licence prohibits uses "related to military or warfare purposes" and espionage, a real risk for a product near mine countermeasures [V, licence page via summariser; legal review required].
- Optional per-family self-supervised warm-up on unlabelled tiles (Mine-JEPA/BenthicDINO style), always with distillation anchoring to avoid the Mine-JEPA collapse.
- Builds the leave-one-sensor-out / leave-one-site-out harness and the per-sensor numbers Stage B must beat.

**Stage B — NetSight Core, one sensor-conditioned backbone** [P]
- ViT-S/B initialised from DINOv2; **sensor token** plus **FiLM** modulation every N blocks from a metadata vector: log frequency, along/across beamwidths, native along/across pixel size and tile footprint, max range, altitude and per-column grazing angle (side-scan), sensor-type one-hot (SSS, SAS, MBES backscatter, FLS, 3D), correction flags. Scalars Fourier-encoded; 50–70% metadata dropout with a learned "unknown" token (Copernicus-FM practice).
- Objective: masked image modelling with sonar-aware targets (multi-scale gradients of log-intensity, after SARATR-X) + cosine distillation from frozen DINOv2 (after DOFA+) + optional cross-frequency multi-crop when the same seabed is seen at two frequencies.
- Geometry invariance in the representation (BenthicDINO-style penalty on grazing angle and range); **no** invariance in calibration, which stays per sensor.
- Data mixing: sensor sampling ∝ n^0.5 so rare sensors aren't drowned out; resolution tiers (SAS cm, side-scan 5–20 cm, MBES backscatter dm–m) rather than resampling everything to one size.
- Augmentations: multiplicative (gamma) speckle, synthetic TVG and beam-pattern roll-off, range-dependent blur, across-track stretch, anisotropic downsampling to mimic other sensors, ping-line dropout, nadir masking, dynamic-range changes; port/starboard flips only, never along range.
- Compute: **≈100–600 A100 GPU-hours** for continued pretraining on 0.3–1M tiles [E, extrapolated from published runs]; pilot on 5–10% first.

**Go / no-go between A and B** (pre-registered; thresholds are our proposal) [P]
- GO if, over ≥ 3 seeds with survey-level bootstrap: (1) on held-out sensors with 5–10% labels, shared + few-shot beats per-sensor models on AP50 **and** recall at fixed false alarms/km², or matches them with ≥ 5× fewer labels; (2) in-sensor performance within ≈1 AP point of the per-sensor model **for every sensor**; (3) calibration after per-sensor recalibration no worse; (4) the applicability gate separates held-out sensors at a pre-agreed AUROC and flagged surveys really are worse.
- NO-GO: keep Stage A heads and share only the trust layer; publish the negative result (it is still a first).

### 7.5 Sensor order

| Order | Sensor | Why | Free data to start | Main risk |
|---|---|---|---|---|
| 1 (now) | Side-scan | Problem statement, most data | NOAA mosaics + contact lists, Bodine/GhostVision Humminbird sets, SubPipe, JNCC raw, AI4Shipwrecks (research only) | Mosaic-only inputs hide gain history |
| 2 | Multibeam backscatter (+ bathymetry) | Co-acquired on most NOAA, wind and cable surveys; GeoHab backscatter guidelines give a normalisation standard | NOAA folders hold side-scan and backscatter over the same seabed (e.g. H13684, CC0) [V] | Coarser resolution, vendor sector corrections |
| 3 | Forward-looking / imaging (Oculus, Gemini, ARIS, Omniscan FS) | Verification step of search and recovery; cheap hardware (Omniscan 450 FS ≈ $1,750–3,757) [S] | DFKI UXO set (BSD-3), NKSID (MIT repo label), UATD/Marine Debris FLS (research only) | Polar, short-range, temporal data |
| 4 | SAS | Highest resolution | SCTD 3.0 (>10k snippets, licence unconfirmed), first cross-frequency numbers would be new | Scarce, defence-linked |
| 5 | 3D / water column; magnetometer fusion for UXO | Niche; magnetometer matters more than any extra sonar for UXO [P] | Almost none public | Proprietary formats |

---

## 8. Methods, stage by stage

### 8.1 L0–L1 Ingest, QC and normalisation

| Task | Method | Source / lesson |
|---|---|---|
| Read formats | pyxtf (XTF), xtfjsf (XTF+JSF incl. SAS), gsfu (GSF, KMALL→GSF), pykmall, oculus-python; MB-System (GPL-3) only as a **separate command-line step**, never linked | [S] readers; licences unchecked except MB-System GPL [V] |
| Navigation provenance | Record where every position came from (GNSS, USBL, layback model, default). **Never** substitute fixed or formula positions silently; a survey without usable nav gets "position withdrawn" | Audit: some competitors assign fixed nav [V] |
| Bottom tracking, slant→ground range | First strong return, smoothed; `ground = √(slant² − altitude²)` | v1 [P] |
| Gain and angle correction | Sonar TVG + empirical across-track equalisation (side-scan); GeoHab Backscatter Working Group angular-response correction (multibeam) | [S] GeoHab; formula in ch. 6.7 to be read |
| Speckle | Log transform; light despeckling only for evidence features, never heavy on detector input (thin lines vanish) | v1 [P] |
| Dropout repair | Interpolate only isolated bad rows; keep large continuous zero regions as missing (they mark "not searched") | Adopted from Varuna [V audit] |
| Quality mask Q (0–1 per ping) | Roll/pitch thresholds and rates, altitude jumps, ping/time gaps, stripe artefacts (low neighbour-ping correlation), towfish height outside 8–20% of range | HSSD towfish-height rule [V] |
| Resolution tiers and geometry channels | Resample per tier; add per-pixel range and grazing angle (`θ ≈ arctan(altitude / ground_range)`) as channels | [P], BenthicDINO idea [V] |

### 8.2 L2 Detection

- Tiled inference (e.g. 640 px, 20–25% overlap), cross-tile merging, a stride-4 feature level for small objects; **low threshold** here to favour recall, since calibration and the operating point come later [P].
- Labelling assist with **SAM 2** (Apache-2.0) and CVAT; masks reviewed by a person [V SAM 2 licence].
- Raw detector scores are never shown as probabilities.

### 8.3 L3 Evidence (what an expert checks)

| Evidence | Method | Rule |
|---|---|---|
| Shadow and height | Shadow segmentation along range; flat-seabed height `h ≈ H·Ls/(R+Ls)` | **Soft feature, never a gate.** Expectation is class-conditional: bundles and wrecks should cast shadows; flat nets may not [H]. Competitor anti-pattern: a blanket ×0.48 penalty when no shadow [V audit] |
| Mesh texture | Gabor energy, 2-D FFT periodicity | Needs ≥ ~600 kHz-class resolution; Stolte resolved "gillnet lines as thin as 1cm" at 600 kHz [V] |
| Line continuity | Frangi ridge + Hough, tracked across pings | Float/sink lines, ropes, pipes, cables |
| Ripple-field deviation | Structure tensor / FFT orientation and wavelength | Ripples are regular over long distances; gear patches break the pattern |
| Local anomaly | DINOv2 patch features from **this survey's** normal seabed, coreset memory bank, kNN distance (FAISS) | PatchCore-style [P] |
| Context | Range bin, grazing angle, seabed complexity, Q, depth | Feeds calibration covariates |

### 8.4 Class taxonomy (two-level, always with `unknown`) [P, evidence per row]

| Family | Labels | Evidence |
|---|---|---|
| Ghost gear | `net_bundle_or_mound` (heap or snagged, stands proud) · `net_flat_or_collapsed` (low relief, textured patch, trailing lines; shadow little or none) · `net_standing_or_suspended` (**provisional**, no signature study) · `line_rope` · `trap_pot` | Stolte Fig. 2 bundles cast shadows [V]; flat-net behaviour [H]; pots in GhostVision [V] |
| Disaster debris | `vessel_wreck` · `container_box` · `vehicle_like` · `large_structure_block` · `rubble_field` (polygon, not point) · `pipe_cable_linear` · `tree_log_vegetation` (low confidence) | Tohoku, Katrina/Rita, Sandy survey practice [S]; proposal for response needs |
| General | `compact_debris` (anchor, tyre, drum) · `rock_boulder` · `natural_seabed_texture` (reef edge, flora, sediment change: hard negatives) · `unknown_manmade_contact` · `unknown` | Stolte confusers [V] |
| UXO mode | `cylinder_like` and size descriptors as **attributes**, not classes; `pUXO_candidate` flag | Cenos UXO specification [V] |

Ambiguous splits merge to the parent (e.g. `vessel_wreck` vs `container_box` → `large_manmade_object`) when the split's probability is below a stated threshold [P].

### 8.5 L4 Association and fusion

- Static objects across pings, passes and sensors: **Mahalanobis gating** with `d² = Δᵀ(Σ₁+Σ₂)⁻¹Δ` against χ²(2) (5.99 at 95%), class and size compatibility as soft costs, **Hungarian** assignment per pass pair, cluster-level persistent IDs with an append-only merge/split history [P; MCM contact-clustering literature S].
- Misses on an overlapping pass are recorded (they are Pd information).
- Association quality is measured on injected and real repeated objects (match precision/recall, mis-association rate).
- Fused scores are **recalibrated after association** and never combined with the independence formula.

---

## 9. The trust layer in detail

This is the core of NetSight. Every row has a method, the metric that proves it, and the minimum data [method literature V/S; minimum numbers E].

| Component | Method | Proof metric | Minimum data |
|---|---|---|---|
| Per-contact probability | Calibrate the **final** emitted score (after NMS, fusion, association). Default: Platt/beta with covariates (score, range, seabed complexity, box size); isotonic/histogram only with thousands of contacts per condition; temperature scaling only as a baseline | Box/range-aware D-ECE (Küppers et al.) plus ordinary reliability diagram, Brier; survey-level bootstrap CIs | Hundreds of labelled contacts per condition for parametric maps (≈400 for ε = 0.05), 2,000+ for binning [E]; spread over ≥ 5–10 independent surveys |
| Operating point | Choose the threshold on calibration surveys with Learn-then-Test / conformal risk control, using false alarms per km² as the loss; freeze it | Recall (Clopper-Pearson, cluster-level) at the fixed FA/km² on held-out surveys; FROC curve (recall vs FA/km², log-x) with a stated matching radius | Enough area to see ≈30–100 false alarms at the budget [E] |
| Pd map | Target injection into **real** seabed (elevation estimate + 3-D target model + side-scan ray tracing; GAN refinement optional), random positions, per cell conditional on class, net state, size, range, complexity, Q; hierarchical model with sensor as a random effect | Per-cell one-sided Clopper-Pearson lower bound | Zero-miss claims need ≈29 / 59 / 299 effective independent trials for Pd ≥ 0.90 / 0.95 / 0.99 [E, exact binomial] |
| Pd validity (the closed loop) | Compare injected-Pd predictions with detection of **real** laid targets and surveyed objects at the same range and seabed | Observed detection inside predicted band; reliability diagram of Pd itself | ≈20–30 real targets gives a first, wide check [E] |
| Multi-pass combination | Measure pairwise miss-correlation ρ by injecting the same object at the same place in overlapping passes; fit a shared-difficulty model | ρ with CI; predicted vs observed joint detection | Many overlapping-pass positions. Until ρ is measured, report **[max Pdₖ, 1−Π(1−Pdₖ)]** and publish the lower end |
| Search-completeness wording | Bayesian update uses (1 − Pd), so an overstated Pd wrongly "clears" cells → publish lower bounds | Sensitivity of posterior to Pd shown | — |
| Position uncertainty | Explicit budget: GNSS/INS + towfish (USBL or layback, feather, lateral offset) + heading + slant/ground conversion + pick error + reference-point ambiguity; correlated within a pass | Empirical coverage of 95% ellipses on known targets (mean d² ≈ 2, ≈95% within 5.99), reliability over nominal levels | ≈60 known-position targets for ±5–6 point resolution [E] |
| Applicability gate | Hard gate on sonar model, frequency band, range scale, resolution, processing chain; soft gate on embedding kNN + Mahalanobis (L2-normalised) + survey-level MMD/KS against reference banks; **injection canary** in every new survey | False-withdrawal and missed-withdrawal rates on deliberately shifted held-out surveys; flagged surveys must really be worse | ≥ 2 sonars/configurations to demonstrate withdrawal |
| Provenance | W3C PROV-style records (data, model, calibrator, contact, reviewer), append-only and hash-chained; calibrator released as a versioned artefact with an evidence pack in DNV-RP-0671 claims-and-evidence form | Re-run reproduces every contact and probability; tamper detection | — |

**Claim levels** [P]: *Calibrated* (inside envelope, calibrator validated) → *Indicative* (soft drift detected; scores relative only) → *Withdrawn* (outside envelope; no probabilities or Pd shown, only candidate list).

**Conformal tools buy an average, not a per-contact guarantee.** SeqCRC/CRC bound the expected loss over calibration and test draws, valid only when surveys are exchangeable; a new seabed or sonar breaks that [V, Andéol et al. 2025]. Wording: "on surveys drawn like the calibration surveys, the expected fraction of true objects missed is at most α", never "each object has ≥ 1−α chance of being flagged".

**Statistics rules** [P]: never split by tile or frame; hold out whole surveys, sites and (for the "new sonar" claim) whole sonar models; resample whole lines or surveys in bootstraps; report the spread across surveys and the worst sensor, not only the mean; Clopper-Pearson for any headline bound, Wilson only for descriptive plots; 2–3 pre-registered FA/km² operating points.

---

## 10. Features adopted from the 120-repository audit

| Feature | Seen in | How NetSight does it, and why it is stronger | Priority |
|---|---|---|---|
| Final-output calibration | Sagar-Netra, Aqua-AI (temperature scaling) | Calibrate the post-fusion score with covariates; D-ECE + reliability on untouched surveys | P0 |
| Survey/site-level splits, manifests and hashes | DEPTH, KADAL (flags its own leakage) | Mandatory; split provenance in the evidence pack | P0 |
| Statistical bounds | DEPTH (Clopper-Pearson, block bootstrap) | Clopper-Pearson lower bounds on recall and Pd; cluster bootstrap | P0 |
| Applicability withdrawal | DEPTH (withdraws on unfamiliar sonar) | Three-level claim gate with injection canary (§9) | P0 |
| Empirical Pd map | Sagar-Netra (hand-set coefficients) | Injection-fitted, real-target-validated, lower bounds, dependence-aware | P0 |
| False-alarm budget | Not established anywhere | FA/km² operating point via risk control | P0 |
| Class-specific handling of missing shadow | SIH26 (blanket ×0.48 penalty) | Class-conditional soft shadow evidence; net-state ablation | P1 |
| Expert review + immutable record | DeepSight, 22 repos with review code | Separate reviewer opinion from field verification; record model and calibrator versions; this is also the outcome ledger (§17.3) | P1 |
| Persistent object IDs, cross-pass association | DeepSight, Sagar-Netra (image-space) | Geographic Mahalanobis gating + Hungarian + merge/split history | P1 |
| Raw XTF/JSF ingestion with navigation | Varuna, Sagar-Netra, KADAL | Navigation provenance; "position withdrawn" when nav is missing | P1 |
| Geometry-preserving dropout repair | Varuna | Repair isolated rows only; large gaps marked as not searched | P1 |
| Position uncertainty | KADAL, sonarsentinel, Aqua-AI (mostly radii) | Propagated covariance with a coverage test on known targets | P1 |
| Pd-driven second-look planning | Sagar-Netra, DEPTH, SIH26 (generic or simulated) | Rank re-survey polygons by expected Pd gain per boat-minute; constraints stated | P2 |
| Edge / ONNX, offline GIS, async jobs | Sagar-Netra, Aqua-AI, DEPTH | ONNX Runtime int8 on CPU, offline map tiles, resumable jobs, published CPU benchmark | P2 |
| Synthetic net generation | SIH26, Synthetic-Ghost-Nets repo | Injection on real seabed for Pd sweeps only; never for calibration | P1 |
| Anomaly scoring | vineeth29 (autoencoder), sonarsentinel | Survey-local PatchCore-style memory bank | P1 |
| **Deferred** | Chatbot/knowledge assistant, decorative 3-D, mass estimates, vehicle autonomy, floating-debris drift tracker | Widen the demo without fixing evidence; drift is not a seabed problem | Defer |

---

## 11. Data plan

### 11.1 Three kinds of ground truth (never mix them in one claim)

| Kind | Meaning | Proves | Sources |
|---|---|---|---|
| Expert disposition | A hydrographer or archaeologist judged the contact | Calibration **against expert judgement** | NOAA Descriptive Reports, most public datasets |
| Physical verification | Diver, ROV, clearance or retrieval established what it was | Calibration against reality; real false alarms | UXO campaigns, ghost-gear removals, partner pilots |
| Known placement | Target laid at a known position | Pd and position uncertainty | Own trials, Bath mannequin set, DFKI UXO set, AI4Shipwrecks known wrecks |

No public dataset we found provides **verified false positives**. That gap is the main data problem and the moat opportunity.

### 11.2 Sources by licence status

| Tier | Source | What it gives | Licence | Tag |
|---|---|---|---|---|
| **Commercial-OK** | NOAA H-surveys (e.g. H13684: 900 kHz side-scan mosaics, 300 kHz backscatter, BAG, Descriptive Report) | Contacts + dispositions (inside DR PDFs), two sensors on the same seabed | CC0 | [V] |
| | Bodine side-scan substrate/depth/shadow image-label pairs (Zenodo 10119320, 13.8 GB) | Recreational (Humminbird-class) side-scan with labels | CC BY 4.0 | [V] |
| | Catalan seafloor-sediment set (Zenodo 10209445, 434,164 unlabelled patches) | Pretraining | CC BY 4.0 | [V] |
| | SubPipe (Zenodo 10808161, 10,030 images) | Pipelines, dual-frequency side-scan | CC BY 4.0 (code GPL-3.0) | [V] |
| | Bath mannequin set | Known-placement body-like target | CC BY 4.0 | [V] |
| | DFKI UXO set (Zenodo 13778485, 74k+ frames) | Imaging sonar + camera, 3-D ground truth | BSD-3 | [V] |
| | JNCC/Cefas raw side-scan (survey CEND 11/11) | Raw UK side-scan | OGL, "no limitations" | [V] |
| | INFOMAR (Ireland) | Backscatter grids, shipwreck catalogue | CC BY 4.0 | [S] |
| | PINGMapper | Processing for Humminbird, Lowrance, Garmin, Cerulean | MIT | [V] |
| **Commercial with conditions** | GhostVision crab-pot set (Zenodo 20056679, 899 MB; Hugging Face copy 6,674 images) | Real derelict-gear boxes | CC BY-SA 4.0 (ShareAlike; HF page text says GPL — ask authors) | [V] |
| **Research-only until written permission** | AI4Shipwrecks (286 images), UATD, SCTD 3.0, KLSG, NKSID (MIT label on repo), SASSED | Benchmarks | Unconfirmed | [V]/[S] |
| | Marine Debris FLS (Zenodo 15101686, 7.1 GB) | Forward-looking debris | **CC BY-NC-SA** (non-commercial) | [V] |
| **Request-based** | NOAA raw side-scan (JSF/HSX via trackline archive), USGS raw XTF (e.g. CMGDS 38005), Crown Estate Marine Data Exchange (licences vary; some need permission) | Raw pings, wind-farm surveys | Varies | [S] |
| **Partnership gold** | Offshore-wind UXO target lists with ROV results (public PDFs on Archaeology Data Service, Scottish marine licences; raw sonar with developers) · WWF Germany Baltic data (proprietary) · Puget Sound and Chesapeake derelict-gear programmes (Virginia recovered 9,970 pots with side-imaging sonar) | Physically verified real and false contacts | NDA / MoU | [S] |
| **India** | NIOT, NIO, GSI (side-scan + SAS), IIT Madras | Local seabed, a validation sector | Model-to-data MoU (data stays on their premises) under NDSAP | [S] |
| **Own** | Seeded-target trials (§12.4) | Pd, position coverage | Ours | [P] |
| **Synthetic** | Injection engine; HoloOcean simulator; diffusion synthesis (Syn2Real reported ≈60% AP gain from added synthetic data, abstract only) | Pretraining, Pd sweeps | Ours | [S]/[P] |

**Rules** [P]: (1) a licence register entry before any file enters a training set; (2) research-only sets live in a separate store and never touch commercial weights; (3) calibration is fitted and reported **only on real data with known outcomes**; synthetic and injected data are for pretraining and Pd sweeps.

### 11.3 NOAA contact-outcome pipeline (the free first dataset)

1. Select 20–40 H-surveys with side-scan contact listings (start: H13684, H12243, H12251, H12333, H12394, H12396) [V/S].
2. Download DR PDF, mosaics, backscatter, BAG; parse contact listings, Danger-to-Navigation and AWOIS investigation sections (OCR + table extraction; budget real effort).
3. Map contact positions to mosaic GeoTIFFs; record disposition (`descrp` New/Update/Delete/Retain/Not Addressed; DTON) [V HSSD].
4. Note: NOAA's Wrecks and Obstructions database removes disproved or salvaged items [V], so negatives must come from the DRs.
5. Output: contact-outcome table v0 with provenance, labelled "expert disposition".

Precedent: hydrographers reviewed 24,726 automatic side-scan detections from two NOAA-contracted sheets to build ground truth; a classifier reportedly reached ≈93% Pd at ≈6% false-alarm rate [S].

### 11.4 First 8 weeks of data work

| Week | Action |
|---|---|
| 1 | Download commercial-OK sets (Bodine, Catalan, SubPipe, Bath, DFKI). Send request emails: NOAA `hsd.inquiries@noaa.gov` and `trackline.info@noaa.gov`, USGS `PCMSC_data@usgs.gov`, AI4Shipwrecks and SCTD 3.0 authors (licence), GhostVision authors (GPL vs CC BY-SA), NIOT/NIO/GSI/IIT Madras (MoU) |
| 2–3 | Pull NOAA folders; build the DR parser; contact-outcome table v0; download GhostVision and JNCC raw side-scan |
| 4 | INFOMAR wrecks and backscatter; USGS/Hudson River XTF; Marine-Geo 6159 EdgeTech XTF |
| 5–6 | Process replies; check Marine Data Exchange terms; research-only benchmarks kept separate |
| 7–8 | Marine Debris FLS as research benchmark only; ghost-gear report figures as qualitative references; follow up Indian requests; choose Pd-validation targets (INFOMAR and NOAA wrecks) |

---

## 12. Evaluation protocol and what counts as success

### 12.1 Splits
Leave-one-sensor-out across families; leave-one-site-out within each sensor; leave-one-platform-out where possible; geographic blocks, never overlapping tiles across splits [P].

### 12.2 Baselines (each one beaten is a pitch line)

| Baseline | What it represents |
|---|---|
| B0: detector raw score | A typical SIH project |
| B1: temperature scaling on the detector score | Sagar-Netra / Aqua-AI |
| B2: hand-set logistic Pd and max-Pd across passes | Sagar-Netra Pd grid |
| B3: shadow-required filter | Common hazard-picking heuristic |
| B4: per-sensor models (Stage A) | What Stage B must beat |

### 12.3 Metrics
Detection AP50 and AP_small; **recall at 2–3 pre-registered FA/km² points**; FROC; D-ECE, reliability, Brier (before and after per-sensor recalibration); Pd-vs-range curves; Pd validity on real targets; ellipse coverage; withdrawal AUROC and false/missed withdrawal; association precision/recall; CPU latency per 100 m of track; dive-plan precision (top-10 real), compared with the ≈half-real baseline from Stolte. Every number broken down by depth, seabed type and sensor (BenthicDINO's 0.651 vs 0.280 depth split shows why) [P].

### 12.4 The seeded-target trial (Pd ground truth)
- Lay targets of known size at GNSS-surveyed positions in a lake, harbour or university basin: 1 m and 2 m cubes (S-44 reference shapes), a net panel flat on the bed, a net bundle, a rope line, a pot [P].
- Survey at several ranges, speeds, altitudes (8–20% of range) and passes; record conditions.
- Hardware: Cerulean Omniscan 450 SS ≈ $5,440 (Blue Robotics page), £5,640 (RobotShop UK) or $6,700 (another reseller), plus ≈£250 integration kit [S]; boat borrowed from NIOT, IIT Madras or Planys if possible [P].
- Outputs: Pd-vs-range per target, injected-vs-real Pd comparison, ellipse coverage, flat-net shadow test (answers hypothesis §2.3).

### 12.5 Open benchmark
Publish the NOAA contact-outcome table (CC0 sources), injected-target protocol, scoring scripts (D-ECE, FROC, Pd validity, ellipse coverage) and baseline results; later add the first published cross-frequency numbers on SCTD 3.0 splits if its licence allows [P].

---

## 13. Outputs, standards and wording

### 13.1 Contact record (JSON; CSV flattens the same keys) [P, field basis in comments]

```json
{
  "contact_id": "S0012-0017",            // HSSD userid
  "survey_id": "...", "line_id": "...", "pass_ids": ["..."], "channel": "stbd",
  "lat": 0.0, "lon": 0.0,                 // WGS84
  "pos_cov_m2": [[0,0],[0,0]],            // along/across covariance rotated to N/E
  "horiz_unc_95_m": 0.0,                  // S-44 THU language; method stated
  "length_m": 0.0, "width_m": 0.0,        // Cenos: longest dimension / perpendicular
  "height_m": null, "height_method": "shadow|mbes|none",   // HSSD cnthgt
  "shadow_present": false,                // soft evidence, never a gate
  "class_probs": {"net_flat_or_collapsed": 0.0, "rock_boulder": 0.0, "unknown": 0.0},
  "top_label": "...", "p_real": 0.0, "p_real_ci90": [0.0, 0.0],
  "confidence_band": "low|medium|high",   // Cenos convention
  "claim_level": "calibrated|indicative|withdrawn",
  "calibration": {"calibrator_id": "...", "method": "beta+covariates", "d_ece": 0.0, "calib_set_id": "..."},
  "uncertainty_flags": ["soft_seabed", "range_edge", "nadir_gap", "single_pass_only"],
  "persistent_object_id": "OBJ-0042", "association_history": ["..."],
  "ancillary_confirmation": "none|second_pass|mbes|diver|rov",
  "tecsou": 2,                            // S-57: found by side scan sonar
  "disposition": "candidate|needs_review|verified_real|verified_false|retain",
  "puxo_candidate": false,                // UXO mode only
  "images": ["S0012-0017_waterfall.png"],
  "provenance_hash": "...", "model_id": "...", "reviewer": null, "remarks": ""
}
```

**Pd map product**: per cell and per reference target: `pd_lower90`, `pd_mean`, `pd_interval`, `pass_count`, `holiday_flag`, `range_from_nadir`, `altitude_ratio`, `seabed_class`, `claim_level`; metadata mirrors the S-44 minimum list (feature detection ability, feature search %, uncertainties at 95%, dates) plus "not for navigation" [V S-44/HSSD; P design]. S-101 mapping is not yet checked; map to S-57 names for now.

### 13.2 The evidence pack (per survey) [P]
Summary page with claim level and envelope; contact table; Pd maps per reference target; operating point and expected false alarms (Σ(1−P(real))) and expected real contacts (ΣP(real)); reliability diagrams; applicability results and canary result; verification plan; re-survey polygons (GeoJSON/KML); provenance manifest; disclaimer.

### 13.3 Wording rules

| Do not say | Say instead |
|---|---|
| "The channel is clear" / "the area is safe" | "Cells shown green had an estimated Pd of at least 0.8 (90% lower bound) for a [stated reference target] under the recorded conditions" |
| "Certified" (before accreditation) | "Independent probabilistic second-opinion assessment of the supplied data" |
| "Calibrated" on a sensor without validation data | "Calibration not yet validated for this sensor; scores are relative" |
| "Works on any sonar" | "Reads XTF, JSF, GSF and KMALL; validated so far on [listed sensors]" |
| "Experts are right only half the time" | "About half of the suspects divers checked were real gear (94 of 176; Stolte et al. 2022)" |
| "Diver search costs €140/ha" | "The authors estimate at least ~€140/ha for a scooter-equipped diving team versus ~€8/ha for sonar search (Stolte et al. 2022)" |
| "Collapsed nets cast no shadow" | "Flat nets are expected to cast little or no shadow (hypothesis we test); shadow is never used as a hard filter" |
| "S-44 compliant net detection" | "S-44 feature detection is defined for cubes; we report net Pd separately" |
| "~90% detection" (borrowed from GhostNetZero) | Only our own measured, held-out numbers |
| "AI-verified", "confirmed ghost net" before diver/ROV | "Candidate contact", "potential ghost-gear contact", "pUXO candidate, unverified" |

**Standard disclaimer**: "NetSight provides a probabilistic second-opinion assessment of the supplied data. It does not certify the absence of objects. No single survey system can guarantee detection of all features. Residual risk remains and must be managed by the duty holder under the project's ALARP process. Not for navigation." [P, built from S-44, HSSD and UXO-spec language V]

---

## 14. Tech stack, licences and compute

| Layer | Choice | Licence note |
|---|---|---|
| Format readers | pyxtf, xtfjsf, gsfu, pykmall, oculus-python; MB-System via CLI only | Small-reader licences **unchecked**; MB-System GPL-3 [V] |
| Geo | GDAL/rasterio, pyproj, shapely, PostGIS | Confirm in WP0 audit |
| ML | PyTorch; DINOv2 (Apache-2.0 reported, verify); D-FINE / DEIM (Apache-2.0); RF-DETR N–L (Apache-2.0); SAM 2 (Apache-2.0) | Avoid Ultralytics (AGPL), DINOv3 and DEIMv2-DINOv3 variants (military clause), Objects365 checkpoints, RF-DETR Atto/Femto/Pico/XL/2XL (platform licence) [V] |
| Features / stats | OpenCV, FAISS, scikit-learn, statsmodels | Confirm in WP0 |
| Experiment tracking | MLflow or DVC; dataset manifests with hashes | — |
| Provenance | Append-only hash-chained records (W3C PROV vocabulary) in PostgreSQL | — |
| Backend / UI | FastAPI; React + MapLibre or Leaflet; offline tiles | — |
| Edge | ONNX Runtime, int8, CPU | Benchmark on our own CPU; no published CPU numbers for these heads |
| Integration | **File-in, report-out** (exported XTF/JSF/GeoTIFF); no HYPACK SDK, whose terms forbid using SDK materials "to train or fine-tune AI or machine learning systems" [V] | — |

**Compute** [E]: Stage A fits on a single 24–48 GB GPU (fine-tuning small detectors); Stage B ≈100–600 A100 GPU-hours, piloted on 5–10% of data first. Apply for cloud research credits and incubator compute before buying hardware.

---

## 15. Build plan (work packages)

Each package ends with a testable deliverable. Months are from project start.

| WP | Name | Deliverable | Acceptance test | Months |
|---|---|---|---|---|
| WP0 | Governance and licences | Licence register for every dataset and dependency; impartiality policy; data-rights clause template; repo with CI | Every training file traced to a licence entry; CI green | 0–1 |
| WP1 | Ingest + normalisation | Adapters (XTF, JSF, GeoTIFF first; GSF/KMALL next), SonarRecord + SensorDescriptor, Q mask, ground range, geometry channels, nav provenance | Round-trip tests on sample files; Q flags injected dropouts; missing nav → "position withdrawn" | 0–3 |
| WP2 | Data and labels | NOAA DR parser + contact-outcome table v0; labelling guide (taxonomy §8.4, observable net-state rules); SAM 2–assisted labelling | ≥ 10 surveys with usable contact listings (kill criterion if fewer); inter-annotator agreement measured | 0–4 |
| WP3 | Detection (Stage A, side-scan) | D-FINE/DEIM detector, tiled inference, ONNX export | Beats B0 on held-out surveys at matched FA/km²; AP_small reported | 1–4 |
| WP4 | Evidence + fusion | Shadow/height, texture, lines, ripple deviation, anomaly; fusion model | Ablation shows each feature's effect; class-conditional shadow beats B3 on flat-net cases | 2–5 |
| WP5 | Calibration + operating point | Calibrator on final output; LTT/CRC threshold at FA/km² | D-ECE and reliability on untouched surveys beat B1; recall CI at fixed FA/km² | 2–5 |
| WP6 | Pd + injection engine | Injection on real seabed, per-cell Pd with lower bounds, hierarchical model, multi-pass interval | Pd lower bounds reported per stratum; beats B2 on real-target agreement once trial data exist | 3–7 |
| WP7 | Applicability gate | Hard + soft gates, injection canary, claim levels | Withdrawal AUROC on a held-out sensor; flagged surveys measurably worse | 4–7 |
| WP8 | Association, geolocation, uncertainty | Persistent IDs; covariance per contact; ellipse coverage test | Mis-association rate on injected repeats; ellipse coverage on known targets | 3–8 |
| WP9 | Provenance + review workflow | Hash-chained ledger; reviewer vs field-verification records; evidence-pack generator | Replay reproduces all outputs; tamper test fails as expected | 2–6 |
| WP10 | Outputs, UI, edge | Contact JSON/CSV, Pd GeoTIFF/GeoJSON, KML, PDF evidence pack, dashboard (upload, waterfall overlays, map, Pd layer, evidence cards, reliability plots), verification plan, re-survey polygons, offline CPU mode | Opens in QGIS and Google Earth; offline run with no network; CPU benchmark published | 3–8 |
| WP11 | Evaluation harness + benchmark | LOSO/LOSiO harness, baselines B0–B4, scoring scripts, preprint v0 and benchmark v0 | Pre-registered results published with CIs | 3–6 |
| WP12 | Second sensor: multibeam backscatter | GeoHab-style normalisation; backscatter head; side-scan + backscatter fusion on NOAA paired data | Measurable calibration or Pd gain from fusion, or a documented negative | 9–16 |
| WP13 | Seeded-target trial | Trial design, targets, survey, analysis | Pd-vs-range curves; injected-vs-real comparison; flat-net shadow result | 4–9 |
| WP14 | NetSight Core (Stage B) | Sensor-conditioned backbone; go/no-go report | Pre-registered go/no-go (§7.4) | 12–20 |
| WP15 | Third sensor: forward-looking | FLS adapter + head; search-and-recovery mode | Same harness; withdrawal works across sensors | 15–22 |
| WP16 | UXO mode | Cenos-style fields, 1.0 m pick rule, boulders rank-only, pUXO wording; magnetometer flag input | Reviewed by a UXO consultant in an interview or pilot | 10–16 |

---

## 16. The first funding demo (around month 4)

What the demo must show, end to end, on public data only [P]:

1. Upload a NOAA survey (mosaic + DR) and a Humminbird/JNCC raw file; both parse with navigation provenance shown.
2. Contacts on the waterfall and map, with P(real), class probabilities and `unknown`.
3. Reliability diagram on **held-out** NOAA surveys: NetSight vs raw score (B0) vs temperature scaling (B1).
4. Recall at a stated FA/km², with an interval.
5. Pd map with lower bounds for a 1 m cube and a net patch; holidays and nadir shown as not searched.
6. Multi-pass interval shown honestly ([max, independence]).
7. Applicability gate: a different sonar's data gets "indicative" or "withdrawn" with the reason.
8. Provenance replay: one contact traced back to data, model and calibrator.
9. Verification plan: top contacts with expected real finds Σ P(real).
10. A one-page evidence pack PDF with the disclaimer.

**One contact through the system** [I — format only, not results]:

| Step | Contact S0012-0017 |
|---|---|
| L0–L1 | Starboard ping 12,408; nav from USBL; Q = good; 38 m ground range |
| L2 | `net_flat_or_collapsed` candidate, raw score 0.91 |
| L3 | No measurable shadow (consistent with class, not penalised); strong mesh periodicity; line continues over 40 pings; breaks ripple field; high local anomaly |
| L4 | Matched on pass 2 (d² = 1.7); persistent ID OBJ-0042 |
| L5 | P(real) = 0.74 (90% interval 0.63–0.83); passes the 2 FA/km² operating point |
| L6 | Claim level: calibrated (inside envelope; canary passed) |
| L7 | Cell Pd lower bound for net patch: 0.71; nearby nadir strip: < 0.2 → re-survey polygon |
| L8 | Position ± 3.4 m (95%) |
| L10 | Rank 3 in the dive plan; record hash stored |

---

## 17. Company plan

### 17.1 Business model: services first [P, evidence from Ocean Geophysics, Cyberhawk, Planys]
1. **Assurance desk** (months 6–15): fixed-price independent second opinion on a contractor's target list and coverage, delivered as a signed evidence pack, paid for by the **risk owner** (developer, UXO consultant, warranty surveyor, port, S&R contractor). The tool runs internally.
2. **Productise** after 10–20 paid jobs with labelled outcomes: API and file-based batch tool, later a plug-in where licensing allows.
3. **Licence the method** to an accredited inspection body or a sonar/software vendor if that is the better exit (consolidation is the verified exit pattern, e.g. Kraken's C$615M purchase of Covelya, closed 2 July 2026) [S].

Pricing hypotheses to test in interviews [H]: per-survey fee of at least a few thousand dollars, or a five-figure annual licence for repeat clients.

### 17.2 Who pays and why neutrality matters
- If the contractor whose list we grade pays us, we inherit the issuer-pays conflict seen in credit rating (S&P ratings rose after its 1974 switch to issuer-pays) [S].
- Marine warranty survey is usually a condition of offshore-wind construction insurance, and independence is called "one of the most important factors" [S].
- Independent testing and inspection keeps margins: Intertek, Bureau Veritas and SGS reported 2025 adjusted operating margins of 18.1%, 16.3% and 16.0% [S].

### 17.3 Moat ladder [P]

| Rank | Moat | First step |
|---|---|---|
| 1 | Neutrality paid for by the risk owner | Written impartiality policy (modelled on ISO/IEC 17020); no OEM or contractor equity or exclusivity; ≥ 3 formats supported |
| 2 | Open method and benchmark | Preprint + benchmark structured like DNV-RP-0671 claims-and-evidence; mapped to S-44, HSSD and UXO-spec terms; invite vendors to be scored |
| 3 | Outcome-label ledger | Data-rights clause in every pilot for anonymised post-investigation outcomes; schema = contact + outcome + conditions |
| 4 | Tool behind accredited sign-off, later own accreditation | Partner with a warranty surveyor, UXO consultancy or NABCB-accredited Indian inspection body; keep 17020-style records from day one; NABCB fees ≈ $800 per assessor-day [S] |
| 5 | Insurer-backed guarantee | Service credits first; insurer approach after a loss history exists (Augury/HSB precedent: up to $100k warranty) [S] |
| 6 | Narrow patent | At most one Indian provisional on a specific technical pipeline (injection-driven coverage map controlling re-survey planning); keep data and sensor models as trade secrets; freedom-to-operate check vs SeeByte insertion |

### 17.4 Partnerships [P]
- **Indian GhostNetBusters-style consortium**: an institute (NIOT, NIO or IIT Madras), NetSight, and an operator whose dives or recoveries verify contacts (NGO, port or Planys). Hosts with maritime programmes: NTCPWC at IIT Madras (Sagarmala, ≈Rs 77 crore) and the Cochin Shipyard–IIT Madras marine-startup programme (≈Rs 50 crore corpus) [S].
- **Data-for-validation NDAs** with survey contractors: they get a free retrospective assurance report, we get anonymised outcomes.
- **Non-exclusive** co-marketing with low-cost sonar makers (Cerulean, Deep Trekker); never exclusivity with an OEM or a contractor.

---

## 18. Funding plan

| Source | Amount | Fit and conditions | Tag |
|---|---|---|---|
| Startup India Seed Fund (via incubator) | Up to Rs 20 lakh grant + up to Rs 50 lakh debt/convertible | Proof of concept and prototype | [S] |
| DST NIDHI-PRAYAS (via incubator) | Up to Rs 10 lakh | Prototyping | [S] |
| iDEX SPARK (DISC / Open Challenge) | Up to Rs 1.5 crore in milestone tranches | Needs a matching Navy problem statement; firewalled defence variant only | [S] |
| iDEX Prime | Up to Rs 10 crore | TRL 4+ | [S] |
| ADITI 4.0 | Up to Rs 25 crore (≤ 50% of development budget) | Closed 4 May 2026 | [S] |
| Deep Ocean Mission (MoES) | ≈Rs 4,077 crore programme over five years | No startup call found; route via NIOT collaboration | [S] |
| International | Innovate UK marine UXO challenge, Offshore Wind Growth Partnership (amounts not captured); GhostNetBusters-type regional AI grants (≈€221k) | Needs a UK/EU partner | [S] |

**Order** [P]: incubator entry (IIT Madras Incubation Cell, NTCPWC or Cochin Shipyard–IITM) → Startup India Seed Fund + NIDHI-PRAYAS for Stages 0–2 → iDEX SPARK only when a Navy statement fits, in a separate codebase/dataset/entity (as Planys did with Planys Ark) → seed round or iDEX Prime after TRL 4 and paid pilots. Not yet researched: TDB, MeitY SAMRIDH/TIDE 2.0, EU BlueInvest, cloud credits.

**Known cash costs** [S/E]: sonar for trials $5.4–6.7k + ≈£250 kit; Stage B compute 100–600 A100 GPU-hours [E]; travel for pilots; accreditation later (≈$800 per assessor-day, 5–10 days ≈ $4–8k in assessment fees alone [E]). Rs 10–20 lakh in grants covers Stages 0–2 if a boat is borrowed [E].

---

## 19. 24-month roadmap with kill criteria

| Stage | Months | Goal | Milestones | Kill criteria |
|---|---|---|---|---|
| 0 | 0–2 | Find the payer, secure data rights | 20–25 interviews (half outside India; warranty surveyors, UXO consultants and S&R contractors first); licence register; impartiality policy; request emails sent | No named budget holder **and** nobody willing to share anonymised data |
| 1 | 1–5 | Retrospective calibration + MVP | WP1–WP5, WP9–WP11 on side-scan; NOAA contact-outcome table; preprint v0 + benchmark v0; funding demo (§16); incubator entry; SISFS / NIDHI-PRAYAS applications | Fewer than 10 NOAA surveys with usable listings, or calibration no better than the raw-score baseline at matched detection rate |
| 2 | 4–9 | Seeded-target Pd trial | WP6–WP8, WP13: Pd-vs-range, injected-vs-real comparison, ellipse coverage, flat-net shadow test | Predicted Pd misses observed detection beyond agreed bounds, or no vessel and no grant by month 9 |
| 3 | 6–15 | Paid assurance pilots | 2–3 fixed-price reviews (one EU/UK wind or cable consultant, one Indian port or dredging client, one S&R contractor); data-rights clauses; 17020-style records; UXO mode (WP16) | Fewer than 2 paying pilots by month 15, or clients refuse to return outcome data |
| 4 | 9–20 | Second sensor + one shared model + firewall | WP12 (backscatter fusion), WP14 (Stage B go/no-go); export classification; separate defence workstream if an iDEX statement fits | Fusion gives no measurable gain, or export classification blocks civil exports |
| 5 | 18–24 | Productise and harden | WP15 (forward-looking); API/batch tool after ≥ 10 labelled jobs; partnership with an accredited inspection agency or warranty surveyor; PI insurance; seed round or iDEX Prime; first insurer conversation | No repeat customer, or an incumbent bundles equivalent **validated** calibration for free |

Stages overlap on purpose. Track two numbers throughout: calibration samples per sensor (decides when "calibrated" is honest) and physically verified outcomes in the ledger (decides when a guarantee becomes possible).

---

## 20. Team [P]

| Role | Why |
|---|---|
| ML lead (detection, calibration, statistics) | Owns WP3, WP5–WP7, WP11, WP14 |
| Sonar / hydrography lead | Normalisation, Pd physics, S-44/HSSD alignment; recruit a hydrographer advisor (retired Navy, NIOT or a Category A/B hydrographer) early |
| Data and GIS engineer | Adapters, NOAA parser, geolocation, outputs |
| Full-stack / edge engineer | Dashboard, evidence pack, offline CPU mode |
| Business, policy and partnerships lead | Interviews, licences, grants, MoUs, pilots |
| Advisors | UXO consultant or warranty surveyor; a lawyer for licences, export and liability |

---

## 21. Legal, export and liability

| Issue | Plan |
|---|---|
| Model and code licences | Avoid AGPL (Ultralytics) and DINOv3 (military/espionage clause) unless legal review clears them; MB-System only as a separate process; HYPACK SDK not used; Objects365 checkpoints avoided [V] |
| Dataset licences | Register per file; CC BY-SA (GhostVision) ShareAlike obligations reviewed; CC BY-NC sets research-only; unconfirmed sets research-only until written permission [V] |
| Indian data | NDSAP: restricted data only through authorisation; model-to-data MoUs so data never leaves the institute [S] |
| Export control | US EAR ECCN 6A001.a.1 covers side-scan/SAS systems above technical thresholds (e.g. designed for > 500 m depth; archived texts) [S]; India's SCOMET list covers dual-use software and technology [S]. Get a formal classification before the first foreign contract |
| Defence firewall | Any mine-like-object variant in a separate codebase, dataset and legal entity, so civil EU/UK clients aren't blocked |
| Liability | Never "clear"; ALARP language; disclaimer (§13.3); "not for navigation"; professional indemnity insurance before paid pilots (specialist hydrographic-surveyor cover exists) [S] |

---

## 22. Risk register

| Risk | Likelihood | Impact | Mitigation |
|---|---|---|---|
| No buyer pays for calibrated confidence or coverage | High | Fatal | Stage 0 interviews and paid-pilot ask before heavy engineering; pivot to licensing the method or a research/grant track |
| Shared backbone doesn't transfer across sonar types | Medium-high | Medium | Stage A is the shipped product; Stage B is a pre-registered bet |
| Injected targets don't behave like real ones | Medium | High | Seeded-target trial; real-target validation of Pd; publish the gap |
| Calibration doesn't transfer to new sites/sensors | High | Medium | Per-sensor fits, claim levels, canary, honest "indicative" state |
| Too few real labels with outcomes | High | High | NOAA pipeline, partnerships, outcome clauses, own trials |
| Mosaic-only client data (unknown gain) | Medium | Medium | Separate, lower claim level for mosaic inputs |
| Licence surprises (datasets, weights) | Medium | High | WP0 register; research-only store |
| Vendors or classification societies add validated calibration | Medium | High | Speed to an open benchmark and outcome ledger; aim to be the method behind them |
| Export or defence entanglement | Low-medium | High | Firewall and classification |
| Flat-net hypothesis wrong | Medium | Low | Shadow stays a soft feature; result published either way |

---

## 23. Honest claims

**Safe to claim now** [V]
- About half of the suspects divers checked in the Baltic campaign were real gear (94 of 176).
- Survey standards state that no single system can guarantee detection of all features, and 100% side-scan coverage cannot disprove a feature.
- AI sonar detection exists and is increasingly bundled by vendors; pieces of calibration and Pd mapping exist in mine hunting and in a few SIH projects.
- No public side-scan dataset we found contains labelled ghost nets, and none provides verified false positives.

**Claim only as design or target** [P]
- Calibrated per-contact probability, validated Pd map, applicability gate, one shared model across sonars, edge deployment: proposed until measured.
- Every performance number is a target until measured on held-out surveys.
- Net results are injection- or trial-based and labelled as such until real verified nets exist.

**Never claim**

| Don't say | Say instead |
|---|---|
| "We detect debris buried in mud" | "Side-scan sees objects on or partly in the seabed; buried objects need a sub-bottom profiler or magnetometer" |
| "First calibrated sonar tool" / "first Pd map" | "We validate what others score or hand-set: final-output calibration, injection-fitted and real-target-checked Pd, withdrawal on unfamiliar sonar" |
| "Tested in Indian waters" | "Indian validation runs through an MoU with [institute]; until then results are on public data" |
| "We replace divers" | "We help divers and ROVs spend time on better-supported contacts" |
| "One AI works on every sonar" | "One model family; validated so far on [listed sensors]" |

---

## 24. Likely judge and investor questions

| Question | Answer |
|---|---|
| Why not just YOLO? | YOLO finds candidates. It doesn't know whether its score is a real probability, whether this sonar is outside what it was trained on, or where the survey could not have seen anything. Those are what we measure. |
| Other SIH teams already have calibration and a Pd grid. What's new? | They score with temperature scaling or hand-set coefficients. We calibrate the final output on held-out surveys, fit Pd from experiments, check it against real laid targets, report lower bounds, and withdraw claims on an unfamiliar sonar. We show all of it against their approach as baselines. |
| SeeByte already does target insertion. | Yes, for naval ATR, and we cite it. We found no published validation of injected Pd against real targets; closing that loop for civilian debris is our contribution. |
| Does it work on any sonar? | One model family with sensor-conditioned normalisation and per-sensor calibration. It reads several formats today; it claims calibrated numbers only where validated, and says so on every report. |
| Where does ghost-net data come from? | Real derelict-gear data (GhostVision pots), our own laid nets, partner data under MoU, and injected nets for Pd sweeps only. Calibration uses only real outcomes. |
| Who pays? | The party carrying the risk: wind and cable developers, UXO consultants, warranty surveyors, S&R contractors, ports. We test this in 20–25 interviews before scaling. |
| Why can't Kongsberg copy you? | It can copy the maths. It can't credibly grade its own sonar's output; independence is what assurance buyers pay for. |
| What do you need from NIOT? | One validation sector under a model-to-data MoU, sensor specifications and navigation format, and a hydrographer's time to review contact outcomes. |
| Is it safe to say an area is clear? | We never say that. We give a Pd lower bound for a stated target, and a residual-risk statement. |

---

## 25. Changes from v1 (`NetSight_Solution.md`)

| v1 said | v2 says | Why |
|---|---|---|
| "Even experts are right only about half the time" | "About half of the suspects divers checked were real (94 of 176)" | Only 32% of suspects were checked; no miss rate [V] |
| Diver search ≈ €140/ha; 49 positions in 5 diving days | Authors' estimate "at least 140 Euros per hectar" (scooter scenario) vs ≈€8/ha sonar; "22 of 49 sonar positions verified during 5 diving days" were confirmed (45%) | Verified with exact wording [V] (earlier reports had marked these unverified) |
| Nets 37.9% of Gulf of Mannar gear litter | 43.17 ± 5.48% of reef debris (Edward et al. 2020) unless 37.9% is found | Not found [S] |
| X-Press Pearl as Indian precedent | Survey in Sri Lankan waters for Sri Lanka | [V] |
| "We saw no calibration, no Pd map" in other SIH teams | Three repos have calibration code; Sagar-Netra has a hand-set Pd grid; DEPTH withdraws on unfamiliar sonar | Audit [V] |
| "A collapsed net casts no shadow" (fact) | Hypothesis; shadow is a soft feature; tested in the trial | No source supports it; bundles cast shadows [V] |
| Side-scan only | One model family across sonars; staged sensor order; shared trust layer | Drawback 1 |
| YOLO11n-seg (AGPL) with YOLOX fallback | D-FINE / DEIM / RF-DETR N–L (Apache-2.0); DINOv2 init; no DINOv3 | Licences [V] |
| Isotonic per range bin; refit with ~100 contacts | Platt/beta with covariates by default; isotonic only with thousands; ~100 contacts gives only a rough refit with wide bands; claim levels | Calibration literature [V/S] |
| Cumulative Pd = 1 − Π(1 − Pdᵢ) with optional max | Interval [max, independence] until miss-correlation ρ is measured; publish lower end | Correlated looks [V/S] |
| Pd validated with real cut-outs | Validated against real **laid** targets in a seeded-target trial, plus surveyed objects | Closed loop [P] |
| Position error by first-order propagation | Same, plus a coverage test of ellipses on known targets | [P] |
| Seven classes | Two-level taxonomy with net states, traps, ropes, disaster classes, hard negatives and `unknown` | [V/S/P] |
| JSON with lat/lon, class, P(real) | HSSD/S-57/Cenos-aligned schema with claim level, covariance, provenance | Standards [V] |
| BenthiCat "≈1M tiles with raw XTF and labels" | Confirmed open release is 434,164 unlabelled patches (CC BY 4.0); check which release carries labels | [V] |
| pyxtf (MIT) | Licence unverified; check in WP0 | [S] |
| No business plan | Services-first assurance desk, neutrality moat, funding sequence, roadmap with kill criteria | Market and moat research |

---

## 26. Next 30 days

1. **Interviews**: book the first 10 (warranty surveyor, UXO consultant, S&R contractor, port hydrographer, NIOT, Planys) using the eight-question script in `reports/Sonar survey market and buyers.md`.
2. **Emails** (week 1): NOAA (raw data, contact listings), USGS, AI4Shipwrecks, SCTD 3.0 and GhostVision authors (licences), NIOT/NIO/GSI/IIT Madras (MoU).
3. **WP0**: licence register, impartiality policy draft, repository with CI.
4. **WP1/WP2 start**: XTF + GeoTIFF adapters; download commercial-OK sets; NOAA DR parser on H13684 and the five listed surveys.
5. **WP11 start**: pre-register splits, baselines B0–B4 and operating points before seeing results.
6. **Incubator**: application to IIT Madras Incubation Cell / NTCPWC or the Cochin Shipyard–IITM programme.
7. **Fix v1 claims** in any slide or document still using the old wording (§25).

---

## 27. Key sources

Full source trails, with verified/secondary tags, are in `reports/` and `research_notes/`. The most-used primary sources:

- Stolte et al. 2022, *The quest for ghost gear in the German Baltic Sea* — https://www.frontiersin.org/articles/10.3389/fmars.2022.981840
- IHO S-44 Edition 6 (Preview read; check 6.2.0) — https://metanorma.github.io/mn-samples-iho/documents/s44/document.pdf
- NOAA Hydrographic Surveys Specifications and Deliverables 2022 and 2026.0.02 — https://www.nauticalcharts.noaa.gov/publications/docs/standards-and-requirements/specs/HSSD_2022.pdf · https://www.nauticalcharts.noaa.gov/publications/documents/HSSD_2026-0-02.pdf
- Cenos offshore wind farm UXO survey specification — https://marine.gov.scot/sites/default/files/cenos_eia_vol.4_-_a4_-_uxo_survey_specifications_redacted.pdf
- Guerneve et al., terrain characterisation and contact insertion (SeeByte) — https://arxiv.org/abs/2404.18663
- Küppers et al. 2020, multivariate confidence calibration for object detection — https://arxiv.org/abs/2004.13546
- Kuzucu et al. 2024, calibration of object detectors — https://arxiv.org/abs/2405.20459
- Andéol et al. 2025, conformal object detection by sequential risk control — https://arxiv.org/abs/2505.24038
- Tibshirani et al. 2019, conformal prediction under covariate shift — https://arxiv.org/abs/1904.06019
- BenthicDINO — https://arxiv.org/abs/2608.23215 · Mine-JEPA — https://arxiv.org/abs/2604.00383 · SCTD 3.0 — https://arxiv.org/abs/2608.08106
- DOFA — https://arxiv.org/abs/2403.15356 · Copernicus-FM — https://arxiv.org/abs/2503.11849 · Panopticon — https://arxiv.org/abs/2503.10845 · Teacher-guided OOD (2026) — https://arxiv.org/abs/2603.11269
- DCBD optical-to-side-scan adaptation — https://pmc.ncbi.nlm.nih.gov/articles/PMC11148073/
- GhostNetZero preprint — https://ecoevorxiv.org/repository/view/10294/
- D-FINE — https://github.com/Peterande/D-FINE · DEIM — https://github.com/Intellindust-AI-Lab/DEIM · RF-DETR — https://github.com/roboflow/rf-detr · SAM 2 — https://github.com/facebookresearch/sam2 · DINOv3 licence — https://ai.meta.com/resources/models-and-libraries/dinov3-license
- NOAA H13684 (CC0) — https://catalog.data.gov/dataset/h13684-nos-hydrographic-survey-2023-04-29 · Bodine side-scan labels — https://zenodo.org/records/10119320 · GhostVision — https://zenodo.org/records/20056679 · PINGMapper — https://github.com/CameronBodine/PINGMapper · JNCC raw side-scan — https://data.gov.uk/dataset/9e58988b-1ef6-4808-a629-fe4ffe27706a · Marine Debris FLS — https://zenodo.org/records/15101686
- W3C PROV — https://www.w3.org/TR/prov-overview/ · DNV-RP-0671 — https://www.dnv.com/digital-trust/recommended-practices/assurance-of-ai-enabled-systems-dnv-rp-0671/
- HYPACK SDK terms — https://www.xylem.com/en-qa/brand/hypack/integrate-with-hypack/
- New Mangalore Port hydrographic witnessing tender — https://newmangaloreport.gov.in/index.php/sites/default/files/2023-07/HydrographicSurveyTD.pdf
- Richardson et al. 2022, global fishing gear loss — https://pmc.ncbi.nlm.nih.gov/articles/PMC9555783/ · Mongabay 2026, India ghost gear — https://news.mongabay.com/2026/06/indias-fishers-confront-homegrown-ghost-gear-problem/
- INS Sarvekshak / X-Press Pearl — https://www.cgihambantota.gov.in/section/press-releases/indian-naval-ship-ins-sarvekshak-completes-800-miles-of-survey-around-mv-xpress-pearl/
- SIH26057 competitor audit — `SIH26057_100_Repository_Analysis_README (1).md` (static audit; nothing was run)

> Re-check any [S] number against its source before it goes on a slide. Nothing in this plan has been built or measured yet.
