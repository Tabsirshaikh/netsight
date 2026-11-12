# NetSight research workspace

The dark-only dashboard lives at `/app`. The landing page is unchanged. The
viewer uses Canvas 2D; the dashboard does not mount a three.js scene.

## Install and run

Use the repository's supported Python environment and prepare its existing
research models, pixel-cache datasets, and calibration prediction dump.

The optional-dependency entry is provided separately in
`docs/web/pyproject_app_extra.toml`. Merge `app` into the repository's existing
`[project.optional-dependencies]` table, then run:

    uv sync --extra app

Alternatively, install the same dependencies directly into the uv environment:

    uv pip install "fastapi>=0.115" "uvicorn>=0.30" "python-multipart>=0.0.9"

From the repository root, start the API:

    uv run python -m netsight.app.server --port 8000

Offline CPU mode (no GPU, no network; general model from its ONNX export):

    uv run python -m netsight.detect.onnx_export export <data>/runs/research_v0.4/model <data>/runs/onnx_v0.4/model.onnx
    uv run python -m netsight.app.server --port 8000 --onnx <data>/runs/onnx_v0.4/model.onnx

In another terminal:

    cd web
    npm install
    npm run dev

Open `http://127.0.0.1:5173/app`. Use `127.0.0.1`, not `localhost`. Both Vite
development and preview proxy relative `/api` requests to the loopback API.

Production-build check:

    cd web
    npm run build
    npm run preview

Preview is at `http://127.0.0.1:4173/app`.

CPU-only API tests:

    uv run pytest tests/test_app_server.py

The tests require FastAPI's TestClient dependencies, including `httpx`, in the
test environment. They inject a runtime and pack writer; they do not download
models or access a prediction dump, dataset, or GPU.

## Research assets

Paths are relative to `netsight.config.data_dir()`:

- General: `runs/research_v0.4/model`
- Ghost-gear: `runs/ft_v0.4_ghostvision/model`
- Calibration and geometry reference: `runs/calib_v0.4`
- Sample pixels: `cache/pixels`
- Packs and greyscale previews: `runs/dashboard_packs/<survey_id>/`
- Provenance ledger: `runs/dashboard_ledger.jsonl`

Each model directory needs its existing `manifest.json`, including `model_id`,
`model_class`, `label`, and `manifest_sha256`.

Initialization is lazy. The first health request loads both models, fits the
existing calibrator, and caches up to two test images from each of GhostVision,
GhostVision shift, AquaScan, Mine, SCTD, and SubPipe. CUDA is used when available.
If the data are absent, the API returns a descriptive JSON initialization error.

The server binds only to `127.0.0.1`. It is a local research tool, not an
authenticated multi-user service. CORS permits only the specified local Vite
origins. Do not expose the API through a public reverse proxy.

## Workflow and controls

1. **Upload / drop:** choose up to 20 PNG, JPG, TIF, TIFF, or BMP images.
   Multiple images form a single survey. The entire multipart request, including
   overhead, is limited to 50 MiB. Individual images are limited to 40 million
   pixels. A multi-page TIFF uses its first frame. Images are converted to
   greyscale uint8. Server-generated PNG previews make TIFFs viewable in browsers.
2. **Held-out samples:** choose one or more gallery images. Sample selection can
   be combined with uploads. Dataset tags identify the test-set source.
3. **Model:** General v0.4 or the Ghost-gear specialist. Changes take effect on
   the next run. The saved result retains its own model label and manifest.
4. **Applicability profile:** select General or a dataset-specific geometry
   envelope. General passes `None` to the existing reference functions.
5. **False-alarm budget:** 0.25–3 per image. Sliding immediately previews the
   count operating point using raw scores across the entire survey:
   `floor(budget × number of images)` highest scores. The corresponding
   kth-largest score is the threshold; boundary ties are included, matching
   score-at-or-above-threshold flagging. A zero count gives an infinite
   threshold, represented as `null` in JSON. The budget is not an observed
   false-alarm rate on the uploaded survey.
6. **Flip TTA:** enables the predictor's horizontal-flip views. Disabling it
   selects `views="none"`.
7. **Analyze / re-run:** runs the research detector, existing calibration,
   evidence extraction, geometry applicability, validation recall, and evidence
   pack writer. Model work and ledger writes are serialized.
8. **Viewer:** wheel to zoom, drag to pan, `0` or Fit to fit, `+`/`-` to zoom.
   Tall waterfall strips include a clickable minimap. Use the thumbnail strip
   to switch images. Box colour/opacity reflects calibrated probability;
   dashed boxes are below the current threshold. Hover for a tooltip; click
   to inspect.
9. **Contacts:** sort by probability or raw score. `j`/`k` move selection across
   images. Enter zooms to the selection when focus is in the workspace; Enter
   on a contact-row button selects and zooms to that contact.
10. **Command palette:** Ctrl/Cmd+K. Search samples, choose a model, set a
    budget, create a new survey, or export. Arrow keys navigate; Enter applies;
    Escape closes. Focus returns to the previous control.

The running sonar animation and stage captions are illustrative, not backend
progress telemetry. The backend returns one complete response. Reduced-motion
preferences disable the sweep, rings, and GSAP transitions.

## Interpreting results

Probabilities are **calibrated on validation surveys**. They do not establish an
object's identity.

The inspector distinguishes calibrated, indicative, and withdrawn applicability,
with the reference function's statement and reasons. Evidence fields are
rendered directly from the existing evidence extractor, including available
shadow, height, texture, line, ripple, and anomaly measurements. Missing features
are not invented. A missing measurable shadow is not penalised.

Recall is sourced from **validation surveys, same budget rule (not this
survey)**, with its interval. It is not measured from the user's unlabelled
images.

Slider changes are a local preview. Saved applicability, recall, evidence, JSON,
and HTML remain tied to the completed run. Newly preview-flagged contacts may not
have evidence yet. Re-run at the new budget to regenerate the complete pack.
Changing model, profile, or TTA similarly requires a new run.

Completed surveys remain in page memory until the page is closed. Preview images
are Blob object URLs and are revoked on unmount. Evidence packs remain on disk.
There is no automatic deletion policy; remove old local packs according to the
team's data-retention requirements. Original-upload SHA-256 hashes are included
in the evidence inputs; sample inputs hash their canonical PNG representation.
Duplicate input names receive unique suffixes.

Downloads use the existing evidence-pack builder and writer, with the existing
provenance ledger. Pack URLs refer to immutable completed survey IDs.

## Injection boundary

`netsight.app.server.runtime_factory` is public and lazy. Tests may replace it
before the first request, or call `create_app(factory=...)`.

`Runtime` exposes the models/processors, predictor, calibrator, geometry,
validation-recall, threshold, evidence extractor, cached samples, output paths,
and optional pack writer. The default runtime imports and uses the repository's
existing detector, survey reference functions, evidence extractor, pack builder,
and Ledger; it does not replace their research logic.

## Design references

Principles only; no copied assets or interface templates:

- **Linear:** calm density, restrained hierarchy, compact controls, keyboard
  navigation.
- **Vercel / Stripe:** explicit empty states, readable forms, quiet gradients,
  clear saved-versus-preview state.
- **Raycast:** searchable, keyboard-operated command palette.
- **Grafana dark:** legible numeric summaries and consistent status encoding.
- **Mission-control interfaces, including Anduril Lattice and Palantir:**
  image-centric workspace, persistent context, tactical overlays, and an
  adjacent evidence inspector.

The palette and typography use the site's deep-ocean, ink, sonar, and signal
colours with Space Grotesk, DM Sans, and IBM Plex Mono. Status is conveyed with
text, symbols, and border patterns as well as colour. Focus rings, semantic
controls, keyboard alternatives, responsive panels, and reduced-motion fallbacks
are included.
