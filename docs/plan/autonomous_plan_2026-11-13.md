# Autonomous run 2026-11-13 (user away until morning)

Goal: phases 1-5 of the model-improvement plan, in parallel, verifying each step before spending
compute or tokens (the user already trained the model 4 times; retrain only after a test shows a
real gain). User checks the phase-4 survey labels in the morning.

Limits: ChatGPT Plus (Codex) is scarce - only GPT-6.1-sol-medium for re-checks (10 images ~2% of the
5-hour window). Gemini 3.8 Flash low (antigravity, 3 accounts) for bulk review - free for ChatGPT.
Quota page: http://localhost:20128/dashboard/quota (check with playwright-core + Edge).

## Phases
1. Test labels: Gemini review mine/GhostVision/Contact test sets -> sol re-check of unsure +5% ->
   Claude spot-check -> corrected labels v2 (originals kept) -> re-score v0.1-v0.4.
2. Pilot: Gemini review of mine training labels -> 1 h proxy (cleaned vs old) scored on v2 test
   labels -> only if real gain: GhostVision train cleanup + full training.
3. Geometry correction from sonar metadata (code); mine specialist.
4. More data: public surveys pre-labelled + Gemini-reviewed, for the user to check.
5. Multi-class model incl. ApertureLab synthetic classes (only after a proxy test).

## Log
