# Sensor-Agnostic / Cross-Sensor Sonar AI for NetSight (state of the art as of Nov 2026)

Scope: how to move NetSight's AI from side-scan only to many sonar types (side-scan, SAS, MBES backscatter and water column, forward-looking/imaging multibeam such as Oculus or BlueView, 3D sonar), while keeping the "trust layer" (calibrated per-object probabilities plus Pd/coverage maps per seabed cell) credible.

Evidence legend used below:
- **[READ]**: I fetched the primary page (arXiv abstract or HTML full text, PMC full text, GitHub README) this session.
- **[SEARCH-ONLY]**: Known only from a search-engine summary/snippet. Not opened. Treat details as unverified.
- **[BACKGROUND, NOT VERIFIED THIS SESSION]**: From prior knowledge, with a URL I believe is correct but did not open this session. The report writer should flag or drop these if they cannot be checked.

---

## Q1. Are there sonar foundation models or self-supervised pretraining approaches across sonar types (2023-2026)?

### Takeaway
No public "universal sonar" foundation model trained jointly across side-scan, SAS, MBES and FLS was found. What exists are single-modality SSL backbones: BenthicDINO (side-scan, 2026), Mine-JEPA (side-scan, 2026), and SAM fine-tunes for FLS (SonarSAM, 2023). The strongest finding is that small in-domain SSL beats huge generic optical pretraining (Mine-JEPA beats DINOv3), and that physics-aware SSL (BenthicDINO) transfers across side-scan sensors. A multi-sonar pretrained backbone is an open gap NetSight could credibly target, but not one it can download.

### Cited Findings
**BenthicDINO (side-scan, physics-informed self-distillation)** [READ]
- Authors Taqi Hamoda, Hayat Rajani, Nuno Gracias. arXiv 2608.23215, v1 24 Aug 2026, v2 16 Oct 2026. — [arXiv abs](https://arxiv.org/abs/2608.23215)
- Method: ConvNeXt-v2 backbone, DINO-style self-distillation, physics-guided augmentations, and an HSIC penalty that pushes features to be statistically independent of viewing geometry V = (incidence angle θ, slant range r_s). The goal is to separate seabed content from acquisition effects. — [arXiv abs](https://arxiv.org/abs/2608.23215); [HTML full text](https://arxiv.org/html/2608.23215)
- Augmentations: speckle (Gaussian σ ~ U(0.01, 0.05), p = 0.5); synthetic TVG as a linear range-dependent decay with far-edge retention β ~ U(0.3, 0.7), p = 0.5; radiometric jitter (contrast U(0.8, 1.2), brightness U(−0.1, 0.1)). Incidence angle and slant range are not augmented. They enter only through the HSIC term, with γ = 0.3 and an RBF kernel approximated by random Fourier features. — [HTML](https://arxiv.org/html/2608.23215)
- Pretraining data: subset of BenthiCat (~1 million SSS tiles, Catalonia, Spain, collected by Tecnoambiente SLU), Klein 3000H, 500 kHz channel only. — [HTML](https://arxiv.org/html/2608.23215)
- Habitat mapping (S3Seg, frozen features plus linear probe): 1% labels gives mIoU 0.706; 10% gives 0.844; 100% gives 0.882. No supervised baseline is reported on S3Seg. — [HTML](https://arxiv.org/html/2608.23215)
- **Cross-sensor transfer:** On AI4Shipwrecks (EdgeTech 2205 at 520 kHz CHIRP on an Iver3 AUV, Thunder Bay, Lake Huron, 28 sites, 50/50 site-disjoint split, frozen encoder plus a U-Net decoder trained from scratch), BenthicDINO gets IoU_ship 0.423 and F1 0.553. Supervised U-Net gets 0.411 IoU, DeepLabv3 0.363, HRNet 0.372, ViT-Adapter 0.283. It ranks 2nd of 7, behind InSPyReNet (0.445 IoU, optical-pretrained). Performance depends strongly on depth: 0.651 IoU on 5 sites deeper than 40 m vs 0.280 on 8 shallower sites. — [HTML](https://arxiv.org/html/2608.23215)
- No code or weights link was found in the abstract page or the first ~100k characters of the HTML. The last ~12k characters were not read. — [arXiv abs](https://arxiv.org/abs/2608.23215)

**Mine-JEPA (side-scan, in-domain JEPA SSL)** [READ]
- Kwon et al. (Maum AI, with SNU/KAIST/Yonsei affiliations), arXiv 2604.00383, 1 Apr 2026. — [arXiv HTML](https://arxiv.org/html/2604.00383v1)
- Pretrained on only 1,170 unlabeled real SSS images (~153K 96×96 patches), optionally plus ~256K synthetic patches. It starts from ImageNet-1K weights. — [arXiv HTML](https://arxiv.org/html/2604.00383v1)
- Beats fine-tuned DINOv3 (1.7B-image pretraining): binary mine/non-mine F1 0.935 vs 0.922; 3-class macro-F1 0.820 (ViT-S) and 0.814 (ViT-Tiny, 5.5M params) vs 0.810 (21.5M params). — [arXiv HTML](https://arxiv.org/html/2604.00383v1)
- Applying in-domain SSL on top of DINOv3 *hurt* it by 10.4 points (real data) and 13.3 points (real+synthetic). — [arXiv HTML](https://arxiv.org/html/2604.00383v1)
- ImageNet-1K-only init gives 0.739 macro-F1 vs 0.557 from random init. Generic optical pretraining is therefore still a useful starting point. — [arXiv HTML](https://arxiv.org/html/2604.00383v1)
- No cross-dataset or cross-sensor tests. The authors list SAS and FLS as future work. No code or weights URL found. — [arXiv HTML](https://arxiv.org/html/2604.00383v1)

**SonarSAM ("When SAM Meets Sonar Images", FLS)** [SEARCH-ONLY]
- arXiv 2306.14109 (2023). Fine-tunes SAM for sonar with LoRA and visual prompt tuning on the forward-looking sonar Marine Debris dataset with box prompts. It reports large gains over stock SAM. — [arXiv](https://arxiv.org/html/2306.14109v1); [GitHub wangsssky/SonarSAM](https://github.com/wangsssky/SonarSAM)
- Code is Apache-2.0, last push 27 Jul 2024 (per ecosyste.ms), ~71 stars. — [ecosyste.ms](https://awesome.ecosyste.ms/projects/github.com%2Fwangsssky%2FSonarSAM); [relatedrepos](https://relatedrepos.com/gh/wangsssky/SonarSAM)

**Other related items** [SEARCH-ONLY unless marked]
- SonarLLM (arXiv 2608.24325, 2026): sonar-optical multimodal LLM plus benchmark (recognition, counting, VQA, captioning). It is not a CLIP-style cross-sonar encoder. — [arXiv PDF](https://arxiv.org/pdf/2608.24325)
- Self-supervised multibeam (imaging) sonar restoration via coherent forward modelling (arXiv 2610.31490, 2026): despeckle plus deblur trained on registered multi-frame sequences without clean ground truth. — [arXiv](https://arxiv.org/abs/2610.31490)
- Self-supervised FLS enhancement bridging cross-modal degradation gaps (arXiv 2504.10974). — [arXiv PDF](https://arxiv.org/pdf/2504.10974)
- Adapting vision foundation models to acoustics for pose-free 3D sonar reconstruction (arXiv 2609.06261, 2026). — [arXiv HTML](https://arxiv.org/html/2609.06261)
- Survey "Sonar-based Deep Learning in Underwater Robotics: Overview, Robustness and Challenges" (Aubard, Madureira, Teixeira, Pinto, arXiv 2412.11840, Dec 2024). The abstract stresses limited data, noise and a "lack of robustness in sonar-based DL research", and names sim-to-real as a future direction. The abstract does not discuss foundation models or calibration [READ, abstract only]. — [arXiv](https://arxiv.org/abs/2412.11840)
- Survey "Sonar Image Datasets: A Comprehensive Survey of Resources, Challenges, and Applications" (arXiv 2510.03353) and the curated list Awesome-Sonar-Image-Resources. Both are useful for collecting multi-modality pretraining data. — [arXiv PDF](https://arxiv.org/pdf/2510.03353); [GitHub](https://github.com/Jorwnpay/Awesome-Sonar-Image-Resources)

### Inferences
- The best evidence-backed backbone recipe for NetSight is: (a) start from generic optical weights (ImageNet or DINO family), (b) continue SSL on in-domain sonar tiles from *all* sensor types available, (c) add BenthicDINO-style geometry-invariance (HSIC against grazing angle and range) plus physics augmentations (speckle, TVG, gain jitter). Mine-JEPA's DINOv3 result is a caution: naive continued SSL on a strong generic model can *hurt*, so ablations are mandatory.
- BenthicDINO is the most relevant published proof that sensor-geometry-aware SSL transfers between side-scan systems (Klein 3000H 500 kHz pretraining to EdgeTech 2205 520 kHz evaluation). But the frequencies are close, and it is still side-scan to side-scan. Its large depth sensitivity (0.651 vs 0.280 IoU) shows acquisition conditions still dominate.
- A cross-modality backbone covering SSS, SAS, MBES backscatter mosaics and FLS fans is not published, so far as these searches found. NetSight should present it as a research bet, not an existing capability.

### Gaps
- No public weights were confirmed for BenthicDINO or Mine-JEPA. Check the GitHub pages of the Gracias lab (Univ. Girona) and Maum AI directly.
- No sonar "CLIP" contrastive sonar-text encoder was found as a released model. SonarLLM details were not read.
- I did not find "universal sonar" or multi-sensor SSL papers in IEEE JOE or OCEANS. Those venues are partly paywalled and were not searched deeply.

---

## Q2. Cross-sensor domain adaptation and transfer: how big is the drop, and what fixes it?

### Takeaway
Hard cross-sensor numbers for sonar are scarce. The best quantified sonar adaptation result is the optical-to-side-scan detection study (Sci. Rep. 2024). There, source-only detection reached mAP 9.58 vs 58.88 for the fully supervised oracle. CycleGAN style transfer combined with a teacher-student UDA (DCBD) recovered most of the gap, to mAP 48.64 (AP50 92.16 vs oracle 94.26). For SAS, the SCTD 3.0 dataset defines cross-frequency splits (240 kHz to 450 kHz) and claims "cliff-like" drops, but publishes no numbers. Analogous fields (LiDAR) report 30–70% relative drops under sensor change [SEARCH-ONLY].

### Cited Findings
**DCBD: optical-to-side-scan UDA detection** [READ] (Wei et al., *Scientific Reports* 14:12687, 2024; Faster R-CNN ResNet-101, Adaptive Teacher base)
- Source: labeled optical ship images (856 images). Target: unlabeled clear-water SSS (~850 train / 785 test). — [PMC full text](https://pmc.ncbi.nlm.nih.gov/articles/PMC11148073/)
- mAP / AP50: Source only 9.58 / 21.07; CycleGAN alone 19.45 / 50.37; DA-Faster R-CNN 10.53 / 26.11; Adaptive Teacher 26.78 / 54.07; AT + CycleGAN 44.92 / 89.20; **DCBD 48.64 / 92.16**; Oracle (supervised) 58.88 / 94.26. — [PMC](https://pmc.ncbi.nlm.nih.gov/articles/PMC11148073/)
- The paper notes a known tension: making features more domain-invariant can reduce their discriminability and hurt detection. — [Nature/Sci Rep](https://www.nature.com/articles/s41598-024-63501-1)
- Code and data: [github.com/firekeepers/DCBD](https://github.com/firekeepers/DCBD) (stated in the paper; repo not opened). — [PMC](https://pmc.ncbi.nlm.nih.gov/articles/PMC11148073/)

**SCTD 3.0: SAS cross-frequency benchmark** [READ] (Peng Zhang, arXiv 2608.08106, Aug 2026)
- Over 10,000 real SAS snippets, multi-frequency (240 kHz, 450 kHz, "others"), 10 target categories, hierarchical physical-attribute annotations (burial, shadow integrity, specular highlights, resonance). — [arXiv abs](https://arxiv.org/abs/2608.08106)
- Defines operating conditions EOC-1 (train SAS-240k, test SAS-450k), EOC-2 (the reverse) and EOC-3 (mixed bands). **No numerical cross-frequency results are reported in the HTML.** Cross-region and cross-view tests are stated as future work. — [arXiv HTML](https://arxiv.org/html/2608.08106)
- In-distribution: SAS-240k overall mAP@0.5 = 0.708. SAS-450k gives per-class values only (e.g., cone 0.906, cylinder_resonant 0.362, cube 0.000). — [arXiv HTML](https://arxiv.org/html/2608.08106)
- The abstract asserts a "cliff-like performance drop" in-the-wild, which the body does not quantify. Data: [github.com/automlresearch/SCTD-3.0](https://github.com/automlresearch/SCTD-3.0) (licence not checked). — [arXiv abs](https://arxiv.org/abs/2608.08106)

**BenthicDINO cross-sensor SSS transfer** [READ]: see Q1. A frozen encoder pretrained on Klein 3000H transferred to EdgeTech 2205 data competitively (0.423 IoU vs 0.411 for a supervised U-Net). — [arXiv HTML](https://arxiv.org/html/2608.23215)

**FLS sim-to-real and UDA** [SEARCH-ONLY]
- Teacher-student UDA for FLS obstacle segmentation; target data from an Oculus MD750d on an AUV (MDPI JMSE 13(11):2134, 2025). — [MDPI](https://www.mdpi.com/2077-1312/13/11/2134)
- CycleGAN translation of synthetic to real acoustic-camera images, unpaired (239 synthetic / 293 real), for 3D reconstruction (MDPI JMSE 14(19):1796). — [MDPI](https://www.mdpi.com/2077-1312/14/19/1796)
- A physics-based FLS simulation dataset is argued to close the sim-to-real gap better than graphics-based simulation or style transfer, which misses propagation attenuation. — [ACM DL](https://dl.acm.org/doi/full/10.1145/3788910.3788922)
- "Synthetic Enclosed Echoes" dataset to reduce the simulated/real sonar gap (arXiv 2505.15465). — [arXiv PDF](https://arxiv.org/pdf/2505.15465)
- SonarSweep (Oculus M1200d plus camera fusion, sim-to-real training). — [arXiv](https://arxiv.org/html/2511.00392v1)

**Side-scan transfer learning** [SEARCH-ONLY]
- Multi-domain collaborative transfer learning for SSS classification (Remote Sensing 14(2):355). — [DOI](https://doi.org/10.3390/rs14020355)
- Crossed point-to-point second-order self-attention transfer recognition (Remote Sensing 15(18):4517). Reports declines for poorly defined target classes under weak supervision. — [DOI](https://doi.org/10.3390/rs15184517)

**Analogy from other sensors** [SEARCH-ONLY]
- LiDAR cross-sensor work cites 30–70% relative drops when moving between datasets or sensor configurations. — [ResearchGate](https://www.researchgate.net/publication/335497756_Cross-Sensor_Deep_Domain_Adaptation_for_LiDAR_Detection_and_Segmentation)
- Cross-resolution SAR detection finds resolution differences make feature-level adaptation unreliable. This is relevant to SSS-to-SAS resolution gaps. — [arXiv 2507.08290](https://arxiv.org/pdf/2507.08290)

### Inferences
- Fix hierarchy suggested by the evidence: (1) supervised fine-tuning with a small number of target-sensor labels (oracle gap). (2) Pixel-level style transfer (CycleGAN) *plus* feature/teacher-student UDA, which together beat either alone by a large margin (44.9 vs 19.5 or 26.8 mAP in DCBD). (3) Physics-based simulation of the target sensor. (4) Geometry-invariant SSL backbones.
- The DCBD domain gap (optical to sonar) is *larger* than a typical sonar-to-sonar gap. Sonar-to-sonar UDA should therefore recover at least as much, but this is an inference, not a measured result.
- NetSight should assume a material drop when switching sensors and *measure it per sensor*. SCTD 3.0's EOC-1/EOC-2 splits are a ready-made public cross-frequency SAS benchmark that NetSight could report numbers on, which would itself be a credibility asset.

### Gaps
- No paper found quantifying SSS-to-SAS, SAS-to-SSS, SSS-to-MBES-backscatter or FLS-hardware-to-FLS-hardware (e.g., Oculus to BlueView) detection drops.
- SCTD 3.0 cross-frequency numbers are not published in the version read.
- The IEEE paper "Assessment of mine hunting performance evaluation parameters across multiple side-looking sonar systems and frequencies" ([IEEE 7404535](https://ieeexplore.ieee.org/document/7404535/)) is directly relevant, but the fetch returned empty (paywall/JS). Its content is unverified.

---

## Q3. Physics/geometry normalization layers, and parameterising calibration and Pd by sensor properties

### Takeaway
Community-standard normalisation exists for MBES backscatter: the GeoHab Backscatter Working Group guidelines (Lurton & Lamarche eds., 2015; journal summary in Marine Geophysical Research 2018). They cover datagram-to-angular-response processing, sector/beam-pattern compensation and angular-dependence correction (Ch. 6.7). Through-the-sensor (TTS) Pd modelling from NATO CMRE and FFI already parameterises Pd by seabed complexity and in-situ image features, and has been assessed across multiple side-looking systems and frequencies. Together these are the template for a sensor-parameterised normalisation and Pd layer.

### Cited Findings
**Backscatter standards** [SEARCH-ONLY]
- GeoHab Backscatter Working Group, "Backscatter measurements by seafloor-mapping sonars. Guidelines and Recommendations" (2015, ~200 pp., eds. X. Lurton & G. Lamarche). Chapter 6 covers datagrams to angular responses and mosaics; section 6.7 covers angular dependence correction. — [NIWA guidelines page](https://niwa.co.nz/oceans/backscatter-measurement-guidelines); [BWSG report PDF](https://webstatic.niwa.co.nz/static/BWSG_REPORT_MAY2015_web.pdf)
- It was motivated by the lack of commonly accepted acquisition and processing procedures for MBES backscatter. — [NIWA](https://niwa.co.nz/oceans/backscatter-measurement-guidelines)
- Journal summary: Lamarche & Lurton, "Recommendations for improved and coherent acquisition and processing of backscatter data from seafloor-mapping sonars," *Mar. Geophys. Res.* 39:5–22 (2018). — [Ifremer Archimer](https://archimer.ifremer.fr/doc/00385/49655); [Springer PDF](https://rd.springer.com/content/pdf/10.1007/s11001-017-9315-6.pdf)
- Building cross-sensor libraries of angular response curves per sediment type and frequency needs *absolute* MBES calibration (Lurton et al., MGR 2018). — [Springer PDF](https://springerlink.bibliotecabuap.elogim.com/content/pdf/10.1007/s11001-018-9348-5.pdf)
- A BSH-hosted workflow models BS angular dependence with the Generic Seafloor Acoustic Backscatter (GSAB/GSM) model and removes the manufacturer's default sector compensation. The source is a secondary, garbled scan. — [BSH digital library](https://digitale-bibliothek.bsh.bund.de/viewer/fulltext/174864/4/)

**Geometry invariance in learned features** [READ]
- BenthicDINO conditions on V = (incidence angle, slant range) via HSIC and simulates TVG with range-decay augmentation. This is a *learned* counterpart of explicit TVG and angular correction. — [arXiv HTML](https://arxiv.org/html/2608.23215)

**Through-the-sensor Pd modelling** [SEARCH-ONLY]
- CMRE's in-situ performance evaluation framework predicts the probability that ATR misses a target. It uses TTS features (e.g., ping-to-ping correlation), not just range, and uses Bayesian statistics so residual-risk maps carry uncertainty. Sand ripples show up as reduced-Pd "veins". — [Dugelay et al., UACE 2019](https://www.uaconferences.org/docs/2019_papers/UACE2019_927_Dugelay.pdf)
- FFI's model combines a-priori and in-situ parameters ("through-the-sensor") and uses an image-complexity metric to build Pd models for different seafloor conditions. — [ResearchGate: TTS performance evaluation for modern mine hunting](https://www.researchgate.net/publication/323254213_Through-the-sensor_performance_evaluation_for_modern_mine_hunting_operations)
- Seabed roughness and clutter density drive sonar image complexity, which limits detection and classification performance. — [ResearchGate](https://www.researchgate.net/publication/323254213_Through-the-sensor_performance_evaluation_for_modern_mine_hunting_operations)
- Assessment of mine-hunting performance-evaluation parameters *across multiple side-looking sonar systems and frequencies* (IEEE). Content not read. — [IEEE 7404535](https://ieeexplore.ieee.org/document/7404535/)
- Bayesian-network evaluation of modern mine-hunting effectiveness. — [ResearchGate](https://www.researchgate.net/publication/355849953_A_Bayesian_Network_Approach_to_Evaluating_the_Effectiveness_of_Modern_Mine_Hunting)
- TTS-aware AUV path replanning (track orientation chosen with TTS metrics). — [arXiv 2006.12896](https://arxiv.org/pdf/2006.12896)
- Residual-risk maps built on ~4 m² grid cells colour-coded by remaining mine probability. — [ResearchGate: Performance assessment tool for AUV based mine hunting](https://www.researchgate.net/publication/289887237_Performance_assessment_tool_for_AUV_based_mine_hunting)
- Review of AUV side-scan target detection (MDPI JMSE 14(2):145, 2026). — [MDPI](https://www.mdpi.com/2077-1312/14/2/145)

### Inferences
Proposed normalisation chain (the "normalised representation" NetSight should produce):
1. **Geometry**: slant-to-ground-range correction using altitude/bathymetry (for SSS/SAS); beam-to-seafloor projection for MBES; fan-to-Cartesian conversion for FLS. Georeference each sample.
2. **Resolution**: resample to a common metres-per-pixel grid per *resolution tier* (e.g., SAS ~2–5 cm, SSS ~5–20 cm, MBES BS ~0.25–1 m). Do not upsample coarse sensors to SAS resolution. Keep the native along-track and across-track resolution as metadata channels. The cross-resolution SAR finding (feature-level adaptation unreliable across resolutions) supports tiering.
3. **Radiometry**: undo vendor TVG where possible; apply beam-pattern/sector correction; apply angular-response normalisation (GeoHab Ch. 6.7, GSAB-type model) for MBES BS; apply empirical across-track gain normalisation for SSS. Output log-intensity plus per-pixel grazing angle, range, and an incidence mask (nadir and shadow).
4. **Auxiliary channels** fed to the model: grazing angle, slant range, altitude, frequency, beamwidth, pulse/bandwidth-derived range resolution. Use them for conditioning (FiLM-style) and for HSIC-style invariance regularisation (BenthicDINO).
- **Pd parameterisation**: model Pd per cell as Pd = f(target size / sensor resolution cell, grazing angle, range/SNR proxy, seabed complexity or clutter metric, number of independent looks/aspects, sensor ID). Fit it with a hierarchical (partially pooled) logistic or GAM, with sensor as a random effect. This follows the CMRE/FFI TTS approach, in which Pd depends on in-situ image complexity and geometry rather than nominal range alone, and Bayesian estimation carries uncertainty into the map. This lets a new sensor borrow strength from others while its own data accumulate.

### Gaps
- I did not read Chapter 6.7 of the GeoHab report directly, so the exact recommended angular-normalisation formula is unverified.
- No paper was found that jointly normalises SSS, SAS, MBES and FLS into one ML-ready representation. This would be NetSight's own engineering.
- The Pd-vs-sensor-parameter regressions in the CMRE and FFI papers were not opened. Coefficient forms are unverified.

---

## Q4. Data format layer: formats to ingest and open-source readers (with licences)

### Takeaway
No single open library reads every format. A practical ingest layer combines MB-System (GPL-3, broad multibeam and side-scan coverage, including Reson 7k as MBIO 88), pyxtf (XTF), xtfjsf (XTF plus EdgeTech JSF, including SAS), gsfu/pygsf (GSF), kmall readers (Kongsberg), CCOM-JHC common readers (all/kmall/s7k), oculus-python (Blueprint .oculus), GDAL (GeoTIFF mosaics, BAG) and auvlib. GPL licensing of MB-System matters for a commercial product: call it as a separate process or tool rather than linking it.

### Cited Findings
- **MB-System**: GNU GPL v3. The README mentions Reson 7k ("MBIO format 88") and EdgeTech Jstar output (mb7k2jstar). The README does not list kmall, XTF or GSF, though a forum post says MBIO formats 84/211 read XTF sidescan [READ README; XTF claim SEARCH-ONLY]. — [GitHub dwcaress/MB-System](https://github.com/dwcaress/MB-System); [MB-System mbformat manual](https://www.ldeo.columbia.edu/res/pi/MB-System/mbweb/html/mbformat.html); [GeoMapApp forum](https://www.tapatalk.com/groups/geomapapp/import-of-xtf-files-t85.html)
- **XTF**: oysstu/pyxtf reads/writes XTF (rev. 42). pktrigg/pyxtf is an older (2016, XTF v34) module [SEARCH-ONLY]. — [oysstu/pyxtf](https://github.com/oysstu/pyxtf); [pktrigg/pyxtf](https://github.com/pktrigg/pyxtf)
- **XTF + EdgeTech JSF (SSS and SAS)**: jreGH/xtfjsf, numpy-only, converts between the formats [SEARCH-ONLY]. — [GitHub](https://github.com/jreGH/xtfjsf)
- **GSF**: gsfu is pure Python, reads/writes/indexes GSF and includes a KMALL-to-GSF converter. pygsf is a native Python reader. gsfpy wraps the UKHO C library (Linux only) [SEARCH-ONLY]. — [valschmidt/gsfu](https://github.com/valschmidt/gsfu); [PyPI gsfu](https://pypi.org/project/gsfu/0.3.0/); [guardiangeomatics/pygsf](https://github.com/guardiangeomatics/pygsf)
- **Kongsberg .kmall**: valschmidt/kmall (Python reader), ausseabed/kmall fork, and the pykmall PyPI package [SEARCH-ONLY]. — [PyPI pykmall](https://pypi.org/project/pykmall/1.1.2/); [Awesome-Hydrospatial list](https://github.com/monocilindro/Awesome-Hydrospatial)
- **Kongsberg .all / .kmall / Reson .s7k**: CCOM-JHC "common data readers" parsers (all/kmall/s7k). The GLOBE Java application (Ifremer) processes KMALL, .all and s7k [SEARCH-ONLY]. — [Awesome-Hydrospatial](https://github.com/monocilindro/Awesome-Hydrospatial)
- The KMALL format carries precomputed lat/lon/depth/time/ellipsoidal height, which eases post-processing. — [Kongsberg webinar page](https://www.kongsberg.com/maritime/about-us/news-and-media/webinars/EM)
- **Blueprint Oculus .oculus**: oculus-python (PyPI, experimental, v0.0.2a0) imports/exports v1 and v2 .oculus logs and exports to netCDF4 and HEVC mp4, via the CLI `bps_oculus_io` [SEARCH-ONLY]. — [PyPI oculus-python](https://pypi.org/project/oculus-python)
- **Multi-format C++/Python**: nilsbore/auvlib (GSF, XTF and more) [SEARCH-ONLY]. — [GitHub](https://github.com/nilsbore/auvlib)
- A third-party "sonar-catalog" format overview lists s7k as the Reson/Teledyne multibeam format [SEARCH-ONLY]. — [sonar-catalog](https://brandonrc.github.io/sonar-catalog/docs/formats/overview/)
- **BAG / GeoTIFF**: GDAL has a BAG raster driver, and the Open Navigation Surface project maintains the BAG reference library [BACKGROUND, NOT VERIFIED THIS SESSION]. — [GDAL BAG driver](https://gdal.org/drivers/raster/bag.html); [OpenNavigationSurface/BAG](https://github.com/OpenNavigationSurface/BAG)

### Inferences
- Adapter priority by market reach: (1) XTF (most SSS/SAS vendors can export it). (2) EdgeTech JSF. (3) GSF and Kongsberg .all/.kmall (MBES backscatter and water column). (4) Reson/Teledyne .s7k (MBES). (5) Oculus .oculus (FLS). (6) GeoTIFF mosaics and BAG as a vendor-neutral fallback for any sensor whose raw format is closed (lose geometry channels, keep georeference).
- For a commercial product, prefer permissively licensed Python readers. Wrap GPL tools (MB-System) as external CLI steps to avoid copyleft contamination. Licences of most of the small readers were not checked and must be audited.

### Gaps
- Not found or not checked: open readers for Teledyne BlueView .son, R2Sonic, Norbit native, Kraken/Kongsberg HISAS SAS formats, and 3D sonar (e.g., Coda Echoscope) formats. These are likely proprietary SDK only. Verify with each vendor.
- Licences of pyxtf, xtfjsf, gsfu, pygsf, kmall and oculus-python were not verified.
- Current MB-System support for kmall was not confirmed.

---

## Q5. Is the "trust layer" (calibration + Pd/coverage) inherently more sensor-agnostic than detection?

### Takeaway
Largely yes in *form*, but not in *fitted values*. Conformal prediction and isotonic/Platt calibration act on scores and need only a held-out calibration set. CMRE/FFI-style Pd models act on geometry and seabed-complexity features. So the *software* is sensor-agnostic. But calibration guarantees assume exchangeability between calibration and deployment data, so calibrators must be fit per sensor (and ideally per site or seabed type). Coverage per cell in object detection is non-trivial: box-wise conformal needs IoU matching. No sonar-specific conformal-prediction paper was found.

### Cited Findings
- Conformal prediction needs a trained model plus a separate calibration set to compute nonconformity scores. Extending it to detection is hard because outputs are structured boxes, handled via box-wise conformalisation, IoU matching, or two-step localisation/classification schemes [SEARCH-ONLY]. — [Andéol et al., PMLR v204 (2023)](https://proceedings.mlr.press/v204/andeol23a/andeol23a.pdf); [Two-step CP for boxes, arXiv 2403.07263](https://arxiv.org/pdf/2403.07263)
- "Probabilistic Object Detection with Conformal Prediction" (arXiv 2605.07549, 2026): coordinate-wise CP on box corners with Bonferroni correction, scaled by aleatoric uncertainty from loss attenuation. Gains from calibration are modest over raw aleatoric estimates [SEARCH-ONLY]. — [arXiv abs](https://arxiv.org/abs/2605.07549)
- A MATLAB split-conformal detection workflow cites ~1,000 calibration samples per class for stable quantiles [SEARCH-ONLY]. — [MathWorks](https://www.mathworks.com/help/deeplearning/ug/quantify-uncertainty-in-object-detection-using-split-conformal-prediction.html)
- Safety-critical CP precedents: runway detection with conformal mAP (arXiv 2505.16740) and railway signal detection (arXiv 2301.11136) [SEARCH-ONLY]. — [arXiv 2505.16740](https://arxiv.org/pdf/2505.16740); [arXiv 2301.11136](https://arxiv.org/pdf/2301.11136)
- Sonar-specific: no conformal prediction or calibration paper for sonar detection was found in the searches. The 2024 sonar-DL robustness survey abstract lists verification, OOD and adversarial work, not calibration [READ, abstract only]. — [arXiv 2412.11840](https://arxiv.org/abs/2412.11840)
- CMRE's TTS framework already produces Bayesian Pd/residual-risk maps with uncertainty from geometry and in-situ features, independent of the ATR internals [SEARCH-ONLY]. — [Dugelay et al., UACE 2019](https://www.uaconferences.org/docs/2019_papers/UACE2019_927_Dugelay.pdf)
- Covariate-shift-weighted conformal prediction (Tibshirani, Barber, Candès, Ramdas 2019) restores validity under known shift via likelihood-ratio weights [BACKGROUND, NOT VERIFIED THIS SESSION]. — [arXiv 1904.06019](https://arxiv.org/abs/1904.06019)

### Inferences
- The trust layer is NetSight's most portable asset and arguably its moat. One codebase (isotonic or beta calibration, Mondrian/group-conditional conformal with sensor × seabed-type groups, hierarchical Pd model) can serve every sensor. Only the *fitted* parameters are sensor- and site-specific.
- Practical rule: each new sensor needs (a) a labelled calibration set (on the order of hundreds to ~1,000 matched detections per class, per the MathWorks guidance), or (b) ground-truth targets of known position (seeded-target trials, as in MCM practice), before probabilities can be marketed as "calibrated" on that sensor. Until then, the product should show a "calibration not yet validated for this sensor" state.
- Conformal guarantees fail silently under sensor/site shift, so an OOD or shift detector on normalised features (e.g., image-complexity or embedding distance) should gate the calibrated output.

### Gaps
- No empirical study was found on how isotonic or conformal calibration transfers between sonar sensors, or how much miscalibration a sensor switch causes.
- No sonar multi-sensor evidence-fusion and calibration paper was found (e.g., SSS + MBES joint detection probability).

---

## Q6. Proposed layered architecture with evidence and honest risks

### Takeaway
A six-layer design is defensible: sensor adapters, then a physics-normalised representation, then a shared backbone with sensor-conditioned heads, then evidence fusion, then per-sensor/site calibration, then a sensor-parameterised Pd/coverage map. The normalisation, calibration and Pd layers rest on established practice (GeoHab, CMRE/FFI TTS, conformal). The shared cross-modality backbone is the least proven layer and should be presented as a staged research bet.

### Cited Findings (evidence per layer)
1. **Sensor adapter** (format readers to a common ping/swath/frame data model with navigation, attitude, altitude, frequency, beamwidth, pulse length): readers in Q4 — [MB-System](https://github.com/dwcaress/MB-System); [pyxtf](https://github.com/oysstu/pyxtf); [xtfjsf](https://github.com/jreGH/xtfjsf); [gsfu](https://github.com/valschmidt/gsfu); [oculus-python](https://pypi.org/project/oculus-python)
2. **Normalised representation** (ground-range, resolution tiers, TVG/beam-pattern/angular correction, geometry channels): [GeoHab BSWG report](https://webstatic.niwa.co.nz/static/BWSG_REPORT_MAY2015_web.pdf); [Lamarche & Lurton 2018](https://archimer.ifremer.fr/doc/00385/49655); geometry invariance helps transfer — [BenthicDINO](https://arxiv.org/html/2608.23215); resolution mismatch hurts feature adaptation — [arXiv 2507.08290](https://arxiv.org/pdf/2507.08290)
3. **Shared backbone + sensor-specific heads/adapters**: in-domain SSL beats giant generic pretraining — [Mine-JEPA](https://arxiv.org/html/2604.00383v1); physics-aware SSL transfers across SSS hardware — [BenthicDINO](https://arxiv.org/html/2608.23215); parameter-efficient (LoRA/prompt) adaptation of foundation models to sonar works for FLS — [SonarSAM](https://github.com/wangsssky/SonarSAM); for new sensors with few labels, style transfer plus teacher-student UDA recovers most of the gap — [DCBD, Sci Rep 2024](https://pmc.ncbi.nlm.nih.gov/articles/PMC11148073/)
4. **Evidence fusion** (multiple passes, aspects or sensors over the same object/cell): Bayesian TTS fusion into residual-risk maps — [Dugelay et al., UACE 2019](https://www.uaconferences.org/docs/2019_papers/UACE2019_927_Dugelay.pdf); grid-cell mine-probability maps — [ResearchGate](https://www.researchgate.net/publication/289887237_Performance_assessment_tool_for_AUV_based_mine_hunting)
5. **Calibration per sensor/site**: split/box-wise conformal for detection — [Andéol et al. 2023](https://proceedings.mlr.press/v204/andeol23a/andeol23a.pdf); [arXiv 2605.07549](https://arxiv.org/abs/2605.07549); calibration sample-size guidance — [MathWorks](https://www.mathworks.com/help/deeplearning/ug/quantify-uncertainty-in-object-detection-using-split-conformal-prediction.html)
6. **Pd / coverage map per sensor model**: TTS Pd from in-situ features and seabed complexity — [FFI TTS](https://www.researchgate.net/publication/323254213_Through-the-sensor_performance_evaluation_for_modern_mine_hunting_operations); multi-system/frequency evaluation parameters — [IEEE 7404535](https://ieeexplore.ieee.org/document/7404535/) (not read); TTS-driven replanning — [arXiv 2006.12896](https://arxiv.org/pdf/2006.12896)

**Benchmarks NetSight can report on**: AI4Shipwrecks (EdgeTech 2205) as used in [BenthicDINO](https://arxiv.org/html/2608.23215); SCTD 3.0 cross-frequency SAS splits — [GitHub](https://github.com/automlresearch/SCTD-3.0); FLS Marine Debris (as used by [SonarSAM](https://arxiv.org/html/2306.14109v1)); dataset catalogues — [arXiv 2510.03353](https://arxiv.org/pdf/2510.03353), [Awesome-Sonar-Image-Resources](https://github.com/Jorwnpay/Awesome-Sonar-Image-Resources)

### Inferences
**Recommended concrete architecture (my synthesis; not a published system)**
- **L0 Adapters**: one plugin per format, emitting a common `SonarRecord` (samples, timestamps, nav/attitude, altitude, sensor descriptor {type, frequency, bandwidth, horizontal/vertical beamwidth, range resolution, along-track resolution, source level if known}).
- **L1 Normalisation**: produces (a) a georeferenced intensity raster per resolution tier, (b) per-pixel geometry channels (grazing angle, slant range, altitude-normalised range, shadow/nadir masks), and (c) quality flags. This is classic signal processing, which makes it explainable and auditable.
- **L2 Backbone**: start from an ImageNet/DINO-family init, then continue SSL across all in-house sonar tiles with BenthicDINO-style geometry-HSIC and physics augmentations. Run ablations against no-SSL, since Mine-JEPA shows continued SSL can hurt a strong generic model. Sensor descriptor enters via FiLM/conditioning tokens. Use separate lightweight heads (or LoRA adapters) per modality family: (i) SSS/SAS waterfall, (ii) MBES BS mosaics, (iii) FLS polar frames (temporal), (iv) MBES water-column and 3D point/voxel (likely a separate point-cloud or voxel head, since 2D imaging backbones don't map directly).
- **L3 Fusion**: track/associate detections across pings, passes and sensors in map coordinates. Combine per-look likelihoods with a Bayesian update that accounts for correlated looks.
- **L4 Calibration**: isotonic or beta calibration plus Mondrian conformal, grouped by {sensor model, frequency band, seabed class}. Add a shift detector that falls back to "uncalibrated" when inputs are out of distribution.
- **L5 Pd/coverage**: hierarchical Bayesian Pd(target size/resolution, grazing angle, range/SNR proxy, local image complexity, number of looks | sensor). Fit from seeded targets or synthetic insertion. Propagate per-cell posterior Pd to search-completeness maps.

**Honest risks**
- *Backbone transfer across modalities is unproven*: every published SSL result found is within one modality (SSS) or one sensor family. FLS (polar, temporal, short-range, high frame rate) and MBES water column are physically very different from SSS waterfalls.
- *Data scarcity and labels*: SAS public data are scarce and mostly single-band (SCTD 3.0 claim). Defence-relevant SAS data (HISAS etc.) are often restricted, and access from India may be limited.
- *Raw vs mosaic*: many customers deliver only vendor-processed GeoTIFF mosaics with unknown TVG/gain. This breaks radiometric normalisation and grazing-angle channels, so expect degraded calibration for mosaic-only inputs.
- *Calibration validity*: calibrated probabilities require per-sensor and per-site calibration data. Marketing a "calibrated probability" on an uncalibrated sensor is the biggest credibility risk.
- *Licensing*: GPL (MB-System) and proprietary vendor SDKs (BlueView, R2Sonic, Norbit, SAS) constrain a commercial product.
- *Evaluation bias*: BenthicDINO's 0.651 vs 0.280 IoU split by depth shows a single averaged metric can hide large condition-dependent failures. Report results stratified by depth, seabed type and sensor.

### Gaps
- No published end-to-end multi-sonar ATR plus calibration system was found to benchmark the architecture against.
- Vendor format specifications (Kongsberg KMALL, Teledyne s7k DRF, EdgeTech JSF, Triton XTF) were not opened this session. Confirm versions and licence terms from the vendors.
- 3D sonar (e.g., Coda Echoscope) and MBES water-column AI papers were not searched specifically.
