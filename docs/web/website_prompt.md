You are a world-class creative developer and motion designer (the kind whose work wins Awwwards
Site of the Day, FWA and CSS Design Awards). Build PHASE 1 of the NetSight website: a cinematic,
scroll-driven storytelling site that explains the project. It must feel like an award-winning
product launch site: dark, deep-ocean atmosphere, precise typography, buttery 60 fps animation,
dozens of distinct animated elements, and every animation must EXPLAIN something, not decorate.

## The project (content source - use these facts only)

NetSight (team SIH26057) finds debris on the seabed - ghost fishing nets, traps, lost gear,
wrecks - in side-scan sonar surveys, and tells the user how far each detection can be trusted.
- Side-scan sonar: a towfish pulled behind a boat sends acoustic pings sideways; echoes build a
  "waterfall" image of the seabed line by line; objects stand out and cast acoustic shadows;
  directly under the towfish is a dark water-column gap (nadir).
- Pipeline: ingest + normalise the survey (convert every sonar to one pixel size) -> detector
  (D-FINE, a transformer object detector) -> evidence (shadow/height, mesh texture, lines,
  ripple-pattern breaks, local anomaly) -> calibration (scores become honest probabilities) ->
  applicability gate (is this survey like the data we validated on? claim level "calibrated",
  "indicative" or "withdrawn") -> evidence pack (JSON + report) recorded in a hash-chained,
  tamper-evident ledger.
- The honest-test story (our key message): the same model scores 0.72 AP50 when tested on its
  own training images (how most papers test), 0.53 on random held-out images, and 0.21 on survey
  years it has never seen. Papers report 75-99% on random splits; NetSight reports performance on
  surveys the model has never seen.
- Research model v0.4 results on never-seen surveys (AP50): shipwrecks/aircraft/people (SCTD)
  0.82, people (AquaScan) 0.61, crab pots (GhostVision) 0.36, a different sensor (Contact) 0.26
  -> 0.40 with the ghost-gear specialist, mine-like objects 0.22. Average 0.42 (v0.1 was 0.27).
- Trust layer facts: raw detector scores are overconfident; after calibration the error is
  0.004-0.035. A false-alarm budget fixed in advance broke on 8 of 12 new surveys; NetSight's
  label-free counting rule held the budget on 12 of 12. Correcting a survey's pixel geometry
  lifted a stretched-sensor recording from 0.175 to 0.368 with no retraining.
- More surveys help: crab-pot detection rose 0.26 -> 0.34 -> 0.37 with 5 -> 10 -> 21 training
  recordings; an unseen sensor tripled.
- Wording rules (strict): label results "research model"; never write "guaranteed", "100%",
  "always detects", "certified" or claims we have not measured; no invented statistics about the
  world (if a section needs one, write the sentence without a number).

## Tech stack (use the best open-source tools from GitHub/npm; exact versions in package.json)

- Vite + React 18 + TypeScript, Tailwind CSS.
- GSAP 3 with ScrollTrigger, SplitText, Flip and DrawSVG (all free) via `@gsap/react` useGSAP.
- Lenis smooth scroll, synced with ScrollTrigger (`lenis.on('scroll', ScrollTrigger.update)`,
  drive Lenis from `gsap.ticker`, `gsap.ticker.lagSmoothing(0)`).
- Three.js via @react-three/fiber + @react-three/drei (+ @react-three/postprocessing for bloom,
  noise, chromatic aberration used sparingly). All 3D models PROCEDURAL (built from geometry in
  code: hull, towfish, cable, seabed terrain, debris) - no downloaded 3D assets.
- Custom GLSL shaders where they add meaning: caustics on the seabed, the sonar ping wavefront,
  the waterfall image building up line by line, scan-line noise.
- Fonts from Google Fonts only (e.g. a technical grotesk for headings + a mono for data).

GSAP rules (follow exactly): useGSAP with a `scope` ref in every component; ScrollTrigger only on
top-level timelines/tweens (never on tweens inside a timeline); `ease: "none"` for scrubbed
timelines; animate transforms (x, y, scale, rotation) and autoAlpha, never top/left/width/height;
`gsap.matchMedia()` with `(prefers-reduced-motion: reduce)` giving a calm static version of every
section; register plugins once in one module; create ScrollTriggers top-to-bottom and call
ScrollTrigger.refresh() after fonts/canvases load; clean up everything on unmount; no
`markers: true` in the final code.

## Sections (each a separate component; one pinned, scroll-scrubbed story per section)

1. **Hero** - night ocean surface seen from above water, a research vessel (procedural) towing a
   side-scan towfish on a cable; the camera dives below the surface as you scroll; fan-shaped
   sonar pings sweep the seabed; title "NetSight" assembles from sonar echo particles (SplitText
   chars + particles). Subtitle: "Finds debris in side-scan sonar - and tells you how far to
   trust each find."
2. **How side-scan sees** - pinned: a single ping travels out (wavefront shader), echoes return,
   each return paints one line of a waterfall image; scrolling paints the whole image; a net and a
   trap appear with their acoustic shadows; the nadir gap is labelled. Small annotations draw in
   with DrawSVG.
3. **Exploded pipeline** (the signature moment) - like a watch exploding into its parts: the
   towfish/survey "block" breaks apart in 3D on scroll into six labelled components (Normalise,
   Detect, Evidence, Calibrate, Gate, Evidence pack); each piece glows while its caption explains
   it in one sentence; then they reassemble into one system.
4. **Papers vs reality** - three animated columns 0.72 / 0.53 / 0.21 with the captions above;
   the punchline "A buyer needs the third number. We report it."
5. **What the model finds** - a gallery of procedural/AI-image sonar tiles with detection boxes
   drawing in, per-target scores counting up (SCTD 0.82, AquaScan 0.61, GhostVision 0.36, sensor
   shift 0.26 -> 0.40, mine-like 0.22), a "research model" tag on the section.
6. **Trust layer** - three claim-level badges (calibrated / indicative / withdrawn) explained
   with a survey card that changes level as its pixel geometry is stretched (Flip animation); a
   reliability diagram whose bars settle onto the diagonal as calibration is applied; the
   "budget held 12 / 12 vs 4 / 12" comparison.
7. **Geometry correction** - a stretched sonar strip un-stretches on scroll; the score ticks
   0.175 -> 0.368.
8. **More surveys, better model** - an animated learning curve (5 -> 10 -> 21 recordings) with a
   map-like grid of survey tiles lighting up.
9. **Evidence pack + ledger** - a report card assembles; hash blocks chain together; one block is
   "tampered" and the chain turns red at that link.
10. **Call to action** - "Open the dashboard" (links to `/app`, a placeholder page in this phase)
    and team credits (SIH26057). Footer.

Global: a custom cursor that becomes a sonar ping ripple over interactive elements; a scroll
progress "depth gauge" on the side (0 m -> seabed); section transitions with masked reveals;
subtle film grain; sound OFF by default with an optional toggle (no autoplay audio). Keyboard
accessible, visible focus, semantic headings, alt text, contrast AA. Mobile: simplified 3D
(lower particle counts, DPR capped at 1.5, no postprocessing), all content still readable.
Performance: lazy-load each canvas when near the viewport, pause offscreen render loops, keep
the main bundle small (code-split three.js), no layout thrash.

## AI-generated imagery

Do not reference images that do not exist. Instead create `web/assets.manifest.json`: a list of
{ "file": "public/img/<name>.webp", "model": "gemini-3.1-flash-image", "size": "1920x1080",
"prompt": "<detailed art-directed prompt>", "used_in": "<component>" } for 6-10 stills (e.g.
moody research vessel at dusk, towfish on deck, underwater light shafts, seabed with a ghost net
silhouette) in one consistent art direction (deep navy, teal sonar glow, warm accent). Every
component must look finished WITHOUT these images (procedural gradient/shader fallback) and use
the image when the file exists.

Also create `web/video/` with a Remotion project (`npx remotion render`) for a 20-second
explainer video: towfish ping -> waterfall builds -> boxes appear -> trust badge -> evidence pack.

## Deliverables

- Everything under `web/`: package.json (scripts: dev, build, preview, lint), vite.config.ts,
  tsconfig.json, tailwind config, index.html, src/main.tsx, src/App.tsx, src/lib/gsap.ts (plugin
  registration + Lenis setup), src/sections/*.tsx, src/three/*.tsx (scenes, procedural models,
  shaders in src/three/shaders/*.glsl.ts), src/components/*.tsx (cursor, depth gauge, badges,
  counters), src/content.ts (ALL text and numbers in one place, from the facts above),
  web/assets.manifest.json, web/video/* (Remotion), web/README.md (how to run, how assets are
  generated).
- Code that builds with `npm install && npm run build` with no TypeScript errors.
- Prefer complete, working, polished sections over many half-done ones: if you run out of space,
  finish sections 1-4 and 10 fully and list the rest in README as TODO with their design notes.

Return ONLY the files, each starting with a line `=== FILE: <path> ===` followed by the raw file
content (no markdown fences).
