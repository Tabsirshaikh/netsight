# Measured, not assumed: calibrated contacts and injected-target search completeness for side-scan sonar on unseen surveys

NetSight team (student project), 2026

Preprint v0. Research model and benchmark report.

## Abstract

After a side-scan sonar survey, contact detection leaves separate questions: which reported contacts are real, and how effectively was the seabed searched? We evaluate these questions on held-out survey recordings rather than random images. In a mine-detection replication, AP50 changes from 0.72 on training images to 0.21 on unseen survey years. Our accepted D-FINE-S research model combines dataset balancing with weight averaging. We calibrate contact probabilities on validation detections and constrain the number of reported contacts on each new survey. This label-free count rule held the false-alarm budget on 6/6 test sets in the current evaluation. We estimate search completeness by transplanting real targets into held-out seabed imagery at the survey operating threshold. Transplant detection broadly tracks real-object recall on several datasets but fails for context-dependent pipelines and wrecks. Simple parametric targets were never detected. A geometry-based applicability gate identifies many recall failures but misses failures within familiar sensor geometry. Evidence-feature fusion also fails to transfer. We report these negative results alongside detector, calibration, completeness, gate, and CPU measurements. The resulting outputs support review and conditional search assessment, not a claim that an undetected object is absent.

## Introduction

A completed sonar survey does not resolve whether every reported contact is real. It also does not establish how likely the system was to detect an object in each searched patch. These are different unknowns. A convincing contact can occur in poorly searched seabed. A patch with no contacts can still contain objects that the detector would miss.

We use `P(real)` for the calibrated probability that a detector contact matches a labelled object under the evaluation rule. We use detection probability, or Pd, for the fraction of injected targets recovered under a stated placement and target protocol. Neither quantity is a general probability that an object exists anywhere in a survey. Contact calibration concerns reported detections. Injection concerns the response to specified targets placed in sampled backgrounds.

Evaluation must also reflect the intended deployment. Adjacent sonar images can share seabed, sensor settings, acquisition geometry, and target appearance. Holding out random images can therefore leave much of the survey environment represented in training. A survey-level split asks the harder operational question: what happens when the next recording differs from those used to fit the model?

Our mine-detection replication illustrates the distinction. The rounded comparison is 0.72 AP50 on training images against 0.21 on unseen survey years. The random held-out image result lies between them. The 0.72 figure is not itself a random-split result. We retain that distinction because combining training-image and random-image evaluations would obscure the source of the apparent performance gap.

Pessanha Santos et al. 2024, in *Data in Brief*, report a preliminary YOLOv4 experiment with 75% mean Average Precision. The available description does not specify a held-out set. Their class-based metric and our class-agnostic AP50 are not identical. We use the comparison to examine evaluation protocol, not to claim a controlled ranking between architectures.

NetSight evaluates the detector and the claims attached to its output. Our contributions are:

- A recording-level evaluation protocol and benchmark manifest, including explicit exceptions and label-convention problems.
- Calibrated `P(real)` and a label-free false-alarm budget enforced by counting reported contacts on the new survey.
- Injected-target Pd at the operational contact threshold, checked against recall on real labelled objects.
- A geometry-based applicability gate measured on held-out blocks, including its missed failures.
- Negative results for evidence fusion, parametric targets, zoom augmentation in v0.3, and the expanded training mixture in v0.5.

We treat these as separable tests. Improved calibration does not establish adequate recall. A count budget does not establish completeness. An applicability pass does not guarantee either.

## Data and protocol

### Datasets, splits, and licences

The accepted research model uses mine-detection, GhostVision, AquaScan, SubPipe, and SCTD data. GhostVision Contact provides an other-sensor shift test. AI4Shipwrecks appears in the benchmark and the rejected v0.5 experiment, but not in v0.4 training.

| Dataset | Held-out groups | Protocol or interpretation note |
|---|---|---|
| mine_detection_sss | Years 2015, 2021 | Validation uses 2017 |
| ghostvision_crabpot | Rec8, Rec9, Rec14 | Validation uses Rec2, Rec13 |
| GhostVision Contact | Contact recording | Other sensor geometry |
| aquascan_1k | 2 survey days | Survey-day grouping |
| subpipe_mini2 | 3 time windows | Labels mark seabed beside the pipe |
| ai4shipwrecks | 13 wreck sites | Official split; excluded from accepted model training |
| SCTD | Official test | Research-only data |

The general rule is to separate recordings, years, or sites rather than images. SCTD uses its official test partition. We do not infer stronger recording independence for that partition than the supplied documentation establishes.

The benchmark manifest records survey groups, image and object counts, and a SHA-256 hash of each sorted image list. This makes the evaluated partition inspectable. The licence register is maintained separately in `licences/`. SCTD is research-only. Because v0.4 learned from SCTD, we call it a research model. It is not a product model and must not be sold as such.

The datasets also differ in annotation practice. SubPipe is a material example: labels can describe seabed beside a pipe rather than a conventional object box. Small box changes then alter matching results. We report this problem rather than treating every unmatched detection as an unambiguous false contact.

### Metrics and fixed rules

The benchmark fixes IoU 0.5 for AP50 and calibration labels. Injected-target hits use IoU 0.3. The operating budget is 1 false alarm per image. Public datasets lack the swath geometry needed for a consistent area-normalised budget. With suitable navigation and area information, the count rule can instead use an area budget.

We report expected calibration error, or ECE, alongside Brier score or log loss where measured. These metrics describe different aspects of probability quality. Recall includes labelled objects that never generated a detection. It is therefore not recall conditional on entering the calibration sample.

Detector comparisons use paired image-bootstrap intervals on the same test images. The v0.4 comparison uses 1000 draws and 95% confidence intervals. These intervals measure uncertainty under image resampling. They do not establish transfer to an unobserved sensor population.

The gate uses 50-image blocks and an ECE failure limit of 0.10. The benchmark also specifies 90% one-sided Clopper-Pearson lower bounds for Pd. Tables below preserve the intervals reported in the corresponding experiments, including the 95% intervals used for the injection realism comparison. These interval conventions should not be interchanged.

## Detector

### Accepted recipe

We use D-FINE-S as a class-agnostic detector. The accepted v0.4 recipe retains dataset balancing from v0.2 and adds exponential moving averaging of model weights. The averaging decay is 0.9998, with warmup over 1000 steps. The training mixture uses a minimum dataset share of 0.15.

Early stopping occurred at epoch 17. The best mean validation AP50 was 0.525 at epoch 11. The model is stored as `runs/research_v0.4/model`. The paired comparison below excludes test-time augmentation.

| Test set | v0.1 AP50 | v0.2 AP50 | v0.4 AP50 | v0.4 − v0.2, 95% CI |
|---|---|---|---|---|
| Mine, held-out years | 0.140 | 0.185 | 0.223 | +0.037 (+0.008, +0.065) |
| GhostVision | 0.345 | 0.353 | 0.361 | +0.008 (-0.018, +0.030) |
| Contact | 0.288 | 0.175 | 0.256 | +0.082 (+0.064, +0.102) |
| AquaScan | 0.530 | 0.574 | 0.615 | +0.041 (-0.002, +0.084) |
| SubPipe | 0.004 | 0.127 | 0.231 | +0.104 (+0.004, +0.216) |
| SCTD | 0.043 | 0.770 | 0.817 | +0.046 (-0.002, +0.093) |

Against v0.2, no point estimate is lower, and several paired intervals exclude no change. This supports accepting weight averaging within this recipe. It does not show a uniform gain on every survey. Against v0.1, Contact declines by -0.031 (-0.056, -0.007).

SubPipe needs particular care. The in-training evaluation gave 0.183, while a rerun of the same model gave 0.231. The annotation convention makes IoU matching unstable. We preserve the paired experiment's values here rather than merging them with rounded summary results or other reruns.

### Protocol replication and rejected changes

| Mine scoring protocol | Test images | AP50 | Recall at 1 FP/image |
|---|---|---|---|
| Own training images | 819 | 0.721 | 0.832 |
| Random 70/10/20 image split, held-out 20% | 234 | 0.528 | 0.681 |
| Whole survey years held out | 168 | 0.209 | 0.216 |

This replication uses the same mine-only D-FINE-S recipe across scoring conditions. It supports survey-level testing as a deployment-relevant requirement. It does not imply that random-split studies are useless; they answer a narrower question.

We rejected zoom augmentation in v0.3 because validation improved while test performance worsened. The mine validation set contained 30 objects, which is too little evidence for fine model selection.

We also rejected v0.5, which added AI4Shipwrecks to the v0.4 recipe. Its best mean validation AP50 was 0.429 against 0.525 for v0.4. In that experiment, Contact changed from 0.258 to 0.153, and mine from 0.222 to 0.195. Those are the experiment's own rerun values. Adding a different target domain did not improve the general research model. A separate specialist remains a more appropriate option to test.

## Calibration and operating point

### What the probabilities mean

Raw detector confidence is not automatically a probability of a real contact. We fit calibration on validation detections and evaluate it on held-out test detections. The resulting `P(real)` remains tied to the annotation and matching rule. It is not a probability of a particular object identity or a guarantee of positional accuracy.

The baseline comparison uses detections with raw score at least 0.1, with up to 800 sampled detections per set. The pooled test sample contains 4,263 detections, of which 467 are labelled real. B0 is the raw score. B1 is temperature scaling. The NetSight comparison here uses beta calibration.

| Test set | B0 raw ECE | B1 temperature ECE | Beta ECE | Beta log loss vs B0 |
|---|---|---|---|---|
| Pooled | 0.173 | 0.085 | 0.042 | 0.259 vs 0.371 |
| AquaScan | 0.190 | 0.077 | 0.013 | 0.080 vs 0.265 |
| GhostVision | 0.171 | 0.044 | 0.020 | 0.244 vs 0.363 |
| Contact | 0.116 | 0.056 | 0.062 | 0.375 vs 0.393 |
| Mine | 0.217 | 0.161 | 0.041 | 0.290 vs 0.451 |
| SCTD | 0.153 | 0.134 | 0.052 | 0.333 vs 0.422 |
| SubPipe | 0.198 | 0.123 | 0.056 | 0.209 vs 0.361 |

Beta calibration improves on raw scores throughout this comparison. It does not beat temperature scaling on Contact. A separate full calibration report evaluates several calibration families on own-dataset validation detections. Its best method varies by dataset. Those results use a different evaluation sample and should not be substituted into this baseline table.

### Counting instead of transferring a threshold

A validation-frozen score threshold assumes that the new survey produces a sufficiently similar false-alarm distribution. That assumption fails in these data. In the earlier v0.1 experiment, a survey-level conformal route also failed to maintain its intended coverage on the test surveys.

Our operational alternative counts contacts on the survey being processed. We set the threshold so that the number flagged does not exceed the budget multiplied by the number of images, or by area when available. False alarms are a subset of flagged contacts. Their count therefore cannot exceed the total flagged count. This is a counting bound, not a learned estimate of false-contact prevalence.

Real contacts consume the same allowance. The bound can consequently reduce recall, especially where many real objects occur. It also does not impose an identical allowance on every individual image.

| Test set | Frozen threshold: FA/image | Budget held? | Frozen recall | Count rule: FA/image | Count-rule recall, 95% CI |
|---|---|---|---|---|---|
| Mine | 4.06 | No | 0.468 | 0.57 | 0.154 (0.122-0.190) |
| GhostVision | 1.35 | No | 0.545 | 0.55 | 0.313 (0.276-0.351) |
| Contact | 0.66 | Yes | 0.264 | 0.49 | 0.219 (0.196-0.243) |
| AquaScan | 1.00 | Yes | 0.687 | 0.39 | 0.605 (0.540-0.667) |
| SubPipe | 1.14 | No | 0.491 | 0.70 | 0.404 (0.276-0.542) |
| SCTD | 0.82 | Yes | 0.891 | 0.18 | 0.736 (0.644-0.816) |

The count rule held the budget on 6/6 current test sets. It also held on 12/12 cases in the earlier survey-level evaluation. These are distinct evaluations, not independent replications to be pooled. We promise only the count constraint. Recall remains an estimate with an interval and an applicability qualification.

## Search completeness by injection

### Target placement and recovery

We estimate Pd by placing targets into held-out test imagery and rerunning the detector. The experiments use up to 300 test images per dataset and independent placement runs with seed 0 and seed 1.

Targets are placed where no labelled object lies and the base detector produced no overlapping detection. A seabed mask restricts placement to insonified background. Its local-mean criterion is at least half the image's 75th-percentile brightness.

Transplants are real labelled objects taken from another image of the same test survey. A padded, feathered margin retains the shadow. The transplant is scaled to the local seabed level. Parametric targets instead use a highlighted block with an acoustic shadow, or a flat textured patch, at the dataset's median object size.

A hit requires IoU at least 0.3 and a score at or above the survey's own count-based operating threshold. We use the threshold that governs reported contacts. Pre-existing detections cannot receive credit. This measures recovery of added targets under a defined perturbation; it does not directly observe the unknown objects in the original seabed.

### Seabed-mask error and realism check

The first smoke run placed targets uniformly, including in the dark water column at nadir. Transplant recovery was 5% against 64% real recall. Restricting placement to seabed changed recovery to 50% against 64%. We report this implementation error because placement validity is central to interpreting injection.

We then compare transplant Pd with recall on real labelled objects at the same threshold and IoU 0.3.

| Test set | Real recall, 95% CI | Transplant Pd, seed 0 | Seed 1 | Interpretation |
|---|---|---|---|---|
| Mine | 0.19 (0.16-0.23) | 0.29 (0.22-0.36) | 0.32 | Consistent / slightly optimistic |
| GhostVision | 0.40 (0.36-0.44) | 0.47 (0.41-0.53) | 0.45 | Consistent |
| Contact | 0.25 (0.23-0.28) | 0.31 (0.26-0.37) | 0.35 | Consistent / slightly optimistic |
| AquaScan | 0.64 (0.58-0.70) | 0.52 (0.45-0.58) | 0.55 | Consistent |
| SubPipe | 0.72 (0.58-0.83) | 0.23 (n=30) | 0.31 | Pessimistic |
| SCTD | 0.76 (0.67-0.84) | 0.26 (n=23) | 0.37 | Pessimistic |

The agreement is approximate, not equivalence. On several datasets, transplantation provides a useful check on background-dependent detectability. On SubPipe and SCTD it fails the realism comparison. Pipelines and wrecks occupy much of the image and depend on wider context. Few free placement sites remain.

The evaluation donors come from the same test survey. This matches sensor and object appearance but limits the claim. The dashboard instead uses donors from validation surveys. The held-out same-survey experiment does not by itself validate every dashboard donor transfer.

### Parametric targets and seabed strata

Parametric targets produced 0 detections out of about 1,000 in each seed, on every dataset. We cannot conclude that real reference objects would be invisible. We can conclude that these synthetic appearances are unsuitable proxies for this detector.

In the context of IHO S-44-style reference targets, a drawn highlight and shadow cannot establish Pd for a physical “1 m cube”. That requires realistic rendering or a seeded-target field trial. This is not a claim of S-44 compliance.

Background also matters. The texture strata below are tertiles of local coefficient of variation, using seed 0.

| Test set | Smooth Pd | Medium Pd | Rough Pd |
|---|---|---|---|
| AquaScan | 0.74 | 0.55 | 0.34 |
| GhostVision | 0.59 | 0.46 | 0.38 |
| Mine | 0.35 | 0.22 | 0.30 |
| Contact | 0.36 | 0.35 | 0.24 |

The ordering is not uniformly monotonic. Texture helps describe variation; it does not provide a universal correction curve.

### Comparison with a hand-set completeness curve

B2 is a hand-set range-dependent Pd curve, with a maximum-over-passes rule. Its single-pass form is `0.95 / (1 + exp(12 (r - 0.85)))`, with zero inside a 5% nadir gap. Relative range assumes a centre nadir, verified for AquaScan and assumed elsewhere.

| Test set | Near: B2 / measured [95% CI] | Middle: B2 / measured [95% CI] | Far: B2 / measured [95% CI] |
|---|---|---|---|
| AquaScan | 0.95 / 0.43 [0.28-0.58] | 0.93 / 0.59 [0.53-0.64] | 0.69 / 0.47 [0.38-0.55] |
| GhostVision | 0.82 / 0.47 [0.41-0.53] | 0.93 / 0.41 [0.35-0.48] | 0.70 / 0.54 [0.44-0.63] |
| Mine | 0.94 / 0.39 [0.29-0.51] | 0.93 / 0.28 [0.21-0.34] | 0.72 / 0.24 [0.12-0.41] |
| Contact | 0.87 / 0.29 [0.23-0.36] | 0.93 / 0.36 [0.30-0.43] | 0.60 / 0.33 [0.26-0.40] |

The range bands are 0-0.33, 0.33-0.66, and 0.66-1. Both placement seeds are pooled. Every B2 value exceeds the corresponding measured interval. Thus this assumed curve overstates measured transplant recovery. This comparison rejects that curve for these experiments, not every possible physical coverage model.

Cells with fewer than 5 injection trials are reported as insufficient. They are not filled with assumed completeness.

## Applicability gate

The gate asks whether survey geometry falls within an envelope estimated from validation surveys of the same data kind. It returns calibrated or indicative status and a continuous out-of-envelope distance.

We evaluated 32 blocks of 50 consecutive held-out images across 6 test sets. Failure was defined before inspection: calibrated-probability ECE above 0.10, or recall at the operating budget below the validation recall interval's lower end. Recall failure was assessed for blocks with at least 10 objects.

| Gate status | Blocks | Claims failed | Failure rate, 95% CI |
|---|---|---|---|
| Flagged: indicative | 15 | 14 | 0.93 (0.68-1.00) |
| Passed: calibrated | 17 | 6 | 0.35 (0.14-0.62) |

The distance score has AUROC 0.71 for claim failure. Flagged blocks fail more often, but passing is not a certificate. Every observed failure was a recall shortfall. No block exceeded the calibration-error limit; the largest ECE was 0.065.

All Contact and held-out mine blocks were flagged. Missed failures included GhostVision blocks from Rec14 and Rec9, with recall 0.18-0.29, and both SubPipe blocks. Familiar geometry cannot reveal every background or annotation problem. An AquaScan block with recall 0.54 was falsely flagged.

This is not yet a withdrawal test on a fully held-out sensor family. Only the Contact recording provides the documented other-sensor case. We retain “indicative” as a warning about unsupported transfer, not as a corrected probability.

## Evidence features

We measured shadow, texture, lines, ripple, anomaly, and box geometry for detections. We tested whether fitting these features with detector scores improves `P(real)`. All fitting used validation surveys.

| Test set | Score-only log loss | Fusion log loss | AUROC: score-only / fusion |
|---|---|---|---|
| Pooled | 0.259 | 0.288 | 0.864 / 0.858 |
| AquaScan | 0.080 | 0.242 | 0.956 / 0.923 |
| GhostVision | 0.244 | 0.264 | 0.858 / 0.856 |
| Contact | 0.375 | 0.494 | 0.808 / 0.741 |
| Mine | 0.290 | 0.363 | 0.796 / 0.814 |
| SCTD | 0.333 | 0.901 | 0.923 / 0.840 |
| SubPipe | 0.209 | 0.550 | 0.884 / 0.897 |

Fusion worsens held-out log loss throughout. Removing several feature groups improves it, consistent with survey-specific patterns that do not transfer. We reject fusion for the current model.

B3 tests the stronger rule that a contact must have a measurable shadow.

| Test set | Real detections dropped | AUROC with B3 |
|---|---|---|
| Pooled | 412 of 467 (88%) | 0.49 |
| GhostVision | 80 of 81 (99%) | 0.49 |
| Mine | 76 of 80 (95%) | 0.46 |
| SCTD | 75 of 105 (71%) | 0.57 |

The shadow extractor assumes the shadow lies to the right. That is inappropriate for part of a centre-nadir waterfall and overstates this filter's loss. The result therefore evaluates this implementation, not an ideal shadow measurement.

We retain evidence features as measurements for expert review. They neither modify `P(real)` nor suppress contacts. More surveys and survey-normalised features are prerequisites for revisiting fusion.

## Deployment notes

### CPU execution and parity

The ONNX export is 41 MB, uses opset 17, and includes a sidecar with model identity and hashes. The check used an AMD Ryzen laptop CPU with 16 threads and no GPU.

| Measurement | PyTorch CPU | ONNX Runtime CPU |
|---|---|---|
| Seconds per image | 1.15 | 0.70 |
| Megapixels per second | — | 1.21 |

The sample contains 8 images of 0.6-2 MP, tiled at 640 px. Detection counts at score 0.3 matched on all images. The largest top-score difference was 0.000003. This is a limited parity test, not proof of identical output for every input or threshold.

The timing report estimates roughly 3.3 s per 100 m of track for a 100 m swath at 5 cm pixels. It excludes flip test-time augmentation, which doubles processing. The ONNX path requires neither a network connection nor a GPU.

### Georeferenced review and coarse mosaics

GeoJSON and KML contact outputs and GeoTIFF completeness layers provide georeferenced review formats. Their interpretation still depends on navigation, pixel geometry, target placement validity, and applicability status. File format does not establish positional accuracy. The benchmark includes an ellipse-coverage evaluation route, but the supplied results do not establish its performance here.

Evidence packs combine JSON and HTML with a hash-chained ledger. They preserve model and processing evidence for review rather than replacing expert disposition.

The NOAA 1 m mosaic check is a deployment limitation: the detector found 0 of 7 confirmed objects at 1 m pixels. This imagery is out of scope for the detector, and completeness is flagged indicative. It must not be read as evidence of a clear seabed.

Separately, the benchmark contains NOAA report-derived contact outcomes. These are expert dispositions supported by sonar and multibeam, not diver verification. Many negative dispositions mean a charted item was not found again. They support indicative studies, not an interchangeable source of ordinary real/false detection labels.

## Limitations and future work

The present limitations are explicit:

- **Limited survey diversity.** Held-out recordings are more demanding than random images, but they do not represent every seabed or sensor family.
- **Small validation samples.** Model selection can favour changes that do not survive testing. The rejected augmentation result demonstrates this risk.
- **Annotation dependence.** `P(real)`, AP50, and measured false alarms inherit box conventions and incomplete labels. SubPipe exposes this problem directly.
- **Restricted calibration evidence.** Validation-based calibration improves the reported tests. It does not establish accuracy under arbitrary domain shift.
- **Recall cost of counting.** A contact-count ceiling bounds false alarms conservatively. It can discard real contacts and does not guarantee local completeness.
- **Injection realism.** Pasting cannot reproduce burial, scour, or true shadow geometry on a new slope. Same-survey donors also limit target diversity.
- **Sparse completeness cells.** Insufficient trials remain insufficient. A continuous-looking map must not conceal missing evidence.
- **Incomplete applicability detection.** Geometry misses recall failures within familiar acquisition geometry and does not resolve label problems.
- **Coarse-image failure.** The NOAA mosaic result is outside supported detector scale.
- **Research-only training.** The accepted weights are not a commercially deployable model.

The next decisive completeness experiment is a seeded-target field trial. It should compare known physical targets with predicted recovery under recorded acquisition conditions. This is needed before assigning reference-target meaning to the injection maps.

We also need more varied surveys and larger validation sets. GhostVision learning experiments support this direction, while showing that recording choice affects transfer. More data should mean more acquisition diversity, not only more adjacent images.

A metadata-driven resampling module should correct pixel size and aspect before inference. The existing Contact resampling result is encouraging but optimistic because test-label geometry informed the settings. Future evaluation must derive factors from acquisition metadata rather than test labels.

Multibeam backscatter is a future extension, not an established capability in these results. A product model must be trained and evaluated using commercially licensed data only. It requires its own benchmark results; the research model's measurements cannot simply be inherited.

## Data and code availability

The repository and benchmark materials are available from the authors. The repository contains detector, calibration, operating-point, injection, applicability, fusion, georeferencing, and ONNX evaluation code. The model location and experiment paths above identify the reported research artefacts.

The benchmark folder describes the protocol and generation command. Generated materials include `splits.json`, NOAA outcome tables, `results_v0.4.json`, and file hashes. The split manifest records survey groups and image-list hashes. The licence register remains authoritative for dataset use.

Research reports retain accepted and rejected experiments, including rerun differences and known implementation limits. Dataset redistribution and model reuse remain subject to their licences. These materials support inspection and replication of the stated claims, not unrestricted reuse of every underlying source.
