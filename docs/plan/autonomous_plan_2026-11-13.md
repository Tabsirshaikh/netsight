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
- 04:30 Phase 1a running: Gemini 3.8 Flash low, 7 workers (mine test 2, GhostVision test 2, Contact 2, mine train 2 incl. reverse). 1,773 images; ~4.5/min at 5 workers. Phase 3a square-pixel resampler committed. ApertureLab reader + licence committed; images downloading.
- 04:37 Phase 5 test training started: proxy + ApertureLab synthetic (class-agnostic), compare with proxy_base.
- 04:52 Phase 5 classifier (resnet18 crops, 13 classes): same-source 51-100% correct but cross-dataset wreck 41%, person 11%, rock (synthetic->real boulders) 1%, pipe (synthetic->real SubPipe) 0%. Classifier learns the sonar, not the object; synthetic classes do not transfer. Net/rope/tyre classes from synthetic data NOT built. runs/classifier_v0/results.json. Phase 1: mine test review done (168; 23 with unsure) -> sol re-check of 33 running.
- 04:54 Mine test rescored: v0.4 AP50 original 0.223 -> conservative v2 0.337 -> generous v2 0.570; model ranking and earlier proxy verdicts unchanged. Gemini rejected 21% MILCO / 36% NOMBO expert labels that look real in spot-check, ~70% of its additions clearly objects -> conservative mode is the main result.
- 05:28 Phase 5 detector test (proxy + ApertureLab): AquaScan -0.095, GhostVision -0.028, Contact +0.038, SubPipe +0.089, mine n.s. -> rejected. Sol vs Gemini on 33 hard mine images: same verdict on 141/275 boxes (51%). Phase 2 pilot started: mine training labels 176 kept + 321 Gemini-added objects.
- 05:30 GhostVision (441) and Contact (550) Gemini reviews done; sol re-check of 68 + 40 images running. Mine review pack built: review_packs/mine_test (168 images; 224 original, 580 proposed, 350 unsure).
- 05:33 Phase 3a verified end to end on a real-format XTF (ApertureLab sss_0000): 293 pings at 0.207 m along vs 0.05 m across -> rows x4.13 to square pixels. XTF reader now accepts single-sided files. GhostVision/Contact rescored (Gemini only): v0.4 0.361->0.551 and 0.256->0.386 conservative.
- 05:57 Phase 1 complete (incl. sol 33+68+40 images). Conservative v2 AP50 v0.4: mine 0.334, GhostVision 0.557, Contact 0.390 (GV specialist 0.496). Review packs built: review_packs/{mine,ghostvision,ghostvision_shift}_test. Old mine fine-tune still worse on v2 (0.303 vs 0.334).
- 06:12 Phase 2 GATE FAILED: proxy with cleaned mine training labels (+321 Gemini-added objects) vs proxy_base: mine conservative v2 -0.014 [-0.037,+0.013] at IoU .5, +0.005 at .3; generous +0.061 is circular (trained and scored on the same Gemini additions). Original labels: AquaScan -0.053, AI4Shipwrecks -0.037, SubPipe +0.246 (unstable set). -> No GhostVision train cleanup, no full retrain (saves ~9 h). Phase 5 also rejected (synthetic: classifier does not transfer, detector mixed).
- 06:12 Last model lever under test: D-FINE-M (Apache-2.0 COCO) proxy, same recipe, vs proxy_base.
- 07:10 D-FINE-M proxy PASSED the gate: conservative v2 mine +0.048 [+0.014,+0.087], GhostVision +0.124 [+0.079,+0.168], Contact +0.015 n.s.; SubPipe -0.118 at IoU 0.3 (real loss). Full training v0.6 (v0.4 recipe, D-FINE-M) started.
