# NetSight Step 1 - dataset detail research

Researched 2026-11-06. Sources: Zenodo REST API (`https://zenodo.org/api/records/<id>`), HTTP Range reads of zip central directories (no bulk download; Zenodo and Bath servers honour `Range`), Hugging Face API + rendered dataset card, GitHub API, Bath EPrints page, data.gov.uk CKAN API, arXiv paper.
Status tags: VERIFIED = read directly from API/page this session. UNVERIFIED = not read, or inferred.

Summary of risks:
- GhostVision (2): licence CONFLICT. Zenodo metadata = CC BY-SA 4.0; HF YAML = cc-by-sa-4.0; HF card body says "released under the GPL license". Treat as conditional/unconfirmed until the authors clarify.
- Bath (5): images are UNLABELLED (README: "the full set of labelled data has been lost"). Only useful for pretraining / unlabelled calibration.
- DFKI UXO (6): imaging sonar (ARIS Explorer 3000), not side-scan. Different modality.
- JNCC/Cefas (7): CKAN record has no file. Only a generic HTML link `http://jncc.defra.gov.uk/opendata`. Direct file route NOT found.
- AI4Shipwrecks (8): licence not visible (Deep Blue returns 403 to scripted fetch; paper names no licence). Research-only until confirmed.
- Catalan (4): no smaller subset; 3-part split zip, 52.25 GB total.

---

## 1. Bodine - Sidescan Sonar Substrate, Depth, and Shadow Image-Label-Pairs
- Title (VERIFIED): "Sidescan Sonar Substrate, Depth, and Shadow Image-Label-Pairs"
- Record: Zenodo 10119320, DOI 10.5281/zenodo.10119320 (concept 10.5281/zenodo.10119319). Published 2023-11-13. Creator: Bodine, Cameron S.
- Licence (VERIFIED, API): `cc-by-4.0`, access open. Description page text carries no extra licence statement. No conflict found.
- Related: derived from Doodler (github Doodleverse/dash_doodler) and makesense.ai; supplement to 10.5281/zenodo.10120054; source of 10.5281/zenodo.10093642 (the trained models).
- Files (VERIFIED, single file):
  - `PINGMapperv2.0_SegmentationModelsv1.0_ImageLabelPairs.zip` 13,769,924,043 bytes, md5 `ecb454c2f1526bd3bfef6e6a6dc375d1`
  - URL: https://zenodo.org/api/records/10119320/files/PINGMapperv2.0_SegmentationModelsv1.0_ImageLabelPairs.zip/content
- Zip layout (VERIFIED via Range read of central directory, 31,026 entries, 31,014 PNG, 13.77 GB uncompressed):
  - `Bedpick_ImgLblPairs/images` (6,488) + `Bedpick_ImgLblPairs/masks` (6,488; names end `_mask.png`)
  - `Shadow_ImgLblPairs/images` (3,533) + `labels` (3,533)
  - `Raw_Substrate_ImgLblPairs/images` (2,748) + `labels` (2,748)
  - `EGN_Substrate_ImgLblPairs/images` (2,738) + `labels` (2,738)  (EGN = empirical gain normalised)
- Format (VERIFIED samples): 8-bit greyscale PNG images, 500 px wide, variable height (e.g. 500x1301, 500x1256; bedpick crops 1020x500). Labels are 8-bit single-channel PNG masks (class index = pixel value; the pixel-value-to-class mapping was NOT read: UNVERIFIED, see PINGMapper / Doodleverse docs).
- Count: 12,000 image-label pairs across the 4 sub-sets excluding bedpick duplicates is not stated; the listed per-folder counts above are exact.
- Sensor: Humminbird Solix (file names `Solix_USM1`), consumer side-scan (VERIFIED from file names; frequency not stated in record - UNVERIFIED). Area: Louisiana/Mississippi-style river names (BougeChitto, LEA_163...) - UNVERIFIED; record has no geography.
- Commercial limits: none visible. Attribution required (CC BY).
- Internal layout readable without download: YES (zip central directory via Range request).

## 2. GhostVision derelict crab pot dataset and models
- Title (VERIFIED): "Derelict Crab Pot Object Detection Dataset and Models for GhostVision v1.0.0" (title starts with a crab emoji). Zenodo 20056679, DOI 10.5281/zenodo.20056679 (concept 10.5281/zenodo.20056678). Published 2026-05-06. Creators Bodine, Baxevani, Abbasi, Wierzbicki, Christoph, Hughes. Paper: Bodine et al. 2026, J. Marine Science and Engineering 14(10):951, doi 10.3390/jmse14100951.
- Licence: Zenodo API `cc-by-sa-4.0` (VERIFIED). HF repo YAML `license: cc-by-sa-4.0` and HF licence badge cc-by-sa-4.0 (VERIFIED). HF card body "License" section says "This dataset is released under the GPL license." (VERIFIED). CONFLICT. Models also on HF (gv-rf-detr, gv-yolo12, gv-yolo26) - their licences NOT checked (YOLO/Ultralytics weights typically AGPL-3.0: UNVERIFIED).
- Files (Zenodo, VERIFIED, single file):
  - `GhostVision_DatasetAndModels.zip` 898,783,834 bytes, md5 `36872df7198d915e39db0d837f34655a`
  - URL: https://zenodo.org/api/records/20056679/files/GhostVision_DatasetAndModels.zip/content
- Zip layout (VERIFIED, 6,703 entries, 946.65 MB uncompressed):
  - `sss-crab-pot-detection-ds/{train(5,721 jpg+metadata.jsonl), valid(555), test(398)}` + `README.md`  => 6,674 JPEGs
  - `gv-rf-detr/`, `gv-yolo12/`, `gv-yolo26/`: each has `class_names.txt, environment.json, model.safetensors, model_type.json, README.md, weights.onnx`
- HF dataset `PINGEcosystem/sss-crab-pot-detection-ds` (VERIFIED): gated "auto" (login + accept needed for raw README/files; the rendered card and file list are public). 559 MB total. Splits identical to the zip: train 5,721 / valid 555 / test 398 images (file list: 5,722 / 556 / 399 incl. metadata.jsonl). Tag `imagefolder`, DOI 10.57967/hf/8397.
- Labels: JSONL per split (`metadata.jsonl`), one row per image: `{"file_name":..., "objects":{"bbox":[[x,y,w,h],...], "category":[...], "area":[...]}}`; bbox is pixel `[x,y,width,height]` (COCO-style); empty lists for negatives. Classes in the card: `Crab-Pot` (high confidence), `Maybe-Crab-Pot` (ambiguous). The model `class_names.txt` for yolo26 lists only `Crab-Pot` (so models were trained on one class).
- Image size (VERIFIED sample): 640x640 JPEG, ~58-118 KB each. File names are Roboflow exports (`..._png_jpg.rf.<hash>.jpg`), so train contains Roboflow augmentation duplicates of the same source image (leakage risk if split naively; use provided splits).
- Sensor: consumer-grade Humminbird side-scan. Area: Delaware Inland Bays (Rehoboth Bay near Dewey Beach, Indian River Bay, White Creek) and Delaware Bay. Frequency not stated (UNVERIFIED).
- Commercial limits: CC BY-SA 4.0 share-alike on adaptations (if it is CC BY-SA); GPL would be worse for redistribution of derivatives. Do not mix into a proprietary redistributed dataset until conflict resolved. Recommend emailing authors.
- Layout readable without download: YES (zip central directory; HF file list).

## 3. SubPipe
- Title (VERIFIED): "SubPipe: A Submarine Pipeline Inspection Dataset for Segmentation and Visual-inertial Localization". Zenodo 10808161, DOI 10.5281/zenodo.10808161 (concept 10.5281/zenodo.10053564). Published 2024-03-12.
- Licence (VERIFIED, API): `cc-by-4.0`. Record text requires reuse/publication to include this copyright text: "SubPipe is a public dataset of a submarine outfall pipeline, property of Oceanscan-MST. This dataset was acquired with a Light Autonomous Underwater Vehicle by Oceanscan-MST, within the scope of Challenge Camp 1 of the H2020 REMARO project." GitHub code GPL-3.0: NOT checked this session (UNVERIFIED).
- Files (VERIFIED):
  - `SubPipe.zip` 27,846,463,589 bytes, md5 `abf70702276c69c04c8774c7832f8550` (~80 GB unzipped; central directory Range read failed with IncompleteRead - layout not listed)
  - `SubPipeMini.zip` 5,907,533,517 bytes, md5 `8c63dac2e37dea0bbfda13fa6602b264` (~12 GB, camera/segmentation focus)
  - `SubPipeMini2.zip` 4,945,761,374 bytes, md5 `7e0d925f93a89bc0e8715e4f6f7caecb` (~16 GB, side-scan focus; USE THIS for sonar)
  - URLs: https://zenodo.org/api/records/10808161/files/<name>/content
- SubPipeMini2 layout (VERIFIED, 20,089 entries, 15.6 GB uncompressed): `SubPipeMiniSSS/config.yaml`; `DATA/*.csv` (Acceleration, Altitude, AngularVelocity, Depth, EstimatedState, ForwardDistance, Pressure, Rpm, Temperature); `DATA/SSS_LF_images/{Image (1,055 files), YOLO_Annotation (697 txt), COCO_Annotation (1 json)}`; `DATA/SSS_HF_images/{Image (1,011), YOLO_Annotation (671), COCO_Annotation (1)}`; `DATA/Cam0_images` (16,200), `DATA/Cam1_images` (430). (Counts include non-image sidecar files; Image folders hold the sonar images.)
- Labels: YOLO txt per image (`class xc yc w h` normalised, e.g. `0 0.7818 0.071 0.0356 0.138`) AND COCO json per frequency (per chunk). Object = pipeline (bounding boxes). Record totals: 10,030 SSS images (LF 5,000 at 2500x500; HF 5,030 at 5000x500), 6,335 annotations (LF 3,163, HF 3,172). One image ~ every 20 pings, ~1/s.
- Sensor (config.yaml, VERIFIED): Klein 3500 side-scan; LF 455 kHz, HF 900 kHz; Cam0 GoPro Hero 10, Cam1 grey-scale. Platform LAUV (OceanScan MST). Area: submarine outfall pipeline (Portugal, OceanScan) - region not stated in record (UNVERIFIED).
- Commercial limits: CC BY 4.0 with mandatory copyright notice above; pipeline is Oceanscan-MST property.

## 4. Catalan seafloor sediment side-scan patches (DeeperSense)
- Title (VERIFIED): "A Large Scale Side-Scan Sonar Dataset of Seafloor Sediments for Self-Supervised Pretraining". Zenodo 10209445, DOI 10.5281/zenodo.10209445 (concept 10.5281/zenodo.10209444). Published 2023-11-24. Creators Martinez-Clavel Valles, Rajani, Gracias, Garcia.
- Licence (VERIFIED): `cc-by-4.0`. No conflict.
- Files (VERIFIED) - a SPLIT ZIP; all three required, no smaller subset exists:
  - `sss_ssl_dataset_N713_384.z01` 21,474,836,480 B, md5 `6a41f1196f12c17491e28c7a84672194`
  - `sss_ssl_dataset_N713_384.z02` 21,474,836,480 B, md5 `0b90b20d98ef48e0eabf168d9071d193`
  - `sss_ssl_dataset_N713_384.zip` 9,302,423,575 B, md5 `1ba31d40f0cde4dc374a78378a88df99`
  - Total 52,251,696,535 B (~52.3 GB). URLs: https://zenodo.org/api/records/10209445/files/<name>/content. Must be re-joined (`zip -s 0 in.zip --out joined.zip` or 7-zip on the .zip with .z01/.z02 beside it).
- Format: 384x384 patches from 384-line waterfalls, 192 px overlap along- and across-track; 434,164 images (stated). Image file type (PNG/JPG) and internal folders NOT stated: UNVERIFIED. No labels (self-supervised pretraining set); the supervised companion set is in paper doi 10.1016/j.oceaneng.2023.115647.
- Sensor/area: collected by Tecnoambiente SL along the coast of Catalunya (H2020 DeeperSense, grant 101016958). Sonar model/frequency NOT stated (UNVERIFIED).
- Subset answer: NO. Workaround: Range-read individual entries from the final `.zip`? Not possible - a split zip's entries are spread over parts. Practical option: download the first part of `.z01` (Range) and extract only the first N entries with a tolerant tool - UNVERIFIED.
- Commercial limits: none beyond CC BY attribution.

## 5. University of Bath - sunken mannequin side-scan
- Title (VERIFIED): "Sidescan sonar images for training automated recognition of submerged body-like objects". Bath Research Data Archive id 1467, DOI 10.15125/BATH-01467, https://researchdata.bath.ac.uk/1467/ . Published 30 Oct 2024. Authors Rymansaib, Nga, Treloar, Hunter. Funder EPSRC EP/X030156/1.
- Licence (VERIFIED, page text on both data file and README): Creative Commons Attribution 4.0. Requests citation of two papers (doi 10.1002/rob.22164, doi 10.3390/rs16214036).
- Files (VERIFIED):
  - `sidescan_sonar_images_PRIME_CNN_training.zip` 6,165,203,835 B (Content-Length; HTTP 200, Accept-Ranges bytes). No checksum published (compute md5 after download). URL https://researchdata.bath.ac.uk/1467/1/sidescan_sonar_images_PRIME_CNN_training.zip
  - `README.txt` (1 kB) https://researchdata.bath.ac.uk/1467/2/README.txt
- Zip layout (VERIFIED via Range read, 3,544 entries, 6.69 GB uncompressed): `<site>/<date>/run<N>/{450,990,tracks,paths}/...`; sites include underfall_yard, bathampton_canal, dundas_aqueduct, minerva_bath_rowing_club. 3,056 PNG, 397 MAT (USV position data), 6 CSV (GPS waypoints), 1 JPG, 1 TXT.
- Format: PNG sonar images, dimensions appended to file name (e.g. `450_port_cond_1-15_00x2_68m.png`), "uncorrected and require rescaling" (paper Fig. 3). Sensors: Blueprint Subsea StarFish 450 (450 kHz) and StarFish 990 (990 kHz) side-scan on an autonomous USV. Only 990 kHz was used for CNN training; 450 included.
- LABELS: NONE. README: "Images are unlabelled with regards to the target / background class. Some directories contain a separate subdirectory named 'target'... Unfortunately, the full set of labelled data has been lost." (VERIFIED). Some smeared/warped images should be discarded.
- Area: Kennet and Avon Canal, Minerva Bath Rowing Club (Bath), Underfall Yard (Bristol); 5 Oct 2017 - 8 Apr 2022. Freshwater canal/harbour, not sea.
- Commercial limits: none (CC BY).

## 6. DFKI underwater UXO acoustic-optical dataset
- Title (VERIFIED): "An Acoustic and Optical Dataset for the Perception of Underwater Unexploded Ordnance (UXO)". Zenodo 13778485, DOI 10.5281/zenodo.13778485 (concept 10.5281/zenodo.11068045). Published 2024-09-23. Paper doi 10.1109/OCEANS55160.2024.10754316.
- Licence (VERIFIED, API): `bsd-3-clause`. Unusual for data but explicit; no conflict.
- Files (VERIFIED):
  - `data_export_recordings.7z` 16,658,054,765 B md5 `30c45956c0d034c27e3988711195c8c6` (main dataset)
  - `data_export_polar.7z` 16,487,715,574 B md5 `6e785ffd07bbab4f491794c2244df478` (polar-transformed sonar frames)
  - `data_processed.7z` 61,513,277,947 B md5 `2b9ef16c763a6964c608ed99a9cd1edb` (extracted/cut unmatched raw data)
  - `sample.7z` 1,732,018,855 B md5 `fcadef5fcc1a2cbdcc67812a5df732d7` (smallest real data - use this first)
  - `data_export_3dmodels.7z` 26,442,213 B md5 `4ed8820771bbb39819eacf66b50ff509`
  - `data_export_calibration.7z` 1,020 B md5 `bb7641890899bf424e3eeb242509f261`
  - `preview.jpg` 3,357,783 B md5 `963caf95ca23c40a878a86ff4b4f137d`; `setup_labeled.jpg` 321,484 B md5 `73d1a0f785aef0cf4646ab874d0c7674`; `teaser_uxo.png` 3,692,857 B md5 `1c6d744784e5b117754f4adabab5d214`
  - URLs: https://zenodo.org/api/records/13778485/files/<name>/content. Total ~96 GB.
- Content: ~100 recordings of 3 UXO types, >74,000 matched annotated imaging-sonar + camera frames, photogrammetric 3D models, pose/attitude data, controlled test tank. Sensor: ARIS Explorer 3000 imaging (forward-looking) sonar - NOT side-scan. Labels were generated on the SD camera frames; "multiply all coordinates by 3" for the included FHD images. Label file format (JSON? txt?) and internal layout NOT stated in record: UNVERIFIED. 7z archives: layout is not readable by simple Range requests (needs 7z header parse) - not attempted.
- Commercial limits: BSD-3 permits commercial use with notice. Domain (tank, imaging sonar) differs from SSS; use only as optional extra.

## 7. JNCC / Cefas raw sidescan sonar, Inner Dowsing, Race Bank, North Ridge cSAC + Haisborough, Hammond, Winterton cSAC
- Title (VERIFIED, CKAN): "Raw sidescan sonar data  from Inner Dowsing, Race Bank and North Ridge cSAC, and Haisborough, Hammond and Winterton cSAC" (CEND 11/11, Cefas Endeavour). data.gov.uk id 9e58988b-1ef6-4808-a629-fe4ffe27706a. https://data.gov.uk/dataset/9e58988b-1ef6-4808-a629-fe4ffe27706a/ ; CKAN API https://ckan.publishing.service.gov.uk/api/3/action/package_show?id=9e58988b-1ef6-4808-a629-fe4ffe27706a
- Licence (VERIFIED): `uk-ogl` (OGL v3). Access constraints "No limitations". Custodian JNCC. Metadata modified 2018-05-17. Bounding box lon 0.514-2.194, lat 52.764-53.424 (southern North Sea, off Lincolnshire/Norfolk).
- Download route: NOT FOUND. CKAN lists exactly one resource: "opendata", format HTML, url `http://jncc.defra.gov.uk/opendata` (which redirects to a generic JNCC open-data page, not the files). `https://data.jncc.gov.uk/data/<id>` returns 404. A sibling record (processed mosaics) offers `JNCC2011-06IDRBNR-HHWfinalacoustic-ss.zip` (ZIP; processed GeoTIFF mosaics, not raw) - from search snippet, UNVERIFIED.
- File format / size: UNVERIFIED (raw sidescan from Cefas surveys is normally XTF or similar; not confirmed). Next step: email data@jncc.gov.uk or check Cefas Data Hub / MEDIN / Defra DSP for the raw files.
- Commercial: OGL allows commercial use with attribution. Labels: none (raw acoustic only).

## 8. AI4Shipwrecks
- Title (VERIFIED): "Machine Learning for Shipwreck Segmentation from Side Scan Sonar Imagery: Dataset and Benchmark, AI4Shipwrecks Dataset". Deep Blue Data (U. Michigan) https://deepblue.lib.umich.edu/data/concern/data_sets/8623hz41x , DOI 10.7302/dmf4-x492. Paper: Sethuraman et al., IJRR 44(3):341-354 (2025), doi 10.1177/02783649241266853; arXiv 2401.14546. Project page https://umfieldrobotics.github.io/ai4shipwrecks/ (download page /download/).
- Licence: NOT VISIBLE. Deep Blue page returned HTTP 403 to scripted fetch (I did not try to bypass it). Search snippet confirms a "License" field exists but not its value. The paper calls the dataset "open-source" but names no licence. => UNVERIFIED, treat as research-only.
- Files: 3 files totalling 1.14 GB (from search snippet; names/sizes/checksums UNVERIFIED). Deep Blue direct downloads are at https://deepblue.lib.umich.edu/data/downloads/<id> (one id seen in results: 12579s883, meaning unconfirmed).
- Format (paper, VERIFIED): 286 side-scan images (161 contain wrecks, 28 distinct wrecks), exported PNG from EdgeTech Discover; 1,728 px wide, variable height (avg ~3,480). Cropped tiles 1,728x1,728, stride 100 => 2,539 train + 1,722 test tiles. Labels: binary per-pixel masks (0 other, 1 shipwreck), "standard binary mask format". 50/50 train/test split grouped by site.
- Sensor: EdgeTech 2205 dual-frequency (540/1610 kHz); released imagery from the low-frequency channel (centre 520 kHz, CHIRP 488.5-551.5 kHz). Platform Iver3 AUV. Area: NOAA Thunder Bay National Marine Sanctuary, Lake Huron, Michigan (surveys 2022-2023). Raw .JSF to be deposited at NOAA NCEI.
- Commercial: unknown until licence read manually in a browser.

## 9. NKSID (NanKai Sonar Image Dataset)
- Repo (VERIFIED): https://github.com/Jorwnpay/NK-Sonar-Image-Dataset , default branch `main`, last push 2024-04-11, size ~51 MB. Paper: Jiao, Zhang, Zhang, "Open-set recognition with long-tail sonar images", Expert Systems with Applications 2024, p.123495.
- Licence (VERIFIED): `LICENSE` file is MIT (Copyright (c) 2023 Wenpei Jiao); GitHub API reports `mit`. README states no separate data licence. Whether MIT legitimately covers the sonar images is an author claim - flag as unconfirmed for the data itself.
- Layout (VERIFIED via GitHub tree API; sizes in bytes): `NKSID/big_propeller.zip` 788,429; `cylinder.zip` 856,536; `fishing_net.zip` 500,009; `floats.zip` 8,384,673; `iron_pipeline.zip` 5,698,845; `small_propeller.zip` 233,740; `soft_pipeline.zip` 850,590; `tire/half batch from 1 to 400.zip` 17,641,118; `tire/half batch from 401 to 834.zip` 16,450,421; `kfold_train.txt` 479,400; `kfold_val.txt` 120,150; `train_abs.txt` 93,679; `img/data_info.png` 1,075,353. Total ~52 MB. Raw URL pattern: https://raw.githubusercontent.com/Jorwnpay/NK-Sonar-Image-Dataset/main/NKSID/<file> (URL-encode spaces in tire names). No md5 published (git blob SHAs only).
- Classes (8, from folder names): big_propeller, cylinder, fishing_net, floats, iron_pipeline, small_propeller, soft_pipeline, tire. 2,617 images, long-tailed.
- Labels: image-level classification, no boxes/masks. `train_abs.txt` lines are `<relative path> <label index>` (paths like `../data/NKSID/big_propeller/img_192.jpg`); `kfold_train.txt`/`kfold_val.txt` hold ten-fold splits as lines of sample indices (`#p0-k0` headers) pointing to line n of train_abs.txt. JPEG format; image size not read (UNVERIFIED).
- Sensor: Oculus M750d multibeam forward-looking sonar, 750 kHz and 1.2 MHz, ranges 2-15 m; ROV; Bohai Bay (39N 118E), targets hung on buoys. Not side-scan.
- Commercial: MIT on repo; confirm with authors.

---

## Proposed `datasets.yaml`

```yaml
# NetSight dataset manifest - generated 2026-11-06 from research (see datasets_detail.md)
# tier: commercial = permissive licence verified; conditional = share-alike/ambiguity/attribution notices;
#       research_only = licence unknown or restrictive. Never build commercial artefacts from research_only.
datasets:
  - id: bodine_substrate
    title: "Sidescan Sonar Substrate, Depth, and Shadow Image-Label-Pairs"
    source_url: https://zenodo.org/records/10119320
    doi: 10.5281/zenodo.10119320
    licence: CC-BY-4.0
    licence_status: verified
    commercial_use: "yes"
    tier: commercial
    files:
      - name: PINGMapperv2.0_SegmentationModelsv1.0_ImageLabelPairs.zip
        url: https://zenodo.org/api/records/10119320/files/PINGMapperv2.0_SegmentationModelsv1.0_ImageLabelPairs.zip/content
        size: 13769924043
        md5: ecb454c2f1526bd3bfef6e6a6dc375d1
    format: "8-bit greyscale PNG, 500 px wide, variable height; Humminbird Solix SSS"
    labels: "PNG index masks; folders Bedpick/Shadow/Raw_Substrate/EGN_Substrate x images + labels|masks (31,014 PNG); class-id mapping UNVERIFIED"
    notes: "Attribution required. Layout verified via zip central directory."

  - id: ghostvision_crabpot
    title: "Derelict Crab Pot Object Detection Dataset and Models for GhostVision v1.0.0"
    source_url: https://zenodo.org/records/20056679
    doi: 10.5281/zenodo.20056679
    licence: "CC-BY-SA-4.0 (Zenodo, HF metadata) vs GPL (HF card body)"
    licence_status: conflict
    commercial_use: conditional
    tier: conditional
    files:
      - name: GhostVision_DatasetAndModels.zip
        url: https://zenodo.org/api/records/20056679/files/GhostVision_DatasetAndModels.zip/content
        size: 898783834
        md5: 36872df7198d915e39db0d837f34655a
    format: "640x640 JPEG (Roboflow exports), Humminbird consumer SSS, Delaware bays; train 5721 / valid 555 / test 398"
    labels: "JSONL per split: file_name + objects{bbox [x,y,w,h] px, category, area}; classes Crab-Pot, Maybe-Crab-Pot"
    notes: "HF mirror PINGEcosystem/sss-crab-pot-detection-ds is auto-gated. Share-alike; resolve GPL conflict with authors. Roboflow augmentation duplicates inside train - use provided splits. Bundled models (rf-detr, yolo12, yolo26) licences unverified."

  - id: subpipe_mini2
    title: "SubPipe: A Submarine Pipeline Inspection Dataset (SubPipeMini2, side-scan part)"
    source_url: https://zenodo.org/records/10808161
    doi: 10.5281/zenodo.10808161
    licence: CC-BY-4.0
    licence_status: verified
    commercial_use: "yes"
    tier: commercial
    files:
      - name: SubPipeMini2.zip
        url: https://zenodo.org/api/records/10808161/files/SubPipeMini2.zip/content
        size: 4945761374
        md5: 7e0d925f93a89bc0e8715e4f6f7caecb
      - name: SubPipeMini.zip
        url: https://zenodo.org/api/records/10808161/files/SubPipeMini.zip/content
        size: 5907533517
        md5: 8c63dac2e37dea0bbfda13fa6602b264
      - name: SubPipe.zip
        url: https://zenodo.org/api/records/10808161/files/SubPipe.zip/content
        size: 27846463589
        md5: abf70702276c69c04c8774c7832f8550
    format: "Klein 3500 SSS images, LF 455 kHz 2500x500 (5000 imgs), HF 900 kHz 5000x500 (5030 imgs); JPEG; plus nav CSVs and camera images"
    labels: "YOLO txt per image (class xc yc w h normalised) + one COCO json per frequency; single object class (pipeline); 6335 boxes"
    notes: "Must reproduce Oceanscan-MST/REMARO copyright notice. Code repo GPL-3.0 (UNVERIFIED) - do not vendor code. Mini2 layout: SubPipeMiniSSS/DATA/SSS_{LF,HF}_images/{Image,YOLO_Annotation,COCO_Annotation}."

  - id: catalan_sss_ssl
    title: "A Large Scale Side-Scan Sonar Dataset of Seafloor Sediments for Self-Supervised Pretraining"
    source_url: https://zenodo.org/records/10209445
    doi: 10.5281/zenodo.10209445
    licence: CC-BY-4.0
    licence_status: verified
    commercial_use: "yes"
    tier: commercial
    files:
      - name: sss_ssl_dataset_N713_384.z01
        url: https://zenodo.org/api/records/10209445/files/sss_ssl_dataset_N713_384.z01/content
        size: 21474836480
        md5: 6a41f1196f12c17491e28c7a84672194
      - name: sss_ssl_dataset_N713_384.z02
        url: https://zenodo.org/api/records/10209445/files/sss_ssl_dataset_N713_384.z02/content
        size: 21474836480
        md5: 0b90b20d98ef48e0eabf168d9071d193
      - name: sss_ssl_dataset_N713_384.zip
        url: https://zenodo.org/api/records/10209445/files/sss_ssl_dataset_N713_384.zip/content
        size: 9302423575
        md5: 1ba31d40f0cde4dc374a78378a88df99
    format: "384x384 SSS patches (192 px overlap), 434,164 images; file type UNVERIFIED; split zip, all 3 parts needed"
    labels: "none (self-supervised pretraining)"
    notes: "No smaller subset. 52.25 GB total. Catalonia coast, Tecnoambiente SL, DeeperSense H2020. Sonar model/frequency unstated."

  - id: bath_mannequin
    title: "Sidescan sonar images for training automated recognition of submerged body-like objects"
    source_url: https://researchdata.bath.ac.uk/1467/
    doi: 10.15125/BATH-01467
    licence: CC-BY-4.0
    licence_status: verified
    commercial_use: "yes"
    tier: commercial
    files:
      - name: sidescan_sonar_images_PRIME_CNN_training.zip
        url: https://researchdata.bath.ac.uk/1467/1/sidescan_sonar_images_PRIME_CNN_training.zip
        size: 6165203835
        md5: null   # not published; compute after download
      - name: README.txt
        url: https://researchdata.bath.ac.uk/1467/2/README.txt
        size: null
        md5: null
    format: "PNG (3056) + MAT nav (397) + CSV waypoints; StarFish 450 and 990 kHz; layout site/date/run/{450,990,tracks,paths}"
    labels: "NONE - unlabelled; some 'target' subfolders only; labelled set lost (README)"
    notes: "Only usable for unlabelled/calibration. Images uncorrected, need rescaling; dims in filename. Canal/harbour freshwater."

  - id: dfki_uxo
    title: "An Acoustic and Optical Dataset for the Perception of Underwater Unexploded Ordnance (UXO)"
    source_url: https://zenodo.org/records/13778485
    doi: 10.5281/zenodo.13778485
    licence: BSD-3-Clause
    licence_status: verified
    commercial_use: "yes"
    tier: commercial
    files:
      - {name: sample.7z, url: "https://zenodo.org/api/records/13778485/files/sample.7z/content", size: 1732018855, md5: fcadef5fcc1a2cbdcc67812a5df732d7}
      - {name: data_export_recordings.7z, url: "https://zenodo.org/api/records/13778485/files/data_export_recordings.7z/content", size: 16658054765, md5: 30c45956c0d034c27e3988711195c8c6}
      - {name: data_export_polar.7z, url: "https://zenodo.org/api/records/13778485/files/data_export_polar.7z/content", size: 16487715574, md5: 6e785ffd07bbab4f491794c2244df478}
      - {name: data_processed.7z, url: "https://zenodo.org/api/records/13778485/files/data_processed.7z/content", size: 61513277947, md5: 2b9ef16c763a6964c608ed99a9cd1edb}
      - {name: data_export_3dmodels.7z, url: "https://zenodo.org/api/records/13778485/files/data_export_3dmodels.7z/content", size: 26442213, md5: 4ed8820771bbb39819eacf66b50ff509}
      - {name: data_export_calibration.7z, url: "https://zenodo.org/api/records/13778485/files/data_export_calibration.7z/content", size: 1020, md5: bb7641890899bf424e3eeb242509f261}
    format: "ARIS Explorer 3000 imaging sonar + camera frames, 7z archives; internal layout UNVERIFIED"
    labels: "annotations on SD camera frames; multiply coords by 3 for FHD; file format UNVERIFIED"
    notes: "Imaging (forward-looking) sonar, controlled tank - not side-scan. Optional/low priority."

  - id: jncc_cefas_raw_sss
    title: "Raw sidescan sonar data from Inner Dowsing, Race Bank and North Ridge cSAC, and Haisborough, Hammond and Winterton cSAC"
    source_url: https://data.gov.uk/dataset/9e58988b-1ef6-4808-a629-fe4ffe27706a/
    licence: OGL-UK-3.0
    licence_status: verified
    commercial_use: "yes"
    tier: commercial
    files: []   # no direct file link in CKAN; only http://jncc.defra.gov.uk/opendata (HTML)
    format: "UNVERIFIED (raw SSS, likely XTF); size UNVERIFIED"
    labels: "none"
    notes: "Download route unresolved - contact data@jncc.gov.uk / Cefas. Blocked until file located."

  - id: ai4shipwrecks
    title: "Machine Learning for Shipwreck Segmentation from Side Scan Sonar Imagery: Dataset and Benchmark (AI4Shipwrecks)"
    source_url: https://doi.org/10.7302/dmf4-x492
    licence: "UNKNOWN (Deep Blue licence field not read)"
    licence_status: unconfirmed
    commercial_use: unknown
    tier: research_only
    files: []   # 3 files, ~1.14 GB per search snippet; names/sizes/md5 not retrieved
    format: "PNG exports from EdgeTech 2205 low-freq (520 kHz), 1728 px wide x variable height; 286 images, 28 wrecks; Thunder Bay NMS, Lake Huron"
    labels: "binary per-pixel masks (0 other, 1 shipwreck); 50/50 site-grouped train/test; 1728x1728 tiles stride 100 (2539 train / 1722 test)"
    notes: "Deep Blue returned 403 to scripted fetch. Read licence in a browser and fetch files manually before any use."

  - id: nksid
    title: "NanKai Sonar Image Dataset (NKSID)"
    source_url: https://github.com/Jorwnpay/NK-Sonar-Image-Dataset
    licence: "MIT (repo LICENSE; data-specific licence not stated)"
    licence_status: unconfirmed
    commercial_use: conditional
    tier: conditional
    files:
      - {name: big_propeller.zip, url: "https://raw.githubusercontent.com/Jorwnpay/NK-Sonar-Image-Dataset/main/NKSID/big_propeller.zip", size: 788429, md5: null}
      - {name: cylinder.zip, url: "https://raw.githubusercontent.com/Jorwnpay/NK-Sonar-Image-Dataset/main/NKSID/cylinder.zip", size: 856536, md5: null}
      - {name: fishing_net.zip, url: "https://raw.githubusercontent.com/Jorwnpay/NK-Sonar-Image-Dataset/main/NKSID/fishing_net.zip", size: 500009, md5: null}
      - {name: floats.zip, url: "https://raw.githubusercontent.com/Jorwnpay/NK-Sonar-Image-Dataset/main/NKSID/floats.zip", size: 8384673, md5: null}
      - {name: iron_pipeline.zip, url: "https://raw.githubusercontent.com/Jorwnpay/NK-Sonar-Image-Dataset/main/NKSID/iron_pipeline.zip", size: 5698845, md5: null}
      - {name: small_propeller.zip, url: "https://raw.githubusercontent.com/Jorwnpay/NK-Sonar-Image-Dataset/main/NKSID/small_propeller.zip", size: 233740, md5: null}
      - {name: soft_pipeline.zip, url: "https://raw.githubusercontent.com/Jorwnpay/NK-Sonar-Image-Dataset/main/NKSID/soft_pipeline.zip", size: 850590, md5: null}
      - {name: "tire/half batch from 1 to 400.zip", url: "https://raw.githubusercontent.com/Jorwnpay/NK-Sonar-Image-Dataset/main/NKSID/tire/half%20batch%20from%201%20to%20400.zip", size: 17641118, md5: null}
      - {name: "tire/half batch from 401 to 834.zip", url: "https://raw.githubusercontent.com/Jorwnpay/NK-Sonar-Image-Dataset/main/NKSID/tire/half%20batch%20from%20401%20to%20834.zip", size: 16450421, md5: null}
      - {name: kfold_train.txt, url: "https://raw.githubusercontent.com/Jorwnpay/NK-Sonar-Image-Dataset/main/NKSID/kfold_train.txt", size: 479400, md5: null}
      - {name: kfold_val.txt, url: "https://raw.githubusercontent.com/Jorwnpay/NK-Sonar-Image-Dataset/main/NKSID/kfold_val.txt", size: 120150, md5: null}
      - {name: train_abs.txt, url: "https://raw.githubusercontent.com/Jorwnpay/NK-Sonar-Image-Dataset/main/NKSID/train_abs.txt", size: 93679, md5: null}
    format: "JPEG, Oculus M750d multibeam forward-looking sonar (750 kHz / 1.2 MHz), 2617 images, Bohai Bay; NOT side-scan"
    labels: "image-level classification, 8 classes (big_propeller, cylinder, fishing_net, floats, iron_pipeline, small_propeller, soft_pipeline, tire); train_abs.txt '<path> <label>', ten-fold index lists in kfold_*.txt"
    notes: "No checksums published (compute locally). Small (~52 MB) - smoke-test candidate. Confirm data licence with authors."
```
