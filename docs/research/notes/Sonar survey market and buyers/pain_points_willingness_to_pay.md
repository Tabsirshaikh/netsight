# Pain points and willingness to pay in sonar-based underwater search and survey (state as of Nov 2026)

Method note for the report writer: "Read" means I fetched and read the page or PDF text. "Search-summary" means the claim comes from a search-result summary and I did not read the full page; treat those as lower confidence and re-check before quoting. "Vendor" means a company describing its own product. Many hard numbers the brief asked for (day rates, cost per target, shortage of interpreters) were NOT found; see Gaps in each section.

## 1. Cost of false alarms (verifying a contact; UXO, mine-hunting, diver/ROV verification)

### Takeaway
The false-alarm problem is real and widely stated in offshore-wind UXO work: the large majority of listed targets turn out to be non-UXO, and each target needs ROV/diver/vessel time. However, I found NO published euro or dollar cost per target investigated, and no published ROV/diver/UXO-spread day rate. The money-at-stake evidence is indirect (vessel days scale with target count; jack-up and project-delay costs).

### Cited Findings
- Fugro (vendor, read) says "Up to 99 %" of targets dredged out following a survey are false positives (mostly debris such as anchors and chains), and, in a separate "Did you know" box in the same article, "95 %" of potential targets listed in a typical UXO survey are false positives. The article is internally inconsistent (99% vs 95%) and is marketing. — [Fugro long-read](https://www.fugro.com/news/long-reads/2021/five-key-uxo-considerations-for-successful-offshore-projects-fugro-longread)
- Same Fugro article: a survey that identifies 1,500 UXO targets "will require three times more vessel days" than one that finds 500 targets; Fugro claims a 75% reduction in false positives from its 3D imaging, used on about 2,000 targets. Vendor claim, no methodology. The article gives no monetary figures. — [Fugro long-read](https://www.fugro.com/news/long-reads/2021/five-key-uxo-considerations-for-successful-offshore-projects-fugro-longread)
- GEOMAR (peer-reviewed conference paper, read): "During UXO survey and clearance campaigns, a large number of false positive target points drive costs and efforts"; the majority of detected-then-investigated objects are non-UXO (anthropogenic scrap, boulders). The paper describes EU-funded BASTA project work: AI to generate target lists from multibeam data, data-quality factors, and an AUV with magnetometers and camera for autonomous target investigation. No euro cost figures in the paper. — [Frey et al., GEOMAR, Tackling Cost Drivers of Maritime EXO Surveys (PDF)](https://oceanrep.geomar.de/id/eprint/55572/1/TacklingCostDriversofMaritimeEXOSurveys.pdf)
- Target-to-UXO ratios from named projects (search-summary, secondary): Dudgeon offshore wind farm, 243 potential UXO targets, 20 needed clearance (about 8%); a Boskalis Baltic cable-route campaign examined 773 targets and recovered 25 UXO (about 3%). — [search results summarising Renewable Energy World / Boskalis articles](https://www.renewableenergyworld.com/?p=206652), [Boskalis via SWZ Maritime](https://swzmaritime.nl/news/2024/01/23/how-boskalis-searches-the-seabed-for-unexploded-ordnance/) (I could not read the Renewable Energy World page: HTTP 403)
- A 2026 SeaTerra presentation to the Baltic Sea Parliamentary/BSPC process states only about 6% of all targets turn out to be UXO (search-summary; I could not open the PDF, HTTP 525). — [BSPC document](https://resources.bspc.net/documents/utf-8Q20260517C2AD5FBSPC5Fv02pdf2.pdf)
- Land analogue (not marine): a Seequent/Geosoft trade report quotes an operator expecting about a 95% false-positive rate; at a 27-ha Vietnam site, 26,000 initial targets became 4,200 likely targets, of which 507 were real UXO (under 2%). Useful as order-of-magnitude only. — [Seequent, Currents, Bombs and ROVs (PDF, read)](https://files.seequent.com/PDFs/UXO-near-surface-marine-report.pdf)
- Campaign cost scale: UK Innovate UK challenge text says UXO removal for offshore wind is site-specific and "in most cases runs to six or seven figures" (search-summary of campaign-level cost, not a unit cost). — [Innovate UK KTN challenge](https://iuk-business-connect.org.uk/opportunities/ix-challenge-marine-unexploded-ordinance-removal-for-offshore-wind-farms/)
- Spread and delay costs (search-summary, secondary): Dominion Energy said its Dec 2025 stop-work order cost the CVOW wind project about $5 million per day; a jack-up can cost up to $350,000/day; a generic market report (no methodology) says a geophysical campaign for one lease area is $5-15 million over 60-120 days, with standby at 75-90% of the day rate. These are not sonar-contact-verification costs. — [gCaptain on Dominion](https://gcaptain.com/federal-work-halt-and-tariffs-push-dominions-offshore-wind-project-to-11-5b/), [Renewable Energy World](https://www.renewableenergyworld.com/?p=206652), [UNSPSC 72121602 report](https://storage.googleapis.com/unspsc_code/reports/72121602.html)
- Seequent article (read) says reducing target counts by 10% "can significantly reduce" marine UXO survey time and cost (qualitative). — [Seequent blog](https://www.seequent.com/optimizing-uxo-target-lists-with-alm-geophysics-library-of-previously-found-targets/)
- Mine countermeasures (defence): ATR literature stresses false-alarm control because otherwise ATR "adds time to the mission"; one Navy-sponsored briefing claims MCM timeline reduction "up to 50%" and another ATR result a PFA cut of 80% at PD 85%. These are vendor/government-research claims; no cost per contact prosecuted found. — [SeeByte whitepaper](https://www.seebyte.com/images/section/uploads/SeeByte-Whitepaper-A.I-in-the-Underwater-Battlespace-1-1.pdf), [Navy SBIR topic](https://www.navysbir.com/09_1/117.htm) (search-summary)
- Stolte et al. 2022 (diver verification about EUR 140/ha, 5 diving days for 49 positions): NOT verified. Several searches and two candidate Frontiers 2022 papers I opened (fmars.2022.873700 Bell et al.; fmars.2022.833617 Chatzievangelou et al.) are not it and contain no such figures. I cannot confirm the figure or the paper's identity.

### Inferences
- The best-evidenced false-alarm "price" is vessel-days-per-target: Fugro's 3x vessel days for 3x targets implies cost scales roughly linearly with target count, so a verified reduction in false targets maps directly to spread-days saved. To turn this into euros the team needs a spread day rate (not found) times average verification time per target (not found).
- The 3-8% real-UXO ratios from named projects (Dudgeon, Boskalis, SeaTerra) are better evidence than the vendor "95-99%" claim.
- Most of the false-alarm reduction in UXO is magnetometer plus multibeam/3D imaging work, not side-scan alone; a sonar-only AI product addresses only part of the target-list problem.

### Gaps
- No cost per target investigated (ROV, diver, or UXO specialist) from any primary source; no UXO-spread or diver day rates; Ordtek/6 Alpha/CIRIA C681/C754 documents were not retrieved.
- Stolte et al. 2022 numbers not found.
- No mine-hunting prosecution cost per contact (navy budget documents or GAO reports were not located).

## 2. Cost of missed objects / false all-clear, and legal coverage requirements

### Takeaway
The legal/standards hook for "searched everything" exists (IHO S-44 Special Order requires a full sea-floor search and detection of 1 m cubes; UXO work is governed by ALARP risk assessment), and specialist liability insurance for hydrographic surveyors exists. But I found no quantified claim values for a missed-object event (grounding on uncharted wreck, dredger/trawler strike, UXO detonation), so the size of the missed-object liability cost is undocumented here.

### Cited Findings
- IHO S-44 Special Order: system detection capability for cubic features larger than 1.0 m; Order 1a larger than 2.0 m (to 40 m depth); full sea-floor search required for Special Order and Order 1a, not for Orders 1b and 2. S-44 states the cube sizes are minimum requirements and smaller features may exist. — [IHO C-13 Manual, Chapter 4](https://docs.iho.int/iho_pubs/CB/C-13/english/C-13_Chapter_4.pdf), [IHO S-44 5th Ed.](https://legacy.iho.int/iho_pubs/standard/S-44_5E.pdf) (search-summary of both)
- A hydrographic-review paper notes the S-44 "100 per cent bottom search" wording was ambiguous in the 4th edition and that cubes were read as all sides equal 1 m or 2 m. — [International Hydrographic Review](https://journals.lib.unb.ca/index.php/ihr/article/download/20616/23778/29374) (search-summary)
- UXO survey guidance: the Carbon Trust Offshore Wind Accelerator published guidance on geophysical surveying for UXO and boulders (April 2020), supported by Cathie and Ordtek. It states faults in survey design "can lead to the need to repeat surveys, or unexpected damage to equipment". No quantified detection-probability or cost content in the news item. — [Windtech International](https://www.windtech-international.com/industry-news/new-guidance-for-offshore-wind-industry-on-geophysical-surveys-for-unexploded-ordnance-and-boulders) (read); [Carbon Trust page](https://www.carbontrust.com/our-work-and-impact/guides-reports-and-tools/guidance-for-geophysical-surveying-for-unexploded) (not read)
- Fugro: ALARP certificate confirms risk "as low as reasonably practicable"; choosing one provider gives "single mobilisation fee" and one ALARP validity. No price or insurance terms stated. — [Fugro long-read](https://www.fugro.com/news/long-reads/2021/five-key-uxo-considerations-for-successful-offshore-projects-fugro-longread)
- Detonation risk (search-summary): intrusive seabed work can trigger unintended detonation; one trade article calls inadvertent detonation on a marine construction site extremely rare but says UXO finds have caused delays "costing millions of dollars" and contract disputes. No specific dredger or trawler incident with a cost was found. — [Renewable Energy World](https://www.renewableenergyworld.com/?p=206652)
- Uncharted-hazard groundings (search-summary): UK MAIB report on the jack-up barge Octopus, which grounded on an uncharted 7.1 m bank, buckling 4 legs with "substantial cost and project delays" (no amount given); Antilles (1971) struck an uncharted reef; Swedish Supreme Court held a hydrographic office liable to a tanker owner after a rock strike, whereas a US case found no liability but defence costs were very high. — [MAIB Octopus report](https://assets.publishing.service.gov.uk/media/547c705140f0b60241000097/Harold_OctopusReport.pdf), [ITIC liability exposure for hydrographic surveyors](https://itic-insure.com/our-publications/the-wire/liability-exposure-for-hydrographic-surveyors-2607) (neither fully read)
- Specialist professional-indemnity insurance for hydrographic surveyors exists (ITIC), which shows survey errors are an insured risk class. — [ITIC hydrographic surveyors fact sheet 2026](https://www.itic-insure.com/fileadmin/uploads/itic/Documents/Factsheets/2026/Hydrographic_surveyors_fact_sheet_2026.pdf) (search result; not read)
- Germany's munitions problem: about 1.6 million tonnes of munitions in German North and Baltic waters; a EUR 100 million federal emergency programme funds pilot clearance and an autonomous clearance platform. This is a pilot budget, not a full clearance estimate. — [Federal Environment Ministry](https://www.bundesumweltministerium.de/en/topics/marine-conservation/unexploded-munitions-in-our-seas), [yacht.de summary](https://www.yacht.de/en/travel-and-charter/germany/north-sea-and-baltic-sea-federal-government-pledges-millions-for-munitions-recovery/) (search-summary)

### Inferences
- A calibrated "probability this area is clear" aligns directly with how S-44 full-search and ALARP are phrased, but these regimes are met with certificates from existing contractors, not a separate software purchase. No evidence yet that regulators or insurers require or discount for a quantified coverage metric.
- Missed-object cost is probably large per event (vessel damage, wreck removal outside P&I limits) but rare; I have no frequency or claim data.

### Gaps
- No insurance premium discount, requirement, or claim-size data tied to survey coverage; no trawler-snag or dredger-strike cost; port channel clearance certificate economics not found; UXO ALARP documents (CIRIA C681/C754) not retrieved.
- Whether any regulator accepts probabilistic coverage claims: not found.

## 3. Manual-review burden and published productivity gains from AI/ATR (and whether customers paid)

### Takeaway
Everything quantified is vendor-reported. The strongest numbers are boulder-picking speedups (days to minutes) in offshore wind. Interpretation shortage and hours per line-km are asserted qualitatively but not measured in anything I found. Evidence that customers pay is thin: trial customers are unnamed, and one vendor says its tool will not be sold stand-alone.

### Cited Findings
- Coda Octopus Survey Engine (vendor): in a customer trial it recorded 4,600 boulder contacts in 3 km of line data in 9 minutes and produced a contact report in about 50 minutes; the CEO said this "would typically have taken about three days"; 91% detection rate vs manual tagging; "two significant customers" reported productivity gains (unnamed). — [Ocean News](https://www.oceannews.com/k46h), [Offshore Engineer Digital](https://www.oedigital.com/news/443909-artificial-intelligence-aids-subsea-object-detection), [Offshorewind.biz](https://offshorewind.biz/2019/02/11/coda-boulder-hunter-completes-trials) (search-summary)
- Ocean Geophysics (vendor, read): CEO says work that "previously took weeks or months" is done in "a few seconds"; about one second per side-scan line; boulders down to 25 cm; boulder fields can hold "thousands, sometimes millions"; tool "will not be sold stand-alone" but bundled with its processing/interpretation services; no dollar figures; no named customers. — [Offshore Engineer Digital](https://www.oedigital.com/news/512069-ai-tool-to-tackle-boulder-issues-for-offshore-wind-developments)
- Academic: a Kiel/Hydrographic News paper claims a method processes several km of side-scan and identifies thousands of boulders in under a minute (method paper, not a user-cost study). — [DHyG Hydrographic News](https://dhyg.de/index.php/en/hydrographic-news/professional-articles/44-hn-119/272-automatic-boulder-identification-in-side-scan-sonar)
- Fatigue and error in manual review: a side-scan search-and-rescue thesis says manual identification of sparse targets in very high-resolution images is "laborious and error-prone" and fatigue lowers accuracy; Hydro International/EvoLogics (vendor) say even experienced operators can spend hours reading images and need views from several angles. Qualitative, no measured hours. — [DTIC](https://apps.dtic.mil/sti/pdfs/AD0775682.pdf), [Hydro International case study](https://www.hydro-international.com/case-study/object-recognition-for-side-scan-sonar-and-video-feeds-2) (search-summary)
- Defence: Navy SBIR topic says it is "no longer practical for a sonar operator to sift through detections one-by-one" (airborne ASW context). A Tellez 2019 OCEANS paper on real SAS/SSS MCM data concludes the human operator should stay in the loop. — [Navy SBIR N162-093](https://navysbir.com/n16_2/N162-093.htm), [Tellez et al. via search](https://www.hydro-international.com/content/article/object-recognition-for-side-scan-sonar-and-video-feeds) (search-summary)
- Kongsberg: its MCM page describes SITAR automatic target recognition integrated with its SAS sensors/AUVs and in-situ target-list generation; no time-saved numbers found. I found no source for a product called "Target Assistant". — [Kongsberg MCM](https://www.kongsberg.com/campaign/defense/mcm/) (search-summary)
- SonarWiz (Chesapeake) ATR boulder detection productivity numbers, Charles River AutoTRap numbers, and AI4Shipwrecks numbers: not found.

### Inferences
- The most credible "price" signal is boulder/target picking in offshore wind, where the buyer is the survey contractor and the benefit is analyst-time (days) per survey.
- Because incumbents bundle detection into services or sensors (Coda, Ocean Geophysics, Kongsberg), a stand-alone review tool competes against "free" bundled features; the differentiator would need to be calibrated probability and coverage, which no vendor result above claims.

### Gaps
- No hours-per-line-km, interpreter headcount/shortage, or backlog statistics from independent sources.
- No named paying customer or price for any AI/ATR sonar review product.

## 4. Does anyone pay today for confidence scores or search-completeness/coverage guarantees?

### Takeaway
Yes, but as outcome contracts, not as software: governments have paid or promised large "no find, no fee" sums to search contractors, and the unit being sold is searched area, not a probability score. I found no evidence of anyone paying specifically for a calibrated per-object probability or a coverage map as a product. SAROPS/POD and "percentage clearance" evidence was not found.

### Cited Findings
- MH370, 2025-26: Malaysia agreed a "no find, no fee" contract with Ocean Infinity: USD 70 million payable only if wreckage is found, in a 15,000 km2 area of the southern Indian Ocean; final contract length was unclear at the time of the article. — [Baird Maritime](https://www.bairdmaritime.com/amp/story/security/emergency-services/search-and-rescue/malaysia-agrees-terms-for-restarting-mh370-wreckage-search) (read), [SCMP](https://www.scmp.com/news/asia/southeast-asia/article/3303034/malaysia-agrees-no-find-no-fee-terms-restart-flight-mh370-search) (HTTP 403, summary only)
- The 2025-26 seabed search ran March 2025 to January 2026 and ended without a find; Ocean Infinity left the area 23 January 2026 (search-summary of AP and Ocean Infinity update). — [AP via KSAT](https://www.ksat.com/news/world/2026/03/08/12-years-on-renewed-hunt-for-missing-flight-mh370-comes-up-empty-as-families-press-for-answers/)
- 2018 MH370 search by Ocean Infinity was also no-find-no-fee, tiered from USD 20 million (found in the first 5,000 km2) up to USD 70 million (outside 25,000 km2); nothing found (search-summary). — [Gulf News](https://gulfnews.com/amp/story/world%2Fasia%2Ffirm-to-receive-up-to-70m-if-mh370-found-in-new-hunt-1.2155097)
- ARA San Juan (2018): Argentina contracted Ocean Infinity at USD 7.5 million payable only on finding the submarine; wreck found after about a year at roughly 907 m, hours after the contract expired; contract duration reports conflict (60, 100 or 120 days). — [MercoPress](https://en.mercopress.com/2018/11/17/ocean-infinity-will-charge-for-finding-the-submarine), [Buenos Aires Times](https://batimes.com.ar/news/argentina/ara-san-juan-government-to-reward-ocean-infinity-with-us75m.phtml) (search-summary; contract text not found)
- UXO: Fugro's article sells an ALARP certificate as the deliverable; no price. — [Fugro](https://www.fugro.com/news/long-reads/2021/five-key-uxo-considerations-for-successful-offshore-projects-fugro-longread)
- USCG SAROPS probability-of-detection planning, MCM "percentage clearance" and UXO "probability of detection" reports as paid deliverables: not found in my searches.

### Inferences
- In the one segment with enormous per-job budgets (deep-ocean search), the buyer pays for area covered and success, and the contractor carries the coverage risk. This suggests a coverage-and-confidence tool is valuable to the contractor (to price and prove "we searched it") more than to the government buyer.
- Both no-find-no-fee contracts ended with a coverage claim but no find (MH370 twice), so the buyer's pain from false negatives is acute and public, yet it is only 2-3 events in a decade.

### Gaps
- No evidence a buyer paid separately for POD or coverage analytics; ATSB final MH370 search cost (reportedly about AUD 200 million for 2014-17) was not verified here.
- Insurance requirements for "searched" assurance: not found.

## 5. Ghost gear and marine debris funding

### Takeaway
There is real grant money that explicitly buys side-scan sonar surveys (NOAA-funded US projects), but individual awards are small (low hundreds of thousands to a few million dollars) and recipients are NGOs and fishing-community groups using low-cost sonar. In India I found no evidence of funded sonar surveys at all.

### Cited Findings
- NOAA Marine Debris Program gave Virginia Institute of Marine Science / William & Mary Batten School an $8 million, four-year grant (2023) to run the National TRAP Program of sub-awards for ghost-pot removal; one sub-award of $133,172 to the Commercial Fisheries Research Foundation (Narragansett Bay) explicitly uses side-scan sonar. — [EurekAlert release](https://www.eurekalert.org/news-releases/1103691) (search-summary)
- Center for Coastal Studies (Massachusetts): 2025 ghost-gear programme funded by NOAA Marine Debris Program; mapping team does side-scan sonar surveys in Cape Cod Bay, Boston Harbor and Stellwagen Bank; earlier headline of USD 2.7 million. — [CCS announcement](https://coastalstudies.org/news/center-for-coastal-studies-announces-ghost-gear-removal-program-for-2025/), [capecod.com](https://capecod.com/newscenter/top-story/center-for-coastal-studies-receives-2-7m-to-fight-ghost-gear) (search-summary)
- Stockton University (NJ): about USD 241,597 total (roughly half NOAA, half in-kind match), including training crabbers to use low-cost sonar. — [Stockton blog](https://blogs.stockton.edu/biodiversity/?p=487) (search-summary)
- Ocean Conservancy national removal grant programme with NOAA/Bipartisan Infrastructure Law money: award listed at $5,218,000 (Oct 2024-Sep 2028). — [NOAA Marine Debris Program](https://marinedebris.noaa.gov/removal/removing-and-preventing-derelict-fishing-gear-and-large-debris-nationwide) (search-summary)
- WWF Germany has used side-scan sonar for ghost-net searches since 2018; an ECO Magazine article (read) on autonomous AI side-scan surveys gives no cost or time numbers, and the 2024 trials used sample nets at known locations. — [ECO Magazine](https://ecomagazine.com/in-depth/ai-sonar-technology-shines-in-ghost-net-recovery-e-orts/)
- India (Mongabay, June 2026, read): no systematic tracking/retrieval; some state governments and nonprofits pay fishers INR 15,000-70,000 (about USD 160-740) for releasing entangled megafauna or returning damaged nets; CSR funding is used but "unreliable"; Kerala fishers lose about 167.5 kg gear per vessel per year; WWF-India and UNDP not mentioned; sonar not mentioned. — [Mongabay India](https://news.mongabay.com/2026/06/indias-fishers-confront-homegrown-ghost-gear-problem/)
- Global Ghost Gear Initiative (run by Ocean Conservancy) runs small grants (2022 cohort included Ghost Diving); no sonar-specific grant found. — [Ocean Conservancy](https://dev.oceanconservancy.org/?p=63016) (search-summary)

### Inferences
- Ghost-gear money is plentiful in the US relative to elsewhere but fragmented into small awards where sonar is a small line item; this is a grant-funded niche, not a market with recurring software budgets.
- For India, the evidence supports the team's suspicion of weak demand: no funded sonar survey, CSR-dependent and small stipends.

### Gaps
- Not found: EU fund amounts for sonar ghost-net surveys, Ghost Fishing Foundation budgets, WWF-India or UNDP India ghost-gear grants, corporate ESG budgets that buy sonar.
- NOAA current solicitation terms not read.

## 6. Disaster and search-and-recovery examples with costs

### Takeaway
Search-and-recovery costs are large when governments are the buyer, but they are rare, one-off events. Cost data found is mostly headline-level and old.

### Cited Findings
- Titan submersible search (2023): AP reported the cost "will easily stretch into the millions"; the US Coast Guard does not generally seek reimbursement for SAR. No exact total. — [AP via KATV](https://katv.com/news/nation-world/how-much-did-the-titan-submersible-search-cost-massive-international-effort-96-hour-clock-catastrophic-implosion-5-people-killed-coast-guard-crews-titanic-wreck)
- MH370 2014: early-April estimate USD 44 million (Reuters), including a US Navy share of USD 11.4 million; Australia expected an underwater phase of AUD 60 million (search-summary). — [NBC News](https://www.nbcnews.com/news/amp/ncna74436)
- AF447: figures differ widely between sources (USD 50 million; EUR 32 million; USD 105-132 million) and I could not attribute them to a primary source. Do not quote without checking.
- Contract anchors: see section 4 (MH370 up to USD 70 million; San Juan USD 7.5 million).

### Inferences
- The only sonar-search buyers that repeatedly spend millions are national governments and navies in rare incidents; these are not a base for a startup revenue model unless they are reached through contractors like Ocean Infinity.

### Gaps
- No costs found for lake or river sonar searches for missing persons or vehicles, or for ATSB final totals.

## 7. Ranking of pain points

### Takeaway
Offshore-wind and cable-route UXO/boulder target triage is the only area where size, frequency, an identifiable budget holder and a plausible fit for "AI review plus calibrated probability plus coverage" all coincide, but it is crowded by incumbents who bundle similar capability. Everything else scores lower on frequency or budget.

### Cited Findings
- Ranking basis is the evidence in sections 1-6; no additional sources. Key anchors: target-count-driven vessel days ([Fugro](https://www.fugro.com/news/long-reads/2021/five-key-uxo-considerations-for-successful-offshore-projects-fugro-longread)), 3-8% real-UXO ratios ([Boskalis/SWZ](https://swzmaritime.nl/news/2024/01/23/how-boskalis-searches-the-seabed-for-unexploded-ordnance/), [Renewable Energy World](https://www.renewableenergyworld.com/?p=206652)), and bundled boulder AI ([Ocean Geophysics](https://www.oedigital.com/news/512069-ai-tool-to-tackle-boulder-issues-for-offshore-wind-developments)).

### Inferences
Ranked on (a) money at stake, (b) frequency, (c) identifiable budgeted buyer, (d) fit with the product. Scores are my judgement.
1. Offshore-wind UXO target triage and false-alarm reduction (a: high but unquantified per target; b: every project; c: survey contractors such as Fugro, Ordtek, 6 Alpha, and developers and TSOs such as 50Hertz/Elia issuing UXO tenders; d: good partial fit, calibrated per-target probability and a coverage map map onto target lists and ALARP, but it is largely magnetometer/multibeam-driven and incumbents are building AI target lists, e.g., BASTA/GEOMAR).
2. Boulder and object picking for offshore wind and cable routes (a: medium; b: every site survey; c: contractors; d: fits AI review, but already served by Coda and Ocean Geophysics, and the latter bundles it rather than selling it). The three-days-to-minutes claim (vendor) suggests value but also suggests a commoditised feature.
3. German and European munitions clearance programmes (a: high, EUR 100 million pilot funding, 1.6 million tonnes; b: multi-year; c: federal ministry and contractors; d: moderate; timing and tender dynamics unclear).
4. Defence mine countermeasures (a: high; b: continuous; c: navies, but procurement-gated and tied to Kongsberg/SeeByte/Thales-style incumbents; d: strong technical fit via ATR with PFA/PD, but "percentage clearance" evidence not found and access is hard for a student startup).
5. Deep-ocean search-and-recovery (a: very high per event, up to USD 70 million contract; b: very rare; c: governments via contractors; d: good fit for coverage/POD, but contractors price outcomes, not software).
6. Hydrographic compliance and liability (S-44 full search; ITIC-insured surveyors) (a: unknown; b: frequent; c: survey firms; d: coverage evidence is useful for liability defence, but no claim data or willingness-to-pay evidence).
7. Ghost gear and marine debris (a: low, awards of USD 0.13-5 million; b: continuous but small; c: NGOs on grants; d: weak; India shows no sonar funding).

### Gaps
- No direct evidence that any buyer would pay specifically for calibrated confidence or a coverage map. The demand-weakness hypothesis is not refuted: the strongest cost evidence is for general target triage, and the buyers (survey contractors) already offer bundled automation.
- Missing hard numbers that would most change the ranking: cost per verified target, spread day rates, analyst hours per survey, and any customer willingness-to-pay or pricing for ATR/AI review software.
