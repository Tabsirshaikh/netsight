# Model weights, web libraries and services (not covered by the Python dependency scan)

Checked 2026-11-12. Re-check before any commercial release.

| Item | Used for | Licence / terms | Notes |
|---|---|---|---|
| `ustc-community/dfine-small-coco` | detector starting weights | Apache-2.0 | COCO-only checkpoint; the Objects365 variants are not commercially cleared (see `netsight.detect.dfine`) |
| NetSight research model v0.4 | research detector | research only | trained partly on SCTD (research-only data); never sold as is |
| `facebook/sam-vit-base` (optional) | pre-labelling box refinement | Apache-2.0 | downloaded only when `--refine` is used |
| ONNX, ONNX Runtime | CPU / offline inference | Apache-2.0, MIT | Python packages, also in the automatic scan |
| Leaflet 1.9.4 | dashboard map | BSD-2-Clause | front-end npm package |
| OpenStreetMap tiles | dashboard base map | data ODbL; tile usage policy | attribution required; light interactive use only; not available offline (positions and exports do not need it) |
| NOAA NCEI hydrographic surveys | ground truth, mosaics | public domain / CC0 | |
