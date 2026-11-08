# Per-dataset fine-tuning of v0.4 (P2)

Date: 2026-11-08. `pilot --init-from runs/research_v0.4/model --datasets <one> --lr 5e-5
--ema 0.9998 --epochs 8 --patience 2`; paired test comparison against v0.4 (image bootstrap,
1000 draws, 95% CI, AP50).

| Test set | v0.4 | + mine fine-tune | change (CI) | + GhostVision fine-tune | change (CI) |
|---|---|---|---|---|---|
| mine | 0.223 | 0.201 | -0.022 (-0.037, -0.006) | 0.156 | -0.067 |
| ghostvision | 0.361 | 0.358 | -0.003 | 0.375 | +0.014 (-0.003, +0.032) |
| ghostvision_shift (Contact) | 0.256 | 0.202 | -0.054 | **0.398** | **+0.142 (+0.123, +0.160)** |
| aquascan | 0.615 | 0.579 | -0.035 | 0.547 | -0.068 |
| subpipe | 0.231 | 0.325 | +0.094 (n.s.) | 0.180 | -0.051 (n.s.) |
| sctd | 0.817 | 0.765 | -0.052 | 0.779 | -0.038 (n.s.) |

## Decisions

- **GhostVision specialist kept** (`runs/ft_v0.4_ghostvision/model`, research label inherited
  from v0.4): on its own data it gains on the held-out recordings (+0.014, within noise) and
  strongly on the sensor-shifted Contact recording (+0.142, best result on Contact so far, above
  v0.1's 0.288). It forgets other datasets, so it is used for ghost-gear surveys only; v0.4 stays
  the general model.
- **Mine fine-tune rejected**: its validation AP rose every check (0.253 -> 0.292) while its own
  test set fell (-0.022, CI below zero). Mine validation is one survey year with 30 objects; it
  cannot guide training. Consistent with test A: the mine data needs more surveys, not more
  tuning.
