# NetSight — Sonar Survey Assurance for Underwater Debris Clearance
**SIH26057 · AI-Powered Automated Underwater Marine Debris & Anomaly Detection using Side-Scan Sonar Imagery**
Ministry of Earth Sciences (MoES) / National Institute of Ocean Technology (NIOT) · Software · Theme: Disaster Management

> **Status: idea-stage proposal.** Nothing described here has been built or measured yet.
> Every statement carries a tag so the team never over-claims:
> **[FACT]** = published, with a source in §15 · **[INFERENCE]** = our reasoning from facts · **[PROPOSED]** = our design · **[ILLUSTRATIVE]** = example values that show a format, not results.

---

## Contents
1. [One-page summary](#1-one-page-summary)
2. [The problem](#2-the-problem)
3. [What exists today and the gap](#3-what-exists-today-and-the-gap)
4. [The NetSight idea](#4-the-netsight-idea)
5. [Architecture and workflow](#5-architecture-and-workflow)
6. [Offline stages: methods and techniques](#6-offline-stages-methods-and-techniques)
7. [Online stages: methods and techniques](#7-online-stages-methods-and-techniques)
8. [One contact through the whole system](#8-one-contact-through-the-whole-system)
9. [PS requirement traceability](#9-ps-requirement-traceability)
10. [Data and technology stack](#10-data-and-technology-stack)
11. [How the idea would be evaluated](#11-how-the-idea-would-be-evaluated)
12. [Impact and users](#12-impact-and-users)
13. [Honest claims: what we can and cannot say](#13-honest-claims-what-we-can-and-cannot-say)
14. [Risks, limitations and judge questions](#14-risks-limitations-and-judge-questions)
15. [Sources](#15-sources)

---

## 1. One-page summary

| | |
|---|---|
| **Problem** | After cyclones, shipwrecks or floods, ports and the Coast Guard must find underwater debris and declare channels safe. Side-scan sonar (SSS) produces kilometres of noisy imagery that humans review slowly, and even experts are right only about half the time [FACT: 52% of diver-verified sonar suspects were real ghost gear, Stolte et al. 2022]. |
| **Gap** | Every existing tool, and every SIH team we found, answers only *"Where is debris?"* None tells the operator how far to trust each hit or where the survey itself was effectively blind [INFERENCE from §3]. |
| **Idea** | A software layer on top of existing sonar surveys that outputs (1) detected debris, (2) an **honest, calibrated confidence** for each contact, and (3) a **Search-Completeness Map** showing where the seabed was well, partly or poorly searched [PROPOSED]. |
| **One line** | *Other tools show what they found. NetSight also shows how much to trust each find, and where the survey could not have found anything.* |
| **Why it's different** | Search-completeness is standard in naval mine clearance ("percentage clearance") [FACT], but we found no civilian debris or ghost-net tool that reports it [INFERENCE, likely open]. NetSight adapts that proven naval idea to debris clearance. |
| **Feasibility** | Works on India's existing sonar/AUV/ROV survey data [FACT: these assets exist], uses open-source tools and public datasets, no new hardware, runs offline on a laptop or edge device [PROPOSED]. |

---

## 2. The problem

### 2.1 Who faces it
- **Disaster response:** after the MV X-Press Pearl disaster (2021), INS Sarvekshak ran **807 miles** of side-scan survey and identified **54 debris objects plus one uncharted wreck** [FACT, PIB]. [INFERENCE] Ports and channels hit by cyclones, floods or wrecks face the same task: find hazards and declare the area safe.
- **Ghost nets:** about **2% of all fishing gear is lost every year** [FACT, Richardson 2022]. In the Gulf of Mannar, nets were **37.9%** of abandoned-gear litter items on coral reefs [FACT, SDMRI].
- **Survey agencies:** NIOT, the National Hydrographic Office, IWAI, the Coast Guard and port trusts already run SSS surveys [FACT].

### 2.2 How it is done today
Survey vessel / AUV → side-scan sonar → **human scrolls through the waterfall** → suspect list → **divers / ROV verify** → removal or charting [FACT: WWF and Indian hydrographic workflows].

### 2.3 Why that is inadequate
| Pain | Evidence |
|---|---|
| Slow manual review | PS text: "slow, tedious, and prone to human error"; AI4Shipwrecks authors say expert review "can take many months" [FACT] |
| Half the suspects are wrong | 549 suspects → 176 diver-verified → **94 real (52%)** over 58.2 km² [FACT, Stolte 2022] |
| Dives are expensive | Diver search ≈ **€140/ha**; verifying 49 positions took 5 diving days [FACT, Stolte 2022] |
| False "all clear" | A clean-looking map can hide areas the sonar never resolved (nadir gap, far range, bad pings) [INFERENCE] |

### 2.4 Why sonar images are hard to read
| Effect | What it does |
|---|---|
| **Speckle** | Grainy multiplicative noise that looks like small objects |
| **Acoustic shadow** | Raised objects cast dark shadows, but so do rocks and ripples |
| **Nadir gap** | A blind strip directly under the vehicle |
| **Slant range** | The sonar measures diagonal distance; raw images are squashed near the vehicle |
| **Range-dependent resolution** | Small targets fade at far range |
| **Heave / pitch / roll / yaw** | Distortion, smearing and dropped pings |
| **Look-alikes** | Even a strong model confuses rock with ripples 20.7% of the time [FACT, BenthicDINO] |

> **Scope note:** "debris in mud" means debris lying **on or partly in** soft seabed. Fully **buried** debris cannot be seen by high-frequency SSS; that needs a sub-bottom profiler, which is a different sensor [FACT]. We say this openly.

---

## 3. What exists today and the gap

| System | What it does | What it does not do |
|---|---|---|
| **Indian survey fleet** (NHO, IWAI, Navy) | Strong SSS, AUV, ROV and navigation capability [FACT] | No public, standard calibrated confidence or search-completeness output for debris |
| **GhostNetZero.ai** (WWF + Microsoft + Accenture) | AI flags likely ghost nets; humans validate. Reports ~0.82–0.94 centroid detection on 412 private images [FACT, preprint] | No published calibration, no coverage/missed-area map, cloud platform |
| **SeeByte ATR** | Military mine-like object recognition; terrain-aware performance [FACT] | Mines only, closed and commercial |
| **SonarWiz ATR** | Automatic contacts in survey software [FACT] | Boulder model only, no custom training [FACT] |
| **Sonobot / Quadroin / DLR S2D2** | Survey vehicles and drones, some with onboard recognition [FACT] | Platforms, not a debris decision layer |
| **Other SIH26057 teams** (13 tagged repos; ~60 "side scan sonar debris" repos) | YOLO + dashboard + JSON/CSV + shadow check + ONNX [FACT, GitHub, 26 Sep 2026] | We saw no calibration, no Pd map and no net-state modelling [INFERENCE from 10 READMEs + 4 videos] |

**Capability gap (summary of the research matrix):** calibrated confidence, false-alarm-per-km² control and a detectability map are missing everywhere except military mine clearance; ghost-net state modelling and Indian-waters validation are missing everywhere [INFERENCE].

---

## 4. The NetSight idea

### 4.1 Three questions instead of one
| Question | Measure | Example | Operator action |
|---|---|---|---|
| Did we find something? | **Detection** | "Possible net at X" | Look at it |
| How much should we trust it? | **P(real)**, a calibrated probability | 0.78 | Prioritise the dive |
| If debris were here, would we have seen it? | **Pd**, the Probability of Detection | 0.30 | Re-survey this area |

**Analogy:** P(real) is about a suspicious bag you found. Pd is about whether security actually checked the whole airport.

### 4.2 Three pillars
| Pillar | Plain meaning | Technique |
|---|---|---|
| **① Search-Completeness Map** (core) | Green/amber/red map of how well each seabed cell was searched; red becomes a re-survey zone | Pd model learned from a target-injection study, per 5 m cell, combined across passes |
| **② Honest confidence** | "80%" means about 80 of 100 such contacts are real; threshold set by a diver's false-alarm budget | Evidence fusion + isotonic calibration + false-alarms-per-km² threshold |
| **③ Net-aware physics** | A flat, collapsed net casts no shadow, so we don't reject it for lacking one | Class-conditional evidence: shadow expected per object type |

---

## 5. Architecture and workflow

```
 ════════════════ OFFLINE (prepared once, refreshed with new data) ════════════════
 (A) Target Injection Engine ──► training data + known test targets
 (B) Pd Study                ──► Pd model  ─────────────────────────┐
 (C) Calibration Fit         ──► calibrator ───────────────┐        │
                                                           ▼        ▼
 ════════════════ ONLINE (runs on every survey) ═══════════════════════════════════
 Raw log (.xtf / .jsf + nav + attitude)   or   PNG + nav CSV sidecar
        │
 [1] INGEST + QC ──────► quality mask Q ─────────────────────────────┐
        │                                                            │
 [2] TILING + CONTEXT (range, grazing angle, seabed complexity, Q)   │
        │                                                            │
 [3] DETECTOR (candidates: wreck, pipe/cable, cylinder, net, rock)   │
        │                                                            │
 [4] EVIDENCE (shadow per class, texture, anomaly, context)          │
        │                                                            │
 [5] FUSION + CALIBRATION ──► P(real) ──► FA/km² threshold           │
        │                                                            ▼
 [7] GEOTAG + UNCERTAINTY                        [6] Pd / SEARCH-COMPLETENESS MAP
        │                                                            │
        └────────────────► [8] OUTPUTS ◄─────────────────────────────┘
          dashboard · JSON/CSV · GeoJSON/KML · dive plan · re-survey polygons
```

**Chain of value:** Detection → Evidence → Calibrated trust → Search completeness → Action.

---

## 6. Offline stages: methods and techniques

### (A) Target Injection Engine — solving "no ghost-net data exists"
**Why:** no public side-scan dataset contains labelled ghost nets [FACT, Gomes 2025 survey]. Fully simulated sonar transfers poorly: one study fell from **98% on simulation to 40% on real data** [FACT, 2508.18293]. So we paste physically modelled targets onto **real** seabed [PROPOSED, following STARS' lesson that real terrain is essential].

| Step | Method / technique |
|---|---|
| Mesh | Procedural 2-D lattice at realistic mesh size (NumPy) |
| Deformation | Random smooth displacement field (Gaussian-smoothed noise / thin-plate spline warp) to drape, fold and tangle the net, as STARS did for wrecks |
| Float & sink lines | Bright polylines (Bézier curves) along the net edges, which are sonar-visible [FACT, Stolte] |
| Net state | Standing (has height), collapsed (flat), snagged (wrapped on rock or wreck) |
| Other targets | Cylinders, pipe segments and compact debris from simple geometric sprites and real object cut-outs |
| Brightness | Set relative to the local background percentile, so it adapts to dark mud or bright sand |
| Speckle | Multiplicative noise whose statistics are estimated from the surrounding real background |
| Shadow | Ray-cast along the range direction from the target's height profile, using flat-seabed geometry |
| Range blur | Anisotropic Gaussian blur along-track that grows with range (beam widening) |
| Blending | Poisson blending (OpenCV `seamlessClone`) so the detector can't learn cut-and-paste edges |
| Realism check | FID/KID against real SSS tiles, plus expert visual review, plus the real-cut-out Pd test in (B) |

### (B) Pd Study — measuring our own blind spots
| Step | Method / technique |
|---|---|
| Sampling | Stratified sampling of real seabed tiles across range bin × seabed type × quality Q × target type/state |
| Trial | Inject a target at a known place, run stages 3–5 at the chosen operating threshold, record hit or miss |
| Model | Logistic **GAM** (pyGAM) or gradient-boosted trees with monotonic constraints (e.g. Pd must not rise with range): `Pd = f(range, grazing angle, seabed complexity, Q, target type/state)` |
| Uncertainty | Bootstrap resampling gives a confidence band on each Pd value |
| Validation | Repeat with **real** object cut-outs (BenthiCat misc objects, AI4Shipwrecks debris). If real and synthetic Pd agree in the same conditions, the synthetic targets are behaving realistically |

This is the civilian version of naval **target-laying trials**, which is how mine-clearance Pd curves are built [INFERENCE].

### (C) Calibration Fit
| Step | Method / technique |
|---|---|
| Held-out data | One or more survey **sectors** never used in training (geographic split prevents data leakage) |
| Calibrator | **Isotonic regression**, fitted separately per range bin (range-aware, following Küppers et al.'s multivariate calibration); Platt / temperature scaling as a fallback when data is small |
| Proof | Reliability diagram, **ECE** (Expected Calibration Error), **Brier score** |
| Re-fit | For a new sonar or site: label ~100 contacts from one survey and refit [PROPOSED; time needed is an estimate] |

---

## 7. Online stages: methods and techniques

### Stage 1 — Ingest + Quality Check
**Purpose:** read raw data, fix geometry, and mark which pings can be trusted.

| Task | Method / technique |
|---|---|
| Read raw logs | `pyxtf` for XTF; a custom parser for EdgeTech JSF; PNG + CSV navigation sidecar as fallback |
| Per-ping metadata | Lat/lon, heading, speed, altitude, roll, pitch, heave, timestamp, ping number |
| Bottom tracking | First strong return per ping (adaptive threshold), smoothed across pings with a median filter |
| Slant-range correction | `ground_range = √(slant_range² − altitude²)`; removes the water-column strip |
| Gain normalisation | Use the sonar's TVG, then empirical across-track (beam-pattern) equalisation: divide by the mean intensity per range column |
| Speckle handling | Log transform (multiplicative → additive noise). Mild despeckling (Lee / median) is used **only for the evidence features**, not heavily on the detector input, because strong filtering can erase thin net lines. The detector learns robustness through speckle augmentation instead |
| Quality mask **Q** (0–1 per ping) | Attitude thresholds on roll/pitch and their rates; heave via altitude jumps; dropouts via ping-number/time gaps; stripe artefacts via low normalised cross-correlation between neighbouring pings |

**Why it matters:** the PS names heave, pitch, roll and dropouts. Q is reused twice: it lowers contact trust in Stage 5 and marks cells as not searched in Stage 6.

### Stage 2 — Tiling + Context
| Task | Method / technique |
|---|---|
| Tiling | 512 × 512 ground-range tiles with ~20–25% overlap so objects on edges aren't cut |
| Range bin | Near / mid / far across-track |
| Grazing angle | `θ ≈ arctan(altitude / ground_range)` on a flat-seabed assumption |
| Seabed complexity | **DINOv2** (ViT-S/14) patch embeddings, scored by feature variance; classical GLCM texture as a cheap backup |
| Quality | Mean Q of the pings inside the tile |

### Stage 3 — Detector (candidate generation)
| Task | Method / technique |
|---|---|
| Model | **YOLO11n-seg** (small, fast, instance masks). Deployment alternative: **YOLOX** (Apache-2.0), because Ultralytics YOLO is AGPL-3.0 [FACT] |
| Classes (matched to the PS) | `shipwreck`, `pipe_cable` (linear), `cylinder`, `compact_debris`, `net_standing`, `net_collapsed`, plus `rock` as a deliberate distractor class |
| Training | Transfer learning from COCO weights, fine-tuned on real sonar objects (§10) plus injected targets; never on synthetic-only data |
| Augmentation | Speckle noise, gain jitter, range-dependent blur, port/starboard flips, simulated dropout rows |
| Inference | Tiled inference with cross-tile merging (NMS); a **low threshold** here to favour recall, because later stages remove false alarms |
| Labelling aid | **SAM 2**: click a box, get a mask, which speeds up annotation |

The detector's raw score is **not** a probability. Stage 5 turns it into one.

### Stage 4 — Evidence (what a sonar expert would check)
| Evidence | Method / technique |
|---|---|
| **Shadow & height** | Segment the shadow as the dark region beyond the object along the range direction (threshold relative to the local background). Height on a flat seabed: `h ≈ H · Ls / (R + Ls)` (H = altitude, Ls = shadow length, R = ground range to the object's far edge) |
| **Class-conditional shadow expectation** | Wreck / cylinder / compact debris: shadow should match plausible height. Standing net: thin, long shadow. **Collapsed net: little or no shadow is expected and is not penalised.** Rock: shadow + clustering consistent with nearby geology |
| **Mesh texture** | Gabor filter-bank energy and 2-D FFT peak periodicity (a net's mesh is a repeating grid) |
| **Line continuity** | Ridge detection (Frangi filter) plus Hough lines, tracked across consecutive pings (float/sink lines, pipes, cables) |
| **Ripple-field deviation** | Dominant orientation and wavelength of the surrounding seabed from the structure tensor / FFT. Ripples are regular over hundreds of metres; a net is a bounded patch that breaks that pattern |
| **Local anomaly** | PatchCore-style memory bank of DINOv2 features from **this survey's own** normal seabed (coreset subsampling), with kNN distance via FAISS. High distance means unusual for this site |
| **Context** | Range bin, grazing angle, seabed complexity, Q |

### Stage 5 — Fusion + Calibration → P(real)
| Task | Method / technique |
|---|---|
| Fusion | Gradient-boosted trees (LightGBM / scikit-learn HistGradientBoosting) over detector + evidence + context features; logistic regression as the interpretable fallback |
| Explanation | SHAP values per contact show which clues raised or lowered its score (feeds the evidence card) |
| Calibration | The range-aware isotonic calibrator from offline stage (C) gives **P(real)** |
| Threshold | Chosen from held-out data so that expected false alarms stay within the operator's budget, e.g. **≤ 2 false alarms per km²**, using surveyed area computed from navigation |
| Honest totals | If probabilities are calibrated: expected real contacts = Σ P(real), expected false alarms = Σ (1 − P(real)), printed on every report |

### Stage 6 — Pd / Search-Completeness Map (core innovation)
| Task | Method / technique |
|---|---|
| Grid | 5 m × 5 m cells in UTM (metre grid via `pyproj`) |
| Per-pass Pd | For each pass over a cell: look up range, grazing angle, seabed complexity and Q, then apply the Pd model from (B). Nadir-gap cells and pings with Q below the cut-off get Pd ≈ 0 |
| Reference target | Pd is always "for a chosen reference target", e.g. a collapsed net panel or a 1 m cylinder. The operator can switch targets |
| Multiple passes | `cumulative Pd = 1 − Π(1 − Pd_i)`. **Caveat:** this assumes passes are independent; similar look angles are not, so we also offer a conservative mode (max Pd over passes) |
| Colours | Green ≥ 0.8 · Amber 0.5–0.8 · Red < 0.5 (thresholds configurable) |
| Re-survey zones | Threshold red cells, clean up with morphological opening/closing, convert to polygons (`rasterio.features.shapes` + `shapely`), export GeoJSON for the next mission plan |

### Stage 7 — Geotag + Position Uncertainty
| Task | Method / technique |
|---|---|
| Position | Ping GNSS position + heading + signed across-track ground range (port −, starboard +) + **layback** (towfish trailing distance, approximated from cable out and towfish depth; catenary ignored) |
| Coordinates | Compute in UTM with `pyproj`, report in WGS84 lat/lon |
| Size | Object length × width from the mask in ground-range metres |
| Uncertainty | First-order error propagation. Along-track: σ² ≈ σ_GNSS² + σ_layback² + (R·σ_heading)² + σ_pixel². Across-track: σ² ≈ σ_GNSS² + σ_range² + (L·σ_heading)² + σ_pixel² (R = ground range, L = layback). Reported as a 1σ / 95% ellipse |
| Standard | Error terminology aligned with IHO S-44 survey-accuracy practice |

### Stage 8 — Outputs
| Output | Content / technique |
|---|---|
| **JSON / CSV report** (PS requirement) | id, lat, lon, uncertainty (m), length × width (m), class, P(real) %, evidence summary, quality flag |
| **GeoJSON / KML** | Contacts + re-survey polygons; opens in QGIS / Google Earth |
| **Dashboard** | FastAPI backend + React + Leaflet: raw-log upload, scrolling waterfall with overlays, map, Pd layer toggle, evidence cards, reliability diagram, report download |
| **Dive plan** | Top-N contacts ranked by P(real) (optionally weighted by agency priorities) with the expected number of real finds |
| **Edge mode** | ONNX export + int8 quantisation, ONNX Runtime on CPU, processing the waterfall in blocks of pings as it grows (onboard or on a laptop, no cloud) |

---

## 8. One contact through the whole system
> **[ILLUSTRATIVE]** These values show the output format only. They are not measured results.

| Stage | Contact #17 |
|---|---|
| 1 Ingest | Starboard ping 12,408; roll 1.2° → Q = good |
| 2 Tile | 38 m ground range (mid), flat fine sediment (low complexity) |
| 3 Detector | Mask 6.1 × 2.3 m, class `net_collapsed`, raw score 0.91 |
| 4 Evidence | No shadow (**expected** for a collapsed net) · strong mesh periodicity · bright line continues over 40 pings · breaks the local ripple field · high local anomaly |
| 5 Fusion + calibration | P(real) = 0.78 → passes the 2 FA/km² threshold |
| 6 Pd map | Cell Pd = 0.86 (well searched); nearby nadir strip Pd ≈ 0.2 → red polygon |
| 7 Geotag | Lat/lon ± 3.2 m (1σ) |
| 8 Output | JSON row, map pin, evidence card, rank #3 in the dive plan |

```json
{ "id": 17, "class": "net_collapsed", "p_real": 0.78,
  "lat": 9.28xx, "lon": 79.1xx, "uncertainty_m_1sigma": 3.2,
  "length_m": 6.1, "width_m": 2.3, "quality": "good", "cell_pd": 0.86,
  "evidence": { "shadow": "none (expected for class)", "mesh_periodicity": "high",
                "line_continuity_pings": 40, "local_anomaly": "high" } }
```

A plain "shadow required" filter, which many teams use, would have **deleted** this contact.

---

## 9. PS requirement traceability

| PS requirement | Where NetSight meets it |
|---|---|
| Ingest SSS imagery / raw logs | Stage 1 (XTF / JSF / PNG + CSV) |
| Robust to speckle | Stage 1 log-domain handling + Stage 3 speckle augmentation + Stage 4 evidence on denoised copies |
| Robust to varying resolution | Stage 1 slant-range correction; range bins in Stages 2, 5 and 6; range blur in training |
| Robust to acoustic shadows | Stage 4 class-conditional shadow logic |
| Robust to heave / pitch / roll dropouts | Stage 1 quality mask Q → Stages 5 and 6 |
| Detect shipwrecks, pipes, cylinders, entangled nets | Stage 3 classes matched to the PS |
| Separate man-made from natural seabed | `rock` distractor class + Stage 4 evidence + Stage 5 fusion |
| Confidence 0–100% with false-positive filtering | Stage 5 calibrated P(real) + FA/km² threshold |
| Geotagging from metadata / ping headers | Stage 7 |
| JSON / CSV report with lat/lon, dimensions, class | Stage 8 |
| UI: upload logs, overlays on map, download reports | Stage 8 dashboard |
| Edge-deployable | Stage 8 ONNX int8 edge mode |
| **Beyond the PS** | Search-Completeness Map, position uncertainty, dive plan, re-survey polygons |

---

## 10. Data and technology stack

### 10.1 Public data we would use
| Dataset | What it gives us |
|---|---|
| **BenthiCat** | ~1 M real SSS tiles with raw XTF + navigation; labelled cables, misc objects, artificial reefs vs rocks, ripples, sediment. Real man-made vs natural test bed and injection backgrounds |
| **AI4Shipwrecks** | Real shipwreck + debris masks and hard distractor sites |
| **KLSG, SCTD** | Wrecks, aircraft and other compact man-made objects |
| **SubPipe, Marine-PULSE** | Pipelines and linear structures |
| **SCTD 3.0** | Burial and shadow-integrity attributes for physics checks (SAS sensor, used carefully) |
| **Injected targets** | Nets and cylinders from stage (A), always labelled synthetic |
| **Requested from NIOT** | One labelled Indian survey sector, sensor specs, navigation format |

Licences of several datasets (KLSG, Marine-PULSE, SubPipe, BenthiCat terms) are **not yet verified**.

### 10.2 Tools
| Layer | Tool |
|---|---|
| Sonar I/O | pyxtf (MIT), custom JSF parser |
| Geometry / GIS | NumPy, pyproj, shapely, rasterio |
| Detection | YOLO11n-seg (AGPL) / YOLOX (Apache-2.0) |
| Features | OpenCV (Gabor, FFT, Frangi, Hough), DINOv2 ViT-S/14, FAISS |
| Labelling | SAM 2 |
| Fusion / calibration / Pd | scikit-learn, LightGBM, pyGAM, SHAP |
| Backend / frontend | FastAPI, React + Leaflet |
| Edge | ONNX Runtime with int8 quantisation |

---

## 11. How the idea would be evaluated
Planned protocol only: **no numbers exist yet.** We compare against a "free baseline" of YOLO fine-tuned on KLSG + SCTD using its raw score.

| Metric | What it proves |
|---|---|
| mAP50 / mAP50-95 on real held-out sectors | Standard detection quality |
| **Recall at ≤ 2 false alarms per km²** | Performance within a diver budget |
| **ECE, Brier score, reliability diagram** | Whether "80%" really means 80% |
| Collapsed-net recall (injected, labelled synthetic) | The shadow-trap fix works |
| **Pd validity**: synthetic vs real cut-out Pd in the same bins | The Search-Completeness Map is credible |
| False positives on rocks / ripples (BenthiCat) | Man-made vs natural separation |
| Latency (ms per 100 m of track on a stated CPU) | Edge feasibility |
| Dive-plan precision (top-10 real) | Compared with the 52% expert baseline |

**Rules:** split by site/sector, test on real-only data wherever possible, and label every injection-based result as synthetic.

---

## 12. Impact and users

| User | Benefit |
|---|---|
| Port authorities / Coast Guard (post-disaster) | A defensible "channel searched to Pd ≥ 0.8" statement instead of a guess; red zones show exactly what to re-survey [PROPOSED] |
| NIOT / NHO / IWAI survey teams | Faster triage of long surveys; standard machine-readable contacts with error ellipses |
| Dive / ROV teams | Dives ranked by honest probability; fewer wasted dives [INFERENCE: at 52% expert precision, better ranking directly saves dive-days] |
| Conservation groups / fisheries | Ghost-net search that doesn't drop flat nets |

**Environmental and social impact:** fewer ghost nets killing marine life, safer navigation, lower clean-up cost, and use of India's existing sonar investment.

---

## 13. Honest claims: what we can and cannot say

### ✅ Safe to claim now
- Manual sonar review is slow, and expert suspects were right about 52% of the time in a published field campaign.
- No public side-scan dataset contains labelled ghost nets.
- Pd / coverage assessment is standard in naval mine countermeasures; we found no civilian debris tool that offers it.
- Existing tools and SIH projects we reviewed report detections, not calibrated trust or search completeness.
- NetSight is designed to work on existing survey data with open-source tools.

### ⚠️ Claim only as design or target
- "Calibrated confidence", "Search-Completeness Map" and "edge deployment" are **proposed** capabilities.
- Every performance number is a **target** until measured.
- Ghost-net results will be **injection-based** and labelled synthetic until real net data is available.
- The Pd map is first a **relative** ranking of search quality; its absolute accuracy improves with real validation data.

### ❌ Never claim
| Don't say | Say instead |
|---|---|
| "We detect debris buried in mud" | "SSS sees debris on or partly in the seabed; buried objects need a sub-bottom profiler" |
| "99% accuracy on ghost nets" | "Net performance will be measured on injected targets and validated when real data is available" |
| "Tested in Indian waters" | "No public Indian SSS data exists; we request a sample from NIOT" |
| "We replace divers" | "We help divers spend their time on better-supported contacts" |
| "Nobody has done AI sonar detection" | "AI sonar detection exists; our contribution is the trust and search-completeness layer" |
| "First ever Pd map" | "We adapt the navy's proven Pd approach to civilian debris clearance" |

---

## 14. Risks, limitations and judge questions

### 14.1 Risks and limitations
| Risk | Mitigation |
|---|---|
| Synthetic targets may not look real | Real backgrounds only, Poisson blending, FID/KID checks, and real-cut-out Pd comparison |
| Calibration may not transfer to new sites or sonars | Refit per sensor/site with ~100 labelled contacts; show calibration drift between datasets |
| Collapsed nets vs sand ripples are genuinely hard | Ripple-field deviation + local anomaly; report the confusion rate honestly |
| Multi-pass Pd assumes independent looks | Conservative "max Pd" mode as an alternative |
| XTF formats vary by vendor | pyxtf + PNG/CSV fallback |
| AGPL licence of Ultralytics | YOLOX (Apache-2.0) path |

### 14.2 Likely judge questions
| Question | Answer |
|---|---|
| Why not just YOLO? | YOLO finds candidates. It doesn't know if its score is a real probability, how bad the sonar data was, or where the survey was blind. |
| What is Pd, simply? | The chance we would have found a target here if one existed, given the range, seabed and data quality. |
| How do you get ghost-net data? | By injecting physically modelled nets into real seabed images, and labelling those results as synthetic. |
| Won't a model trained on fake nets fail? | That's why we never train on synthetic-only data, use real backgrounds, and mainly use fake nets to **measure** Pd. |
| How is your confidence different? | It's calibrated and checked with a reliability diagram; the threshold comes from a false-alarm budget per km². |
| Flat nets have no shadow; doesn't physics fail? | That's our point: shadow expectation depends on the object type. |
| GhostNetZero already exists. Why you? | It flags likely nets in the cloud with human review. We add calibrated trust, a search-completeness map and offline edge use; the two are complementary. |
| Does it need new hardware? | No. It runs on data from existing sonar surveys. |
| What do you need from NIOT? | One labelled survey sector (~100 contacts), sensor specs and the navigation format. |

---

## 15. Sources
1. SIH26057 problem statement — https://www.sihbuddy.in/ps/SIH26057 · https://zaidsayyed.in/tools/sih-problem-statements/sih26057
2. Stolte et al. 2022, *The quest for ghost gear in the German Baltic Sea* — https://www.frontiersin.org/journals/marine-science/articles/10.3389/fmars.2022.981840/full
3. Richardson et al. 2022, *Global estimates of fishing gear lost* — https://www.science.org/doi/10.1126/sciadv.abq0135
4. SDMRI / MARESSOL Gulf of Mannar report — https://salt.nu/assets/sdmri---maressol-report-abundance-of-abandoned-fishing-gear-in-coral-reefs-1738853088.pdf
5. PIB — INS Sarvekshak / MV X-Press Pearl — https://www.pib.gov.in/PressReleasePage.aspx?PRID=1732390
6. Indian Naval Hydrographic Office equipment — https://hydrobharat.gov.in/home/equipment/
7. IWAI Hydrographic Survey Instructions — https://iwai.gov.in/hydrographic-survey-instructions
8. GhostNetZero preprint (Miao et al. 2025) — https://ecoevorxiv.org/repository/object/10294/download/19035/ · WWF page — https://www.wwf.de/themen-projekte/projektregionen/ostsee/geisternetze/ghostnetzeroai-how-ai-is-saving-marine-life
9. SeeByte ATR — https://www.seebyte.com/products/atr · terrain characterisation — https://arxiv.org/abs/2404.18663
10. SonarWiz ATR — https://chesapeaketech.com/atrinsonarwiz/
11. EvoLogics Sonobot 5 — https://www.evologics.com/autonomous-vehicle/sonobot-5-usv
12. Gomes et al. 2025, sonar dataset survey — https://arxiv.org/abs/2510.03353
13. AI4Shipwrecks — https://arxiv.org/abs/2401.14546
14. STARS (sim-to-real on real terrain) — https://arxiv.org/abs/2310.01667
15. Training-free sonar detection (98% → 40% sim-to-real) — https://arxiv.org/abs/2508.18293
16. BenthiCat dataset — https://arxiv.org/abs/2510.04876
17. BenthicDINO (rock↔ripple confusion 20.7%) — https://arxiv.org/abs/2608.23215
18. SCTD 3.0 — https://arxiv.org/abs/2608.08106
19. WPG-DetNet (shadow-height physics, already published) — https://www.mdpi.com/1424-8220/26/6/1938
20. Küppers et al. 2020, multivariate confidence calibration — https://arxiv.org/abs/2004.13546
21. ATR false-alarm disclosure and operator trust — https://pmc.ncbi.nlm.nih.gov/articles/PMC9969489/
22. NOAA sub-bottom profiler (buried objects need a different sensor) — https://oceanexplorer.noaa.gov/technology/sub-bottom-profiler/
23. pyxtf — https://github.com/oysstu/pyxtf · YOLOX-ViT (Apache) — https://github.com/remaro-network/KD-YOLOX-ViT

> Facts and figures are taken from the team's research dossier ([readme.md](../readme.md)), accessed 26–27 Sep 2026. Re-check any number against its source before it goes on a slide.
