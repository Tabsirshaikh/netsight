# Startups, competitors and go-to-market for AI sonar / underwater survey review (as of 1 Nov 2026)

Method note: ~27 web searches/fetches. Most findings come from search-result summaries of trade press (Marine Technology News, Ocean News, Hydro International, Unmanned Systems Technology) and press releases. Where I fetched a page directly it is marked "fetched". Several sites returned HTTP 403 (businesswire, unmannedsystemstechnology FarSounder page, Hydro International object-recognition article), so those were not read in full. Source type labels: [P] = primary (company/government/filing/press release), [S] = summary/aggregator/trade press, [V] = vendor claim.

## 1. Which startups/companies sell AI sonar interpretation or underwater survey data software? (funding, customers, business model, outcome)

### Takeaway
No independent, venture-backed company selling only AI side-scan/SAS review software with a visible, growing civilian revenue base turned up. The money sits in (a) defence autonomy/ATR software (SeeByte, Greensea IQ), (b) survey-data-as-a-service/platform plays (Terradepth, Bedrock Ocean), (c) hardware-plus-service firms (Planys, Ocean Infinity), and (d) sonar OEMs bundling ATR into their own software (MIND/Klein SpectralAi, EvoLogics, FarSounder, Ocean Geophysics). Consolidation is the dominant "exit": Kraken bought the Sonardyne/EIVA/Voyis/Wavefront group in 2026, while Rovco/Beam collapsed into administration and Nauticus shows going-concern risk.

### Cited Findings

**Defence autonomy / ATR software**
- SeeByte (Edinburgh, Heriot-Watt spin-out) was acquired by Bluefin Robotics (then Battelle-owned) in a deal reported 7 Oct 2013; it kept staff, offices and platform-agnostic products (SeeTrack Military, AutoTracker, CoPilot); price not disclosed — [OE Digital, fetched, S](https://www.oedigital.com/news/457500-bluefin-robotics-acquires-seebyte). Press release title "Bluefin Acquires SeeByte" — [GlobeNewswire, P (not read)](https://www.globenewswire.com/press-release/bluefin-acquires-seebyte-adding-new-software-capabilities-maritime-robotics-portfolio-1838357.htm).
- SeeByte's later activity: 2022 US Navy contract to upgrade Neptune mission-level autonomy and develop ATR modules for the MK18 UUV family — [Unmanned Systems Technology, S](https://www.unmannedsystemstechnology.com/2022/11/upgrade-for-us-navy-uuv-autonomy-capabilities/); Neptune used in a US/UK/NL collaborative mission at REPMUS 2023 per a search summary — [BlueZone Group, S](https://bluezonegroup.com.au/announcements/mission-autonomy-in-mine-countermeasures-coordinating-the-uncrewed-fleet/). Revenue model = government/navy contracts. Current ownership (post-2013) not verified; my search found no evidence of a Saab acquisition (Saab bought a different UK AI firm, BlueBear, in 2023, which had a joint MoD contract with SeeByte) — [Defense News, S](https://www.defensenews.com/global/europe/2023/08/31/saab-buys-british-artificial-intelligence-specialist-bluebear/).
- Greensea IQ: mostly US Navy/USMC contracts, no equity round found. $18.15M, 7-year sole-source IDIQ for Bayonet underwater controller (reported 1 Jul 2026) — [Unmanned Systems Technology, S](https://www.unmannedsystemstechnology.com/2026/07/greensea-iq-awarded-contract-for-subsea-autonomy-controller-development/) and [Marine Technology News, S](https://www.marinetechnologynews.com/amp/news/greensea-contract-663908); $9M USMC task order for Bayonet 250 robots (2025) — [Ocean News, S](https://oceannews.com/news/defense/greensea-iq-awarded-us-marine-corps-contract-for-continuing-acquisition-of-bayonet-250-robots/); ~$2.8M IQNS for Navy MK20 Defender — [Ocean News, S](https://oceannews.com/news/defense/greensea-iq-secures-2-79m-contract-for-iqns-for-us-navy/). A contract tracker lists FY2025 federal obligations of $12.5M across 8 contracts — [HigherGov, S](https://www.highergov.com/awardee/greensea-systems-inc-10038962/).
- Planys (India) defence arm Planys Ark: UUVs for mine countermeasures/ISR; three iDEX challenge wins (see section 5) — [CXOToday, fetched, S](https://cxotoday.com/media-coverage/planys-raises-₹100-crore-to-accelerate-global-expansion-and-launch-defence-arm-planys-ark/).

**Data platform / survey-data-as-a-service**
- Terradepth (Austin): CB Insights says $28.35M raised over 8 rounds, latest Series A-III Aug 2023; IPO Club says $20M Series A (Apr 2022); ~50 employees in 2025 — summary via search, [CB Insights, S](https://www.cbinsights.com/company/terradepth/financials). Launched Absolute Ocean cloud platform 15 Nov 2024 for offshore energy (ingests bathymetry, sonar, video; pricing not stated) — [OE Digital, fetched, S](https://www.oedigital.com/amp/news/519273-terradepth-launches-cloud-based-ocean-mapping-tool-for-offshore-energy-firms). 2025: five-year contract for vertically integrated "Ocean Data as a Service" — [BusinessWire via Mammoth Times, P](https://business.mammothtimes.com/mammothtimes/article/bizwire-2025-5-21-terradepth-awarded-5-year-contract-in-global-offshore-energy). Apr 2026: Absolute Ocean placed in NIWC Atlantic RCC Hopper, letting Navy sponsors sign prototype OT agreements for up to 24 months; company says it runs on AWS GovCloud and Navy enclaves — [BusinessWire, P (403, seen via search snippet)](https://www.businesswire.com/news/home/20260409951116/en/). In 2022 it bought three Teledyne Gavia AUVs — [Unmanned Systems Technology, S](https://www.unmannedsystemstechnology.com/2022/02/gavia-auvs-provided-to-maritime-survey-operator/). Status: active, no shutdown/acquisition found. Note the path from AUV-hardware ODaaS toward a software platform plus Navy prototype deals.
- Bedrock Ocean (California): $25M Series A-2 (June 2025) led by Primary and Northzone; earlier $25.5M Series A (2023), total ~$35.5M per one source; proprietary mission software + AUVs; offshore wind, O&G, environmental, defence; no customer names found — [Built In, S](https://builtin.com/articles/bedrock-ocean-raises-25m-20250611), [Ocean News, S](https://oceannews.com/news/subsea-and-survey/bedrock-raises-25-5-million-in-series-a-funding-round-to-revolutionize-seafloor-exploration-and-accelerate-offshore-wind-energy-development/). Business model = data/survey service with own robots, not stand-alone software.
- HydroSight (Haifa): founded late 2025 (Tomer Adler CEO, Haitham Ezzy CTO, Chen Megera COO); $5M seed announced 7 Sep 2026 led by StageOne Ventures with Vertex Ventures and National Center of Blue Economy (HiCenter Ventures); AI platform that fuses multi-source/multi-epoch marine survey data and flags changes/anomalies; B2B enterprise sales to ports, energy, telecom-cable operators; says it is already running projects with infrastructure owners in Israel and abroad (customers unnamed) — [Calcalist, fetched, S](https://www.calcalistech.com/ctechnews/article/syzscx2oge); also [Dealroom listing](https://app.dealroom.co/companies/hydrosight_1). This is the closest 2026 venture-backed comparator to the student idea (survey-data AI, civil infrastructure buyers, software only). Too new to show outcomes.
- AndrenaM (Colorado, ex-SpaceX founders): $10M seed in ~36 hours (reported 17 Jun 2025), led by First Round Capital; AI on hydrophone/passive-sonar data for a distributed "sonar mesh"; defence/port-security use cases; no customers named; plans own buoys (vertical integration) — [American Bazaar, fetched, S](https://americanbazaaronline.com/2025/06/17/former-spacex-engineers-startup-andrenam-raises-10-million-in-just-over-a-day-463798/). Passive/defence, not survey review.

**Sonar OEM / bundled AI (incumbent competition)**
- MIND Technology / Klein: SpectralAi suite (Scribe annotation, Nexus CNN training, Scribe ATR) for side-scan; after Klein was sold to General Oceans, MIND licensed the suite to General Oceans — [BlueZone Group, S](https://bluezonegroup.com.au/announcements/mind-technology-spectralai-software); [Hydro International, S](https://www.hydro-international.com/content/article/object-recognition-for-side-scan-sonar-and-video-feeds). Shows ATR software being treated as a licensable asset.
- EvoLogics: onboard object recognition on Sonobot USV, trainable on new categories; Ocean Geophysics: boulder-detection AI (~1 s per side-scan line, [V]), not sold standalone but bundled into its interpretation/reporting services — both via [Hydro International listing, S](https://www.hydro-international.com/content/article/automated-side-scan-data-analysis) (search summary; article body not read). Boulder AI for offshore wind also at [OE Digital, S](https://www.oedigital.com/amp/news/512069-ai-tool-to-tackle-boulder-issues-for-offshore-wind-developments) (not read).
- FarSounder: Rhode Island Manufacturing Innovation Voucher (state grant, Jan 2026) to add AI target recognition to 3D forward-looking sonar; existing customers to get updates — [Ocean News, S](https://oceannews.com/news/science-technology/farsounder-awarded-manufacturing-innovation-voucher-to-advance-ai-based-sonar-capabilities/). Amount not retrieved.
- Exail bought simulated sonar data for ATR training — [Naval News, S](https://www.navalnews.com/?p=50680) (title only).
- Bibby Hydromap / STFC Hartree boulder-detection CNN (2020 case study) — [STFC Hartree, P](https://www.hartree.stfc.ac.uk/case-studies/2020/01/09/boulder-detection-from-seabed-sonar-images/): a survey contractor built it in-house.
- Ghost gear: GhostNetZero.ai is a WWF Germany project built with Accenture and Microsoft AI for Good Lab, ~90% detection (Microsoft preprint, not peer reviewed) / 94% (NVIDIA write-up), runs on existing side-scan data, divers verify — [Microsoft Research, P](https://www.microsoft.com/en-us/research/?p=1150234), [Oceanographic Magazine, S](https://oceanographicmagazine.com/news/artificial-intelligence-is-now-used-to-locate-ghost-nets-in-the-ocean/). GhostNetBusters (sonoware + GEOMAR) June 2024 to Dec 2025, grant funded — [sonoware, P](https://sonoware.de/news/2024-08-28_foerderzusage_ghostnetbusters). Ocean AID (Cyphersoft Inc., BC Canada): CA$75k NRC grant (Feb-Dec 2025) for CHIRP fish detection; Caplight lists ~US$31k raised; earlier roadmap aimed at licensing to sonar firms by 2026, no evidence found that was reached — [Government of Canada grants, P](https://search.open.canada.ca/grants/record/nrc-cnrc,172-2024-2025-Q4-1028483,current), [Caplight, S](https://www.caplight.com/company/oceanaid). Ghost-gear efforts are NGO/grant funded, not revenue businesses.

**Large/adjacent players (outcomes)**
- Kraken Robotics bought Covelya Group (parent of Sonardyne, EIVA, Voyis, Forcys, Wavefront Systems, Chelsea Technologies): signed 3 Mar 2026, C$615M (C$480M cash + C$135M shares), closed 2 Jul 2026; Covelya 2025 revenue guided C$249-275M, ~750 staff; Kraken closed a C$402.5M bought deal to fund it — [Kraken release via Barchart, P](https://www.barchart.com/story/news/545088/kraken-robotics-announces-signing-of-strategic-acquisition-to-expand-global-maritime-capabilities), [Hydro International, S](https://www.hydro-international.com/content/news/kraken-acquires-covelya-group-to-form-subsea-technology-powerhouse), [Ocean Science Technology (closing), S](https://www.oceansciencetechnology.com/news/kraken-robotics-completes-covelya-group-acquisition/). One Evertiq headline says "$430M"; likely a USD conversion (Robot Report cites ~US$432M) — [Robot Report, S](https://www.therobotreport.com/kraken-robotics-acquires-covelya-group-for-615m/). Implication: the incumbent sensor/software ecosystem (EIVA = survey software, Sonardyne MINTACS maker, Voyis imaging) is now under one acquirer with a defence orientation.
- Rovco / Vaarst (Beam): Rovco (Bristol, founded 2016) raised almost £50M across three rounds 2019-2024 (Foresight, Equinor, IQT), merged with AI company Vaarst in Sep 2024, then Beam trading as Rovco Ltd entered administration with 100+ redundancies (exact date not retrieved) — [Business Cloud, S](https://businesscloud.co.uk/news/rovco-administration-to-make-100-staff-redundant/). Biggest direct "AI + subsea survey" failure found.
- Nauticus Robotics (ex-Houston Mechatronics, Nasdaq: KITT): going-concern warnings; ~US$7M cash at end-2025 vs ~US$23M operating burn; cash US$1.4M by mid-2026; US$250M equity facility registered — aggregator summaries only, not primary filings (SEC CIK 0001849820): [Panabee, S](https://www.panabee.com/news/nauticus-robotics-earnings-q2-2026-report), [Quartr, S](https://quartr.com/events/nauticus-robotics-inc-kitt-registration-filing_oSeY5kDh). No bankruptcy filing found.
- Ocean Infinity: 14-vessel Armada fleet completed Dec 2025; funding/revenue not disclosed — estimates conflict ($50-69M+ funding; revenue anywhere from $25-50M to $105.7M); treat as unverified — [Breakbulk, S](https://breakbulk.news/ocean-infinity-closes-a-five-year-bet-on-robotics-with-final-armada-vessel-delivery/), [Robotics.press, S](https://www.robotics.press/news/ocean-infinity-company-profile/).
- XOCEAN (Ireland, USV data service): EUR7.9M round (existing shareholders) — [Marine Industry News, S](https://marineindustrynews.co.uk/xocean-secures-e7-9-million-funding-to-support-expansion/).
- Voyis: absorbed into Kraken via Covelya (above). One profile claims only an undisclosed 2018 T-Hub seed round — [Robotics.press, S, weak](https://www.robotics.press/news/voyis-company-profile/).

### Inferences
- Pure-play independent "AI for sonar review" software with disclosed meaningful revenue: none found. The few funded software-first names (HydroSight $5M seed, AndrenaM $10M seed) are 2025-26 vintage and unproven.
- ATR is being given away or bundled by OEMs (Klein/MIND, EvoLogics, FarSounder, Exail) and contractors (Ocean Geophysics, Bibby), which compresses stand-alone pricing.
- The pattern for survivors: government/defence contract flow (SeeByte, Greensea, Terradepth Navy path, Planys Ark) or acquisition by a hardware roll-up (Kraken/Covelya).

### Gaps
- Not found: Seabed.AI-type company, Cathx Ocean funding/outcome, Sea Machines, Fathom5, "Mariner AI", "Blue Ocean Monitoring", Blueprint Subsea, Seatronics, Ocean Aero, Exail/Thales/ECA/SAAB/CMRE ATR revenue, Sonardyne MINTACS commercial details. Not searched individually due to tool-call budget; no sources retrieved, so no claims made.
- SeeByte ownership after 2013 and any later sale: not verified.
- Customer names for HydroSight, Bedrock, AndrenaM: not disclosed.
- Rovco/Beam administration date and administrators: not retrieved.
- Pricing/ARR for any AI sonar product: not found.

## 2. Defence/government vs commercial revenue; is civilian AI sonar review venture-scale?

### Takeaway
Revenue evidence skews to defence/government (Greensea, SeeByte, Terradepth's Navy route, Planys Ark's iDEX/UUV push, AndrenaM's defence-tech investors). No evidence found that civilian AI sonar review alone has produced a venture-scale outcome; civilian players that raised (Bedrock, Terradepth, Rovco) all bundle data collection/hardware and the one with ~£50M raised failed.

### Cited Findings
- Greensea IQ's visible revenue is Navy/USMC contracts (see section 1) — [Marine Technology News, S](https://www.marinetechnologynews.com/amp/news/greensea-contract-663908).
- Terradepth's Absolute Ocean positioned for Navy via RCC Hopper OT agreements, up to 24 months, after launching for offshore energy in Nov 2024 — [BusinessWire, P](https://www.businesswire.com/news/home/20260409951116/en/), [OE Digital, S](https://www.oedigital.com/amp/news/519273-terradepth-launches-cloud-based-ocean-mapping-tool-for-offshore-energy-firms).
- Kraken cited expanding addressable market in defence and maritime surveillance as deal rationale — [Kraken release via Barchart, P](https://www.barchart.com/story/news/545088/kraken-robotics-announces-signing-of-strategic-acquisition-to-expand-global-maritime-capabilities).
- Planys: Ark subsidiary built for defence UUVs (MCM, ISR) while core revenue is industrial inspection — [CXOToday, S](https://cxotoday.com/media-coverage/planys-raises-₹100-crore-to-accelerate-global-expansion-and-launch-defence-arm-planys-ark/).
- Rovco/Beam: ~£50M raised, £8.1M pre-tax loss in 2023 and £8.7M in 2022, then administration — [Business Cloud, S](https://businesscloud.co.uk/news/rovco-administration-to-make-100-staff-redundant/).
- Offshore-wind UXO/boulder programs are currently public-funded R&D (Innovate UK challenge, Fraunhofer IRAV2) and incumbents (N-Sea Magsense, Rovco, Fugro) hold the contracts; no AI-UXO startup with funding found — [IUK Business Connect, P](https://iuk-business-connect.org.uk/opportunities/ix-challenge-marine-unexploded-ordinance-removal-for-offshore-wind-farms/), [Fraunhofer IWES, P](https://www.iwes.fraunhofer.de/en/research-projects/current-projects/irav2.html). GEOMAR notes most survey contacts are non-UXO scrap/boulders, i.e., a false-positive cost problem — [GEOMAR paper, P](https://oceanrep.geomar.de/id/eprint/55572/1/TacklingCostDriversofMaritimeEXOSurveys.pdf).

### Inferences
- Civilian review software addresses a labour-cost line inside survey contractors' budgets. I found no market-size evidence in this pass that it supports venture-scale revenue alone; a defence/dual-use route or acquisition by an OEM looks more plausible than independent scaling.

### Gaps
- No quantitative split of defence vs civilian revenue for any company; no market-size source retrieved for civilian sonar post-processing.

## 3. How independent software vendors reach customers (plug-ins, APIs, OEM, DaaS); licensing/API constraints

### Takeaway
HYPACK has a gated SDK with explicit terms (including a ban on using SDK materials to train/fine-tune AI/ML). I could not confirm any public SonarWiz plug-in API, QPS or CARIS APIs. Evidence of real channels: OEM licensing (MIND to General Oceans), bundling into services (Ocean Geophysics), and platform/DaaS (Terradepth, HydroSight).

### Cited Findings
- HYPACK SDK (Xylem): not publicly downloadable, access on request; reviews may deny/defer; a HYPACK licence alone does not entitle SDK access; contents are docs, interface definitions/APIs, samples, driver guidance; you own what you build, HYPACK owns SDK and embedded code; distribution to other HYPACK customers requires disclosure as third-party software; selling/bundling (e.g., with hardware) requires a separate written agreement; "SDK materials may not be used to train or fine-tune AI or machine learning systems"; no formal partner programme described — [Xylem HYPACK, fetched, P](https://www.xylem.com/en-qa/brand/hypack/integrate-with-hypack/).
- SonarWiz (Chesapeake Technology): supports sidescan, sub-bottom, swath bathymetry, single beam, magnetometer; v7.7 added cloud (AWS) support; dongle-free licences from 7.1. No plug-in/SDK documentation turned up in search — [Chesapeake Technology, P](https://chesapeaketech.com/), [Marine Technology News, S](https://www.marinetechnologynews.com/news/chesapeake-technology-releases-sonarwiz-606757).
- OEM licensing precedent: MIND licensed SpectralAi to General Oceans (acquirer of Klein) for side-scan — [BlueZone Group, S](https://bluezonegroup.com.au/announcements/mind-technology-spectralai-software).
- Bundling precedent: Ocean Geophysics' boulder AI will be integrated into its own interpretation/reporting service rather than sold standalone — [Hydro International, S](https://www.hydro-international.com/content/article/automated-side-scan-data-analysis).
- Training-data acquisition is a recognised barrier: Exail bought simulated sonar data for ATR — [Naval News, S](https://www.navalnews.com/?p=50680).
- Ocean AID's plan to license technology to sonar firms (target 2026) has no evidence of fulfilment — [Caplight, S](https://www.caplight.com/company/oceanaid).
- Data-format openness (XTF/JSF): not verified here. (Common knowledge, uncited: XTF is Triton's published format and JSF is EdgeTech's; confirm before relying.)

### Inferences
- A tool that reads exported XTF/JSF/GeoTIFF mosaics and writes back vendor-neutral annotations (shapefile/GeoJSON/CSV) avoids dependence on any plug-in programme and the HYPACK no-AI-training clause; this is the lowest-friction integration path but gives weaker workflow lock-in.
- HYPACK-SDK-derived data must not be used for model training; keep training data independent of SDK materials.

### Gaps
- SonarWiz, QPS Qimera/QINSy, CARIS (Teledyne), EIVA NaviSuite plug-in/API terms and marketplaces: not found. XTF/JSF specification openness: not verified. Data-as-a-service pricing: not found.

## 4. Defensible niches (assurance/QA layer, ghost gear, UXO/boulders, rapid triage, audit-grade coverage certificates)

### Takeaway
Evidence is thin for all niches; none has an independent funded startup with proven revenue. Strongest signals: boulder/UXO review has real cost pain and active incumbents; ghost gear has strong NGO interest but grant funding; sensor-agnostic multi-survey change/anomaly platforms (HydroSight) are the nearest funded analogue.

### Cited Findings
- Sensor-agnostic / multi-source: HydroSight's pitch is exactly fusing multi-source, multi-time marine survey data into a maintained seabed map and flagging changes, funded $5M seed Sep 2026 — [Calcalist, S](https://www.calcalistech.com/ctechnews/article/syzscx2oge).
- Ghost gear: GhostNetZero.ai (NGO, free-to-ecosystem, ~90-94% claimed [V]) and GhostNetBusters (grant) already occupy the space; experts still verify flagged spots; buried nets vs cables are hard to separate — [Oceanographic Magazine, S](https://oceanographicmagazine.com/news/artificial-intelligence-is-now-used-to-locate-ghost-nets-in-the-ocean/), [sonoware, P](https://sonoware.de/news/2024-08-28_foerderzusage_ghostnetbusters).
- UXO/boulders: boulder detection AI exists at contractors and vendors (Ocean Geophysics, Bibby) and UXO automation is a public R&D priority — see section 2.
- Research caution: review of deep learning for side-scan/SAS notes even small CNNs beat conventional methods — [Engineering Applications of AI review via Hydro Intl search summary, S](https://www.hydro-international.com/content/article/automated-side-scan-data-analysis); SONARMUS EU project reported promising but limited AI results — [Hydro International, S](https://www.hydro-international.com/content/article/ai-ml-boosts-hydrographic-data-processing-in-sonarmus).
- Coverage certificates / audit-grade completeness / insurance: no source found showing demand or a vendor.
- Post-disaster rapid triage: no source found in this pass.

### Inferences
- Calibrated confidence and completeness maps are not marketed by any vendor I found; that may mean white space or may mean no buyer. This needs customer-discovery validation, not desk research.
- Offshore-wind boulder/UXO review plus "defensible deliverable for regulators/insurers" is a plausible wedge, but incumbents bundle AI inside services.

### Gaps
- No evidence on insurer/regulator/classification-society appetite for coverage certificates; no evidence either way on post-disaster triage buyers; no pricing benchmarks.

## 5. India-specific route (iDEX, ADITI, Deep Ocean Mission, NIOT, IIT Madras, Planys funding)

### Takeaway
Planys is the proof that Indian underwater-tech can raise money (INR 100 crore, Dec 2025) but it sells robots and inspection services, not sonar AI. iDEX/ADITI and NIOT/IIT Madras are real channels; I found no sonar-specific iDEX challenge or confirmed DOM startup scheme.

### Cited Findings
- Planys: INR 100 crore (~US$11-12M) primary round, Dec 2025, led by Ashish Kacholia and Lashit Sanghvi with Pratithi, Samarthya, 3i Partners, Letsventure and angels; earlier INR 43 crore in Apr 2024 (Kacholia-led); CB Insights lists Series B US$11.1M on 4 Dec 2025; total raised varies by tracker US$17.5M / US$20.0M / US$22.1M — [CXOToday, fetched, S](https://cxotoday.com/media-coverage/planys-raises-₹100-crore-to-accelerate-global-expansion-and-launch-defence-arm-planys-ark/), [Outlook Business, S](https://www.outlookbusiness.com/companies/planys-technologies-secures-43-crore-funding-led-by-ace-investor-ashish-kacholia), [CB Insights, S](https://www.cbinsights.com/company/planys-technologies/financials), [Hub71 via Sharikat Mubasher, S](https://en.sharikatmubasher.com/media-hub/news/21523849/hub71-startup-planys-secures-12mn-in-primary-funding).
- Planys customers named: Reliance, IOCL, BPCL, MSRDC, Indian Railways, ExxonMobil, Shell, Saudi Aramco, SABIC; 25,000+ operational hours at ~500 sites in 10+ countries; three iDEX challenge wins; planned UUV production facility in South Chennai — [CXOToday, S](https://cxotoday.com/media-coverage/planys-raises-₹100-crore-to-accelerate-global-expansion-and-launch-defence-arm-planys-ark/).
- Planys financials (Inc42, with internal inconsistency): FY25 revenue INR 12.8 Cr (+97%), net loss INR 2.2 Cr on the headline panel; INR 15.7 Cr revenue and INR 1.4 Cr loss in the FAQ panel; FY24 revenue ~INR 6.5-7.1 Cr — [Inc42, fetched, S](https://inc42.com/company/planys-technologies/financials/). Unreliable; verify via MCA filings.
- iDEX/DISC: Defence India Startup Challenge 4 (2020) sought underwater drones able to detect mines, grants up to INR 1.5 crore; ADITI edition 1.0 included a Jalkapi AUV prototype challenge; ~676 startups/MSMEs/innovators in iDEX ecosystem as of Feb 2026; a modular unmanned MCM suite partnership offered for Indian Navy — [MediaNama, S](https://www.medianama.com/2020/09/223-defence-ministry-challenge-startups-drones-satellite-imagery/), [SetIndiaBiz, S](https://www.setindiabiz.com/news/defence-startups-underwater-maritime-technology), [Marine Technology News, S](https://www.marinetechnologynews.com/amp/news/underwater-technology-partnership-pursue-664234). Also INDUS-X underwater challenges (US-India) — [NSIN, P](https://nsin.mil/news/2024-02-26-indusx-challenge-winners).
- Deep Ocean Mission: ~Rs 4,077 crore first five years, on-site business incubator facilities listed as a goal; NIOT focus areas include marine sensor systems and ocean acoustics; know-how transfer table to MSMEs/startups in a May 2026 NIOT presentation (sonar entries not visible); Gateway House notes India lacks ocean-tech startups to partner with — [MoES Rajya Sabha reply, P](https://www.moes.gov.in/sites/default/files/RS-in-English-978-10022022.pdf), [NIOT presentation, P](https://wise2026.tropmet.res.in/assets/docs/NIOT_Presentation.pdf), [Gateway House, S](https://gatewayhouse.in/indias-deep-ocean-mission-for-innovation).
- IIT Madras / Cochin Shipyard maritime startup funding and incubation pipeline (INR 50 crore corpus) — [YourStory, S (promotional)](https://yourstory.com/2026/04/bharat-innovates-2026-iit-madras-india-blue-economy-france).

### Inferences
- A software-only India entrant is unlikely to raise Planys-scale money on sonar AI alone; the credible early funding is grants (iDEX, ADITI, NIOT/DOM, IIT Madras incubation) plus a services/pilot revenue line with Indian ports, oil and gas, Indian Navy hydrography (NHO) and NIOT. Indian Navy/NHO sonar data access will likely be restricted for security reasons (not sourced).

### Gaps
- No sonar-specific iDEX/ADITI challenge found; no confirmed NIOT/MoES incubation scheme for sonar software; Indian Naval Hydrographic Office procurement route not researched; Planys FY25 numbers inconsistent.

## 6. Lessons: what killed or limited underwater-tech startups

### Takeaway
Capital intensity, a small number of buyers, and reliance on a few large contracts show up repeatedly; acquisition by hardware roll-ups is the main success path.

### Cited Findings
- Rovco/Beam: ~£50M raised, successive £8M+ annual losses, administration — [Business Cloud, S](https://businesscloud.co.uk/news/rovco-administration-to-make-100-staff-redundant/).
- Nauticus: ~US$23M operating burn vs ~US$7M cash (end-2025), 72% revenue concentration reported by one aggregator headline, going-concern doubt — [Panabee, S](https://www.panabee.com/news/nauticus-robotics-earnings-q2-2026-report).
- Terradepth moved from AUV-service hardware toward a cloud platform and government prototype vehicles (see section 1) while ~US$28M raised over 8 rounds ending Aug 2023 — [CB Insights, S](https://www.cbinsights.com/company/terradepth/financials).
- Consolidation: Kraken-Covelya (C$615M) and Klein sale to General Oceans with ATR licence-back — see section 1.
- Ocean AID: grant-sized funding and unmet licensing roadmap — [Caplight, S](https://www.caplight.com/company/oceanaid).
- Regulatory lock-in note: HYPACK SDK prohibits AI/ML training with SDK materials (section 3).

### Inferences
- Failure drivers consistent with the evidence: fleet/hardware capex, concentrated customers, long government cycles, and OEMs giving ATR away. Defence sales cycle length was not quantified by any source I retrieved.

### Gaps
- No sourced figures on defence sales-cycle duration; no post-mortems from founders; most "what happened" stories rely on trade press or aggregators.

## 7. Customer-discovery plan (15-20 organisations to interview; 5 demand-testing questions)

### Takeaway
No source gives a ready-made list; this is a recommended plan based on the landscape above. Named firms are drawn from findings in this file or are common industry names I did not verify as having the specific need.

### Cited Findings (basis for the list)
- Planys customer names: Reliance, IOCL, BPCL, MSRDC, Indian Railways — [CXOToday, S](https://cxotoday.com/media-coverage/planys-raises-₹100-crore-to-accelerate-global-expansion-and-launch-defence-arm-planys-ark/).
- Existing AI review users/competitors: Ocean Geophysics, Bibby Hydromap, MIND/General Oceans (Klein), EvoLogics, FarSounder — [Hydro International, S](https://www.hydro-international.com/content/article/automated-side-scan-data-analysis).
- Ghost-gear stakeholders: WWF Germany, sonoware, GEOMAR, Ocean AID — see section 1.
- Offshore-wind UXO/boulder actors: N-Sea, Rovco, Fugro — [Offshore Wind Biz, S](https://www.offshorewind.biz/?p=166439).
- Public-sector: NIOT, Innovate UK programme, Fraunhofer IWES — sections 4-5.

### Inferences (recommendations)
Interview list (aim for 15-20):
1. Survey contractors, global: Fugro, N-Sea, Ocean Geophysics, Bibby Hydromap, Ocean Infinity (data processing leads).
2. Indian/regional survey firms and ports (hydrographic survey leads at major ports, Indian Navy NHO if reachable, NIOT sonar/acoustics group, National Centre for Coastal Research).
3. Offshore wind developers' geoscience/UXO leads (UK/EU/Taiwan/India Gujarat-Tamil Nadu pipeline) and their survey QA consultants.
4. Software/OEM gatekeepers: Chesapeake (SonarWiz), HYPACK/Xylem, QPS, EIVA (now Kraken), Klein/General Oceans, EdgeTech, EvoLogics.
5. Ghost-gear: WWF Germany/GhostNetZero team, Ocean AID, a fisheries or coast-guard recovery lead.
6. Defence/government: Indian Navy mine-warfare/hydrography contacts via iDEX mentors, Planys Ark, a European MCM programme contact, Kraken Robotics (now owner of Wavefront/EIVA/Sonardyne).
7. Insurers/marine warranty surveyors, classification societies, and cable/pipeline operators (telecom cable operators are a HydroSight target).
8. Peer startups: HydroSight, Bedrock Ocean, Terradepth (positioning and channel lessons).

Five questions that test demand:
1. Walk me through the last survey you reviewed: hours spent per line-km on side-scan/SAS review, who did it, and what it cost?
2. What do you do today to prove to a client or regulator that an area was fully searched, and what has gone wrong with that proof?
3. Which software do you review in, and would you accept a tool outside it (export/import) or only an integrated plug-in?
4. What would you need to see (false-negative rate on your own data, calibration) before you trusted an AI "no target here"? Would you share anonymised data to test it?
5. Who pays for it (project budget, overhead, client-mandated) and what would you pay per line-km, per survey or per seat; what procurement path is required?

### Gaps
- Willingness-to-pay data absent from public sources; must come from interviews.
