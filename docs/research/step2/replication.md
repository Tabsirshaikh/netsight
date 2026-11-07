# Replication: is our pipeline weak, or is the gap our test protocol?

Date: 2026-11-08. The mine-detection dataset paper (Pessanha Santos et al. 2024, Data in Brief)
reports, for YOLOv4: "In this preliminary test, using our dataset of 1170 images, over the first
5000 training iterations, we achieved ... a mean Average Precision (AP) of 75%, a Precision of
82%, and a Recall of 64%". No held-out set is described.

We trained mine-only D-FINE-S models with one identical recipe (tile 640, 30 epochs, same
augmentation, schedule and evaluation code; `netsight.detect.replicate`) and scored them three ways.

| Scoring protocol | Test images | AP50 | AP50 small | Recall @ 1 FP/image |
|---|---|---|---|---|
| Own training images (the paper's protocol) | 819 | **0.721** | 0.576 | 0.832 |
| Random 70/10/20 image split, held-out 20% | 234 | 0.528 | 0.360 | 0.681 |
| Whole survey years held out (2015, 2021) | 168 | **0.209** | 0.091 | 0.216 |

Our detector is class-agnostic; the paper's mAP averages MILCO and NOMBO, so the comparison is
indicative.

## Conclusions

1. **The pipeline is competitive.** Scored the way the paper scored, it reaches 0.72 AP50 versus
   the paper's 75% mAP.
2. **Most of the gap is the test protocol.** The same model falls from 0.72 to 0.53 on random
   unseen images and to 0.21 on survey years it has never seen. Reported side-scan numbers are
   mostly measured on random splits; they do not describe performance on a new survey.
3. This is the NetSight problem in one table: a buyer reading "75%" would expect it on their own
   survey, where the same model finds about a fifth of the objects at one false alarm per image.
4. For v0.1, joint training starved the mine set (<5% of tiles): 0.140 on the same held-out years
   versus 0.209 when trained alone. v0.2 adds a minimum share per dataset.
