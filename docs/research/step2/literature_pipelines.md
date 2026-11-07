# Sonar detection literature: pipelines and test protocols

## Method

The 21 papers below were recorded by an automated agent from pages it actually read. Each reported metric quote was checked word for word by a script. Split protocols were then checked by Claude against the saved page text; the results are identified as `split_check_by_claude`.

The table preserves the reported mAP50 wording and values from the attached records. A reported metric is not necessarily comparable across papers: some papers use different names or definitions, and some excerpts do not make the IoU threshold explicit. For split protocols, the table uses the Claude check when a paper is named there; otherwise it says “not found in fetched text.”

## Papers

| Title (short) | Year | Sonar type | Base detector + key modifications | Datasets | Reported mAP50 (as written) | Split protocol |
|---|---:|---|---|---|---|---|
| Multi-Scale Marine Object Detection (BES-YOLO) | 2024 | Side-scan | YOLOv8n; EMA attention, BiFPN, Shape_IoU, wavelet preprocessing | SCTD | 92.4% mAP@0.5 | not found in fetched text |
| Performance evaluation of YOLO models | 2026 | Side-scan | YOLOv4/6/7/9/13n/26n comparison | Two constructed datasets, D1 and D2 | YOLOv6 on D1: 0.944 | not found in fetched text |
| LSD-DETR | 2026 | Forward-looking | RT-DETR-R18; Sonar-DualNet, DR-Fusion, GLSA-BiFPN, HiLo attention | UPSD | 89.6% | not found in fetched text |
| DFSE-YOLO | 2026 | Side-scan | YOLOv11; selective feature enhancement, adaptive residuals, depthwise convolutions | AI4Shipwrecks | 0.7551 | not found in fetched text |
| Improved YOLOv11 for small objects | 2025 | Side-scan | YOLOv11; Sparse Feature module, Dilated Reparam Block, attention fusion | Not stated in fetched excerpt | 0.825 | 70:15:15 ratio |
| Upsampling and downsampling | 2024 | Side-scan | YOLOv8; SRFD/RFCAConv downsampling, Dysample upsampling | Underwater shipwreck dataset | increased 4.4% over baseline; absolute value not stated in abstract | not found in fetched text |
| Multibeam forward-looking sonar dataset | 2022 | Forward-looking | Faster R-CNN and YOLOv3; compared backbones | UATD | mAP 0.839 (Faster R-CNN ResNet-18); paper calls metric mAP, not mAP@0.5 | not found in fetched text |
| Enhanced YOLOv7 for small objects | 2023 | Side-scan | YOLOv7; 160×160 detection layer, CoT/ELA attention, BiFPN | SSDD | 86.9% (mAP@.5) | 6:2:2 ratio |
| SOCA-YOLO and image restoration | 2025 | Side-scan | YOLOv9; SwinIR restoration, SPDConv, CBAM | Cylinder2 | 74.3% | 8:1:1 ratio |
| YOLO variant evaluation and transfer learning | 2026 | Side-scan | YOLOv8n/10n/11n/13n comparison; transfer-learning and optimizer comparison | Two public side-scan datasets | YOLOv11n 0.917; YOLOv8n 0.906 | 80:20 ratio |
| YOLO-DAFS | 2025 | Other | YOLOv11n; DualBottleneck, DyHead-GDC, ADown, C2PSF, SCSA | UTDAC2020, DUO, RUOD | 84.2% UTDAC2020; 84.4% DUO; 86.7% RUOD | 8:1:1 ratio; UTDAC2020 is optical underwater, not sonar |
| DA-YOLOv7 | 2024 | Mixed | YOLOv7; OA-ELAN, SPPCSPCBiFormer, G-ELAN-H; UATD pretraining then SCTD fine-tuning | UATD, URPC, SCTD | 89.4% UATD; 89.9% URPC; 99.15% SCTD | not found in fetched text |
| Improved YOLOv5 for underwater target detection | 2023 | Forward-looking | YOLOv5; attention, BiFPN, decoupled head | AUH-collected sonar dataset | 80.2% | train:val:test 8:1:1 |
| Sonar-based detection for autonomous underwater vehicles | 2025 | Forward-looking | YOLOv8; MLFANet, CIoU-DFL loss | UATD | 81.86% mAP (metric IoU threshold not explicit in excerpt) | UATD “randomly split” |
| CCW-YOLOv5 | 2024 | Forward-looking | YOLOv5; transfer learning, coordinate convolution, attention, modified box loss | Multibeam forward-looking sonar dataset | 85.3% | not found in fetched text |
| CSC-YOLO shipwreck detection | 2025 | Side-scan | YOLOv8n; context-guided block, shared detection head, C2PC; augmentation | New shipwreck dataset | not stated | not found in fetched text |
| Detection transformer and zero-shot NAS | 2025 | Mixed | DETR; NAS-selected CNN-Transformer, FPN, deformable-attention decoder | Two sonar datasets; names not stated in abstract | not stated in fetched abstract text | not found in fetched text |
| ROSAR | 2025 | Side-scan | YOLOX-ViT; knowledge distillation and adversarial retraining | Three field-collected SSS datasets | not stated | not found in fetched text |
| SS-YOLO | 2025 | Side-scan | YOLOv8; PConv/PWConv, ASSF, improved MHSA head | Combined side-scan dataset (SSSD) | 92.4% | not found in fetched text |
| Side-Scan Sonar Image-Based Object Detection With YOLOv8 | 2026 | Side-scan | YOLOv8s; compared with YOLOv5s and YOLOv3-tiny | Two in-house datasets | 85.5% on small dataset; expanded-set mAP@0.5 rises by 1.9% relative (absolute value not stated) | not found in fetched text |
| AquaYOLO | 2025 | Mixed | YOLOv8; residual backbone, feature aggregation and selection modules | UATD and Marine Debris | not stated | not found in fetched text |

## What the papers have in common

YOLO is the most frequent detector family in these records. Counting the base detector entries, 15 papers list a YOLO model as their base or comparison family, including papers that compare several YOLO versions. The remaining entries include RT-DETR, Faster R-CNN, DETR, and YOLOX-ViT. These counts describe the records, not a ranking of detector performance.

Most papers propose changes to an existing detector rather than reporting only a baseline. Recurring themes include attention modules, feature-fusion or neck changes, and modifications intended to improve small-object detection. Examples include added detection layers, BiFPN, feature-selection modules, and altered detection heads. Other approaches target image restoration, downsampling or upsampling, losses, transfer learning, or robustness through adversarial retraining.

The accessible records rarely state input size or training duration; where stated, they vary (for example, the improved YOLOv5 forward-looking sonar paper lists "epochs 300" and "batch_size 8" in its training table). The records do not support a typical input size or training length. Some records do report training-related choices, including transfer pretraining and fine-tuning in DA-YOLOv7, COCO transfer learning and optimizer comparisons in the YOLO variant evaluation, and adversarial retraining in ROSAR.

## How they test vs how NetSight tests

Every split protocol found by `split_check_by_claude` is a random or fixed-ratio image split. The check found **0 held-out survey/site/date tests**. At least seven papers state a random or fixed-ratio split in the fetched text (70:15:15, 6:2:2, 8:1:1, 80:20, "randomly split"); the check found no split statement for seven others, and two pages were not saved. A validation set or testing set mentioned without a protocol does not establish a survey-level holdout.

NetSight evaluates on whole recordings, survey years, or time windows that were never seen in training. Its evaluation includes AP50, AP at IoU 0.3, recall at 0.5, and recall at one false alarm per image. The replication result below illustrates why split choice matters:

| Evaluation of the same recipe on the mine dataset | Score |
|---|---:|
| Own training images, using the paper protocol | 0.721 |
| Random held-out 20% | 0.528 |
| Held-out survey years | 0.209 |

The recipe scores 0.72 on its training images under the paper’s protocol, 0.53 on random held-out images, and 0.21 on unseen survey years. These results show that a random image split and an unseen-year test answer different questions. A high score under the former should not be read as evidence of performance on new surveys.

## Ideas worth testing in NetSight

These are candidate experiments, not established improvements. Each is **untested for us**.

- **Attention or feature selection:** EMA, CBAM, coordinate convolution with attention, or context-aware selection modules. **Untested for us.**
- **Small-object features:** an added high-resolution detection layer or feature-fusion changes such as BiFPN. **Untested for us.**
- **Image restoration or preprocessing:** wavelet reconstruction or SwinIR restoration. **Untested for us.**
- **Training strategies:** transfer learning, offline augmentation or Mosaic, and adversarial retraining. **Untested for us.**
- **Loss changes:** Shape_IoU, CIoU-DFL, or modified bounding-box loss. **Untested for us.**

## Caveats

The datasets differ across papers, and several records do not state dataset sizes or names in the fetched text. The sonar types also differ: the collection includes side-scan, forward-looking, mixed, and other sonar records. YOLO-DAFS includes UTDAC2020, which the split check identifies as optical underwater rather than sonar; URPC is also identified in the record as an underwater optical dataset. These are not straightforward comparisons with side-scan sonar.

The records do not all describe the same detection task: some are class-agnostic in the NetSight pipeline, while papers may evaluate multiple target categories. Metric definitions also differ. For example, one record reports “mAP” without calling it mAP@0.5, and another gives an mAP value without an explicit IoU threshold in the fetched excerpt. Values should not be treated as directly comparable unless the metric, classes, dataset, and evaluation protocol match.

---

Reviewed by Claude on 2026-11-08 against the agent's quote-verified records and the saved page text; drafted by GPT-6-luna. Split protocols were re-checked by searching the saved text for split statements; the survey agent itself had marked every protocol "unclear".
