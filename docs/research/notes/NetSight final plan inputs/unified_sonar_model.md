# Unified (multi-sensor) sonar model for NetSight: evidence and a buildable recipe (as of 6 Nov 2026)

Tagging convention: [READ] = I fetched and read the page (a small fetch-model summarised it; long pages were truncated at ~100k chars, noted where relevant). [SEARCH-ONLY] = only seen in a search-result snippet, not opened. [FROM-MEMORY, NOT FETCHED] = background knowledge with no page verified this session; treat as unverified. Inferences are my own and are labelled as such.

Headline corrections to the brief's earlier findings:
1. BenthicDINO (arXiv 2608.23215) pretrained on ONE sensor (Klein 3000H, 500 kHz channel only, ~1M tiles from the Catalan coast). The paper does NOT run a controlled Klein-to-EdgeTech transfer. The nearest result is a frozen-encoder test on AI4Shipwrecks (EdgeTech 2205 CHIRP, 520 kHz, AUV, Lake Huron). So "transferred across side-scan brands" is only weakly supported. [READ] https://arxiv.org/html/2608.23215
2. I found no public multi-sensor sonar foundation model, and no sonar paper that conditions a network on sensor metadata the way DOFA does for wavelength. A sonar search returned only single-sensor work (Mine-JEPA, BenthicDINO). [SEARCH-ONLY for the absence claim] https://arxiv.org/abs/2604.00383

---

## 1. Analogues: multi-sensor remote-sensing, SAR and ultrasound foundation models

### Takeaway
The proven pattern for "any sensor" is: a shared ViT backbone plus a sensor-aware patch embedding (a hypernetwork in DOFA/Copernicus-FM, channel cross-attention in Panopticon), initialised from DINOv2 and trained on roughly 0.4M to 18M images. Reported evidence of generalising to truly unseen sensors is thin: Panopticon is the only one I read with a dedicated test, and that test is on simulated and out-of-distribution optical/SAR configurations, not on a physically different modality like sonar.

### Cited Findings
- DOFA conditions the patch embedding on each channel's central wavelength. The wavelength gets a 1D sine-cosine encoding, then two FC layers with residuals, then a 4-head Transformer with learnable weight-query tokens and a bias-query token. Two FC layers then output per-channel patch-embedding weights (C x P^2 D) and biases (C x D), reshaped into the conv kernel. The decoder uses the same trick. [READ] https://arxiv.org/html/2403.15356v3
- DOFA pretraining: Sentinel-1 (2 channels), Sentinel-2 (9), Gaofen (4), NAIP (3 RGB), EnMAP (202 hyperspectral); about 11.5M images in total, trained progressively (50K images x100 epochs, then a 410K subset x20 epochs, then one epoch on everything). The paper gives inconsistent image counts in Table 8 (3.5M and 4.5M). [READ] https://arxiv.org/html/2403.15356v3
- DOFA+ is initialised from DINOv2 and trained with masked image modelling plus multi-layer cosine feature distillation from the DINOv2 teacher. It used 150 epochs on 410K images, 8 x NVIDIA L40 (48 GB), about 3 days (my arithmetic: ~580 GPU-hours). DOFA's own GPU count/hours are not stated. [READ] https://arxiv.org/html/2403.15356v3
- DOFA unseen-sensor evidence: strong results on m-forestnet (Landsat-8, never seen in pretraining) and a qualitative figure; the paper has no dedicated unseen-sensor benchmark. Code/weights are public on GitHub and Hugging Face but the paper names no licence. [READ] https://arxiv.org/html/2403.15356v3 ; repo listing [SEARCH-ONLY] https://github.com/zhu-xlab/DOFA
- Panopticon (CVPR 2025 EarthVision workshop, best paper per a search summary): a shared 2D conv embeds each channel separately; a single-query cross-attention fuses channels per spatial patch. Optical channels get a sinusoidal encoding of central wavelength; SAR channels get learned embeddings for orbit x polarisation (12 combinations). Channel attention dim 2304 vs backbone 768. [READ] https://arxiv.org/html/2503.10845v2
- Panopticon data and compute: fMoW (~90K locations), MMEarth (~1.2M), SatlasPretrain (~770K), SpectralEarth (~415K); 16 x A100 40GB, two stages, effective batch 1200, 70 epochs x 1250 iterations per stage (87.5K iterations); total GPU-hours not reported; 98.1M-parameter student (12.9M in the patch embedding). Initialised from DINOv2 ViT-B, but because DINOv2's head weights were not released the authors first trained DINOv2 on fMoW RGB to obtain heads. [READ] https://arxiv.org/html/2503.10845v2
- Panopticon unseen/simulated sensors: reported best on most simulated and OOD sensors (Table 2), with lower variance under spectral subsampling. Ablation of spectral embeddings (stage 2): none 84.8 avg; coarse (optical vs SAR only) 85.1; fine 86.8. Fine-grained spectral info helps optical (MS acc 91.5 to 93.1); for SAR a coarse embedding may suffice, with the authors noting limited SAR eval data. Weights licence not stated in what I read. [READ] https://arxiv.org/html/2503.10845v2
- Copernicus-FM: Fourier-encoded metadata (geolocation, patch area derived from GSD x patch size, time) is ADDED to patch tokens alongside positional encodings; a learnable token replaces missing metadata; metadata drop probability 0.7 in pretraining. A spectral hypernetwork uses central wavelength AND bandwidth; a "variable hypernetwork" extends it to non-spectral inputs (S5P variables, DEM) with Llama 3.2 encoding the variable names. [READ] https://arxiv.org/html/2503.11849
- Copernicus-FM data/compute: Copernicus-Pretrain 18.7M images, 8 modalities (S1, S2, S3, S5P x4, DEM); pretraining on the ~220K all-aligned grids; one run is 512 A100 GPU-hours (128 node-hours on 4 x A100-40GB). The authors list as a limitation that scope is restricted to the Sentinel series; no unseen-sensor result in the part I read. Licence not seen in the part read (last ~17k chars truncated). [READ] https://arxiv.org/html/2503.11849
- SAR (closest physics analogue): SARATR-X pretrains HiViT-B (66M params) on ~186,600 unlabelled SAR target samples from 14 open datasets (SARDet-180K), 8 x RTX 3090, 200 epochs, batch 800. Pretraining set spans X/Ku/C bands, single/quad pol, ~0.1 m to 25 m resolution. Target for masked prediction is multi-scale SAR gradient features (kernel scales 9/13/17): 5/10/20-shot 76.0/81.1/84.5 vs HOG 58.2/64.8/71.7. Detection: SARDet-100K mAP 57.3 vs 56.4 prior best (MSFA); the paper has NO dedicated cross-sensor or cross-resolution ablation; no licence stated. [READ] https://arxiv.org/html/2405.09365v5
- SAR-JEPA (predecessor): masked local patches predict multi-scale SAR gradient representations of unseen context. [SEARCH-ONLY] https://arxiv.org/html/2405.09365v4
- SARDet-100K (NeurIPS 2024): 10 existing SAR detection datasets standardised into ~117k images / ~246k instances / 6 classes; MSFA (Multi-Stage with Filter Augmentation) pretraining bridges RGB-to-SAR. Code at github.com/zcablii/SARDet_100K. A leaderboard snippet lists Faster R-CNN + ConvNeXt-T at 54.8 box mAP (marked unverified). [SEARCH-ONLY] https://proceedings.neurips.cc/paper_files/paper/2024/hash/e7eb8128eb26eafbe901348df1dbacdc-Abstract.html
- Ultrasound (acoustic analogue): EchoCare (arXiv 2509.11752) self-supervised on 4.5M images from 23+ countries, multi-centre/multi-device, 10 benchmarks, code and weights public; USFM (arXiv 2401.00153) on >2M multi-organ/multi-device images with spatial-frequency dual masked image modelling. A search summary notes the multi-device claims rest on data diversity, not on a tested unseen-scanner protocol. [SEARCH-ONLY] https://arxiv.org/abs/2509.11752 ; https://arxiv.org/abs/2401.00153
- Sonar-specific, multi-device: Syn2Real (arXiv 2410.12953) trains/evaluates mine-like object segmentation across several side-scan systems (Starfish 450 kHz on ROV; Sea Scan ARC Scout MkII at 600 and 1200 kHz on AUV) using diffusion-generated synthetic data; focus is synthetic-to-real, not metadata conditioning. [SEARCH-ONLY] https://arxiv.org/abs/2410.12953v1
- Mine-JEPA (CVPR 2026 per a listing): in-domain SSL with SIGReg on only 1,170 unlabelled side-scan images; ViT-Tiny backbone; binary F1 0.935 vs 0.922 for fine-tuned DINOv3 (pretrained on 1.7B images). The authors also report that applying in-domain SSL to existing foundation models DEGRADES performance by 10-13 percentage points. Single sensor, classification only. [SEARCH-ONLY] https://arxiv.org/abs/2604.00383
- BenthicDINO (arXiv 2608.23215, Hamoda, Rajani, Gracias; v1 24 Aug 2026, v2 16 Oct 2026): ConvNeXt-v2 Tiny; DINOv3-style loss (L_DINO + L_iBOT + 0.5 L_Gram + 0.1 L_KoLeo) plus 0.3 x HSIC penalty making features independent of incidence angle and slant range; 224 px global / 96 px local crops from 768x768 tiles (75% overlap) with cross-track distance encodings; 2 x Quadro RTX 6000, effective batch 8192, 100 epochs, LR 1.41e-4 (GPU-hours not reported). Physics-guided augmentations: additive Gaussian "speckle" sigma~U(0.01,0.05), synthetic TVG linear range decay with far-edge retention 0.3-0.7, contrast/brightness jitter. AI4Shipwrecks frozen-encoder result: IoU_ship 0.423, F1 0.553, 2nd of 7; deep sites (>40 m) 0.651 vs shallow (<40 m) 0.280; authors blame pretraining coverage (no man-made structures in pretraining). No code/weights link was visible. Invariance is only measured on augmented views, not across sensors; effective feature rank 53.8 of 768. [READ] https://arxiv.org/html/2608.23215 (last ~11.7k chars truncated)

### Inferences
- Nothing in the literature shows that a wavelength-style hypernetwork transfers to a sonar sensor that was not in pretraining. Sonar has no "spectral bands"; the sensor differences are frequency, beam geometry, resolution, range/TVG processing, and platform. So the DOFA idea must be adapted (see section 2) and the unseen-sensor claim must be tested by us, not assumed.
- The compute scale of published any-sensor models (500 to ~600 A100/L40-class GPU-hours when starting from DINOv2, per DOFA+ and Copernicus-FM) is within reach of a student team only if the training set is small (hundreds of thousands of tiles) and the backbone is ViT-B or smaller.
- SAR evidence says in-domain gradient-style SSL targets beat generic HOG-like ones for speckled coherent imagery (SARATR-X Table V); sonar is similarly speckled, so a sonar-specific masked-prediction target is plausible (inference, untested).

### Gaps
- I did not research or verify Galileo, AnySat, SkySense / SkySense-O, Prithvi, CROMA, SpectralGPT, SMARTIES, TerraMind, BiomedParse or MedSAM2 in this session; no claims are made about them. A follow-up pass should at least read SMARTIES (spectrum-agnostic projection) and AnySat (scale-adaptive tokens) because they address resolution/GSD conditioning.
- No data on how well any of these generalise to a physically new sensor class (all "unseen sensor" results are within optical/SAR EO).
- Total GPU-hours for Panopticon and DOFA (non-plus) are not reported.
- Licences for DOFA, Panopticon, Copernicus-FM, SARATR-X weights are not stated in the pages I read; check each repo's LICENSE before any reuse.

---

## 2. Conditioning a sonar model on sensor metadata

### Takeaway
Three mechanisms have precedent in the EO papers I read: (a) a hypernetwork that generates patch-embedding weights from per-channel descriptors (DOFA, Copernicus-FM), (b) channel-attention patch embedding with descriptor-based positional encodings (Panopticon), and (c) Fourier-encoded scalar metadata added to tokens with a learned "missing" token and heavy metadata dropout (Copernicus-FM). For sonar, which is single-channel with scalar sensor properties, (c) plus FiLM-style modulation is the most direct, and (a) is only worth it if you want to feed multi-channel inputs (e.g. low/high frequency, or amplitude + bathymetry).

### Cited Findings
- Scalar metadata as additive Fourier-encoded tokens with learnable missing-value tokens and drop probability 0.7: Copernicus-FM. [READ] https://arxiv.org/html/2503.11849
- Resolution as metadata: Copernicus-FM derives patch AREA from GSD x patch size and encodes it, i.e. the model is told the physical footprint of each token. [READ] https://arxiv.org/html/2503.11849
- Per-channel descriptor to patch-embedding weights (hypernetwork): DOFA (wavelength) and Copernicus-FM (wavelength + bandwidth). [READ] https://arxiv.org/html/2403.15356v3 ; https://arxiv.org/html/2503.11849
- Descriptor-based positional encoding in key/value of a channel cross-attention; SAR handled with learned categorical embeddings (orbit x polarisation, 12 combos); coarse categorical embedding was nearly as good as fine for SAR. [READ] https://arxiv.org/html/2503.10845v2
- Physics-aware invariance for side-scan: BenthicDINO encodes cross-track distance with tiles and penalises dependence of features on incidence angle and slant range via HSIC (gamma = 0.3); requires recorded navigation data. [READ] https://arxiv.org/html/2608.23215
- FiLM (Perez et al., 2018, arXiv 1709.07871) is the standard feature-wise affine conditioning method. [FROM-MEMORY, NOT FETCHED] https://arxiv.org/abs/1709.07871

### Inferences (my proposal, not tested anywhere I found)
- Metadata vector m per tile: log10 frequency (kHz), log beamwidth along/across, native along-track and across-track pixel size in metres (and the tile's physical footprint = pixel size x tile px), max range, altitude/height above seabed and derived grazing angle (per-column, for side-scan), sensor-type one-hot (SSS, SAS, MBES backscatter, FLS/imaging, 3D), whether TVG/beam-pattern correction was applied. Encode scalars with Fourier features; embed categoricals; pass through an MLP to a vector z_s.
- Use z_s in two places: (1) a "sensor token" appended to the ViT sequence (Copernicus-FM-like), and (2) FiLM scale/shift on the output of each Nth transformer block or on a lightweight conv stem. Apply metadata dropout (~50-70% as in Copernicus-FM) and a learned "unknown" token so the model works when metadata is missing and so it cannot rely on a metadata shortcut.
- Resolution normalisation first, conditioning second: resample every sensor to a common physical pixel size (e.g. fix metres/pixel by range-aware resampling) where the sensor allows, and give the residual native resolution as metadata. SAS is far finer than SSS, so downsampling SAS throws away its advantage; a better option is to keep a small set of scale buckets (e.g. 2 to 3 pixel sizes) and let the area encoding tell the model which one.
- Do not make the model invariant to sensor type for the trust layer: the calibration map (score to probability) must stay per-sensor. Invariance (HSIC-style) is for the representation; calibration is downstream.
- Use geometry-aware positions: add a per-column slant-range/grazing-angle channel or encoding for side-scan (BenthicDINO's cross-track distance idea), and a range/azimuth-coordinate encoding for FLS/multibeam polar images.

### Gaps
- No sonar paper found that uses DOFA/FiLM/metadata tokens; all of the above is extrapolated from EO.
- No evidence on whether coarse sensor-type tokens suffice (as for SAR in Panopticon) or whether frequency/beam parameters are needed; must be settled by ablation in our own data.
- FiLM source not opened this session.

---

## 3. Training recipe: backbone, objective, data mixing, augmentation, budget, licences

### Takeaway
Start from a permissively licensed DINOv2 ViT-S/B (Apache-2.0 per a developer issue; verify in the repo) rather than DINOv3, because the DINOv3 licence is custom and contains a prohibited-use clause covering "military or warfare purposes" and espionage, which is a real risk for a sonar/mine-countermeasure-adjacent product. Do continued, metadata-conditioned self-supervised training with feature distillation from the frozen DINOv2 teacher (the DOFA+ recipe), keep the model small (ViT-S/B or ConvNeXt-v2-T), and use sonar-aware augmentations.

### Cited Findings
- DINOv3 licence (dated 14 Aug 2025): custom Meta licence, royalty-free limited licence to use, reproduce, distribute, modify. Requires copying the agreement and "Built with DINOv3" display when distributing materials/derivatives; Section 1(b)(v) forbids ITAR-covered activities and "prohibited end uses", reported as including uses "related to military or warfare purposes, nuclear industries or applications, espionage" and the development/use of guns or illegal weapons; requires a statement that you are not a trade-controls target; indemnification of Meta; Meta can terminate for breach; terms can be modified by Meta. The licence page itself does not expressly bar commercial use. [READ, via fetch summariser; quotes should be re-checked against the original text] https://ai.meta.com/resources/models-and-libraries/dinov3-license
- A DINOv3 GitHub issue says the custom licence "seems to allow commercial applications" but needs legal review, and states that DINO, DINOv2 and SAM are Apache-2.0. [SEARCH-ONLY] https://github.com/facebookresearch/dinov3/issues/31
- A non-Meta site (dinov3.pages.dev) claims a CC BY-NC 4.0 licence; this contradicts Meta's own page and should be disregarded. [SEARCH-ONLY] https://dinov3.pages.dev/privacy-policy
- SAM 2: checkpoints, demo and training code are Apache-2.0 (a BSD-3-Clause licence file also exists and the page does not say which component it covers; a cc_torch component has its own licence). SAM 2.1 sizes: Tiny 38.9M, Small 46M, Base+ 80.8M, Large 224.4M params. [READ] https://github.com/facebookresearch/sam2
- SonarSAM ("When SAM Meets Sonar Images", arXiv 2306.14109): SAM zero-shot degrades sharply on forward-looking sonar; LoRA and visual prompt tuning compared; repo supports MobileSAM backbone fine-tuning. Repo licence NOT checked. [SEARCH-ONLY] https://arxiv.org/abs/2306.14109 ; https://github.com/wangsssky/SonarSAM . A 2025 IEEE GRSL paper (Li et al.) proposes a different SAM adaptation for FLS. [SEARCH-ONLY] https://pure.nwpu.edu.cn/en/publications/fine-tuning-sam-for-forward-looking-sonar-with-collaborative-prom/
- Published budgets (recap): DOFA+ 8 x L40 ~3 days; Copernicus-FM 512 A100 GPU-hours/run; Panopticon 16 x A100 (hours not reported); SARATR-X 8 x RTX 3090, 200 epochs, 0.18M samples; BenthicDINO 2 x RTX 6000, 100 epochs, ~1M tiles; Mine-JEPA ViT-Tiny on 1,170 images. [READ / SEARCH-ONLY as tagged in section 1]
- Objective choices evidenced in sonar/SAR: DINOv3-style self-distillation with Gram and KoLeo terms (BenthicDINO, side-scan) [READ]; JEPA/SIGReg (Mine-JEPA, side-scan, tiny data) [SEARCH-ONLY]; masked prediction of multi-scale gradient features (SARATR-X, SAR) [READ]. Mine-JEPA reports in-domain SSL applied on top of big foundation models hurt by 10-13 pp [SEARCH-ONLY], which is a warning against naive continued pretraining on tiny sets.
- Ultralytics YOLO is dual-licensed AGPL-3.0 or a paid Enterprise licence; the page does not say which licence covers weights. [READ] https://github.com/ultralytics/ultralytics

### Inferences (proposed recipe, not a published result)
- Backbone: DINOv2 ViT-S/14 or ViT-B/14 (Apache-2.0 to be verified in the repo) or ConvNeXt-v2-T (BenthicDINO's choice). Keep the DINOv3 route as optional only after legal review of the military clause. SigLIP and MAE were not researched; no claim made.
- Objective: DOFA+-style combination: masked image modelling with a sonar-aware target (gradient/multi-scale magnitude à la SARATR-X, computed on log-intensity) + cosine feature distillation from frozen DINOv2 on a few intermediate layers (anchors the representation so small data does not collapse it, consistent with Mine-JEPA's warning). Optionally add a DINO-style multi-crop loss across sensors/frequencies of the same seabed patch if you have overlapping multi-frequency coverage (analogue of Panopticon's "same location across sensors as natural augmentation").
- Data mixing: sample sensors with temperature-flattened weights (e.g. p_s proportional to n_s^0.5) so rare sensors (SAS, 3D) are not drowned out by side-scan; always hold out at least one full sensor and one full site for evaluation (section 6).
- Augmentations: multiplicative (gamma-distributed) speckle rather than only additive Gaussian (BenthicDINO used additive; multiplicative is my suggestion, matching coherent imaging), synthetic TVG gain curves and beam-pattern roll-off (BenthicDINO used linear decay), range-dependent blur/resolution loss, random across-track stretch to emulate slant-range vs ground-range processing, along/across-track anisotropic downsampling to emulate other sensors' pixel sizes, dropout of "ping" lines, nadir-gap masking, intensity-clipping/dynamic-range changes, shadow-preserving flips only if the geometry allows (side-scan flips swap port/starboard; do not flip along range).
- Budget estimate (inference from published runs, not measured): ViT-S/B continued pretraining on ~0.3M to 1M tiles at 224 px for ~100 epochs is of the order of 100 to 600 A100 GPU-hours. That is ~4 to 25 days on a single A100 or roughly 2 to 12 days on a single H100 if the throughput assumptions hold; plan a pilot of 5-10% of the data first to measure it. Tiles of 224 px mean memory is modest; BenthicDINO fit batch 4,096 per GPU on 48 GB-class cards with ConvNeXt-v2-T at 224/96 px crops.
- Distillation from a large teacher into a ViT-S student is the safest route for CPU/edge deployment.

### Gaps
- DINOv2 licence and weights licence not directly opened; relied on a GitHub-issue snippet. SigLIP, MAE and ConvNeXt-v2 licences not checked (ConvNeXt-v2 code licence commonly CC-BY-NC in the original repo [FROM-MEMORY, NOT FETCHED]; if so, pretrained weights from that repo may be non-commercial; verify before use, and check timm re-releases).
- The DINOv3 military clause: I only have a summariser's paraphrase of the clause; the team's legal reviewer must read Section 1(b)(v) in full and decide whether "mine-like object" or defence-adjacent customers trigger it.
- No public numbers on GPU-hours for any sonar SSL model.
- SonarSAM repo licence not checked.

---

## 4. Detection heads with permissive licences

### Takeaway
D-FINE / DEIM (Apache-2.0) and RF-DETR (Apache-2.0 for Nano to Large only) are the best-documented permissive options; Ultralytics YOLO is AGPL-3.0 or paid. No source I read gives small-object AP or CPU benchmarks for any of them, so "best for small objects in noisy sonar" is untested and needs your own benchmark.

### Cited Findings
- RF-DETR: Apache-2.0 for the package and Nano/Small/Medium/Large detection plus all seg sizes; Atto/Femto/Pico/XL/2XL and NAS models are under the Roboflow Platform Model License (PML 1.0), where commercial self-hosting needs an Enterprise add-on. DINOv2 backbone (Atto-Pico use PE-Core-T). COCO AP50:95 on T4/TensorRT FP16: Nano 48.4 (30.5M params, 2.3 ms), Small 53.0 (3.5 ms), Medium 54.7 (4.4 ms), Large 56.5 (6.8 ms). No small-object or ONNX/CPU numbers on the page. [READ] https://github.com/roboflow/rf-detr
- D-FINE: Apache-2.0 repo; COCO AP: N 42.8 (4M params, 2.12 ms), S 48.5 (10M, 3.49 ms), M 52.3 (19M, 5.62 ms), L 54.0 (31M, 8.07 ms), X 55.8 (62M, 12.89 ms), T4 TensorRT 10.4 FP16. Checkpoints trained on Objects365 (`*_obj365`, `*_obj2coco`) may be subject to Objects365 terms and should not be assumed commercially cleared. ONNX/TensorRT export steps provided; no CPU or small-object benchmarks. [READ] https://github.com/Peterande/D-FINE
- DEIM (CVPR 2025): Apache-2.0 per README badge; DEIM-D-FINE AP N 43.0 / S 49.0 / M 52.7 / L 54.7 / X 56.5; DEIM-RT-DETRv2 S 49.0 / M 50.9 / M* 53.2 / L 54.3 / X 55.5. Authors claim ~50% training-time reduction with RT-DETR and D-FINE. DEIMv2 (released 26 Sep 2025) has eight sizes X to Atto; S/M/L/X use DINOv3 features (distilled or pretrained) per the README, so DEIMv2 may inherit DINOv3 licence terms (inference, check). Atto 23.8 COCO AP at 320x320, 0.49M params. No small-object metrics. [READ] https://github.com/Intellindust-AI-Lab/DEIM ; paper [SEARCH-ONLY] https://arxiv.org/html/2412.04234v3
- Ultralytics YOLO: AGPL-3.0 or Ultralytics Enterprise License; weights licence not specified on the page. [READ] https://github.com/ultralytics/ultralytics
- SAR detection precedent: Faster R-CNN with ConvNeXt-T plus MSFA pretraining and SARATR-X-pretrained HiViT-B detectors set SARDet-100K results (57.3 mAP for SARATR-X). [READ/SEARCH-ONLY as in section 1]

### Inferences
- For a shared SSL backbone, the practical path is an RT-DETR/D-FINE-style or plain Faster R-CNN/ViTDet head on top of it; the head should be small and per-task-fine-tunable, with the backbone frozen or low-LR.
- For CPU/edge, D-FINE-N/S or DEIM-N/S (4M/10M params, ONNX export documented) are the realistic candidates. Test on your own CPU with ONNX Runtime; no published CPU number exists in the sources I read.
- Small objects in noisy imagery: DETR-family decoders are known to need more care on tiny targets; plan tiling (e.g. 640 px with overlap) and a P2/stride-4 feature level, and measure AP_small on your own data. Untested here.
- Avoid Ultralytics unless you buy the Enterprise licence or release under AGPL.

### Gaps
- RT-DETRv2 repo licence and Co-DETR, YOLOX licences were not opened (Apache for RT-DETR/YOLOX is common knowledge [FROM-MEMORY, NOT FETCHED]).
- No sonar-specific head comparison found.

---

## 5. Out-of-distribution / applicability detection

### Takeaway
Use embedding-space kNN (preferred) and Mahalanobis scores, plus a two-sample shift test (MMD/KS) between a new survey's embeddings and each sensor's reference set, to decide whether to emit a calibrated probability or an "outside validated domain" flag. But recent evidence says these scores can be insensitive to domain shift when the features come from a model trained on a single domain, so the embedding must come from a broad (multi-sensor or distilled-from-foundation) encoder, and the flag must be validated with leave-one-sensor-out tests.

### Cited Findings
- Teacher-Guided Training paper (arXiv 2603.11269, March 2026, RIT): supervised single-domain training collapses features into a low-rank class subspace ("Domain-Sensitivity Collapse"), making MDS and kNN insensitive to domain shift; fix is to distil residual domain-sensitive signal from a frozen DINOv2 ViT-S/14 teacher via an auxiliary head. Eight single-domain benchmarks (incl. histopathology, EuroSAT satellite). ResNet-50 averages: out-of-domain FPR@95 MDS 25.55% to 13.94%, ViM 26.43% to 15.65%, kNN 34.98% to 20.06%; in-domain FPR@95 stays high for all methods; gains on DINOv2 backbones are small. Code "upon acceptance", not yet released. [READ] https://arxiv.org/html/2603.11269
- Medical OOD: a 2024 survey says Mahalanobis does well on contextual (covariate) shift but poorly on semantic shift and drops sharply on chest X-rays in one comparison; a MELBA 2024 paper found kNN improved scalability and performance over Mahalanobis on liver-segmentation bottleneck features, suggesting the Gaussian assumption fails. [SEARCH-ONLY] https://arxiv.org/pdf/2404.18279 ; https://arxiv.org/html/2408.02761v3
- Remote sensing: a 2023 benchmark paper for scene classification reports kNN-based OOD beating a max-softmax baseline. [SEARCH-ONLY] https://www.arxiv.org/pdf/2303.16616 (the search summary did not confirm this URL matches that paper; verify)
- Feature L2-normalisation substantially improves post-hoc Mahalanobis across 44 models (ICML 2025). [SEARCH-ONLY] https://icml.cc/virtual/2025/poster/43649
- Sonar-specific OOD / sensor-shift detection: I found none. [SEARCH-ONLY for the absence claim, one query run]

### Inferences
- Concrete design: per sensor-and-site "reference bank" of L2-normalised embeddings (tile-level and object-level); at inference compute (i) kNN distance to the reference bank of the claimed sensor (k~10, with the 95th percentile of validation distances as threshold), (ii) Mahalanobis on the same, (iii) a survey-level MMD/KS test on a 1-D projection (e.g. first PCs, or kNN distances), (iv) a metadata-range check (frequency, resolution, range outside training convex hull). Refuse or down-grade calibrated probabilities when any triggers; show the reason.
- Because Mahalanobis/kNN can be blind to shift in collapsed features, evaluate the flag directly: hold out a sensor, and measure AUROC / FPR@95 for "held-out sensor vs in-distribution" and also whether detection precision/calibration really degrade on flagged surveys (the flag is only useful if it predicts failure).
- Use conformal or per-sensor temperature/isotonic calibration on a held-out calibration set; the calibration maps stay sensor-specific even with a shared backbone.

### Gaps
- No evidence of any OOD method validated on sonar; the above is transplanted from medical/remote-sensing work.
- I did not read the survey or the MELBA paper in full.

---

## 6. Honest evaluation protocol

### Takeaway
A shared model should be accepted only if it beats separate per-sensor models on held-out sensors/sites with paired statistics, while not losing on in-sensor performance. The EO and ultrasound papers I read do not run this protocol (SARATR-X has no cross-sensor ablation; ultrasound claims rest on data diversity; BenthicDINO measures invariance only on augmented views), so this is a gap you can fill.

### Cited Findings
- Evidence that existing protocols are weak: SARATR-X no dedicated cross-sensor/cross-resolution ablation [READ] https://arxiv.org/html/2405.09365v5 ; BenthicDINO invariance tested only on augmented views, single run, no seeds/variance reported, no controlled cross-sensor test [READ] https://arxiv.org/html/2608.23215 ; multi-device ultrasound claims rest on dataset diversity [SEARCH-ONLY] https://arxiv.org/abs/2509.11752
- Panopticon's design for the unseen-sensor claim: simulated and OOD sensor configurations plus spectral subsampling variance. [READ] https://arxiv.org/html/2503.10845v2
- AI4Shipwrecks is a public EdgeTech 2205 CHIRP side-scan benchmark that can serve as a held-out sensor/site test; BenthicDINO reports a site-depth breakdown (deep vs shallow). [READ] https://arxiv.org/html/2608.23215

### Inferences (proposed protocol)
- Splits: (1) leave-one-sensor-out (LOSO) across sensor families (hold out e.g. a whole brand/frequency or SAS), (2) leave-one-site-out (LOSiO) within each sensor, with site = geographic survey area, (3) leave-one-platform-out where possible. No tile or overlapping-swath leakage across splits (use geographic blocks, not random tiles; BenthicDINO's 75% overlap tiles would leak).
- Arms: (A) per-sensor model trained only on that sensor; (B) pooled model with no metadata; (C) shared sensor-conditioned model; (D) shared model + brief per-sensor fine-tune (few-shot: 1%, 5%, 10% labels). Same backbone size, head, schedule and augmentation budget for all arms.
- Metrics: object-level detection AP50 and AP_small, recall at fixed false alarms per km^2 (the operational metric), Pd vs range curves, calibration (ECE, Brier, reliability diagrams) before and after per-sensor recalibration, sharpness, and selective prediction (AURC / risk-coverage with OOD refusal). Sample efficiency curves (label fraction vs score).
- Statistics: at least 3 seeds, bootstrap CIs over surveys (not tiles), paired differences vs the per-sensor arm, report worst-sensor performance, not just the mean.
- Go/no-go for the shared model: see section 7.

### Gaps
- No existing sonar benchmark covers multiple sensor families with consistent labels; the team will have to assemble one (data availability not researched here).

---

## 7. Recommended architecture and staged recipe

### Takeaway
Do Stage A first (per-sensor detectors, shared sensor-agnostic trust layer with per-sensor calibration and an OOD gate), collect the LOSO/LOSiO evaluation harness there, then attempt Stage B (one sensor-conditioned backbone) only if a pre-registered go/no-go test passes. The literature does not yet show that a shared sonar backbone beats per-sensor models, so Stage B is a research bet, not a known recipe.

### Cited Findings
- Small in-domain SSL can match large foundation models on one sensor (Mine-JEPA, ViT-Tiny, 1,170 images, F1 0.935 vs 0.922 for fine-tuned DINOv3) [SEARCH-ONLY] https://arxiv.org/abs/2604.00383 , which favours cheap per-sensor models as the Stage A baseline.
- Shared any-sensor backbones in EO need ~0.4M to 18.7M images and 500 to ~600+ GPU-hours when initialised from DINOv2/pretrained (DOFA+, Copernicus-FM, Panopticon) [READ] section 1 URLs.
- Single-sensor sonar SSL showed weak transfer to a shallow-water sensor/site (AI4Shipwrecks shallow sites 0.280 IoU vs deep 0.651) attributed to pretraining coverage [READ] https://arxiv.org/html/2608.23215

### Inferences (recommendation)
Stage A (weeks 0 to ~8): per-sensor detector (D-FINE-S or DEIM-S, Apache-2.0; DINOv2-ViT-S or ConvNeXt-v2-T backbone, license-checked), per-sensor Mine-JEPA/BenthicDINO-style SSL on whatever unlabelled tiles exist, shared trust layer code (score fusion, per-sensor isotonic/temperature calibration on held-out surveys, kNN+Mahalanobis OOD gate, Pd map). Build the LOSO/LOSiO harness and the reference embedding banks. Output: per-sensor numbers = the baseline Stage B must beat.

Stage B (only after A): shared backbone, ViT-S/B from DINOv2, patch stem with metadata tokens + FiLM (section 2), continued SSL with sonar-aware MIM + DINOv2 feature distillation, temperature-flattened sensor sampling, sonar augmentations (section 3). Detection head and trust layer reused from A with per-sensor calibration retained. Compute: pilot on 5-10% data; full run budget of the order of 100-600 A100-class GPU-hours (estimate).

Go/no-go (suggested thresholds, to be pre-registered; my proposal):
- GO if, over >=3 seeds and bootstrap over surveys: (1) on held-out sensors with 5-10% labels, arm D (shared + few-shot) beats arm A by a statistically significant margin on AP50 and recall at fixed false-alarm rate, OR matches it with >=5x fewer labels; (2) on in-sensor test sets, shared model is within a small tolerance (e.g. <=1 AP point) of per-sensor models for EVERY sensor, not only on average; (3) calibration (ECE) after per-sensor recalibration is no worse; (4) the OOD gate achieves a pre-agreed AUROC for held-out-sensor detection and flagged surveys have measurably worse precision.
- NO-GO (stay with Stage A and share only the trust layer) if the shared model only wins on the sensor with the most data, loses on any rare sensor (SAS/3D), or if the OOD gate cannot separate held-out sensors.
- Licence gates before Stage B: confirm Apache-2.0 on the backbone weights actually used; avoid DINOv3/DEIMv2-DINOv3 variants unless legal review clears the military/espionage clause; avoid Objects365-derived detector checkpoints; avoid Ultralytics unless licensed.

### Gaps
- Thresholds above are my suggestions, not from the literature.
- Data availability per sensor family for the team is unknown; Stage B feasibility depends on it.
- Items not covered: SMARTIES, Galileo, AnySat, TerraMind, SkySense, BiomedParse, MedSAM2 specifics; multibeam backscatter and 3D sonar foundation-model literature (no search run); IEEE JOE / OCEANS sources (not searched).
