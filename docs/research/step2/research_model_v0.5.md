# Research model v0.5 (v0.4 recipe + AI4Shipwrecks): rejected

Date: 2026-11-08. Same recipe as v0.4 (weight EMA, min share 0.15) plus AI4Shipwrecks as a sixth
dataset (526 boxes after dropping 16 near-invisible water-column boxes). Early stop at epoch 17,
best mean validation AP50 0.429 (v0.4: 0.525).

| Test set | v0.4 | v0.5 | change |
|---|---|---|---|
| mine | 0.222 | 0.195 | -0.027 |
| ghostvision | 0.361 | 0.335 | -0.026 |
| ghostvision_shift (Contact) | 0.258 | 0.153 | -0.105 |
| aquascan | 0.614 | 0.583 | -0.031 |
| sctd | 0.816 | 0.779 | -0.037 |
| subpipe (unstable label convention) | 0.183 | 0.257 | +0.074 |
| ai4shipwrecks (13 unseen wreck sites) | - | 0.274 | new |

Decision: **rejected** (several drops at or beyond ~0.03, Contact -0.105); v0.4 stays the
research model. The shipwreck strips (1728 x ~5600 px, a very different target) take a sixth of
the training share and the other datasets lose. If wreck detection is wanted, train a separate
shipwreck specialist from v0.4 (`--init-from`), as done for GhostVision, rather than mixing.
