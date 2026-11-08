# NetSight — Phase 1 / Part A

A procedural, scroll-driven research-project launch site.

## Run

Requires Node 20.19+ and npm.

    cd web
    npm install
    npm run dev

Production:

    npm run lint
    npm run build
    npm run preview

The development server and Vite preview both serve the `/app` placeholder. Configure production hosting to rewrite unknown paths to `index.html`.

All dependency versions are exact in `package.json`. Commit the lockfile produced by your first installation.

## Delivered in this part

- Complete cinematic hero: procedural research vessel, articulated towfish, towing cable, ocean surface, seabed, net, trap, lateral ping fans, suspended particles and a scroll-controlled camera dive.
- Complete side-scan explanation: scroll-painted waterfall shader, illustrated net/trap returns and acoustic shadows, dark nadir, ping wavefront, DrawSVG annotations and send/listen/build explanations.
- Complete exploded pipeline: six procedural instrument layers, semantic internal geometry, sequential highlighting, connecting lines, exploded arrangement and reassembly.
- Complete honest-test comparison: Three.js columns and accessible DOM numbers/captions. Values are driven by the same scroll clock. The third value is deliberately highlighted rather than visually exaggerated.
- Complete final chapter: six evidence components converge around one target, dashboard link, project credits and footer.
- Named replacement slots for sections 5–9, with readable research notes and keyboard-accessible disclosure controls.
- `/app` placeholder, cursor, story-depth gauge, optional synthesised sound, reduced-motion layouts and WebGL fallback.
- Centralised editorial content, including every supplied research result for Part B.

Per the explicit Part A boundary, this delivery intentionally does **not** create `assets.manifest.json` or the Remotion/video project.

## Interaction model

Scroll is the clock. Each finished chapter owns one pinned top-level GSAP timeline. Nested timeline tweens never create ScrollTriggers. Scrubbed timelines use linear easing. Parent sections are not pinned; their `.section-stage` is the pin target.

The hero starts with a legible, partially assembled title; scrolling collects the echoes into the wordmark while the camera dives. Essential copy is not contingent on animation completion.

The pipeline starts assembled, expands, illuminates operations in order, then reconnects. Each face contains meaningful geometry:

1. Resampling grid.
2. Proposed bounding boxes.
3. Mesh-like evidence.
4. Calibration bars and reference line.
5. Three applicability states.
6. Linked evidence records.

The waterfall is a deliberately labelled procedural illustration. It is not represented as real survey data. The CTA's evidence geometry is likewise illustrative.

## Motion and accessibility

- Every animated DOM component uses `useGSAP` with a local scope.
- Plugin registration exists only in `src/lib/gsap.ts`. SplitText, Flip and DrawSVGPlugin are registered there; Flip is available for Part B.
- Three.js scene animation stays inside `useFrame`; scenes use the renderer's canvas as their GSAP scope.
- Reduced-motion media queries remove pins and transitions, show final data, use static camera compositions and disable continuous rendering.
- Native pointer remains visible. The additional follower is decorative and disabled on touch and with reduced motion.
- Sound is off initially. AudioContext is created only after an explicit button press. Generated pings are quiet, illustrative and skipped when the document is hidden.
- Semantic section headings, skip link, readable text alternatives, visible focus styles, native links/buttons and accessible counter labels are included.
- The depth gauge is normalised reading progress. Only “0 m” and “Seabed” are labelled; it is not presented as measured bathymetry.
- DOM text remains available if WebGL fails.

## Performance and ownership

- `SceneViewport` imports the WebGL bundle only near the viewport.
- IntersectionObserver pauses offscreen render loops.
- Small screens cap DPR at 1.5, reduce the suspended-particle count, reduce water mesh density and omit postprocessing.
- Bloom is restrained and desktop-only. No chromatic distortion is applied to data.
- Shaders build images procedurally; there are no image or 3D-model downloads.
- Render frames mutate refs/uniforms, not React state.
- Geometry is built once per scene. Imperative primitives are explicitly disposed; declarative R3F geometry/materials are owned by R3F.
- Font readiness, canvas creation and window load trigger sorted ScrollTrigger refreshes.
- GSAP contexts, matchMedia instances, observers, listeners, ticker callbacks and audio resources are cleaned up.

Google Fonts are the only external visual dependency. System-font fallbacks remain usable offline.

## Shared API for Part B

Each shared file documents its public API at the top.

- `SectionShell`: semantic section, stable heading ID convention, `.section-stage` pin target, forwarded outer HTMLElement.
- `SceneViewport`: `kind`, mutable numeric `progress` ref, accessible `label`, optional class name. Add new scene kinds to its union and `three/SceneRoot.tsx`.
- `Counter`: interpolates a ref-driven value without React frame updates; `start/end` define its progress range.
- `Badge`: `calibrated`, `indicative`, `withdrawn`, `research`.
- `ChapterPlaceholder`: temporary title/notes layout, not intended as the final visual treatment.
- `content.ts`: all visible editorial copy and research values.

Create new triggers in document order. After introducing a dynamically mounted scene or changing font-dependent layout, call `refreshStory()`. Keep pins out of placeholder wrappers when replacing them: return `SectionShell` directly, as the finished sections do.

## Part B TODO / design notes

### S05Detections.tsx

Replace the disclosure layout with a pinned gallery of procedural sonar tiles. Draw detection boxes, identify the dataset/target and count AP50 values. Keep the “research model v0.4” label persistent. The Contact tile needs an explicit specialist comparison, 0.26 → 0.40, not an unexplained changing score.

### S06Trust.tsx

Add a survey card whose pixel geometry changes and whose claim level is explained. Use the already-registered Flip plugin for discrete layout transitions, with a calm static alternative. Clearly label a reliability illustration as schematic: the supplied facts give calibration error, not individual empirical reliability-bin values. Show budget held 12/12 versus 4/12, with the fixed-budget failure described as 8/12.

### S07Geometry.tsx

Reuse or extend the waterfall shader's `uStretch` uniform. Show a stretched strip returning to consistent pixel geometry while AP50 changes 0.175 → 0.368. Keep “no retraining” adjacent to the score.

### S08Curve.tsx

Draw the measured crab-pot learning curve at 5/10/21 recordings and 0.26/0.34/0.37 AP50. Survey tiles should represent recordings rather than fabricate geographic locations. State “an unseen sensor tripled” without inventing its baseline.

### S09Ledger.tsx

Assemble a JSON/report evidence card. Connect schematic hash blocks. Change one block and flag the corresponding broken link. Do not imply that a tamper-evident record proves the underlying detection.

## Images and video in Part B

Part A references no missing image URLs and does not depend on an asset manifest. Every supplied section is finished procedurally.

In Part B, create `assets.manifest.json` with the requested 6–10 art-directed prompts using `gemini-3.1-flash-image`. Generate files separately into `public/img/`; the manifest itself is not an image generator. Maintain deep navy, restrained teal echo light and a warm instrument accent. Add a build-time `import.meta.glob` of actual generated files so optional imagery is only referenced when present. Preserve the procedural fallback.

Also in Part B, create a separate `video/` Remotion project and a 20-second composition: towfish ping → waterfall → boxes → trust badge → evidence pack. Keep its tooling separate from this web application's dependency graph.

## Verification checklist

- Run build and lint.
- Check desktop, narrow mobile and landscape layouts.
- Scroll each complete chapter in both directions.
- Toggle reduced motion before and after page load.
- Navigate with Tab, activate every disclosure and follow `/app`.
- Disable WebGL and verify the text and fallback illustrations.
- Confirm no sound before explicit interaction.
- Inspect AP50 labels and comparison values against `content.ts`.
- Confirm production SPA fallback for `/app`.
