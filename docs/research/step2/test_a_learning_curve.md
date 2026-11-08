# Test A: does training on more surveys help? (GhostVision learning curve)

Date: 2026-11-08. GhostVision only, v0.4 recipe (weight EMA 0.9998), nested random subsets of
the 21 training recordings (group seed 0), max 3000 tiles per epoch, up to 10 epochs, early stop
(patience 2 validations). Test: the same held-out recordings (Rec8/Rec9/Rec14) and the
sensor-shifted Contact recording.

| Training recordings | GhostVision test AP50 | AP30 | Contact AP50 | Contact AP30 | best val |
|---|---|---|---|---|---|
| 2 | 0.269 | 0.444 | 0.074 | 0.245 | 0.164 |
| 5 | 0.251 | 0.418 | 0.116 | 0.291 | 0.207 |
| 10 | 0.332 | 0.480 | 0.167 | 0.283 | 0.303 |
| 21 | **0.369** | **0.514** | **0.224** | **0.346** | 0.336 |

## Conclusion

The curve is **still rising** at 21 recordings: from 5 to 21 recordings GhostVision test AP50
gains ~0.06 per doubling, and the sensor-shifted recording triples (0.074 -> 0.224). More
distinct surveys improve both in-distribution detection and robustness to an unseen sensor, so
collecting more labelled surveys is worth the effort (Track 1 / v5). A rough extrapolation
(+~0.05 AP50 per doubling) is not a promise.

Caveats: one random order (seed 0); runs with fewer recordings also trained for fewer steps
(2 recordings: ~600 steps; 21: ~3750), which is how learning curves are usually run but mixes
data and compute; 2 vs 5 recordings is within noise.
