# AI / ATR for side-scan sonar debris and ghost-net detection: prior art on calibrated confidence and search-completeness (Pd) mapping (as of Nov 2026)

Method note: ~25 web searches/fetches. Several fetches returned only abstract pages or search-engine summaries; places where I did not read the full text are flagged. Not searched or not verified: SonarWiz ATR, Kongsberg, Exail, and Thales product documentation; the current IHO S-44 Ed. 6 text; the full GhostNetZero PDF; the Orescanin JOE 2025 paper full text; Frost "Theory of Search" full text; CMRE papers (only catalog/abstract records seen).

## 1. State of the art: AI side-scan sonar detection, datasets, and ghost-net-specific work (2023-2026)

### Takeaway
Public side-scan benchmarks are small, mostly shipwreck/pipeline/habitat/mine-like-object tasks, and none of those I could verify has labelled ghost nets. The only ghost-net-specific AI system found (GhostNetZero) is a non-peer-reviewed preprint reporting ~90% "detection rate" with no released data or code. Ghost-net work elsewhere (Stolte 2022, GhostNetBusters) is manual or early-stage.

### Cited Findings
**Datasets and benchmarks**
- AI4Shipwrecks (Univ. Michigan, IJRR 2024; arXiv 2401.14546): 286 side-scan images, 28 shipwrecks (arXiv v1 says 24; version discrepancy), 161 contain wrecks, 520 kHz AUV data from Thunder Bay NMS. Best of six baselines is SOD/InSPyReNet with IoU 0.445, F1 0.594, TPR 0.652; UNet IoU 0.411; pixel-level metrics, 50/50 split by site. The paper does not discuss calibration, uncertainty or coverage. Authors note performance plateaued at about six training sites and the dataset is small. — [arXiv HTML](https://arxiv.org/html/2401.14546v2); project page: https://umfieldrobotics.github.io/ai4shipwrecks/
- Same paper characterises prior SSS datasets: SeabedObjects-KLSG (2020; 1,190 images, 385 with shipwrecks) and Marine-PULSE (2023; 719 images, no shipwreck images), neither with pixel-wise labels. — [arXiv HTML](https://arxiv.org/html/2401.14546v2)
- Marine-PULSE on Zenodo (v1, Oct 2023): classes pipeline/cable, underwater residual mound, seabed surface, engineering platform. Listed per-class counts sum to 627 vs 719 in the AI4Shipwrecks table (discrepancy unexplained; may be version/counting). Later refined in a JMSE 2025 paper (vol. 13, issue 3). — [Zenodo](https://zenodo.org/record/7922705); [MDPI JMSE](https://www.mdpi.com/2077-1312/13/3/424)
- BenthiCat (Univ. Girona; arXiv 2510.04876; ESSD preprint essd-2026-565, under review): ~1M SSS tiles (Klein 3000H, 500 kHz), 178k co-registered optical images, ~36k tiles with manual segmentation masks; labels are seabed substrate/habitat, not litter. — [arXiv](https://arxiv.org/abs/2510.04876v1); [ESSD preprint](https://essd.copernicus.org/preprints/essd-2026-565/)
- SubPipe (OCEANS 2024; arXiv 2401.17907): LAUV with Klein 3500 SSS; 10,030 SSS images with pipeline bounding boxes (5,000 low-freq + 5,030 high-freq), COCO/YOLO formats; no debris/net class. — [arXiv](https://arxiv.org/abs/2401.17907); [Zenodo](https://zenodo.org/records/12666132)
- MILCO (mine-like objects, 1,170 SSS images, Gavia AUV; Santos et al. 2024), SWDD (wall detection, Klein 3500) — listed on [DataEval docs](https://dataeval.readthedocs.io/en/v0.86.0/reference/autoapi/dataeval/utils/datasets/MILCO.html) and [Zenodo SWDD](https://zenodo.org/records/13692547) (found via search snippet only, not read in full).
- 2025 survey of public sonar datasets (SSS, FLS, SAS, MBES, DIDSON): Gomes et al., SIBGRAPI, arXiv 2510.03353. Only the abstract was read; I could not confirm from it whether any listed dataset has net/fishing-gear labels. — [arXiv](https://arxiv.org/abs/2510.03353)
- Marine Debris Forward-Looking Sonar Datasets (Valdenegro-Toro et al., arXiv 2503.22880, Mar 2025): this is FLS (ARIS Explorer 3000), not side-scan. Watertank 2,627 samples (10 classes: bottle, can, chain, drink carton, hook, propeller, shampoo bottle, standing bottle, tire, valve), turntable 2,150 samples, 7,209 unlabelled quarry frames. Nets are NOT a labelled class. Best segmentation mIoU 74.8% (UNet-ResNet34); SSD detection mAP 91.69. Calibration/uncertainty not addressed. — [arXiv HTML](https://arxiv.org/html/2503.22880v1)
- Roboflow Universe has a community "Side Scan Sonar" dataset; contents not checked. — https://universe.roboflow.com/yilus-workspace/side-scan-sonar-pnolu

**Ghost-net-specific work**
- GhostNetZero preprint (Miao, Dederer, Lee, ... Dodhia, Lavista Ferres; Microsoft AI for Good Lab / WWF Germany / Accenture; EcoEvoRxiv v3, 23 Sep 2025; not peer reviewed): human-in-the-loop web platform; ~90% "ghost net detection rate" on Baltic Sea and Puget Sound data. Precision/recall/F1, dataset size and definition of "detection rate" not reported on the page I read; paper states "There is no data or code available for this study at this moment" and mentions sonar's "limited spatial coverage" without evaluating coverage. Calibration, uncertainty and search completeness are not discussed. — [EcoEvoRxiv](https://ecoevorxiv.org/repository/view/10294/) (PDF: https://ecoevorxiv.org/repository/object/10294/download/19034 — NOT read in full; the summary above is from the landing page, so check the PDF before asserting absence).
- Press descriptions: DeepLabV3 with ResNet50 backbone; "94%" (NVIDIA blog) vs "up to 95%" (award entry) vs ~90% (preprint) are inconsistent self-reported figures; experts review only flagged segments; ">75% faster than manual". — [NVIDIA via Edge AI Vision](https://www.edge-ai-vision.com/2025/06/ai-helps-locate-dangerous-fishing-nets-lost-at-sea/); [Global Seafood Alliance](https://www.globalseafood.org/advocate/leveraging-ai-to-detect-and-retrieve-ghost-fishing-gear-its-a-global-problem/); [Gerety Awards](https://www.geretyawards.com/winners/2025/entry/186259/ghostnetzero-wwf-germany); [Marine Insight](https://www.marineinsight.com/shipping-news/wwf-germany-introduces-ai-platform-to-detect-remove-ghost-nets-from-oceans)
- ghostnetzero.ai itself: fetch returned only the title, so I could not verify the platform's outputs (confidence scores, coverage display). Unverified.
- Stolte et al. 2022, Frontiers in Marine Science 9:981840 (DOI 10.3389/fmars.2022.981840): manual interpretation of 600 kHz Marine Sonics side-scan (towed ~5 m above seabed, 3-4 kn, 100 m swath, "a few cm" resolution, gillnet lines as thin as 1 cm). 5,820 ha over 45 days (>=130 ha/day). 549 suspects, 176 diver-verified (~32%), 94 confirmed ALDFG; "false suspect rate 57%" in Schleswig-Holstein (53 of 93 verified suspects were other objects or active nets). No automated detection, no detection probability or miss rate reported; warns interpretation is harder on soft seabeds. (Fetch covered first 100k of 114k characters.) — [Frontiers](https://www.frontiersin.org/journals/marine-science/articles/10.3389/fmars.2022.981840/full)
- GhostNetBusters (GEOMAR + sonoware, EUR 221k, June 2024 - Jan 2026): ML on SSS (.xtf/.jsf) to cut manual verification; released SidescanTools (open source, "early development stage"); no model performance, confidence or coverage reported on the project page. — [GEOMAR](https://geomar.de/en/ghostnetbusters); [sonoware](https://sonoware.de/news/2024-08-28_foerderzusage_ghostnetbusters)
- NOAA/Mass. DMF derelict lobster-pot work: field trials set pots on simple (sand/mud) and complex (rocky) seafloor to measure side-scan detection rates; the NOAA page and snippets give no numerical rates. Full report (mass.gov PDF) returned HTTP 403, so numbers unverified. This is the closest civilian "empirical Pd of side-scan for fishing gear" effort found. — [NOAA MDP](https://marinedebris.noaa.gov/prevention/estimating-abundance-derelict-lobster-pots-new-england-using-side-scan-sonar); [Mass DMF report](https://www.mass.gov/doc/development-of-side-scan-sonar-methodology-to-survey-derelict-lobster-pots-2017/download)
- Survey of DL for marine debris detection (2024): https://arxiv.org/pdf/2403.18067 (search hit only; not read).

### Inferences
- NetSight claim (3) "no public side-scan dataset has labelled ghost nets" is consistent with everything I found, but I could not exhaustively check every dataset's class list (KLSG, SCTD, Roboflow sets, the 2025 survey table). Phrase as "no dataset we found" rather than "none exists".
- GhostNetZero's own data are explicitly not public (as of preprint v3), which makes an open ghost-net SSS benchmark genuinely absent.
- Reported ghost-net "accuracy" numbers are non-comparable and unverified; the shipwreck benchmark (IoU ~0.45) shows SSS segmentation remains far from solved on public data.

### Gaps
- Full text of GhostNetZero PDF, SCTD dataset details (no search hit; unverified), Marine-PULSE/KLSG class lists, 2025-26 peer-reviewed SSS ghost-net papers (none surfaced; absence not proven), Mass DMF numeric Pd.

## 2. Is calibrated confidence / uncertainty estimation in sonar ATR published or productized?

### Takeaway
Published for synthetic aperture sonar (Penn State / Orescanin group, Bayesian deep learning, calibrated uncertainty, abstention) and in SAR ATR; I found nothing for side-scan debris/ghost-net detection. Vendor ATR (SeeByte) outputs a confidence/"mine-like" score, but I found no documentation of calibration. So "no calibrated confidence" is true for debris/net tools but overstated if applied to sonar ATR research generally.

### Cited Findings
- Orescanin et al., UACE 2023, "Uncertainty quantification with deep learning through variational inference with applications to synthetic aperture sonar": variational-inference network ~92% accuracy with calibrated uncertainty; rejecting the 10% most uncertain samples adds ~4 points; splits aleatoric/epistemic. Task was classifying imaging artifacts, not targets. — [Penn State](https://pure.psu.edu/en/publications/uncertainty-quantification-with-deep-learning-through-variational/); [FFI](https://www.ffi.no/publikasjoner/arkiv/uncertainty-quantification-with-deep-learning-through-variational-inference-with-applications-to-synthetic-aperture-sonar)
- Follow-up journal version (appears to be IEEE JOE 2025) — [PDF](https://kerednoslo.github.io/papers/Orescanin2025.pdf). Characterised only from a search summary; full text not read; venue unverified.
- SAR-domain analogues: Bayesian CNN with uncertainty heat maps for SAR target detection (Remote Sensing 14(23):6096) — https://mdpi.com/2072-4292/14/23/6096; "Calibrated confidences and prediction sets for open-set SAR ATR" (SPIE 2024) — https://biomedicaloptics.spiedigitallibrary.org/conference-proceedings-of-spie/13032/130320W/Calibrated-confidences-and-prediction-sets-for-open-set-SAR-ATR/10.1117/12.3021865.full
- Earlier: Chang et al. 2005 confidence estimation for sonar multi-target classification (simulated images) — https://fds.duke.edu/db/pratt/FIP/silvia.ferrari/publications/336161
- A search for conformal prediction / calibration with side-scan object detection found no sonar-specific results (conformal detection papers surfaced only for railway, runway etc., e.g. https://arxiv.org/pdf/2304.06052). This is a single-search negative, not proof.
- SeeByte ATR/Neptune: gives operators a measure of how "mine-like" each target is; requires tuning per sonar and configuration; onboard real-time; contacts carry confidence scores per a research paper. No calibration documentation found. — [SeeByte](https://seebyte.com/products/atr-system/); [UST profile](https://www.unmannedsystemstechnology.com/company/seebyte/automatic-target-recognition-atr-system/); [core.ac.uk paper](https://core.ac.uk/download/77036084.pdf)
- SeeByte terrain-characterisation paper (arXiv 2404.18663, Apr 2024): inserts simulated mine-like contacts into real SSS to build an ATR performance map of terrain; used in a Neptune MCM mission so AUV revisits areas with low ATR performance. Read via abstract/summaries only. — [arXiv](https://arxiv.org/abs/2404.18663v1)
- CMRE (Dugelay, UACE 2019) on ATR low-score detections and clustering — https://paginas.fe.up.pt/~dee10008/papers/UACE2019_927_Dugelay.pdf (search record only).
- Not checked: Kongsberg, Thales, Exail, SonarWiz ATR documentation.

### Inferences
- Calibration/UQ methods exist and are transferable; applying them to side-scan debris/ghost nets with a reliability-diagram-validated claim appears unpublished, based on limited searching. Novelty lies in the application and validation, not the technique.
- SeeByte's inserted-synthetic-target performance map is conceptually a conditional-Pd estimator, so a "trust" layer for ATR is not conceptually new in MCM.

### Gaps
- No vendor documentation found on whether ATR scores are calibrated; no search of SonarWiz/Kongsberg/Exail/Thales docs.

## 3. Are Pd / coverage / search-completeness maps used in civilian contexts?

### Takeaway
Yes, in several adjacent civilian and dual-use areas: IHO hydrographic "full seafloor search" practice, SAR search planning (SAROPS, sweep width, POD, POS), Bayesian deep-sea wreck/aircraft searches (Metron/Stone, DSTG for MH370), and academic AUV search planning. MCM is where Pd/clearance maps are most developed. I found no civilian debris/ghost-net tool that reports such a map, which supports claim (2) in narrower form; but "exists only in naval MCM" is false.

### Cited Findings
**MCM / defence (NATO-linked)**
- Warakagoda et al., SPIE 2019 (FFI/CMRE-linked): map-based evaluation with a Bayesian "probability of a remaining mine" per cell, noting percentage-clearance metric needs modification. — https://katalog.lib.cas.cz/KNAV/EdsRecord/edsair,edsair.doi...........5583477716017b595cda960734e35b12 (catalog record only)
- Midtgaard et al., OCEANS 2015: through-the-sensor performance estimation across SAS and side-scan systems and five frequency bands, data from CMRE's MANEX'14 trial. — https://katalog.lib.cas.cz/KNAV/EdsRecord/edsair,edsair.doi...........f4b2a980d4d82d98e9719eb50301d84e
- Gazagnaire, Beaujean, Stack (IOA): combines seabed model with ATR to produce Pd/Pfa by seafloor class, Pdc, and percent coverage. — https://www.ioa.org.uk/system/files/proceedings/j_gazagnaire_p_beaujean_j_stack_combining_model-based_and_in_situ_performance_prediction_to_evaluate_detection_and_classification_performance.pdf
- NPS: "cookie-cutter" vs lateral range curves vs engineering-parameter detection models for mine detection probability (SeaFox/REMUS). Surfaced in search; source not individually fetched.
- SeeByte PATT white paper: inserting simulated mines into real SSS to estimate Pd/Pfa by seabed type — https://www.unmannedsystemstechnology.com/wp-content/uploads/2013/10/White-Paper-Performance-Analysis-Testing.pdf (search-hit description only)

**Hydrographic (IHO)**
- S-44 "full sea floor search" = ability to detect all cubic features of a given size (Special Order >1 m; Order 1a >2 m in <=40 m depth or 10% of depth beyond); Order 2 requires no full search. The detection requirement is a binary coverage/feature-detection spec verified by cube-target trials, not a probabilistic map. Sources reflect the 1998 4th edition via commentary and UK C-13; the current S-44 Ed. 6 not checked. — [UK C-13 Ch.4](https://docs.iho.int/iho_pubs/CB/C-13/english/C-13_Chapter_4.pdf); [Kongsberg-related trial paper](https://journals.lib.unb.ca/index.php/ihr/article/download/20616/23778/29374); [Springer chapter](https://link.springer.com/10.1007/978-3-642-45062-4_51)

**Search-and-rescue and Bayesian search**
- SAROPS (US Coast Guard): probability maps of target location, sweep-width tables from detection-vs-range curves, planning that maximises probability of success (POS = containment x detection). Frost's "Theory of Search" (1996) covers POC/POD/sweep width/coverage. — [Wikipedia](https://en.wikipedia.org/wiki/Search_and_Rescue_Optimal_Planning_System); [USCG CG-9 spotlight](https://dcms.uscg.mil/cg9/rdt-e/spotlight/over-ice-search); [Theory of Search](https://navcen.uscg.gov/sites/default/files/pdf/Theory_of_Search.pdf). SAROPS operational docs not read; these are secondary/tertiary.
- Stone / Metron Bayesian search: prior map, allocate effort, posterior update after failed search; AF447 search assumed Pd 0.9 within side-looking-sonar-covered flat-seabed areas; BEA tasked Metron in July 2010 (S.S. Central America cited as an earlier case). — [Edinburgh notes](https://www.inf.ed.ac.uk/teaching/courses/dmr/Notes2019/7-Bayes-case.pdf); [Fusion 2015 talk](https://fusion.c4i.gmu.edu/wp-content/uploads/2015/07/Fusion2015_PlenaryTalk_ColleenKeller.pdf)
- MH370: ATSB/Fugro used a sonar-contact categorisation scheme (fact sheet gives no Pd or sweep width); DSTG published Bayesian search methods (book "Bayesian Methods in the Search for MH370") — secondary mention only. Claims about Ocean Infinity's 2025-26 campaign (7,571 sq km, ended 8 Mar 2026) came from an unreliable site and are UNVERIFIED. I found no public Ocean Infinity search-planning Pd-map documentation. — [ATSB fact sheet](https://atsb.gov.au/sites/default/files/media/5318162/MH370_SonarContact_FactSheet_july.pdf)
- McMahon, Yetkin, Wolek, Waters, Stilwell, "Towards Real-Time Search Planning in Subsea Environments," IROS 2017: maximises formal search effectiveness, with per-environment detection probability and false-alarm rates, validated on AUV SAS data from Boston Harbor. — [arXiv 1707.07662](https://arxiv.org/abs/1707.07662)

**Side-scan coverage geometry**
- Probabilistic observation model for side-scan (likelihood each seafloor region was observed, used to weight mapping): PLOS ONE 2016, https://ideas.repec.org/a/plo/pone00/0146396.html ; PMC: https://pmc.ncbi.nlm.nih.gov/articles/PMC4731207
- HAL/ENSTA "Estimating the Coverage Measure and the Area Explored by a Side-Scan Sonar" (winding-number method for coverage counts) — https://hal-ensta-bretagne.archives-ouvertes.fr/hal-03970541v1
- AUV coverage path planning where row spacing is bounded by acceptable POD — https://arxiv.org/pdf/2006.12896

**Civilian derelict-gear practice**
- NOAA/Chesapeake derelict trap survey: stratified random design using side-scan; MDP/Mass DMF detection-rate trials (numbers not obtained). — [Chesapeake archive](https://webarchive.library.unt.edu/web/20170119130501/https://chesapeakebay.noaa.gov/acoustic-seafloor-mapping/maryland-derelict-fishing-gear-benthic-survey)

### Inferences
- Mapping a swath-coverage mosaic is routine, and Pd/sweep-width/POS maps are standard in SAR and MCM, so claim (2) is wrong in its absolute form ("exists only in naval MCM"). A defensible version: no published civilian debris/ghost-net workflow combines ATR-derived, terrain-conditional Pd with a per-cell search-completeness map; the closest conceptual match is MCM (Gazagnaire; Warakagoda; SeeByte terrain maps) and AUV search planning (McMahon 2017).
- Stolte 2022 reports area surveyed (ha) and a 57% false-suspect rate but no miss rate, illustrating that ghost-net practice reports effort rather than probability of detection.

### Gaps
- No direct paper titled for "sweep width side-scan sonar" for small seabed debris found; Koopman-style lateral range curves for side-scan on debris not located. Full-text verification missing for the MCM papers (catalog records only). No data on Ocean Infinity methodology. No check of Ocean/IEEE OES 2025-2026 proceedings.

## 4. Verdict on NetSight's four claims

### Takeaway
Partly true, partly overstated. Genuinely open: a calibrated-confidence plus Pd/search-completeness product for civilian debris/ghost-net side-scan. Already done in adjacent fields (technique-level): calibrated sonar UQ (SAS), terrain-conditional Pd maps (MCM), Bayesian search/POS maps (SAR, wreck search).

### Cited Findings (claim by claim)
1. "Existing tools and SIH teams only answer 'where is debris?' with no calibrated confidence": SUPPORTED for debris/ghost-net tools (GhostNetZero preprint and press report a single detection rate; Stolte 2022 manual). But platform output fields unverified, and calibrated UQ exists for SAS ATR (Orescanin) and SeeByte outputs scores. — sources in sections 1-2.
2. "No civilian debris/ghost-net tool reports a Search-Completeness/Pd map; exists only in naval MCM": PARTLY. None found for debris/nets (absence of evidence from limited search). But the "only in MCM" part is false: SAROPS, IHO full-seafloor-search practice, Bayesian wreck/aircraft searches, and academic AUV search planning use POD/coverage/POS concepts. — section 3.
3. "No public side-scan dataset has labelled ghost nets": CONSISTENT with findings (AI4Shipwrecks, Marine-PULSE, SubPipe, BenthiCat, KLSG have other classes; Marine Debris FLS dataset is forward-looking and has no net class; GhostNetZero data unreleased). Not exhaustively verified (SCTD, Roboflow, survey table unchecked). Also note ghost nets are discussed as an example in the FLS dataset paper's introduction only.
4. "GhostNetZero has no published calibration or coverage map": CONSISTENT with preprint landing page (no calibration/coverage; "no data or code available"), but the PDF and ghostnetzero.ai UI were not read, so this is "not found" rather than "confirmed absent". Reported accuracy varies 90/94/95% across sources.

### Closest prior art (links)
- SeeByte terrain characterisation and Neptune re-survey of low-ATR-performance areas: https://arxiv.org/abs/2404.18663v1
- Gazagnaire et al. model-based plus in-situ Pdc and percent coverage: https://www.ioa.org.uk/system/files/proceedings/j_gazagnaire_p_beaujean_j_stack_combining_model-based_and_in_situ_performance_prediction_to_evaluate_detection_and_classification_performance.pdf
- McMahon et al. subsea search planning with per-environment detection and false-alarm model: https://arxiv.org/abs/1707.07662
- Orescanin et al. calibrated UQ for SAS: https://pure.psu.edu/en/publications/uncertainty-quantification-with-deep-learning-through-variational/
- GhostNetZero preprint: https://ecoevorxiv.org/repository/view/10294/
- Stolte et al. 2022: https://www.frontiersin.org/journals/marine-science/articles/10.3389/fmars.2022.981840/full
- Side-scan observation-probability model (PLOS ONE): https://pmc.ncbi.nlm.nih.gov/articles/PMC4731207
- SAROPS / Theory of Search: https://navcen.uscg.gov/sites/default/files/pdf/Theory_of_Search.pdf

### Inferences
- Recommended re-wording of NetSight's novelty: "No published civilian debris/ghost-net side-scan workflow reports calibrated, terrain-conditional detection confidence together with a per-cell search-completeness (Pd) map; we adapt techniques from SAS uncertainty quantification, MCM performance mapping and SAR search theory." This is defensible; the original absolute wording is not.
- Key risk: reviewers familiar with MCM (SeeByte, FFI, CMRE) will point to the above prior art, so cite it.

### Gaps
- Unverified: SCTD, KLSG specifics, Kongsberg/Thales/Exail/SonarWiz features, ghostnetzero.ai UI outputs, current IHO S-44 text, Ocean Infinity methods, Mass DMF numeric detection rates (403), exact venue/date of Orescanin 2025 journal paper. Any 2026 papers on ghost nets with SSS were not found, but search coverage of late-2026 literature was limited (web search only, no arXiv/IEEE Xplore listing queries).
