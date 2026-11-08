# NetSight — Phase 1, Part B

This is an additive continuation of the supplied, working Part A project.

## Installation

Keep Part A’s package.json, Vite configuration, TypeScript configuration,
Tailwind configuration, application shell, GSAP registration, shared components,
content.ts and styles.css unchanged.

Replace only:

- src/sections/S05Detections.tsx
- src/sections/S06Trust.tsx
- src/sections/S07Geometry.tsx
- src/sections/S08Curve.tsx
- src/sections/S09Ledger.tsx

Add the other supplied files at their indicated paths.

The sections provide both the named exports already imported by Part A’s App.tsx
and default exports. They use Part A’s existing dependencies; no main-application
dependency changes are required.

From `web/`:

    npm install
    npm run dev
    npm run build

Part B imports its additive stylesheet directly. Do not replace styles.css or add
another GSAP registration module.

## Chapters

### 04 — What the model finds

Five deterministic vector sonar illustrations show returns, acoustic shadows,
scan lines, a nadir and drawn detection rectangles. Their metrics are dataset-level
AP50 results, not confidence estimates for the illustrated objects. The Contact
tile separately identifies the specialist improvement. The average comparison is
labelled by research-model version.

### 05 — Trust

A survey illustration moves between three applicability docks with GSAP Flip.
Its illustrated object stretches as applicability changes; the transition is
explicitly schematic, not a measured gate threshold.

The reliability diagram uses schematic bars, labelled as such. The actual measured
calibration-error range is reported separately. Both false-alarm-budget comparisons
have twelve cells; the fixed-budget comparison shows four held and eight broken.

Flip owns its short transform-only transitions. It does not create nested
ScrollTriggers. Outstanding Flip animations are killed before a new move and on
cleanup.

### 06 — Geometry

A procedural object un-stretches around its SVG origin. The research metric
interpolates between the supplied endpoints. The optional raster layer is background
texture, not the animated object. The illustration is not presented as the actual
recording that produced the reported improvement.

### 07 — More surveys

The chart plots the three supplied crab-pot results against recording counts.
Its connecting segments do not assert intermediate measurements. Twenty-one
recording tiles light in cohorts of five, ten and twenty-one. The tile grid is
explicitly schematic, not a geographic map.

### 08 — Evidence pack

An illustrative report assembles next to a real SHA-256 demonstration chain.
The hashes are computed with Web Crypto, then both the original chain and a copy
with an altered second payload are verified. Stored hashes are not rewritten to
hide the change.

Scrolling introduces the altered state. The keyboard-accessible button lets a
reader explicitly switch between original and altered states; that choice then
takes precedence over scroll. The first broken record and subsequent links turn
red. A textual status accompanies the color.

The JSON download is functional and explicitly illustrative. It contains no
fabricated detector score, probability or applicability claim. The shortened
fingerprints expose their full value through the title attribute.

Web Crypto requires localhost or HTTPS. If it is unavailable, the report remains
readable, the JSON download works, and verification displays an explanatory message
instead of invented hashes.

## Motion and accessibility

Each component uses a scoped useGSAP lifecycle. All chapter ScrollTriggers are on
top-level timelines, created in document order by Part A. Scrubbed timelines use
linear easing. GSAP matchMedia supplies static reduced-motion presentations.

Desktop stages pin when the viewport is at least 900 pixels wide and 700 pixels
high. Narrow or short viewports use unpinned scrubbed timelines so long content is
not trapped above or below the visible viewport. All content remains in normal
document order and is readable without optional images.

The Part A shell already refreshes after fonts load. Optional images additionally
refresh ScrollTrigger after loading. No new WebGL runtime is introduced by Part B:
SVG keeps these data-focused sections lightweight and avoids additional continuous
render loops. Counters reuse the supplied DOM-only Counter component.

## Optional generated images

`assets.manifest.json` contains eight consistently art-directed requests. Generate
them using the named model in your image-generation environment, convert the output
to WebP if necessary, and save each file to its declared path relative to `web/`.

For example:

    web/public/img/sonar-pot.webp

No generated image is required to build or run the site.

`OptionalAsset` waits until its wrapper is near the viewport, requests image
metadata using HEAD, checks both the response status and image MIME type, and only
then mounts an image. This rejects the HTML fallback returned by Vite for missing
public files. The procedural layer remains underneath even after a successful
image load. Failed requests do not produce broken image elements.

Use a static server that serves WebP as `image/webp` and supports HEAD. A server
without HEAD support simply retains the finished procedural presentation.
For subdirectory deployment, the loader respects Vite’s configured BASE_URL.

All generated sonar stills remain labelled illustrations, not validation imagery.
The asset manifest does not imply access to the underlying research datasets.

## Remotion explainer

The video is a separately installed project so its dependencies do not enter the
website bundle.

From `web/video/`:

    npm install
    npm run lint
    npx remotion render src/index.ts Explainer out/explainer.mp4

Alternatively:

    npm run build

For interactive preview:

    npm run dev

Composition: `Explainer`, 1920 × 1080, 30 fps, 600 frames, 20 seconds.

Five four-second beats:

1. Towfish and sideways acoustic ping wavefronts.
2. Waterfall accumulation and dark nadir.
3. Detection rectangles and acoustic-shadow evidence.
4. Schematic calibration and an illustrative applicability badge.
5. Report assembly and linked evidence records.

The composition imports editorial content from the parent website, uses only
procedural SVG and DOM geometry, and has no runtime dependency on generated stills,
external font downloads or audio. Font stacks use the website’s Google-font family
names when installed and local fallbacks otherwise. Frames are deterministic.

Remotion’s browser download and rendering may require network access during initial
setup. Rendering requires a Chromium-compatible environment and video-encoding
support provided by the Remotion CLI.

## Suggested verification

- Build Part A plus these replacements under strict TypeScript.
- Scroll forward and backward through all five chapters.
- Resize into desktop, narrow and short viewport configurations.
- Enable reduced motion before loading and toggle it during a session.
- Navigate links and the ledger button using only the keyboard.
- Inspect the JSON download: no illustrative probability is asserted.
- Verify the original ledger, alter the illustration, and restore it.
- Test on HTTPS/localhost and verify the non-Web-Crypto fallback separately.
- Add one manifest image, leave the others absent, and verify both states.
- Render the Remotion composition with the exact command above.

No Part B chapters are left as placeholders.
