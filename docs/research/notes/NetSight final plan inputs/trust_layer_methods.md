# NetSight trust layer: calibrated per-contact probabilities, empirical Pd / search-completeness maps, statistical bounds, false-alarm-per-area control, cross-pass association, position uncertainty (state of the literature as of Nov 2026)

Tagging convention: **[READ]** = I opened the primary text (HTML or PDF, extracted locally) and the claim comes from it. **[ABSTRACT]** = I read only the arXiv/venue abstract page. **[SEARCH-ONLY]** = claim comes from a search-result snippet or summary; the page was not opened or could not be opened. Items under "Inferences" are my own reasoning or background knowledge, not cited facts, and are labelled **[BACKGROUND]** when they rest on standard textbook knowledge I did not re-verify in this session.

**Correction to the brief.** arXiv 2404.18663 is NOT a Pd/target-injection methods paper in the sense described. It is Guerneve, Loizou, Munafo, Mignotte, "Terrain characterisation for online adaptability of automated sonar processing: Lessons learnt from operationally applying ATR to sidescan sonar in MCM applications" (UACE 2023). Target injection appears in it only as the engine of a terrain-complexity metric (details below). It contains no validation of injected-target Pd against real targets. The citation for the injection pipeline itself is its ref [17], Karjalainen, Mitchell, Vazquez, SSPD 2019 (GAN-based realism), which I did not retrieve.

---

## 1. Calibration for object detection: metrics, calibrators, fused output, sample size, conformal guarantees

### Takeaway
Detection calibration must be measured on the detector's final box-level output with a box-aware metric (D-ECE / LaECE), not image-level ECE. The best-evidenced post-hoc calibrators for detectors are histogram binning / isotonic regression when data are plentiful and Platt (logistic) or beta calibration with box covariates when data are scarce. Temperature scaling alone has documented drawbacks for detectors. Conformal risk control gives finite-sample, distribution-free guarantees, but only on average (marginal), only under exchangeability, and not conditional on a given survey or seabed.

### Cited Findings
- Küppers et al. define detection ECE (D-ECE) as the expected gap between precision and confidence conditioned on box properties: E[ |P(m=1 | p̂=p, ŷ=y, r̂=r) − p| ], computed by binning each dimension of the (confidence + box position/size) space; D-ECE = Σ_n (|I(n)|/|D|)·|prec(n) − conf(n)|; bins with fewer than 8 samples are dropped; D-ECE should be reported with at least the dimensionality used for calibration. [READ] — [Küppers et al., Multivariate Confidence Calibration for Object Detection (ar5iv)](https://ar5iv.labs.arxiv.org/html/2004.13546); abstract at [arXiv 2004.13546](https://arxiv.org/abs/2004.13546)
- Same paper: miscalibration depends strongly on object location (worse near image borders) and on box width/height. Standard (confidence-only) ECE can hide this: in their artificial example global logistic calibration had lower ordinary ECE (1.1%) than the box-dependent variant (2.2%) but much higher D-ECE (8.7% vs 3.3%). [READ] — [ar5iv 2004.13546](https://ar5iv.labs.arxiv.org/html/2004.13546)
- Same paper, calibrators compared: histogram binning (HB), logistic/Platt (LC), beta calibration (BC), each in confidence-only, independent-box-terms and dependent-box-terms forms. Confidence-only: "the simple histogram binning outperforms the logistic and the beta calibration in all cases." With box inputs the multivariate logistic or beta calibration beat HB, especially in the dependent case. Authors' conclusion: HB suits low-dimensional mappings or large datasets; LC/BC suit high-dimensional mappings with limited data because HB's bin count grows exponentially with dimension. Isotonic regression and Dirichlet calibration were not evaluated. [READ] — [ar5iv 2004.13546](https://ar5iv.labs.arxiv.org/html/2004.13546)
- Oksuz, Joy, Dokania (CVPR 2023) introduce Self-Aware Object Detection and the Localisation-aware ECE (LaECE), designed to account for both classification and localisation quality. [SEARCH-ONLY] — [CVPR 2023 paper](https://openaccess.thecvf.com/content/CVPR2023/papers/Oksuz_Towards_Building_Self-Aware_Object_Detectors_via_Reliable_Uncertainty_Quantification_and_CVPR_2023_paper.pdf)
- Kuzucu, Oksuz, Sadeghi, Dokania (ECCV 2024) state that recent evaluation frameworks, metrics and the use of Temperature Scaling have "notable drawbacks leading to incorrect conclusions"; they propose a joint calibration+accuracy evaluation framework and improved LaECE variants (LaECE0, LaACE0), and report that post-hoc Platt scaling and Isotonic Regression "tailored to object detection" are much more effective than recent train-time calibration methods (D-DETR + isotonic beat Cal-DETR by more than 7 D-ECE on COCO). [ABSTRACT] — [arXiv 2405.20459](https://arxiv.org/abs/2405.20459); [ECCV page](https://www.ecva.net/papers/eccv_2024/papers_ECCV/html/3148_ECCV_2024_paper.php)
- Kumar, Liang, Ma (NeurIPS 2019): Platt and temperature scaling are less calibrated than reported and existing techniques cannot estimate residual miscalibration; histogram binning is verifiable but needs O(B/ε²) samples versus O(1/ε²) for scaling methods; their scaling-binning calibrator needs O(1/ε² + B) samples; a meteorology-derived estimator of calibration error needs O(√B) rather than O(B) samples. [SEARCH-ONLY] — [arXiv 1909.10155](https://arxiv.org/pdf/1909.10155)
- Andéol, Fel, de Grancey, Mossina (2023) apply conformal prediction to railway-signal detection, compare several conformal approaches and introduce a conformal-risk-control method, claiming "formally guaranteed uncertainty bounds"; coverage type and proofs not stated in the abstract. [ABSTRACT] — [arXiv 2304.06052](https://arxiv.org/abs/2304.06052)
- Andéol, Mossina, Mazoyer, Gerchinovitz, "Conformal Object Detection by Sequential Risk Control" (arXiv 2505.24038, v2 31 Oct 2025): SeqCRC extends Conformal Risk Control to two sequential tasks with two parameters (confidence threshold then localisation/classification set-size parameters). Theorem 2: E[L_test(λ_cnf⁺, λ⁺)] ≤ α, where the expectation is "over both D_cal and (X_test, Y_test)", i.e. a mean over calibration set and test point; "there is no guarantee that (the bound) holds for all possible test instances, or for all calibration data sets"; test-conditional guarantees "impossible to obtain without further assumptions". Needs non-increasing, right-continuous losses (the matching-based localisation/classification losses are not monotone in practice, so they use a "monotonization trick" with a conservative upper bound that enlarges prediction sets). Needs a "vanishing loss" assumption (after NMS there is at least one prediction per image / at least as many predictions as ground truths if matching is injective, e.g. Hungarian). Finite-sample guarantee with a single data split. Toolkit released. [READ] — [arXiv 2505.24038 PDF](https://arxiv.org/pdf/2505.24038)
- Conformal Risk Control (Angelopoulos et al.) controls the expectation of a monotone loss; worked examples bound the false negative rate on COCO multilabel classification. This is an average-over-test-data FNR bound, not a per-image recall bound. [SEARCH-ONLY] — [arXiv 2208.02814](https://arxiv.org/abs/2208.02814)
- Learn then Test (Angelopoulos, Bates, Candès, Jordan, Lei) frames risk control as multiple hypothesis testing and delivers finite-sample, high-probability risk control for bounded losses without refitting; examples include FDR control in multilabel classification and IoU control in instance segmentation. One listing gives Annals of Applied Statistics 2025 (not confirmed). [SEARCH-ONLY] — [arXiv 2110.01052](https://arxiv.org/abs/2110.01052v4)
- Dai et al. (arXiv 2504.04482, 2025) design per-sample losses to reach user-specified FNR and FDR in medical instance segmentation. [SEARCH-ONLY] — [arXiv 2504.04482](https://arxiv.org/pdf/2504.04482)

### Inferences
- Report two numbers, never one: ordinary reliability of the final contact score, and D-ECE/LaECE with box/position covariates (range-from-nadir, along-track position, image-edge distance, box size). Range is the natural "location" covariate for side-scan; Küppers' border/scale effects map to near-nadir and far-range behaviour. (Inference from Küppers.)
- "Calibrating the final fused output" has no specific methods paper in my results. The defensible rule is procedural: fit the calibrator on the exact artefact the user sees (post-NMS, post-fusion, post-association score), freeze the full pipeline hash, and recalibrate on any upstream change. This follows directly from D-ECE being defined on the final emitted detections (Küppers) and from isotonic/Platt being post-hoc maps (Kuzucu).
- Recommended default calibrator stack: (a) Platt/beta with a few covariates (score, range, local-complexity index) as the primary map when calibration contacts are in the hundreds; (b) isotonic or histogram binning only when thousands of labelled contacts per condition exist; (c) report the verified-calibration style error estimate with CIs (Kumar). Temperature scaling is acceptable only as a baseline, not as the claim.
- Sample-size heuristics from the Kumar bounds: parametric maps (1–3 parameters) are far cheaper than binning; with B bins and target calibration error ε, plan for ~B/ε² samples for binning versus ~1/ε² + B for scaling-then-binning. For ε = 0.05 that is ~400 samples for a scaling map and ~2000+ for 5–10-bin histogram binning before conditioning on any covariate. [BACKGROUND arithmetic from the cited orders; constants not verified.]
- What each conformal tool buys. SeqCRC/CRC: a bound on EXPECTED loss (e.g. expected missed-object fraction) for a pipeline-level threshold, finite sample, valid only if calibration and deployment data are exchangeable, which survey-to-survey seabed and sonar change violates. LTT: same but with a high-probability statement over the calibration draw, better matched to a "withdrawable claim". Neither yields a per-contact probability; neither yields a Pd map. They are best used to set the operating threshold (see section 4), not to replace the calibrated score.
- Wording consequence: say "on surveys drawn like the calibration surveys, the expected fraction of true objects missed is at most α", not "each object has at least 1−α chance of being flagged".

### Gaps
- I found no paper that specifically studies calibration loss caused by NMS, box fusion, test-time augmentation or cross-pass fusion (the audit's concern). Only the generic detector calibration papers above.
- Küppers 2022 book chapter (arXiv 2202.12785) and Oksuz 2023 full text were not opened; formulas for LaECE not verified.
- I did not verify isotonic-overfitting behaviour at small n (Niculescu-Mizil & Caruana 2005) or Guo et al. 2017 temperature scaling; mentioned only as background.
- No sonar-specific calibration paper (side-scan or SAS) was found with a quantitative result.
- Assumption 1 in SeqCRC (presumably exchangeability) content was not confirmed in the extracted text.

---

## 2. Pd estimation in sonar / MCM: target injection, through-the-sensor estimation, lateral range curves, validation, multi-look dependence

### Takeaway
Target insertion into real sonar data (elevation estimate + CAD model + sidescan ray tracing, optionally GAN refinement) is an established way to get a per-location empirical Pd map and false-alarm density, and is used operationally by SeeByte; but the primary sources I could open do not demonstrate validation of injected-target Pd against real laid targets, and the standard multi-look model in the open literature (DRDC) assumes independent looks.

### Cited Findings
- Guerneve et al.: "we perform contact insertion in sidescan sonar data by first estimating the local elevation map of the seabed, then inserting the model of the [object] based on a 3D CAD file and running a sidescan sonar ray tracing algorithm. The ray traced image is then processed with a GAN to improve the realism ... and match the characteristics of the sidescan sonar of interest." The augmented images go to the ATR; since insertion locations are known, PD and false alarm density (FAD) are evaluated; repeating N times with random insertion locations and averaging yields a PD value "at each location of the image" (binary per-pass performance map averaged to a grayscale map). Cost: "from 500 ms up to a minute per 1000-ping sidescan image". Observed: Pd lower over marine-growth/complex areas and at long range (more shadow). They interpret the map as an "algorithm-led, quantitative estimate of terrain complexity for the task at hand". No validation against real laid targets appears in the text I read. [READ] — [arXiv 2404.18663](https://arxiv.org/pdf/2404.18663)
- SeeByte's Performance Analysis and Training Tool (PATT) inserts simulated mine targets into real sidescan data to estimate PD and false-alarm rates; target models stored as height maps; 3-D models accepted. [SEARCH-ONLY, secondary description of a vendor white paper] — [SeeByte white paper](https://www.unmannedsystemstechnology.com/wp-content/uploads/2013/10/White-Paper-Performance-Analysis-Testing.pdf)
- Gazagnaire, Beaujean, Stack, "Combining model-based and in situ performance prediction to evaluate detection and classification performance" exists in Proceedings of the Institute of Acoustics (title and URL surfaced in search; the page returned 404 on fetch and I could not read it). [SEARCH-ONLY, title only] — [IoA PDF link](https://www.ioa.org.uk/system/files/proceedings/j_gazagnaire_p_beaujean_j_stack_combining_model-based_and_in_situ_performance_prediction_to_evaluate_detection_and_classification_performance.pdf)
- Through-the-sensor seabed estimation (TNO, van Vossen, Colin, Ainslie, Benders, IEEE JOE 2014, DOI 10.1109/JOE.2013.2277635) derives acoustic seabed parameters from reverberation to feed in-situ performance prediction. [SEARCH-ONLY] — [FFI listing](https://www.ffi.no/publikasjoner/arkiv/improved-active-sonar-tactical-support-by-through-the-sensor-estimation-of-acoustic-seabed-properties)
- CMRE-FR-2013-025 covers seabed reflectivity/scattering as key inputs to sonar performance prediction for ASW and MCM. [SEARCH-ONLY] — [CMRE report](https://www.sto.nato.int/publications/CMRE%20Technical%20Reports/CMRE-FR-2013-025/CMRE-FR-2013-025.pdf)
- A NATO STO paper frames sidescan ATR as a communication channel and uses mutual information to bound classification performance. [SEARCH-ONLY] — [STO MP-SET-079-28](https://www.sto.nato.int/publications/STO%20Meeting%20Proceedings/RTO-MP-SET-079/MP-SET-079-28.pdf)
- In MCM usage the lateral range curve is called a P(y) curve (Pd versus lateral range); sweep width is the area under the lateral range curve (Koopman); Kragelund et al. describe newer models using engineering parameters and 3-D geometry rather than lateral range curves alone. [SEARCH-ONLY] — [USCG Theory of Search](https://navcen.uscg.gov/sites/default/files/pdf/Theory_of_Search.pdf); [arXiv 2006.12896](https://arxiv.org/pdf/2006.12896)
- DRDC Scientific Report 2014-R58 (Nguyen & Mirshak) computes expected Pd from multiple looks under THREE tactics each assuming independent looks; Pd rises considerably with number of looks (largest gain from one to two looks) and varies with look-angle tactic and target cross-section. A companion paper notes the angular dependence of detection materially affects overall Pd. [SEARCH-ONLY] — [DTIC AD1018043](https://apps.dtic.mil/sti/pdfs/AD1018043.pdf); [Canada publications record](https://publications.gc.ca/site/eng/9.807311/publication.html)
- Heriot-Watt note: the lawnmower nature of side-scan surveys means the same object is often viewed multiple times. [SEARCH-ONLY] — [Heriot-Watt SonarATR page](https://home.eps.hw.ac.uk/~ceeyrp/WWW/Research/SonarATR/outline1.html)
- S-44 Ed. 6.0.0 permits feature search above 100% to be achieved "by adequately overlapping collection or by acquiring more than one independent dataset", and states "no single survey system can guarantee detection of all features". [READ] — [IHO S-44 Ed 6.0.0 (Estonian mirror)](https://www.transpordiamet.ee/sites/default/files/documents/2021-08/S-44_Edition_6.0.0_EN.pdf)

### Inferences
- The injected-target Pd is a measurement of "ATR + sonar + seabed texture" for the INJECTED appearance. Its transfer to real targets depends on injection realism (shadow, highlight, burial, aspect, scour, GAN artefacts). Without a validation arm it is a model-based estimate, not an empirical Pd. Minimum validation design: (1) a held-out set of real known targets (laid-target trials or surveyed wrecks/boulders); (2) compare detection rate of real targets with the injected-Pd predicted for their same location/range/seabed class; (3) report calibration of predicted Pd against observed detection (reliability diagram on Pd itself, with Clopper-Pearson bands). NetSight's differentiator would be this closed loop.
- Multi-pass with correlated looks: the independence formula 1−Π(1−Pd_k) assumes failure events are independent. Looks share seabed clutter, object burial and orientation, so misses are positively dependent and the formula overstates combined Pd (consistent with the audit's warning; I found no open source quantifying the effect). Empirical route: exploit injection. Inject the SAME synthetic object at the SAME geographic position into two or more overlapping passes and measure P(detect in both)/P(miss in both) directly, then fit a dependence model (e.g. beta-binomial / shared-random-effect for "difficulty of this location", or a copula) and report the pairwise miss-correlation ρ. Until ρ is measured, publish combined Pd as an interval bounded below by max_k Pd_k (perfect dependence) and above by the independence formula, and quote the lower end.
- A seabed-complexity covariate (Guerneve's injection-derived map, or texture statistics such as lacunarity) should enter the Pd model as a conditioning variable so the Pd map is not just a function of range.

### Gaps
- No open source found that validates injected-target Pd against real laid targets (CMRE, SeeByte or others). Search targeted "validation" and "target-laying trials" and returned nothing usable.
- Williams (CMRE) performance-prediction papers were not retrieved. The lacunarity literature was not retrieved.
- I could not read the Gazagnaire/Beaujean/Stack IoA paper, so its method and validation are unknown to me.
- DRDC 2014-R58 full text was not opened; the "independent looks" statement comes from the abstract/catalog summary. No source on look-dependence models for sidescan found.
- One lateral-range search result stated that coverage from repeated ensonification "is added multiplicatively", but I cannot attribute it to a specific URL, so it is not used as a citation.
- The Karjalainen et al. SSPD 2019 GAN paper (ref [17] in Guerneve) was not retrieved.

---

## 3. Bayesian search theory and what a Pd / "search completeness" map means

### Takeaway
In Bayesian search (Stone; Metron's AF447 work) a failed search lowers the posterior probability of the searched cells and raises it elsewhere, in proportion to the sensor's detection probability. This makes the Pd map a decision input whose errors propagate: an over-optimistic Pd wrongly "clears" cells. The map's honest meaning is conditional: "if an object of the assumed class and size was present here, the system would have flagged it with probability p under these conditions".

### Cited Findings
- Stone, Keller, Kratzke, Strumpfer, "Search for the Wreckage of Air France Flight AF 447", Statistical Science 29(1), 2014, 69–80 (Metron). The method combines a prior location distribution with the evidence of each failed search pass using Bayes' law; areas searched without success lose probability, unsearched areas gain; the wreck was found within about one week of undersea search in a high-probability region after two years of unsuccessful search. [ABSTRACT + SEARCH-ONLY summary] — [arXiv 1405.4720](https://arxiv.org/abs/1405.4720); [Statistical Science PDF](https://projecteuclid.org/journals/statistical-science/volume-29/issue-1/Search-for-the-Wreckage-of-Air-France-Flight-AF-447/10.1214/13-STS420.pdf); [Metron page](https://www.metsci.com/what-we-do/featured-projects/the-search-for-air-france-447/)
- Stone's work includes USS Scorpion (1968) and SS Central America (1987) and *The Theory of Optimal Search* (Lanchester Prize 1975). [SEARCH-ONLY] — [Metron](https://www.metsci.com/ama/high-profile-searches/)
- Koopman-style detection models: lateral range curve and sweep width as the sensor-performance input to search planning (see section 2 sources). [SEARCH-ONLY] — [USCG Theory of Search](https://navcen.uscg.gov/sites/default/files/pdf/Theory_of_Search.pdf)
- I did not retrieve the AF447 paper's own treatment of detection-probability uncertainty or sensitivity analysis.

### Inferences
- Posterior update after a failed look in cell c is proportional to prior(c)·(1−Pd(c)) [BACKGROUND, standard Bayesian search; not re-verified in this session]. Therefore a Pd that is too high drives the cell's residual probability too low, and that is the unsafe direction for a net/wreck/hazard search. This supports publishing Pd lower bounds, not point estimates.
- Recommended wording for a NetSight Pd map: "Estimated probability that a [class, size, aspect-averaged] object lying in this cell would have produced a reported contact at the stated operating point, given sonar, range, and local seabed complexity. Lower bound at 90% confidence: X. Valid for survey conditions within the stated applicability envelope. It is NOT: the probability that the area is free of objects; a statement about objects outside the modelled classes or burial states; a per-contact probability; or a guarantee for other sonars."
- Net-state (standing, collapsed, snagged) changes the target signature, so Pd must be reported per state, and the posterior of "no net here" must use the state-marginalised Pd with its lower bound (otherwise collapsed nets inflate "cleared").
- Because Pd depends on the SAME correlated seabed across passes, treat posterior updates across passes with the dependence-aware combined Pd of section 2, not a product of independent (1−Pd).

### Gaps
- Could not open the Statistical Science paper text, so its handling of sensor-reliability uncertainty is unknown.
- No source found on communicating Pd-map semantics to non-specialists (human-factors literature).
- Net-state modelling: no sonar literature found in this session.

---

## 4. Statistics: intervals, block bootstrap, spatial CV, survey-level splits, recall at fixed false alarms per km² (FROC)

### Takeaway
Use exact (Clopper-Pearson) bounds for safety claims, Wilson for descriptive intervals, resample whole survey/line blocks rather than frames, split by survey/site (blocked CV), and report recall versus false alarms per km² using FROC conventions, with an explicitly stated matching radius.

### Cited Findings
- Brown, Cai, DasGupta (Statistical Science 2001): the Wald interval has erratic coverage (e.g. at n=100 nominal 95% covers 0.952 for p=0.106 but only 0.911 for p=0.107); they recommend Wilson or equal-tailed Jeffreys for small n and Agresti-Coull for larger n. Their 2002 Annals paper adds that Agresti-Coull is more nearly conservative and longest. [SEARCH-ONLY] — [Statistical Science](https://projecteuclid.org/euclid.ss/1009213286); [Annals of Statistics 2002](https://www.projecteuclid.org/euclid.aos/1015362189)
- Clopper-Pearson guarantees coverage at least nominal for every true proportion but is systematically wider; example 15/20: Wilson (0.531, 0.888) vs Clopper-Pearson (0.509, 0.913). [SEARCH-ONLY, secondary guide] — [CASRAI guide](https://casrai.org/guides/confidence-interval-for-a-proportion/)
- Roberts et al. 2017 (Ecography 40(8):913–929): random CV is over-optimistic when data have spatial, temporal or hierarchical dependence; block CV (splitting by space/time/group) addresses this, and the authors advise it whenever dependence structures exist, even if residuals look uncorrelated; blocking has trade-offs (it can narrow the predictor space available in training). [SEARCH-ONLY] — [Roberts et al.](https://www.biometrie.uni-freiburg.de/mitarbeiter/dormann/roberts-et-al-2017-ecography.pdf)
- FROC: lesion localisation fraction plotted against the mean number of non-lesion localisations (false positives) per image; a mark is scored a localisation only if close enough to a true lesion, and the acceptance radius is somewhat arbitrary, so the FROC curve depends on it. AFROC and JAFROC are alternatives with significance testing; Chakraborty's book (CRC 2017) is the standard reference. A maximum-likelihood FROC fitting procedure reports figures of merit with 95% CIs. [SEARCH-ONLY] — [PMC3679336 (history of FROC)](https://pmc.ncbi.nlm.nih.gov/articles/PMC3679336); [PMC2041901](https://pmc.ncbi.nlm.nih.gov/articles/PMC2041901); [CRAN tpfp](https://cran.r-project.org/web/packages/tpfp/refman/tpfp.html)
- Audit context (provided by user, not independently verified): DEPTH fits thresholds on calibration recordings with Clopper-Pearson bounds and block-bootstrap for correlated frames, and withdraws its guarantee on an unfamiliar sonar.

### Inferences
- Zero-failure arithmetic for claims (exact binomial) [BACKGROUND math]: with 0 misses in n independent trials, the one-sided 95% Clopper-Pearson lower bound on Pd is 0.05^(1/n), so n ≥ 29 for Pd ≥ 0.90, n ≥ 59 for Pd ≥ 0.95, n ≥ 299 for Pd ≥ 0.99. These n count EFFECTIVE independent trials. Injected targets in neighbouring pings/passes are not independent; use effective n = n/(1+(m−1)ρ) for clusters of size m and intra-cluster correlation ρ, or resample at cluster level.
- Clopper-Pearson for any headline lower bound; Wilson only for descriptive plots. Use block (cluster) bootstrap over survey lines or surveys for anything involving contacts across frames; confidence statements about generalisation to NEW surveys need survey-level resampling and are limited by the number of surveys, not the number of pings. (No source retrieved for block-bootstrap theory; Künsch/Lahiri are background only.)
- Splits: never split by frame or tile. Hold out whole surveys (ideally whole sites and, for the "new sonar" claim, whole sonar models). Report the spread of per-survey Pd and recall, not just a pooled figure.
- Recall at fixed false alarms per km²: run the full pipeline over survey areas, convert false contacts to FA/km² by dividing by surveyed seabed area (swath-width × along-track after slant-range correction, not image pixels), choose the threshold on the calibration surveys to meet the FA/km² budget (e.g. via LTT/CRC with FA count as the loss), then report recall and Pd with CIs on held-out surveys at that fixed threshold. State the matching rule (distance gate and, if applicable, IoU) because FROC depends on it. Plot an FROC (recall vs FA/km², log-x) with survey-level bootstrap bands.
- Multiple operating points: report recall at 2–3 pre-registered FA/km² values, not the best-looking point on the curve.

### Gaps
- No mine-hunting-specific FROC or "false alarm density" evaluation paper was retrieved other than Guerneve's use of FAD.
- No source for block-bootstrap theory or spatial block-size selection was retrieved this session.
- No source on how many surveys are enough for survey-level generalisation claims.
- Roberts et al. full text not opened (summary from search only).

---

## 5. Cross-pass contact association and persistent object IDs

### Takeaway
Open-literature support is for distance-gated clustering of contacts and for tracker-style association (nearest-neighbour, JPDA, MHT) in multistatic sonar; I found no side-scan MCM paper using Hungarian or JPDA with propagated position covariance, so that design is an engineering extrapolation.

### Cited Findings
- CAD/CAC fusion for mine detection clusters contacts by the distance between locations and declares a target when a cluster passes a fusion criterion (distance-gated clustering). [SEARCH-ONLY] — [SPIE 6217-1D](https://electronicimaging.spiedigitallibrary.org/conference-proceedings-of-spie/6217/62171D/Application-of-fusion-algorithms-for-computer-aided-detection-and-classification/10.1117/12.666100.full)
- A NATO Undersea Research Centre paper compares a nearest-neighbour tracker with a multi-hypothesis tracker on multistatic sea-trial data and concludes tracking improves detection and localisation of contacts. [SEARCH-ONLY] — [DTIC ADA454740](https://apps.dtic.mil/sti/pdfs/ADA454740.pdf)
- A EUSIPCO 2006 paper classifies approaches as contact-based Kalman, probabilistic multi-hypothesis, and MHT; MHT is multi-scan and generally outperforms scan-based methods. [SEARCH-ONLY] — [EUSIPCO 2006](https://new.eurasip.org/Proceedings/Eusipco/Eusipco2006/papers/1568981977.pdf)
- A multistatic sonar tracker uses an EKF implementation of JPDA followed by a Monte Carlo JPDA stage that handles measurement uncertainty without linearisation. [SEARCH-ONLY] — [Applied Sciences 8(1) 36 (2017)](https://p.gyb.elementfx.com/2076-3417/8/1/36) (result titled PHD/CPHD with a novel detection probability; the JPDA statement came from a neighbouring result, so treat as weakly attributed)
- A US patent describes a coarse filter followed by nearest-neighbour correlation against stored contact tracks plus a reassessment step to fix correlation errors. [SEARCH-ONLY] — [US 6041019](https://image-ppubs.uspto.gov/dirsearch-public/print/downloadPdf/6041019)

### Inferences
- Static objects in repeated side-scan passes are a data-association problem with no motion model: the "track" state is a fixed 2-D position with a covariance, so Mahalanobis gating plus global assignment is sufficient; JPDA/MHT matter mainly when contacts are dense or have ambiguous multiple candidates. Gate on d² = Δᵀ(Σ₁+Σ₂)⁻¹Δ against a χ²(2) threshold [BACKGROUND]: 5.99 for 95%, 9.21 for 99%. Add class-compatibility and size/shadow consistency as soft costs.
- Hungarian assignment per pass-pair solves one-to-one matching, but a contact can legitimately have no match (missed on the other pass, which is itself Pd information) or merge/split (one wide object versus two). Persistent object IDs should be a cluster-level identifier with an append-only history of merges/splits, never rewriting past IDs.
- Association is itself a source of error that needs its own metric: measure pairwise match precision/recall using injected objects (inject at known positions in two overlapping passes) and real repeated targets, and report mis-association rate versus covariance inflation.
- Score fusion across passes must be recalibrated after association (the audit warning), and must not use the independence formula; use the dependence-aware combination from section 2 and verify with D-ECE on the fused output.

### Gaps
- No side-scan-specific, peer-reviewed multi-pass correlation method with quantified performance retrieved. No MCM paper using Hungarian or JPDA for repeated passes found.
- I did not locate CMRE multi-view ATR fusion papers in this session.

---

## 6. Position uncertainty: TPU, layback/towfish models, IHO S-44, testing coverage of confidence ellipses

### Takeaway
S-44 defines horizontal uncertainty (THU) at "95%" via 2.45σ under a normal-error assumption and requires it be recorded and predicted per survey, but I did not find a standard side-scan-contact TPU formula; towfish layback, feathering and lateral offset dominate the budget, and the stated ellipse must be validated against known targets.

### Cited Findings
- S-44 Ed. 6.0.0: THU is the horizontal component of TPU, a two-dimensional quantity with all contributing errors considered; uncertainties at 95% confidence must be recorded with the survey data; calculations are predictive. The "confidence level" is "not the strict statistical definition" but a coverage probability per JCGM 100:2008; assuming normal errors, 95% for 1D = 1.96σ and for 2D = 2.45σ. [READ] — [IHO S-44 Ed 6.0.0](https://www.transpordiamet.ee/sites/default/files/documents/2021-08/S-44_Edition_6.0.0_EN.pdf)
- S-44 Table 1 feature detection (as extracted; table layout is partly garbled, verify against the official PDF): Order 1a "cubic features > 2 m in depths down to 40 m; 10% of depth beyond 40 m"; Special Order "cubic features > 1 m"; Exclusive "cubic features > 0.5 m". Feature search: 100% for Order 1a and Special, 200% for Exclusive. Table 2 lists allowable THU for positioning of fixed objects/features; extracted rows show 5, 2, 2, 2, 1 m (Order 2 to Exclusive) for one row and 2, 2, 1, 0.5, 0.25 m for another, but the row labels were garbled, so do not quote these as contact-position requirements without checking the official table. [READ, extraction caveat] — [IHO S-44 Ed 6.0.0](https://www.transpordiamet.ee/sites/default/files/documents/2021-08/S-44_Edition_6.0.0_EN.pdf)
- Edition 6.2.0 (Oct 2024) was approved by Member States per IHO circular letter 21/2025 (April 2025), adding a priori / a posteriori uncertainty to the glossary and extending the THU concept; the circular proposes revised wording for the 2.45 factor. [SEARCH-ONLY] — [IHO CL21/2025](https://iho.int/uploads/user/circular_letters/eng_2025/CL21_2025_EN_v1.pdf)
- Towfish position error is driven by uncertain feathering angle and effective horizontal layback (catenary changes); lateral offset from side currents is not captured by layback calculations; a NOAA sanctuary mosaic record gives overall horizontal accuracy of roughly 10–30 m for that survey. [SEARCH-ONLY] — [NOAA W00308 DR](https://data.ngdc.noaa.gov/platforms/ocean/nos/coast/W00001-W02000/W00308/DR/W00308_DR.pdf); [NOAA W00309 DR](https://data.ngdc.noaa.gov/platforms/ocean/nos/coast/W00001-W02000/W00309/DR/W00309_DR.pdf)
- NOAA TPU documentation is multibeam-oriented, and choosing the wrong sonar model in CARIS gives incorrect uncertainty values, so a side-scan contact needs its own budget. DRDC work on target positioning reports sub-10 m RMS with an onboard INS for towfish position. [SEARCH-ONLY] — [NOAA OPR-K339-KR-14 DAPR](https://data.ngdc.noaa.gov/platforms/ocean/nos/DAPRs/OPR-K339-KR-14_DAPR.pdf); [DTIC AD1005146](https://apps.dtic.mil/sti/pdfs/AD1005146.pdf)

### Inferences
- Contact position budget (my proposal, to be validated): platform/GNSS-INS position + (USBL or layback model) towfish position + heading/feather + slant-range-to-ground-range conversion (needs altitude/bathymetry) + across-track pick error from pixel size and range resolution + object-reference-point ambiguity (shadow vs highlight). Combine as covariance Σ in the along/across-track frame rotated to north-east, with the dominant towfish terms as explicitly correlated across the pings of one pass (so the within-pass error is common-mode, which is why cross-pass offsets are not independent noise).
- Testing the stated uncertainty: for contacts matched to known targets (GNSS-surveyed laid targets, or objects with ROV/multibeam-derived positions), compute d² = eᵀΣ⁻¹e. If Σ is right, d² follows χ²(2); the fraction with d² ≤ 5.99 should be ≈95% [BACKGROUND]. Report observed coverage with a Clopper-Pearson interval, the mean d² (should be ≈2), and a reliability plot over nominal levels 50–99%. Note that S-44's 2.45σ rule is exactly the 95% radius for an isotropic normal and is not valid for strongly elongated ellipses; use the Mahalanobis χ² formulation instead.
- This turns position uncertainty into a testable, withdrawable claim (like calibration), and makes association gates (section 5) honest.

### Gaps
- No quantitative side-scan contact TPU model or layback-error values from a primary source were retrieved; the NOAA records are survey reports, not method papers.
- The exact S-44 contact/feature-position table rows were not cleanly extracted; need the official PDF (6.2.0).
- No published coverage test of confidence ellipses for side-scan contacts on known targets was found.

---

## 7. Applicability / domain-shift detection: when to withdraw a calibrated claim

### Takeaway
Guarantees from conformal and calibration hold only if deployment data match calibration data; the only conformal fix in my sources (weighted conformal) needs the covariate likelihood ratio to be known or well estimated and assumes P(Y|X) is unchanged, which is precisely what a new sonar violates. So the system needs an explicit applicability gate that withdraws the claim.

### Cited Findings
- Tibshirani, Barber, Candès, Ramdas (NeurIPS 2019): conformal prediction under covariate shift via weighted exchangeability; calibration scores are reweighted by the test-to-train covariate likelihood ratio; assumes identical P(Y|X) with shifted P(X); finite-sample coverage holds when the weights are known, and in practice the weights must be estimated accurately (e.g. with unlabeled data). The guarantee is marginal. [READ (theorem structure, weighted exchangeability definition) + SEARCH-ONLY (marginal/caveat summaries)] — [arXiv 1904.06019](https://arxiv.org/abs/1904.06019); [CMU PDF](https://www.stat.cmu.edu/~ryantibs/papers/weightedcp.pdf)
- A 2024 follow-up note states the method requires the covariate-shift assumption and an exactly or well-approximated high-dimensional likelihood ratio for correct coverage. [SEARCH-ONLY] — [arXiv 2405.06627](https://arxiv.org/pdf/2405.06627)
- Sonar deep-learning review: differences in sonar brands, operating frequencies and environments create a distribution gap between training data and deployment inputs (an OOD problem). [SEARCH-ONLY] — [arXiv 2412.11840](https://arxiv.org/pdf/2412.11840)
- Sonar-specific OOD work: Gerg et al. perceptual-metric prior for SAS robustness; Jiao et al. open-set long-tail sonar recognition; DLR measured the ImageNet-to-sidescan domain gap with VAE embeddings. [SEARCH-ONLY] — [arXiv 2412.11840](https://arxiv.org/pdf/2412.11840); [DLR](https://elib.dlr.de/209455/1/main.pdf)
- Guerneve et al. present terrain complexity (injection-derived Pd map plus operator-labelled terrain classes, with explicit SME labels) as an online adaptability mechanism for ATR in new environments. [READ] — [arXiv 2404.18663](https://arxiv.org/pdf/2404.18663)
- Heriot-Watt-adjacent snippet: an algorithm tuned on one sonar model still achieved a Pd only 6% lower on another without representative target data. [SEARCH-ONLY, thesis excerpt] — [Cardiff thesis (ORCA)](https://orca.cardiff.ac.uk/18588/1/2012baresrphd.pdf)
- Audit context: DEPTH withdraws its guarantee on an unfamiliar sonar (user-supplied).

### Inferences
- Applicability envelope = a written, machine-checkable list: sonar model/frequency/range-scale/ping-rate/resolution, tow geometry, altitude-to-range ratio, seabed class set, water depth range, processing chain version. Hard gate on categorical fields (unknown sonar model, outside frequency band: withdraw all numeric claims; show "uncalibrated").
- Soft gate on continuous shift: monitor input statistics (pixel-intensity/texture histograms, noise floor, score distribution, embedding distance such as Mahalanobis in feature space, and fraction of contacts above an uncertainty threshold) against calibration-survey reference distributions; trigger CUSUM-style or two-sample tests per survey; on trigger degrade claim level from "calibrated" to "indicative" to "withdrawn".
- Use a canary check: injected targets in each new survey provide an in-situ Pd sanity test on the new data (a few hundred injections give a cheap per-survey detection-rate check against the stored Pd model). This extends Guerneve's insertion approach to an online drift detector.
- Weighted conformal is not a substitute for withdrawal, because a new sonar changes P(Y|X) (not only P(X)).

### Gaps
- No peer-reviewed, sonar-specific OOD/applicability-gating method with quantitative results retrieved (cross-sonar generalisation literature thin in results).
- Full text of the sonar OOD papers (Gerg et al., Jiao et al.) not opened.

---

## 8. Provenance records and assurance standards for ML decisions

### Takeaway
No standard prescribes a particular logging technology. DNV-RP-0671 gives a claims-and-evidence assurance framework with continuous validation; ISO/IEC 42001 requires event logs and data provenance records as management-system controls; W3C PROV gives a ready vocabulary (Entity / Activity / Agent) for recording model, calibrator and data lineage.

### Cited Findings
- DNV-RP-0671 "Assurance of AI-enabled systems" (Sept 2023 edition) provides a framework for assuring AI-enabled systems through a claims-and-evidence approach over the lifecycle; it stresses ongoing validation because AI systems change; its scope excludes assurance of organisations/management systems. Free to download. A 2026 DNV position paper argues one-time assurance is insufficient and calls for continuous, adaptive assurance. [SEARCH-ONLY] — [DNV RP page](https://www.dnv.com/digital-trust/recommended-practices/assurance-of-ai-enabled-systems-dnv-rp-0671/); [DNV 2026 news](https://www.dnv.com/news/2026/dnv-outlines-foundations-for-achieving-trustworthy-ai/); [UK gov AI assurance entry](https://www.gov.uk/ai-assurance-techniques/dnv-recommended-practice-assurance-of-ai-enabled-systems). (One SINTEF slide deck writes the number as "RP-0761", which appears to be a typo.)
- ISO/IEC 42001:2023: per secondary summaries, Annex A.7.5 data provenance requires a process giving an audit trail of data origin, history and transformations; A.6.2.7 technical documentation and A.6.2.8 event logs are typical evidence; the standard specifies management-system properties and does not prescribe technology (no on-chain logging required). Vendor mappings are marketing, not authoritative. [SEARCH-ONLY] — [cyberday A.7.5](https://www.cyberday.ai/requirement/iso-42001-a-7-5-data-provenance); [ar.io summary](https://ar.io/iso-42001/); [fluxpoint guide](https://fluxpointstudios.com/materios/guides/iso-42001-nist-ai-rmf-mapping)
- W3C PROV is a family of documents (PROV-DM conceptual model, PROV-O RDF, PROV-N, PROV-XML, PROV-CONSTRAINTS); defines provenance as "information about entities, activities, and people involved in producing a piece of data or thing"; PROV-DM/O/N/CONSTRAINTS are W3C Recommendations dated 30 April 2013. I found no explicit link between ISO 42001 and PROV. [READ] — [W3C PROV Overview](https://www.w3.org/TR/prov-overview/)

### Inferences
- Minimal decision record per contact (PROV mapping: Entity = raw ping data, tile, model weights, calibrator, contact, Pd map; Activity = inference run, calibration fit, association; Agent = software version / operator): survey ID and raw-data hash, sonar/config fingerprint, preprocessing version, model hash, calibrator hash and the calibration-set ID/date, applicability-gate result and claim level, raw score and calibrated probability with interval, position with covariance, association cluster ID and history, operator action. Store as append-only, hash-chained records (each record includes the previous record's hash) so edits are detectable; this satisfies "immutable audit log" without a blockchain.
- Treat a calibrator as a versioned release artefact with its own evidence pack (D-ECE, reliability plots, Pd validation, applicability envelope), mapped to DNV-RP-0671's claims-and-evidence structure: claim ("contacts scored ≥0.8 are true objects ≥80% of the time under envelope E"), evidence (held-out survey results), assumptions, and a monitoring plan that withdraws the claim on envelope breach.
- Certification against ISO 42001 is an organisational matter and out of scope for a student prototype; align the records with A.6.2.8/A.7.5 language so a later audit is feasible.

### Gaps
- I did not read the DNV-RP-0671 text or ISO/IEC 42001 itself (paywalled/secondary summaries only); clause numbers come from secondary summaries and should be verified.
- No sonar- or MCM-specific provenance standard found.

---

## 9. Concluding methods specification (component, method, proving metric, minimum data)

### Takeaway
A rigorous trust layer = (1) a box/range-aware calibrated score on the final output, (2) an injection-derived but real-target-validated Pd map with lower bounds, (3) dependence-aware multi-pass combination, (4) an FA/km²-anchored operating point set by risk control on calibration surveys and verified on held-out surveys, (5) covariance-gated association, (6) position ellipses validated for coverage, (7) an applicability gate that withdraws claims, (8) hash-chained provenance.

### Cited Findings
- Sources underpinning each row are those cited in sections 1–8; no additional external facts are added in this section.

### Inferences
Minimum-data numbers are my estimates from the exact-binomial and Kumar-style sample-complexity arguments above [BACKGROUND arithmetic], to be refined by pilot data; "survey" means an independent survey (distinct day/site), not a tile.

| Component | Recommended method | Metric that proves it | Minimum data |
|---|---|---|---|
| Per-contact probability | Platt/beta calibration on final post-NMS/fusion score with covariates (score, range, complexity index); isotonic/histogram only if data allow (Küppers; Kuzucu) | D-ECE/LaECE with the same covariates (bins <8 dropped), reliability diagram, with survey-level bootstrap CI; ordinary ECE reported but not relied on | Hundreds of labelled contacts per condition for parametric maps; thousands for binning; spread across >= ~5–10 independent surveys; held-out surveys for test |
| Fused/multi-pass score | Recalibrate after association; dependence-aware combination | D-ECE on the fused output on held-out surveys | Overlapping-pass pairs with labels or injected objects |
| Operating threshold at FA/km² | LTT or CRC with FA count / miss fraction as loss on calibration surveys; threshold frozen | Recall (Clopper-Pearson, cluster-level) at the fixed FA/km² on held-out surveys; FROC with survey bootstrap bands | Enough surveyed area to see >= ~30–100 false alarms at the budget; >= 29/59/299 effective independent target trials to certify Pd 0.90/0.95/0.99 with zero misses |
| Pd map | Target injection (elevation + 3-D model + ray trace; GAN optional) at random locations, averaged to per-cell Pd conditional on class, state, range, complexity; report one-sided lower bound | Per-cell Clopper-Pearson lower bound; reliability of predicted Pd versus observed detection of real laid targets | N injections per cell/stratum per the zero-failure arithmetic; real-target validation set (laid-target trial or surveyed objects), even ~20–30 targets gives a first check with wide bounds |
| Real-vs-injected validity | Closed-loop validation | Observed detection rate of real targets within predicted lower/upper Pd band; calibration of Pd itself | Same real-target set |
| Multi-pass combination | Pairwise dependence measured by repeated same-position injection; report interval [max Pd_k, independence formula]; quote lower end until ρ measured | Measured pairwise miss-correlation ρ with CI; predicted vs observed joint detection | Injection in >= 2 overlapping passes at many positions |
| Search-completeness semantics | Bayesian posterior update using Pd lower bound; wording per section 3 | Sensitivity of posterior to Pd (lower vs point) shown; no claim of "area clear" without stated bound | None extra |
| Association | Mahalanobis gating with Σ_i+Σ_j, global (Hungarian) assignment, merge/split-aware persistent IDs | Match precision/recall and mis-association rate vs injected and real repeated objects | Overlapping passes with known object positions |
| Position uncertainty | Explicit TPU budget with correlated towfish terms; Σ per contact | Empirical coverage of 95% ellipse (target ≈95%), mean Mahalanobis d² ≈ 2, reliability over nominal levels, CP interval | Known-position targets: ~60 gives a CP half-width of about ±5–6 points around 95%; fewer gives coarse check only |
| Applicability gate | Hard categorical gate (sonar/config) + soft shift monitors + per-survey injection canary | False-withdrawal and missed-withdrawal rates on deliberately shifted held-out surveys; calibration after gating | At least 2 sonars/configs to demonstrate withdrawal behaviour |
| Provenance | PROV-style, hash-chained append-only records; calibrator as versioned artefact with evidence pack mapped to DNV-RP-0671 claims | Reproducibility test (re-run reproduces contact and probability from the record); tamper-detection test | None extra |

### Gaps
- Items I could not support from sources and that therefore remain proposals: look-dependence model for repeated side-scan passes; side-scan contact TPU budget; applicability-gate thresholds; calibration of the combined Pd; net-state signature modelling.
- Sample-size figures in the table are order-of-magnitude planning numbers, not results from a cited study.
- Not retrieved despite being requested: Williams/Gazagnaire performance-prediction content, CMRE through-the-sensor Pd, lacunarity, laid-target trial validation, MCM FROC practice, block-bootstrap theory, IHO S-44 contact-specific requirements, direct DNV-RP-0671 and ISO/IEC 42001 text.
