# NetSight data acquisition: sonar data and ground-truth labels (as of 2026-11-06)

Tagging: [READ] = I fetched and read the page itself this session. [SEARCH-ONLY] = only seen in search-result snippets/summaries, not opened. Anything I could not verify is in Gaps. Where a fetch failed (403/404) I say so.

## 1. NOAA specifics: finding H-surveys with side-scan + contact listings, raw XTF/HSX/GSF, example IDs

### Takeaway
NCEI hosts an H-survey folder per survey under a predictable path; the Descriptive Report (DR) PDF carries (or references as a "Separate") the side-scan contact listing, but the folders I opened hold only processed products (BAG, TIFF mosaics, DR, bottom samples), not raw XTF. Raw side-scan is archived by NCEI under a separate trackline/side-scan holding and the only confirmed route to it is contacting NCEI/HSD; I could not confirm a self-serve raw-XTF path or the number of H-surveys with side-scan.

### Cited Findings
- Directory structure [READ]: `https://data.ngdc.noaa.gov/platforms/ocean/nos/coast/H12001-H14000/H12333/` contains 7 subfolders: BAG/, Bottom_Samples/, DR/, GeoImagePDF/, TIDES/, TIFF/, project_sketches/. No XTF/HSX/GSF/raw folder. Its DR/ folder holds a single file H12333.pdf (4.6 MB). — [H12333 folder](https://data.ngdc.noaa.gov/platforms/ocean/nos/coast/H12001-H14000/H12333/), [H12333 DR folder](https://data.ngdc.noaa.gov/platforms/ocean/nos/coast/H12001-H14000/H12333/DR/)
- Path pattern: `data.ngdc.noaa.gov/platforms/ocean/nos/coast/H<start>-H<end>/H<NNNNN>/DR/H<NNNNN>.pdf` (blocks of ~2000, e.g. H12001-H14000). — [H12243 DR](https://data.ngdc.noaa.gov/platforms/ocean/nos/coast/H12001-H14000/H12243/DR/H12243.pdf) [SEARCH-ONLY]
- Contact listing is usually a "Separate" attached to the survey records, and it is referenced from the DR: H12243 and H12251 DRs list "Separates V - Side Scan Contact Listing and Images of Significant Contacts"; H12394 and H12396 list it as Separates III; H12333 DR states all side-scan contacts are in Separate V and significant features are in the S-57 feature file. These are statements from search-result summaries of those DRs. [SEARCH-ONLY] — [H12243](https://data.ngdc.noaa.gov/platforms/ocean/nos/coast/H12001-H14000/H12243/DR/H12243.pdf), [H12251](https://data.ngdc.noaa.gov/platforms/ocean/nos/coast/H12001-H14000/H12251/DR/H12251.pdf), [H12394](https://data.ngdc.noaa.gov/platforms/ocean/nos/coast/H12001-H14000/H12394/DR/H12394_DR.pdf), [H12396](https://data.ngdc.noaa.gov/platforms/ocean/nos/coast/H12001-H14000/H12396/DR/H12396_DR.pdf), [H12333](https://data.ngdc.noaa.gov/platforms/ocean/nos/coast/H12001-H14000/H12333/DR/H12333.pdf)
- Important caveat: for H12333 the DR folder contains only the DR PDF (no separate appendix files listed), so the contact listing is inside the (large) DR PDF or in the paper "Separates" and may not be a separately downloadable file. [READ folder listing] — [H12333 DR folder](https://data.ngdc.noaa.gov/platforms/ocean/nos/coast/H12001-H14000/H12333/DR/)
- Recent survey example, data.gov record H13684 (Central Chesapeake Bay, Sandy Point to Bodkin Point, MD; Oct 2022 - Apr 2023), 14 resources: Descriptive Report (PDF+XML), project-level DAPR, 2 BAGs, two 1 m 900 kHz side-scan mosaics (TIFF), a 2 m 300 kHz multibeam backscatter TIFF, bottom samples, GeoImage PDF. No raw sonar files listed. Licence CC0 1.0 (but "Access Level: non-public" metadata glitch). Contact hsd.inquiries@noaa.gov. [READ] — [H13684 on data.gov](https://catalog.data.gov/dataset/h13684-nos-hydrographic-survey-2023-04-29)
- Data.gov catalogue also has entries for other surveys (H12525, H12521, H12510, H12677, H13581, F00869) listing processed products; an H12525 record says the data it holds are "raw" and not QC'd by NOAA, released for limited public use with caution. [SEARCH-ONLY] — [H12525](https://catalog.data.gov/dataset/h12525-nos-hydrographic-survey-2013-06-131), [H13581](https://catalog.data.gov/dataset/h13581-nos-hydrographic-survey-2022-07-24)
- NCEI says it archives/disseminates >11,000 smooth sheets and >8,000 DRs (mid-1800s to present). [SEARCH-ONLY, from a search summary] — [NCEI hydro DR listing](https://data.ngdc.noaa.gov/platforms/ocean/nos/coast/H12001-H14000/H12243/DR/H12243.pdf) (weak source; verify at NCEI hydrographic survey page; the product page https://www.ncei.noaa.gov/products/hydrographic-survey-data returned 404)
- Raw side-scan at NCEI: the NCEI "Marine Trackline Geophysical Data" catalogue has a Side-Scan Sonar database; record is CC0 1.0 but metadata also says "non-public"/otherRestrictions, so confirm with NCEI. Search/access via the Trackline Geophysical Data Viewer https://www.ncei.noaa.gov/maps/trackline-geophysics/ ; contact trackline.info@noaa.gov or ncei.info@noaa.gov. [READ] — [data.gov side-scan trackline record](https://catalog.data.gov/dataset/marine-trackline-geophysical-database-for-side-scan-sonar-data), [NCEI trackline product page](https://www.ncei.noaa.gov/products/marine-trackline-geophysical-data)
- A NCEI submission guide states the side-scan database "primarily maintains raw (as collected) and processed data files in JSF or HSX format" (from search snippet; the PDF itself returned 404 when I fetched it). [SEARCH-ONLY] — [NCEI submission guide](https://www.ncei.noaa.gov/sites/g/files/anmtlf171/files/2023-10/SubmittingMarineGeophysicalData.pdf)
- The NCEI trackline product page [READ] does not state formats, survey counts or a download protocol. — [NCEI trackline page](https://www.ncei.noaa.gov/products/marine-trackline-geophysical-data)
- 3-5 example survey IDs with side-scan sonar contact listings (referenced in DR text; DR PDFs not opened by me): H12243, H12251, H12333, H12394, H12396 (all in the H12001-H14000 block; DR URLs above). Additional H12 DRs returned by the same search: H12334, H12335, H12353, H12331, H12395. [SEARCH-ONLY]. For a survey with confirmed side-scan mosaics + backscatter + DR in the folder: H13684 [READ].
- USGS republications of NOAA surveys with mosaics from raw XTF: H11321 (Rhode Island Sound, OFR 2007-1366, Klein 5500, XTF -> 1 m mosaic), H11322 (OFR 2008-1181, Klein 5500 455 kHz, XTF), H11251, H11346, H12296. Pages describe mosaics and metadata; they do not state that the raw XTF or contact lists are in the release. [SEARCH-ONLY] — [H11322](https://pubs.usgs.gov/of/2008/1181/data/sidescan/utm/h11322_1m_sss_utm/h11322_1m_sss_utm.html), [H11321 metadata](https://cmgds.marine.usgs.gov/publications/of2007-1366/data/sidescan/utm/h11321_1m_sss_utm/h11321_1m_sss_utm_meta.htm), [H12296](https://pubs.usgs.gov/of/2014/1018/data/sidescan/h12296_1msss_utm19.html)
- USGS also republishes the DRs for some surveys (e.g. H12139, H12010, H12011, H12015, H12137 in OFR 2012-1005-P). [SEARCH-ONLY] — [H12139 DR](https://pubs.usgs.gov/of/2012/1005_p/data/pdfs/H12139_DR.pdf)

### Inferences
- Practical contact-label path: pick 20-50 H-surveys, download the DR PDF, parse the "side scan contact listing" table (and Danger-to-Navigation / "Dangers to navigation" and AWOIS investigation sections), and pair with the TIFF mosaic. Labels will be PDF text/tables, so budget OCR/table extraction effort; and contact positions can be matched to mosaic GeoTIFFs but not to raw pings.
- Raw XTF/HSX for H-surveys should be treated as "request-only" until NCEI/HSD confirm otherwise.
- Count of H-surveys with side-scan: not established. Rough bound from sources: NCEI holds >8,000 DRs total, of which only a subset (newer ones, and those with SSS) have mosaics.

### Gaps
- I did not open any H-survey DR PDF, so I have not verified actual contact-table content, AWOIS "investigated/disproved" wording, or DTON report structure for the example IDs.
- Number of surveys with side-scan and the correct "raw data" request procedure not found (NCEI hydrographic-survey page 404'd; the NCEI submission guide 404'd). Ask hsd.inquiries@noaa.gov and trackline.info@noaa.gov.
- NCEI search tools (Hydrographic Survey Metadata viewer / NOAA Survey Data viewer at nauticalcharts.noaa.gov) not fetched.

## 2. USGS raw side-scan releases (ScienceBase / CMGDS) with XTF and contact lists

### Takeaway
USGS publishes raw Klein/EdgeTech XTF via its Coastal & Marine Geology data system (CMGDS) and OFR pages, but I found no specific ScienceBase release that bundles XTF plus a verified contact list; the best confirmed items are mosaic releases and XTF-in-metadata mentions.

### Cited Findings
- USGS CMGDS dataset id=38005 ("2015-315-FA_xtf.zip") is listed as unprocessed Klein SonarPro XTF files (fetch returned 403 so metadata/licence unread). [SEARCH-ONLY] — [CMGDS 38005](https://cmgds.er.usgs.gov/services/cmgds-dataset.php?id=38005)
- USGS OFRs describe XTF acquired with Klein 3000/5000/5500 and EdgeTech 272T using Triton ISIS; ancillary mosaics at 1-2 m. [SEARCH-ONLY] — [OFR 2008-1174 data page](https://pubs.usgs.gov/of/2008/1174/html/data.html), [OFR 2008-1181 H11322](https://pubs.usgs.gov/of/2008/1181/data/sidescan/utm/h11322_1m_sss_utm/h11322_1m_sss_utm.html)
- NOAA OCM Hudson River NY "side-scan sonar backscatter tiles ... XTF" record: raw XTF converted from Hypack HSX, collected Nov-Dec 2009 Saugerties to Troy; distributed as a zip on a NOAA FTP server. No target/ground-truth mentioned. [SEARCH-ONLY] — [data.gov Hudson River XTF](https://catalog-beta.data.gov/dataset/side-scan_sonar-backscatter-tiles-for-hudson-river-ny-xtf)
- USGS data are generally US-government public domain (not verified on these specific pages). 

### Inferences
- XTF from USGS/OCM is good for self-supervised pretraining but lacks labels unless matched to NOAA contact lists (e.g. H11321/H11322 mosaics are NOAA H-surveys, so the corresponding NOAA DR contact lists can be pulled from NCEI).

### Gaps
- No verified ScienceBase item with XTF + contact list; cmgds 403; licence text for each item not read. Ask USGS PCMSC_data@usgs.gov for specifics.

## 3. Recreational side-imaging: PINGMapper, Humminbird datasets, GhostVision, Roboflow

### Takeaway
There is a genuinely usable, openly licensed recreational-sonar ecosystem from Cameron Bodine (PING Ecosystem): MIT-licensed software, a CC BY 4.0 13.8 GB substrate/depth/shadow label set, and the GhostVision derelict crab-pot detection dataset (6,674 Humminbird images, CC BY-SA 4.0, with a licence conflict on Hugging Face). Roboflow datasets were not examined.

### Cited Findings
- PINGMapper: open-source Python tool for side-scan processing and benthic habitat mapping, MIT licence; part of PING ecosystem (PINGInstaller, PINGWizard, PINGVerter); topic tags Humminbird, Lowrance, Garmin, Cerulean. No sample data on the repo page. [READ] — [PINGMapper GitHub](https://github.com/CameronBodine/PINGMapper)
- PINGMapper docs (search snippet): tested on Humminbird 1197, 1198, 1199, Helix, Solix, Onix. [SEARCH-ONLY] — [PINGMapper docs](https://cameronbodine.github.io/PINGMapper/)
- Zenodo 10119320 "Sidescan Sonar Substrate, Depth, and Shadow Image-Label-Pairs", Cameron S. Bodine (NAU), CC BY 4.0, single zip 13.8 GB (PINGMapperv2.0_SegmentationModelsv1.0_ImageLabelPairs.zip); labelled with Doodler and Make Sense; image count not stated; page does not mention Humminbird. [READ] — [Zenodo 10119320](https://zenodo.org/records/10119320)
- GhostVision dataset Zenodo 20056679 (v1.0.0, published 2026-05-06): "Derelict Crab Pot Object Detection Dataset and Models for GhostVision", licence CC BY-SA 4.0, GhostVision_DatasetAndModels.zip 898.8 MB, models RF-DETR/YOLO12/YOLO26, sonar brand not stated on Zenodo. Authors: Bodine, Baxevani, Abbasi, Wierzbicki, Christoph, Hughes, Bagoren, Hines, Greco, Trembanis (Univ. of Delaware). [READ] — [Zenodo 20056679](https://zenodo.org/records/20056679)
- Hugging Face PINGEcosystem/sss-crab-pot-detection-ds: 6,674 images, 559 MB, consumer-grade Humminbird side-scan, Delaware Inland Bays and Delaware Bay, axis-aligned bounding boxes in JSONL, classes Crab-Pot and Maybe-Crab-Pot. Licence conflict: page text says "released under the GPL license" but metadata tag is cc-by-sa-4.0. [READ] — [HF dataset](https://huggingface.co/datasets/PINGEcosystem/sss-crab-pot-detection-ds)
- GhostVision paper: 3,110 annotated images used in training for YOLOv12, YOLOv26, RF-DETR; under review at J. Marine Science and Engineering (per search result). [SEARCH-ONLY] — [PyPI ghostvision](https://pypi.org/project/ghostvision/)
- GhostVision is about derelict crab pots, not nets. GhostNetZero (Microsoft/WWF; ~90% detection on Baltic and Puget Sound data per preprint; NVIDIA reports 94%) - no public dataset found. [SEARCH-ONLY] — [Microsoft Research GhostNetZero](https://www.microsoft.com/en-us/research/?p=1150234), [NVIDIA blog](https://developer.nvidia.com/blog/ai-helps-locate-dangerous-fishing-nets-lost-at-sea)
- Two USFWS lower Chena River (2022) Humminbird Helix 15 side-scan geodatabases on data.gov (habitat products, not ML labels). [SEARCH-ONLY] — [data.gov Chena](https://catalog.data.gov/dataset/filegeodatabase-of-chena-river-habitat-map-with-water-column-2022)
- A Hugging Face dataset "drishti-sss" and a KADAL v6 (Apache-2.0 claimed, derivative incl. Kaggle side-scan benchmark) appeared in search; unvetted derivative sets, provenance unclear. [SEARCH-ONLY] — [drishti-sss](https://huggingface.co/datasets/rehan9599/drishti-sss)

### Inferences
- CC BY-SA 4.0 on GhostVision is share-alike: commercial use is allowed but derivatives (possibly trained datasets/labels; model weights are legally unclear) carry ShareAlike obligations; need legal read. The GPL text on HF is a red flag; ask the authors to clarify.
- Humminbird imagery is lower quality than survey-grade sonar; it is a domain-shift source, mainly useful for object detection of pot-like/net-like targets and for testing the pipeline on cheap data.

### Gaps
- Roboflow Universe side-scan datasets not searched/fetched; licences (often CC BY 4.0 per project, but not verified here) unknown.
- No public Garmin/Lowrance side-scan datasets found.
- Bodine Zenodo 10120054/10093642/6604785 not opened.

## 4. Other national archives: licences and raw availability

### Takeaway
Licences are mostly open (CC BY 4.0 for INFOMAR, OGL for UK, per-dataset on AusSeabed), but most portals expose gridded/processed products, not raw side-scan. The most promising raw-side-scan sources found are JNCC/Cefas (OGL) and Marine Data Exchange (terms unverified).

### Cited Findings
- INFOMAR (Ireland): CC BY 4.0, attribution "Contains Irish Public Sector Data (Geological Survey Ireland & Marine Institute) licensed under CC BY 4.0"; per-survey-leg packages include backscatter grids, imagery, sub-bottom and reports; no explicit raw backscatter statement. [SEARCH-ONLY] — [INFOMAR data page](https://infomar.ie/data), [INFOMAR licence PDF](https://infomar.ie/sites/default/files/pdfs/INFOMAR%20Licence%20Agreement%20and%20Acknowledgement%2008_2022.pdf), [data access policy](https://infomar.ie/sites/default/files/pdfs/INFOMAR%20Data%20Access%20Policy%20and%20Guidelines%201.pdf)
- INFOMAR also has an "INSS Surveyed Shipwreck" catalogue entry (possible shipwreck labels) [SEARCH-ONLY] — [INSS shipwreck](https://dgi-training.prod.derilinx.com/dataset/infomar-inss-surveyed-shipwreck)
- AusSeabed: no blanket licence; per-dataset (some CC BY 4.0, some "Other"); mostly gridded geotiff/ASCII; no evidence of raw .all/.kmall. Portal managed by Geoscience Australia and includes side-scan sonar among dataset types. [SEARCH-ONLY] — [AusSeabed portal user guide](https://asbdatamanagement.atlassian.net/wiki/spaces/AMDPUG), [AusSeabed data.wa.gov.au entry](https://catalogue.data.wa.gov.au/app/ausseabed-marine-data-portal)
- UKHO / Admiralty Marine Data Portal: bathymetry under OGL v3.0 plus UKHO conditions (not for navigation, specific attribution); >4,000 bathymetry surfaces; no confirmation that side-scan is offered. Sources are 2020-2022. [SEARCH-ONLY] — [Admiralty access data](https://www.admiralty.co.uk/access-data), [GOV.UK portal guidance](https://www.gov.uk/guidance/inspire-portal-and-medin-bathymetry-data-archive-centre)
- JNCC/Cefas raw side-scan: data.gov.uk record "Raw sidescan sonar data from Inner Dowsing, Race Bank and North Ridge cSAC and Haisborough, Hammond and Winterton cSAC" (survey CEND 11/11), publisher JNCC, licence Open Government Licence (v3 link), access constraints "No limitations"; format and size not stated; points to jncc.defra.gov.uk/opendata. [READ] — [data.gov.uk record](https://data.gov.uk/dataset/9e58988b-1ef6-4808-a629-fe4ffe27706a/raw-sidescan-sonar-data-from-inner-dowsing-race-bank-and-north-ridge-csac-and-haisborough-hammo)
- Crown Estate Marine Data Exchange (MDE): holds geophysical, geotechnical, archaeological/shipwreck data; "over 60% of offshore renewables survey data in England, Wales, NI freely available", Scotland added. Licences vary: a 2013 Dudgeon geophysical record says free for teaching/research/government but permission required for commercial use; another record shows "No Licence Provided". MDE terms page URL I tried (marinedataexchange.co.uk/terms-and-conditions) returned 404. [SEARCH-ONLY] — [Dudgeon survey on data.gov.uk](https://data.gov.uk/dataset/09ad3e54-c42a-427a-9693-7a4e913c05cf/2013-gardline-dudgeon-offshore-wind-farm-geophysical-survey), [Renewable Energy Magazine](https://www.renewableenergymagazine.com/wind/crown-estate-publishes-new-open-data-from-20140902)
- BGS offshore backscatter areas OGC API and MEDIN archives exist (open government licence listed). [SEARCH-ONLY] — [BGS OGC API](https://ogcapi.bgs.ac.uk/collections/offshorebackscatterareas/items/65477389?f=html)
- Public EdgeTech raw XTF: Marine-Geo/IEDA dataset 6159 (2005 Chilean fjord, NBP0505, towed EdgeTech). [SEARCH-ONLY] — [Marine-Geo 6159](https://www.marine-geo.org/tools/datasets/6159)

### Inferences
- For commercial use, MDE is high-risk on licence until the actual terms and per-dataset licences are read; OGL (JNCC/BGS/UKHO) and CC BY 4.0 (INFOMAR) are low-risk.
- MDE UXO/geophysical reports might contain target lists, which would be valuable for labels, but this is unverified.

### Gaps
- EMODnet, BSH (Germany), Netherlands, MAREANO (Norway), CHS (Canada), LINZ (NZ): not searched (budget exhausted). Do not assume licences.
- MDE terms, registration, UXO register: not confirmed.
- UKHO side-scan availability: not confirmed.

## 5. Vendor and software sample data

### Takeaway
I found no officially hosted vendor sample-file pages with usage terms; the practical sample XTF sources are public research archives.

### Cited Findings
- Kongsberg Sonar Mosaic supports XTF import via an optional module; no Kongsberg XTF samples found; Kongsberg EM data on R2R are in .all format. [SEARCH-ONLY] — [Kongsberg Sonar Mosaic datasheet](https://www.kongsberg.com/globalassets/discovery/commerce/seafloor-mapping/sonar-mosaic/sonar-mosaic_datasheet_en.pdf)
- XTF specification includes DEMO_XTF.ZIP reader sample (Triton). [SEARCH-ONLY] — [XTF format doc](https://www.ldeo.columbia.edu/res/pi/MB-System/mbweb/formatdoc/XtfFileFormat_X26.pdf)
- R2R (rvdata.us) hosts research-vessel filesets; some contain side-scan/multibeam; licences by fileset. [SEARCH-ONLY] — [R2R example fileset](https://www.rvdata.us/search/fileset/100790)

### Inferences
- Vendor samples (EdgeTech, Klein/GO, Teledyne, Cerulean, Deep Trekker, Blueprint Oculus, SonarWiz/Hypack/QPS) usually come with "evaluation" terms; treat as for-testing only, not for training, unless written permission is obtained.

### Gaps
- None of the named vendors' sample-data pages were fetched or found. Needs direct vendor email requests.

## 6. Licence verification for labelled datasets

### Takeaway
Only the Marine Debris FLS licence was verified on the actual page, and it is non-commercial (CC BY-NC-SA 4.0). SubPipe, Catalan, Bath and DFKI (confirmed earlier) remain the safe commercial set. AI4Shipwrecks, UATD, SCTD 3.0, NKSID, KLSG have no verified licence statement and should be treated as research-only until written permission.

### Cited Findings
- Marine Debris FLS (arXiv 2503.22880): Zenodo record 15101686 is licensed CC BY-NC-SA 4.0 (non-commercial), 7.1 GB in 28 files, ARIS Explorer 3000 forward-looking sonar, watertank/turntable/quarry settings. arXiv abstract page shows CC0 icon for the article only. [READ] — [Zenodo 15101686](https://zenodo.org/records/15101686), [arXiv 2503.22880](https://arxiv.org/abs/2503.22880)
- AI4Shipwrecks: 28 shipwrecks, 286 labelled side-scan PNGs, Thunder Bay NMS, Iver3 AUV with EdgeTech 2205; Deep Blue DOI 10.7302/dmf4-x492, 3 files 1.14 GB. Project page states no licence, only a citation request. Deep Blue page returned 403 for me; licence field unread. [READ project page; Deep Blue SEARCH-ONLY] — [project page](https://umfieldrobotics.github.io/ai4shipwrecks/), [Deep Blue](https://deepblue.lib.umich.edu/data/concern/data_sets/8623hz41x), [arXiv 2401.14546](https://arxiv.org/abs/2401.14546?context=cs). (The GitHub URL github.com/ai4shipwrecks/ai4shipwrecks I guessed 404'd; not a real repo as far as I know.)
- UATD: Tritech Gemini 1200ik multibeam FLS, >9,000 images, 10 classes; hosted on figshare (DOI 10.6084/m9.figshare.21331143.v3); the Scientific Data article is CC BY 4.0 but the page states no dataset licence. Figshare page not opened. [READ article] — [PMC9715547](https://pmc.ncbi.nlm.nih.gov/articles/PMC9715547/)
- SCTD 3.0 (arXiv 2608.08106): >10,000 real synthetic aperture sonar (SAS) snippets (240 kHz, 450 kHz and others); GitHub github.com/automlresearch/SCTD-3.0 labelled "MIT license" but the repo page shows no dataset size/download and says the paper is under review; MIT on the repo does not necessarily cover the data. [READ] — [arXiv abs](https://arxiv.org/abs/2608.08106), [GitHub](https://github.com/automlresearch/SCTD-3.0)
- SCTD 1.0 mirror (Pascal VOC) shows no licence text. [SEARCH-ONLY] — [SCTD mirror](https://github.imc.re/MingqiangNing/SCTD)
- NKSID (Nankai Sonar Image Dataset): forward-looking sonar (not side-scan), 2,617 images, 8 classes, long-tailed; GitHub repo Jorwnpay/NK-Sonar-Image-Dataset marked MIT licence, data in zip files in the repo, citation requested. [READ] — [GitHub](https://github.com/Jorwnpay/NK-Sonar-Image-Dataset); modality per [arXiv 2510.03353](https://arxiv.org/abs/2510.03353?context=cs) [SEARCH-ONLY]
- KLSG / SeabedObjects (Huo et al. 2020): ship and airplane side-scan dataset; no licence found; repository mirror at huoguanying/SeabedObjects-Ship-and-Airplane-dataset. [SEARCH-ONLY] — [mirror](https://relatedrepos.com/gh/huoguanying/SeabedObjects-Ship-and-Airplane-dataset)
- A survey paper "Sonar Image Datasets: A Comprehensive Survey" (arXiv 2510.03353) catalogues these sets (useful index to find more). [SEARCH-ONLY] — [arXiv](https://arxiv.org/html/2510.03353v1)
- SASSED: not searched.

### Inferences
- "MIT" on a GitHub repo hosting data is ambiguous; for a startup, get an email confirmation from authors or limit use to non-commercial benchmarking.
- NKSID is MIT on repo and is the best candidate of the unconfirmed set, but it is forward-looking sonar, a different modality from side-scan.

### Gaps
- Actual LICENSE files of SCTD-3.0, NKSID not read (page showed label only). UATD figshare licence, AI4Shipwrecks Deep Blue licence, KLSG licence, SASSED licence unverified.

## 7. Indian portals

### Takeaway
I could not confirm any downloadable side-scan, backscatter or multibeam dataset on any Indian government portal. GSI holds a large offshore repository and has sidescan/SAS equipment, but access appears to be by request/MoU.

### Cited Findings
- GSI Marine and Coastal Survey Division (Mangaluru) has mapped most of India's 2.1 million km2 EEZ and holds a large offshore data repository; Indian Navy signed an MoU with GSI for seabed sediment data (2020). [SEARCH-ONLY] — [Indian Navy MoU](https://indiannavy.nic.in/node/25258), [OE Digital](https://www.oedigital.com/news/474913-indian-navy-signs-mou-for-offshore-data-with-gsi)
- GSI vessel got a Kongsberg GeoAcoustics 2094D side-scan package (2013) and RV Samudra Ratnakar carries SAMS DT-6000 synthetic aperture sonar (2017 Current Science). [SEARCH-ONLY] — [Kongsberg news](https://www.kongsberg.com/maritime/news-and-events/news-archive/2013/kongsberg-geoacoustics-sidescan-sonar-package-for-new-indian-survey-vessel)
- No hits for Bhukosh marine layers, NIOT, NCCR, NCPOR, INCOIS or data.gov.in sonar datasets.

### Inferences
- Indian data will likely have to be obtained by direct institutional request/MoU; this is also a differentiator but a long lead-time item; start the request in week 1.

### Gaps
- Entire question largely unanswered: data.gov.in, INCOIS, NIOT, NCCR, NCPOR, Deep Ocean Mission data policy and Bhukosh not fetched.

## 8. Ghost-net sonar imagery (qualitative references)

### Takeaway
Public ghost-gear sonar imagery exists mainly as figures in reports about derelict crab/lobster pots (not nets); no public ghost-net sonar image dataset found.

### Cited Findings
- NOAA Chesapeake Bay Office Maryland Derelict Fishing Gear Benthic Survey: side-scan survey of derelict crab traps; trap retrieval confirmed sonar IDs (ground-truthed); estimate >85,000 ghost traps; figure shows traps as cubes. [SEARCH-ONLY] — [archived NOAA page](https://webarchive.library.unt.edu/web/20170119130501/https://chesapeakebay.noaa.gov/acoustic-seafloor-mapping/maryland-derelict-fishing-gear-benthic-survey)
- Olympic Coast NMS 2007 (600 kHz Marine Sonic) and Puget Sound/Port Gardner/Dungeness Bay reports (Northwest Straits, NOAA MDP-funded). [SEARCH-ONLY] — [Port Gardner 2009](https://www.snocomrc.org/media/1307/2009-port-gardner-derelict-fishing-gear-project.pdf), [Clallam final report](https://nwstraits.org/sites/default/files/2025-10/cla-2006-0013-clallam-county-derelict-fishing-gear-nrc-final-report.pdf)
- Massachusetts "Development of side-scan sonar methodology to survey derelict lobster pots (2017)". [SEARCH-ONLY] — [mass.gov PDF](https://www.mass.gov/doc/development-of-side-scan-sonar-methodology-to-survey-derelict-lobster-pots-2017/download)
- GhostNetZero (see section 3): no public data.

### Inferences
- Report figures are fine as qualitative references or for internal reading; republishing images or training on them needs permission from authors/agencies (report copyrights not checked).

### Gaps
- WWF Baltic and Ghost Fishing reports not searched.

## 9. Prioritised 8-week acquisition plan

### Takeaway
Start with datasets whose commercial licence is confirmed (earlier research + CC BY 4.0 Bodine pairs), build the NOAA DR-contact-label pipeline in parallel, and send all permission/request emails in week 1 since replies take weeks.

### Cited Findings (what each item gives; sources above)
- Week 1: (a) Download Zenodo 10119320 (13.8 GB, CC BY 4.0: substrate/depth/shadow labels) [READ]; (b) download the previously confirmed commercial-OK sets (SubPipe, Catalan 10209445, Bath, DFKI) — licences from earlier research. (c) Send emails: hsd.inquiries@noaa.gov (raw XTF/HSX for specific H-surveys + contact lists), trackline.info@noaa.gov (side-scan raw holdings), PCMSC_data@usgs.gov (XTF + target lists), AI4Shipwrecks/Univ. of Michigan Field Robotics (licence), SCTD-3.0 authors (data licence), GSI/NIOT/NCCR (data request). 
- Week 2: Pull 20-30 NOAA H-survey folders (DR + TIFF mosaics + BAG + backscatter), start with H13684 [READ] and H12243, H12251, H12333, H12394, H12396 [SEARCH-ONLY]. Each folder is hundreds of MB to few GB (sizes not verified; DR PDF for H12333 is 4.6 MB). CC0. Gives: contact positions + dispositions via DR text (real-vs-not labels, calibration).
- Week 3: Parse DR contact tables (OCR/table extraction); build first calibration table of contacts with disposition (investigated/disproved/DTON). Download GhostVision Zenodo 20056679 (899 MB, CC BY-SA 4.0) or HF (559 MB) and JNCC raw sidescan (OGL) — gives small-target (pot) bounding boxes and raw UK side-scan.
- Week 4: INFOMAR shipwreck/backscatter downloads (CC BY 4.0) for wreck labels and hardness maps; USGS CMGDS 38005 XTF and Hudson River XTF for raw pretraining data; Marine-Geo 6159 (EdgeTech XTF).
- Week 5: Review replies; use NOAA raw if released (XTF/HSX/JSF). Search AusSeabed side-scan items filtered to CC BY 4.0; check Marine Data Exchange terms with The Crown Estate before downloading.
- Week 6: Research-only benchmarking: AI4Shipwrecks (1.14 GB), UATD (figshare), NKSID, SCTD-3.0 — use only for internal evaluation unless licences are confirmed; do not mix into a commercial training set.
- Week 7-8: Add Marine Debris FLS (7.1 GB, CC BY-NC-SA) only as research benchmark; gather ghost-pot/net report figures (NOAA Chesapeake, Northwest Straits) as qualitative references; start Indian data request follow-ups; define POD validation targets using wrecks from INFOMAR and NOAA AWOIS/wreck features.

### Inferences
- Volumes are rough: confirmed downloads total roughly 14 GB (Bodine) + ~1 GB (GhostVision) + 1.1 GB (AI4Shipwrecks) + 7.1 GB (Marine Debris FLS) + NOAA folders (unknown) ; H-survey folder sizes were not measured.
- Raw multi-sensor pretraining data are the scarcest item; request-based raw NOAA/USGS/Indian data are the main way to scale.

### Gaps
- Volumes for NOAA folders, raw-data availability, and EMODnet/BSH/MAREANO/CHS/LINZ were not established. Plan should be re-planned after week-1 email replies.
