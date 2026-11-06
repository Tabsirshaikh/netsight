# NetSight: practical company path (validation, services-first, funding, partnerships, compliance, roadmap). Research as of 6 Nov 2026

Verification labels used below:
- **[VERIFIED]**: I fetched the page and read the claim in its text.
- **[SUMMARY-ONLY]**: the claim comes from search-engine result snippets/summaries. I did not open the page. Check it before relying on it.
- **[OPINION]**: my inference, not evidence.

Method note: I made about 20 tool calls. Two direct fetches failed: hydro-international.com returned HTTP 403, and idex.gov.in timed out. So most of these findings are SUMMARY-ONLY. Several of the brief's items could not be researched in this budget and are listed under Gaps: Innovate UK, NOAA SBIR, TDB, SAMRIDH/TIDE, cloud credits, PI insurance, SAS vs MBES costs, Indian hire rates, and team hiring.

## 1. Cheap proof of value: retrospective validation and low-cost target trials

### Takeaway
The cheapest credible first proof is a retrospective study on public NOAA NOS surveys. NCEI publishes side-scan mosaics, and the Descriptive Reports often contain hydrographer side-scan contact listings. There is also published precedent: hydrographers reviewed about 24.7k automatic side-scan detections to build ground truth for false-alarm classifiers. Owning hardware for target-laying trials costs about USD 5.4–6.7k for a Cerulean Omniscan 450 SS on a BlueBoat-class USV. I found no Indian hire rates.

### Cited Findings
- NOAA/NOS hydrographic survey records on NCEI/data.gov typically include a side-scan sonar mosaic (TIFF), a Descriptive Report (PDF + XML) and a BAG bathymetry grid. The data are marked "not to be used for navigation" [SUMMARY-ONLY]: [data.gov H12525](https://catalog.data.gov/dataset/h12525-nos-hydrographic-survey-2013-06-131); [data.gov F00869](https://catalog-old.data.gov/dataset/f00869-nos-hydrographic-survey-2022-10-04)
- Some Descriptive Reports include an appendix titled "Separates III Sidescan Sonar Contact Listing", for example H12396. This is a ready-made, hydrographer-dispositioned contact list. I found no standalone downloadable contacts file. Contents vary by survey [SUMMARY-ONLY]: [NCEI H12396 DR PDF](https://data.ngdc.noaa.gov/platforms/ocean/nos/coast/H12001-H14000/H12396/DR/H12396_DR.pdf); [NCEI report index H11638](https://www.ngdc.noaa.gov/nos/H10001-H12000/H11638.html)
- USGS has republished 1 m side-scan GeoTIFFs from NOAA surveys, for example H12023 in Block Island Sound and H12296 [SUMMARY-ONLY]: [USGS H12023](https://cmgds.marine.usgs.gov/catalog/whcmsc/open_file_report/ofr2013-1003/h12023_1msss_utm19.html); [USGS H12296](https://cmgds.marine.usgs.gov/catalog/whcmsc/open_file_report/ofr2014-1018/h12296_1msss_utm19.html)
- Hydro International, "Automated Side-scan Data Analysis", covers SAIC's work on NOAA-contracted surveys (NOAA began contracting surveys to industry in 1994, and many required 200% side-scan coverage) [SUMMARY-ONLY; fetch returned 403]: [Hydro International](https://www.hydro-international.com/content/article/automated-side-scan-data-analysis)
  - Hydrographers comprehensively reviewed 24,726 automatic detections from two survey sheets to create ground truth.
  - That ground truth was used to train neural-net classifiers to label each detection as a legitimate contact or a false alarm.
  - One single-stage network is reported at about 93% Pd and about 6% Pfa, with 1,348 clutter returns misclassified as targets.
  - This is direct precedent for NetSight's "is this contact real" calibration, built on historical survey data.
- Steiniger, Schröder and Stoppe (ICUA 2022) used a CNN to classify side-scan change-detection candidates and reported significantly fewer false alarms [SUMMARY-ONLY]: [IOA proceedings](https://author.ioa.org.uk/conference-proceeding/icua-southampton-20-23-june-2022-vol44-pt1/y-steiniger-s-schroder-j-stoppe-reducing-the-false-alarm-rate-of-a-simple-sidescan-sonar-change-detection-system-using-deep-learning)
- On synthetic aperture sonar (SAS), a neural network trained on detector output plus local seafloor characteristics gave an average 50% false-alarm reduction [SUMMARY-ONLY]: [Heriot-Watt](https://researchportal.hw.ac.uk/en/publications/reducing-false-alarms-in-automated-target-recognition-using-local/)
- University of Liverpool thesis (Aug 2025) on YOLOv8 boulder detection in side-scan imagery [SUMMARY-ONLY]: [Liverpool repository](https://livrepository.liverpool.ac.uk/3194759/1/201666320_Aug2025.pdf)
  - Data came from CM Geomatics.
  - The most stable model reached about 78% detection rate.
  - The thesis criticises earlier UXO classifiers (for example Quidu et al.) for publishing only training accuracy and loss, with no validation.
- A UXO workflow paper combines multibeam with AUV ground truth. It notes that expert annotations were "not fully ground truthed" and that confirming them needs camera and magnetic data [SUMMARY-ONLY]: [ResearchGate](https://www.researchgate.net/publication/356038528_Workflow_towards_autonomous_and_semi-automized_UXO_Survey_and_Detection)
- Shipwreck segmentation dataset and benchmark for side-scan sonar (arXiv 2401.14546). The authors warn that mosaic misalignment causes label errors and manually corrected the test labels [SUMMARY-ONLY]: [arXiv](https://arxiv.org/pdf/2401.14546)
- Fraunhofer IWES IRAV2 is developing automated UXO detection and classification for dumping areas and uses generative models to make synthetic sonar training data [SUMMARY-ONLY]: [Fraunhofer IWES](https://www.iwes.fraunhofer.de/en/research-projects/current-projects/irav2.html)
- Hardware prices for target-laying trials [SUMMARY-ONLY, retailer pages]:
  - Cerulean Omniscan 450 SS: about USD 5,440 on the Blue Robotics BlueBoat page, GBP 5,640 at RobotShop UK, and USD 6,700 at Charpierov.
  - Hydro International quotes "from USD 2,590 per side". This may be a per-transducer price.
  - Integration kit: about CAD 371 or GBP 250.
  - Sources: [RobotShop UK](https://uk.robotshop.com/products/cerulean-omniscan-450-side-scan-sonar-for-marine-exploration-blueboat-bluerov2); [Hydro International company page](https://www.hydro-international.com/content/company/cerulean-sonar); [Charpierov](https://charpierov.com/?p=9549)
- Indian sellers list USVs with side-scan for search-and-rescue on IndiaMART. Price was not captured [SUMMARY-ONLY]: [IndiaMART](https://m.indiamart.com/proddetail/unmanned-surface-vehicle-with-side-scan-sonar-for-search-and-rescue-sar-activity-2854740924291.html)
- GhostNetBusters (GEOMAR + sonoware) used existing side-scan data plus ML to find gill-net metal lines and reduce the number of verification dives [SUMMARY-ONLY]: [GEOMAR](https://www.geomar.de/en/ghostnetbusters); [sonoware](https://sonoware.de/news/2024-08-28_foerderzusage_ghostnetbusters)
  - Funding: EUR 221k from Schleswig-Holstein's AI fund.
  - Timeline: June 2024 to January 2026.
  - It produced an open-source side-scan processing tool.
  - Sonoware says detecting net remains needs at least 100 kHz and about 20 m range.
- WWF's GhostNetZero.ai (with Microsoft) reports about 90% ghost-net detection on Baltic and Puget Sound data. This is a non-peer-reviewed preprint [SUMMARY-ONLY]: [EcoEvoRxiv](https://ecoevorxiv.org/repository/view/10294/); [Microsoft Research](https://www.microsoft.com/en-us/research/?p=1150234)

### Inferences
- [OPINION] Retrospective validation proves calibration, not detection.
  - NOAA contact listings are hydrographer judgements, often confirmed with multibeam or a dive. They are not a dig result for every contact.
  - A study built on them can show that NetSight's probabilities are well calibrated against expert disposition (reliability diagrams, ECE).
  - It cannot prove "probability of detection" against unknown misses. For that, NetSight needs seeded or known targets.
- [OPINION] The cheapest Pd/coverage proof is a seeded-target trial.
  - Lay objects of known size and position in a lake, harbour or university test basin.
  - Survey them with an Omniscan 450 SS on a BlueBoat-class platform at several ranges, speeds and seabed types.
  - Main capital cost is about USD 6–8k for sonar plus kit, before the boat. This matches the IHO-style "target detection" trial logic.
- [OPINION] GhostNetBusters is the best structural template: a public AI grant, an incumbent sonar-software SME, and a recovery NGO whose dives provide verification. NetSight could copy this structure with an Indian NGO, the Navy, or a port.

### Gaps
- I did not verify the IHO S-44 Edition 6 target-detection specification (cube sizes by Order) in a primary source.
- I found no published retrospective validation of AI on an offshore-wind UXO campaign where every target was investigated. These datasets sit with developers and UXO consultants and are not public.
- I found no Indian hire rates for a USV/ROV with side-scan, Sonobot, or Deep Trekker. No public price lists turned up. NIOT, IIT Madras and Planys would need direct quotes.
- I did not check prices for Deep Trekker, Humminbird or Lowrance.

## 2. Services-first models: evidence from geospatial, inspection and marine AI firms

### Takeaway
The strongest evidence says services-first is normal in this space. Ocean Geophysics, a UK marine-geophysics processor, built an ML boulder detector and explicitly does not sell it as a standalone product. Cyberhawk was "an inspection company first" for six years before launching iHawk software. Planys, an IIT Madras spin-out, sells inspection services and raised staged rounds up to a reported Rs 100 cr.

### Cited Findings
- Ocean Geophysics (Offshore Engineer, 7 Mar 2024) [VERIFIED]: [OE Digital](https://www.oedigital.com/news/512069-ai-tool-to-tackle-boulder-issues-for-offshore-wind-developments)
  - The tool is a machine-learning algorithm that auto-detects boulders down to 25 cm on side-scan lines, removes duplicates, and takes about one second per line.
  - The company describes its core business as "specialist processing, interpreting, and reporting of marine geophysical data".
  - The tool "will be integrated into that offering and will not be sold as a stand-alone product".
- Ocean Geophysics later reportedly set up a UXO clearance service for Dutch offshore wind [SUMMARY-ONLY]: [Marine Technology News](https://www.marinetechnologynews.com/news/tackle-boulder-issues-offshore-635133)
- Cyberhawk [SUMMARY-ONLY]: [World Pipelines](https://www.worldpipelines.com/business-news/20112018/cyberhawk-celebrates-a-decade-in-business/); [DataRoot Labs interview](https://datarootlabs.com/blog/chris-fleming-cyberhawk-interview)
  - Founded in 2008. First industrial UAV inspection in 2009.
  - Co-founder Malcolm Connolly: "an inspection company first and foremost". Data volume forced them to build their own software.
  - iHawk launched in 2014 for asset-integrity management, and later became "a major part of our business model". AI defect models were added later.
- Planys Technologies [SUMMARY-ONLY]: [YourStory 2018](https://yourstory.com/2018/02/underwater-robotics-planys-tech-series-a); [YourStory 2021](https://yourstory.com/2021/11/marine-robotics--planys-technologies-iit-madras); [Inc42](https://inc42.com/buzz/planys-raises-inr-43-cr-to-offer-underwater-infrastructure-testing-solutions); [iTWire](https://itwire.com/it-industry-news/strategy/planys-raises-%E2%82%B9100-crore-to-accelerate-global-expansion-and-launch-defence-arm,-planys-ark)
  - Spun out of IIT Madras CNDE and incubated at the IITM Incubation Cell. Incorporated June 2015.
  - Started with robotic inspection of ports and ships, then moved into oil and gas pipelines.
  - Funding history:
    - About USD 260k angel round (Keiretsu Forum), Dec 2015.
    - About Rs 14 cr Series A (ONGC Startup Fund, MEMG), 2018.
    - USD 1.6M pre-Series A (Keiretsu, LetsVenture, Shell), 2021.
    - Rs 43 cr led by Ashish Kacholia, which included "digital analytics and reporting platforms".
    - A reported Rs 100 cr round plus a defence subsidiary, Planys Ark. Dates for the last two rounds were not captured.
- Andrenam, a sonar-analysis AI company focused on defence and maritime surveillance, reportedly raised a USD 10M seed and an USD 18M Series A (Dealroom, Jul 2026). This is the product-first counter-example, and it is defence-funded [SUMMARY-ONLY; details unconfirmed]: [Dealroom](https://dealroom.co/news/140710-underwater-sensing-startup-andrenam-lands-18m-series-a-to-scale-pearl-bu/); [Zeitenwende](https://zeitenwendemedia.substack.com/p/andrenam-secures-10m-to-develop-first)

### Inferences
- [OPINION] The evidence favours a services-first "assurance desk" for NetSight.
  - Sell a fixed-price independent second-opinion review of a contractor's target list and coverage, delivered as a signed report.
  - Use the tool internally, as Ocean Geophysics does.
  - Productise into an API or desktop plugin only after about 10–20 paid jobs have produced labelled outcomes.
- [OPINION] Each job's outcomes (investigated or not, real or not) feed the calibration dataset. This answers both the "lack of data" and "easy copying" drawbacks: the moat becomes the outcome-labelled corpus and the track record, not the model architecture.
- [OPINION] Planys is the natural Indian partner or first customer. It already sells underwater inspection, mentions analytics platforms, and has defence links through Planys Ark. It is also a possible acquirer or competitor, so protect your IP before sharing models.

### Gaps
- I did not research Terra Drone, Skylark, Fugro spin-offs, or Fugro's own AI tooling.
- I found no quantitative evidence, such as a failure-rate study, on whether services-first succeeds more often in marine.

## 3. Partnerships: OEMs, contractors, universities, programmes

### Takeaway
Indian maritime incubation is now concrete. NTCPWC at IIT Madras (set up 2018, about Rs 77 cr, under Sagarmala/MoPSW) and a Cochin Shipyard and IIT Madras marine-startup programme (reported Rs 50 cr corpus) are the most relevant hosts. The GhostNetBusters model (research institute + sonar-software SME + NGO, with a public AI grant) is a documented partnership template. I found no public partnership terms (data-for-validation, revenue share or OEM licence) for sonar AI.

### Cited Findings
- NTCPWC at IIT Madras was set up in 2018 as an incubation centre. A Lok Sabha answer gives its cost as about Rs 77 cr. It sits under the Sagarmala Programme (Ministry of Ports, Shipping and Waterways), not MoES [SUMMARY-ONLY]: [NTCPWC](https://ntcpwc.iitm.ac.in/New/about.php); [Lok Sabha AU1271](https://eparlib.nic.in/bitstream/123456789/2973827/1/AU1271.pdf)
- Cochin Shipyard and IIT Madras signed an agreement to jointly support marine startups. IITM provides incubation, mentorship and training. A 2026 YourStory article cites a Rs 50 cr corpus and lists underwater acoustics and autonomous marine vehicles as IITM research areas [SUMMARY-ONLY]: [Raksha Anirveda](https://raksha-anirveda.com/cochin-shipyard-iit-madras-sign-agreement-to-jointly-support-marine-start-ups/); [YourStory Apr 2026](https://yourstory.com/2026/04/bharat-innovates-2026-iit-madras-india-blue-economy-france)
- Deep Ocean Mission: the nodal institution is NIOT (MoES). Its scope includes the manned submersible, desalination and OTEC. The one startup example found, Virya Paramita Energy, co-developed a wave-energy converter with IITM under a joint development agreement [SUMMARY-ONLY]: [YourStory Apr 2026](https://yourstory.com/2026/04/bharat-innovates-2026-iit-madras-india-blue-economy-france)
- GhostNetBusters [SUMMARY-ONLY]: [GEOMAR](https://www.geomar.de/en/ghostnetbusters); [sonoware](https://sonoware.de/news/2024-08-28_foerderzusage_ghostnetbusters)
  - Partners: GEOMAR (lead), sonoware GmbH (sonar-software SME), and One Earth – One Ocean e.V. (manual net recovery and dive verification).
  - The output was released as open source.

### Inferences
- [OPINION] Typical term shapes (none of these terms were found in sources):
  - Survey contractors or developers: a data-for-validation NDA. NetSight gets historical side-scan data plus investigation outcomes. The partner gets a free retrospective assurance report and a perpetual licence for internal use.
  - OEMs (Cerulean, Deep Trekker): a co-marketing or plugin arrangement, not exclusivity.
  - Universities: a joint grant application with IP split under the incubator's policy.
- [OPINION] Avoid exclusive OEM licences early. "Independent assurance" loses credibility if NetSight is tied to one vendor.
- [OPINION] NTCPWC suits ports and Sagarmala customers. The Cochin Shipyard and IITM programme gives a path to naval and shipyard users.

### Gaps
- I found no public contract terms for sonar data-sharing or co-development.
- I did not research EdgeTech, Klein, EvoLogics, Deep Trekker or Blueprint partner programmes.
- I did not research NOAA, NIO or IISc collaboration routes.

## 4. Funding and support (India and global)

### Takeaway
- iDEX gives up to Rs 1.5 cr (SPARK/DISC/Open Challenge) and up to Rs 10 cr (iDEX Prime), paid in milestone tranches.
- ADITI 4.0 offers up to Rs 25 cr, capped at 50% of the product-development budget. It closed on 4 May 2026, and its approved budget runs only to FY2025-26.
- The Startup India Seed Fund offers up to Rs 20 lakh grant plus Rs 50 lakh debt or convertible.
- NIDHI-PRAYAS is commonly cited at up to Rs 10 lakh. One source claims Rs 20 lakh, which is uncorroborated.
- Several ocean accelerators seen for 2026 had already closed or were US/Canada-only.

### Cited Findings
- iDEX SPARK (DISC / Open Challenge) gives grants up to Rs 1.5 cr. iDEX Prime gives up to Rs 10 cr for TRL 4 and above [SUMMARY-ONLY; idex.gov.in fetch timed out]: [DDP MoD iDEX](https://ddpmod.gov.in/offerings/schemes-and-services/idex); [iDEX FAQ](https://idex.gov.in/faq); [myScheme](https://www.myscheme.gov.in/schemes/idex)
  - The iDEX FAQ lists milestone tranches: Milestone 0 at 10%, the intermediate milestones at 20% each, and Milestone 5 at 10%.
  - Sources conflict on equity. One says DIO takes no equity; another mentions "equity or other relevant structures". Read the grant agreement.
  - I could not verify a 50% co-funding requirement for SPARK or Prime.
- ADITI 4.0 [SUMMARY-ONLY]: [ADITI scheme PDF](https://www.idex.gov.in/uploads/page/aditi_scheeme.pdf); [StartupGrantsIndia](https://www.startupgrantsindia.com/aditi-4-0-challenge-grant-program-defence-innovation-organisation-idex-422)
  - Up to 50% of the product-development budget, maximum Rs 25 cr per applicant, milestone-based.
  - Up to two winners per challenge.
  - Requires DPIIT recognition, or an Indian company or MSME.
  - Scheme budget Rs 750 cr for FY2023-24 to FY2025-26.
  - ADITI 4.0 closed on 4 May 2026. I found no confirmation of funding after FY2025-26.
- Some aggregators list an iDEX Open Challenge cycle ending 30 June 2026. That date has passed. Watch for the next DISC round [SUMMARY-ONLY]: [Startupflora](https://startupflora.com/blog/idex-challenge-guide-2026)
- Startup India Seed Fund Scheme: up to Rs 20 lakh grant (PoC, prototype, trials) and up to Rs 50 lakh debt or convertible debentures, disbursed through incubators [SUMMARY-ONLY]: [KIIT-TBI via StartupGrantsIndia](https://www.startupgrantsindia.com/providers/kiit-tbi/startup-india-seed-fund-scheme)
- DST NIDHI-PRAYAS is generally cited as up to Rs 10 lakh for prototyping through host incubators. Startupfeed.in alone claims an increase to Rs 20 lakh plus a Rs 40 lakh deep-tech tier, which is uncorroborated [SUMMARY-ONLY]: [Ahmedabad Univ.](https://ahduni.edu.in/academics/schools-centres/venturestudio/startup-opportunities/nidhi-prayas/); [IITH NIDHI-PRAYAS policy](https://itic.iith.ac.in/downloads/Nidhi%20Prayas%20Policy.pdf); [startupfeed (outlier)](https://startupfeed.in/?p=10454)
- Ocean accelerators seen in 2026 search results [SUMMARY-ONLY]:
  - VentureWell Ocean Enterprise Accelerator: deadline 7 Jul 2026, US applicants only.
  - Blue Action Canada: closed 15 Feb 2026.
  - Nordic Blue (A'Pelago): closed 5 Dec 2025.
  - Seaworthy Collective's 2026 incubator.
  - Sources: [Opportunity Desk](https://opportunitydesk.org/2026/06/15/venturewell-ocean-enterprise-accelerator-2026/); [Ocean News](https://oceannews.com/news/science-technology/seaworthy-collective-opens-applications-for-2026-ocean-enterprise-studio-incubator/); [Entnerd](https://entnerd.com/en/applications-now-open-for-the-nordic-regions-first-blue-economy-accelerator/)
- UK Innovate UK Business Connect ran an "IX challenge" on marine UXO removal for offshore wind farms. It shows that UK challenge calls exist on this exact problem. Eligibility and current status were not checked [SUMMARY-ONLY]: [IUK Business Connect](https://iuk-business-connect.org.uk/opportunities/ix-challenge-marine-unexploded-ordinance-removal-for-offshore-wind-farms/)
- Hydrosurv won Offshore Wind Growth Partnership (OWGP) funding in Jan 2026 for offshore seabed-mapping work. This is a UK supply-chain grant route [SUMMARY-ONLY]: [Workboat365](https://workboat365.com/hydrosurv-wins-owgp-funding-to-transform-offshore-seabed-mapping)
- Schleswig-Holstein's AI fund gave EUR 221k to GhostNetBusters, an example of a regional AI grant in a target market [SUMMARY-ONLY]: [sonoware](https://sonoware.de/news/2024-08-28_foerderzusage_ghostnetbusters)

### Inferences
- [OPINION] Suggested funding stack, in order:
  1. Incubator entry at IITM IC, NTCPWC or the Cochin Shipyard–IITM programme, which unlocks NIDHI-PRAYAS and the SISFS grant (about Rs 10–20 lakh each).
  2. An iDEX DISC or Open Challenge (up to Rs 1.5 cr) when a Navy problem statement on seabed mine or object classification, or search-and-recovery, appears.
  3. iDEX Prime or ADITI only after TRL 4+.
- [OPINION] The defence route speeds up funding but raises the compliance burden (section 5). Keep the civil assurance product separate from any defence variant, in code, data and corporate entity. This mirrors Planys Ark.

### Gaps
- Not researched in this budget:
  - TDB, MeitY SAMRIDH and TIDE 2.0, and MoES Deep Ocean Mission startup calls.
  - Sagarmala or Maritime India Vision 2030 innovation funds, and port challenges.
  - EU Horizon / Mission Ocean, BlueInvest, Katapult Ocean, 1000 Ocean Startups, Ocean Exchange.
  - NOAA SBIR (requires a US entity).
  - Microsoft, AWS and Google startup credits.
- No current open deadlines were confirmed for any Indian scheme.

## 5. Legal and compliance: export control, data, liability

### Takeaway
- **US EAR:** side-scan sonar and SAS fall under ECCN 6A001.a.1 only if they meet technical thresholds. One threshold is design for depths over 500 m, and there are resolution criteria. Low-cost shallow units like the Omniscan are probably outside it, but this needs checking.
- **India:** the SCOMET list controls dual-use items including software and technology. Sensors sit in Category 8, but I did not confirm the exact sonar entry.
- **Liability in UXO work** runs under the ALARP framework of CIRIA C754 (2015). A tool output must be framed as risk-reduction evidence, never as "all clear".

### Cited Findings
- EAR 6A001.a.1.a.3 covers side-scan or synthetic aperture sonar for seabed imaging when specified parameters are met. One is "designed or modified to operate at depths exceeding 500 m"; across-track resolution is defined as 75 / bandwidth (kHz). These sources are archived 2001–2012 CCL texts and the current text may differ [SUMMARY-ONLY]: [archived BIS CCL Cat 6 (2013)](https://webarchive.library.unt.edu/web/20130216093249/http:/www.bis.doc.gov/policiesandregulations/ear/ccl6.pdf); [HK STC Cat 6](https://www.stc.tid.gov.hk/english/checkprod/files/cat6.pdf)
- Software for controlled sonar is normally handled in the 6D entries. I did not confirm this against the current CCL [SUMMARY-ONLY, inference from search summary]: [UMass Dartmouth export control](https://www.umassd.edu/research/institutional-compliance/export-control/program-guidelines/protocol-specific-considerations/)
- SCOMET is India's dual-use, munitions and nuclear list, Categories 0–8, in Appendix 3 of Schedule 2 of ITC(HS). Exports of listed items need authorisation, and so does export of technology for listed items. An Inter-Ministerial Working Group reviews applications and the DGFT SCOMET Cell issues authorisations [SUMMARY-ONLY]: [DGFT FTP Chapter 10 (HBP 2026)](https://content.dgft.gov.in/Website/HBP_07_2026_Chapter_10.pdf); [Legal500](https://www.legal500.com/intelligence/india/international-law/export-control-in-india-the-%E2%80%98scomet'-list)
  - Category 7 was populated in Sept 2025 with emerging technologies.
  - In Nov 2025, DGFT consulted on a unified SCOMET application form ([ELP](https://elplaw.in/leadership/scomet-update-dgft-issues-trade-notice-seeking-inputs-on-draft-amended-aayat-niryat-forms-anf-one-format-for-all-kinds-of-applications-for-grant-of-scomet-authorisation-for-export-of-scomet-item/)).
  - In June 2026, India eased dual-use export rules for 41 countries ([India Sea Trade News](https://indiaseatradenews.com/india-eases-export-rules-for-dual-use-technology-to-41-countries/)).
- CIRIA C754 (2015), "Assessment and management of UXO risk in the marine environment", was prepared with Royal HaskoningDHV and 6 Alpha. It addresses responsibilities, liabilities and risk-transfer mechanisms including insurance. Industry practice is mitigation to ALARP, followed by a sign-off certificate, and targets from non-intrusive survey go on to intrusive investigation [SUMMARY-ONLY]: [CIRIA project page](https://www.ciria.org/CIRIA/Research/Projects_underway2/UXO_offshore_developments.aspx); [OE Digital](https://www.oedigital.com/news/450209-uxo-guidance-issued); [1st Line Defence](https://www.1stlinedefence.co.uk/services/marine-and-offshore-unexploded-ordnance-uxo-services/)
- NOAA survey data carry "not to be used for navigation" use restrictions [SUMMARY-ONLY]: [data.gov](https://catalog.data.gov/dataset/h12525-nos-hydrographic-survey-2013-06-131)

### Inferences
- [OPINION] Suggested disclaimer wording: "NetSight provides a probabilistic second-opinion assessment of the supplied data. It does not certify absence of objects. Residual risk remains and must be managed by the duty holder under the project's ALARP process."
  - Do not output words like "clear" or "safe".
  - Report Pd/coverage with confidence intervals and the stated target size and class.
- [OPINION] Keep the defence variant (mine-like-object ATR trained on Navy data) in a separate codebase and entity. Otherwise the civil product could become SCOMET- or MoD-restricted, which would kill exports to EU or UK offshore wind clients.
- [OPINION] Get a formal export classification, from DGFT for SCOMET and through a BIS CCATS if you are handling US-origin data or tech, before the first foreign contract.

### Gaps
- I did not confirm the exact current SCOMET entry for sonar or sonar software, or the current EAR 6D/6E text.
- I did not check Indian Navy data-security rules for hydrographic data, or National Hydrographic Office (NHO) data policy.
- I found no evidence on professional indemnity insurance for survey QA (insurers, premiums). C754's actual liability text was not accessible.

## 6. Second sensor, staged roadmap, team

### Takeaway
I found only indirect evidence on the second sensor:
- Boulder and UXO practice combines side-scan with multibeam and magnetometer data.
- The UXO workflow paper says AUV multibeam plus camera and mag data are needed to ground-truth annotations.
- A SAS false-alarm network gave 50% false-alarm reduction.

I found no evidence on team composition or recruitment.

### Cited Findings
- UXO detection workflow fuses multibeam with AUV ground truth. Verification needs camera and magnetic data [SUMMARY-ONLY]: [ResearchGate](https://www.researchgate.net/publication/356038528_Workflow_towards_autonomous_and_semi-automized_UXO_Survey_and_Detection)
- Side-scan is the standard boulder-detection method for wind and cable planning [VERIFIED]: [OE Digital](https://www.oedigital.com/news/512069-ai-tool-to-tackle-boulder-issues-for-offshore-wind-developments)
- A SAS ATR false-alarm network gave an average 50% false-alarm reduction [SUMMARY-ONLY]: [Heriot-Watt](https://researchportal.hw.ac.uk/en/publications/reducing-false-alarms-in-automated-target-recognition-using-local/)
- Cerulean also sells the Omniscan 450 FS, a forward-looking ROV sonar, at about USD 1,750–3,757 retail. It is a cheap entry point for search-and-recovery [SUMMARY-ONLY]: [Geo-matching](https://geo-matching.com/products/omniscan-450-fs); [Adorama](https://www.adorama.com/chasing-omniscan-450-fs-sonar-m2-pro-max-rov-100m-range/p/chsos450fsc1)

### Inferences
- [OPINION] Second sensor for the offshore-wind/cable niche: multibeam backscatter and bathymetry.
  - It is co-acquired on nearly every wind and cable survey, so no new data collection is needed.
  - Contractors already cross-check side-scan contacts against multibeam.
  - SAS data is rarer and more defence-linked.
- [OPINION] Second sensor for search-and-recovery: forward-looking ROV sonar (Omniscan FS, Oculus). It is cheap, and it is used at the verification step.
- [OPINION] Magnetometer fusion matters most for UXO and is a strong stage-3 candidate.

**[OPINION] Staged 18–24 month roadmap**

The evidence anchors for this roadmap are: NOAA public data with contact listings (Stage 0), the Ocean Geophysics and Cyberhawk services-first pattern (Stage 2), iDEX/SISFS/NIDHI amounts (funding), and C754 ALARP framing (liability).

| Stage | Months | Goal | Milestones | Kill criteria |
|---|---|---|---|---|
| 0 | 0–4 | Retrospective calibration on public data | Pull 20–40 NOAA NOS surveys with DR contact listings. Train or calibrate a contact-realness model. Publish reliability diagrams and a short paper or preprint. Enter incubator (IITM IC or NTCPWC). Apply to NIDHI-PRAYAS / SISFS. | Calibration is no better than a simple baseline, for example Pfa not reduced at matched Pd, compared with the roughly 93% Pd / 6% Pfa reported in the SAIC NOAA work. Or no usable contact listings in more than 10 surveys. |
| 1 | 3–9 | Seeded-target Pd trial | Buy or borrow an Omniscan 450 SS plus a small USV (about USD 6–8k for the sonar) or partner with NIOT/IITM/Planys. Lay known targets in a lake or harbour. Produce a Pd-vs-range/size/speed coverage map. | Predicted Pd maps do not match observed detection within agreed confidence bounds. Or the trial cannot be run because there is no partner vessel and no grant. |
| 2 | 6–15 | Services-first paid pilots | Fixed-price independent "target-list and coverage review" for 2–3 clients (Indian ports or dredging, Planys or a survey contractor, one EU/UK wind or cable consultant). Collect investigation outcomes under data NDAs. | Fewer than 2 paying pilots by month 15. Or clients refuse to share outcome data, which means no moat. |
| 3 | 12–20 | Add multibeam backscatter; defence track | Fuse multibeam backscatter and bathymetry with side-scan. Apply to an iDEX DISC or Open Challenge if a relevant Navy statement appears, using a separate defence workstream. | Fusion gives no measurable calibration or Pd gain. Or export-control classification blocks civil exports. |
| 4 | 18–24 | Productise | Plugin or API for contractors, based on at least 10 labelled jobs. Seed raise or iDEX Prime (TRL 4+). PI insurance in place. | No repeat customers. Or a competitor (for example Ocean Geophysics-type in-house tools) bundles equivalent calibration for free. |

### Gaps
- I found no sources on team composition or recruiting hydrographers (IHO Cat A/B, retired Navy or NIOT advisors).
- I found no cost comparison of SAS vs multibeam vs forward-looking sonar data acquisition.
- The roadmap is opinion built on the cited anchors. It is not evidence-validated.
