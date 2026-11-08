# NetSight labelling guide

> Sources: plan section 8.4 (`docs/plan/final.md`), the class-taxonomy and UXO-wording research notes. Draft v0.1 (2026-11-07); items marked "team decision pending" are open, not rules.

## 1. Purpose and kinds of ground truth

NetSight reviews side-scan sonar survey data and gives calibrated probabilities that detected objects are real. Labels must preserve the difference between an interpretation of an image and independent evidence about an object. A plausible appearance is not a confirmed identification.

**Every label must record exactly one ground-truth kind. Never mix these kinds in one label.**

| Ground-truth kind | Meaning |
|---|---|
| Expert disposition | An expert’s interpretation or classification of a sonar contact. This is not physical verification. |
| Physical verification | Evidence from diver/ROV investigation, clearance or retrieval. Record the verification method and what it actually established. |
| Known placement | A laid target with a known placement record. Keep this separate from naturally occurring, physically verified contacts. |

If a contact has several evidence records, retain separate, linked labels rather than combining their ground-truth kinds. For example, preserve the original expert disposition alongside a later physical-verification record. Do not silently upgrade an image interpretation to verified truth.

Student annotations are proposed labels for review; they must not imply expert disposition or physical verification that has not occurred. The team must define who can approve expert-disposition records.

## 2. Two-level taxonomy

Record a **family** and a **fine label**, except that UXO-mode descriptors are attributes, not object classes. Always permit `unknown` and `unknown_manmade_contact`; never force a specific identity.

The taxonomy is NetSight’s design, not a retrieved standard classification scheme. Evidence status describes support for a label or proposed signature, not certainty about an individual contact:

- **Supported:** the attachments identify supporting observations or survey practice.
- **Hypothesis:** the attachments explicitly describe an inference or untested signature.
- **Provisional:** the attachments explicitly mark the label provisional, or present the category as a proposal without established signature evidence.

The qualifications below are essential: supporting survey practice does not validate every proposed visual distinction.

### Ghost gear

| Label | One-line definition | Evidence status and qualification |
|---|---|---|
| `net_bundle_or_mound` | A net in a heap, tangled or snagged at a structure, standing proud of the seabed. | **Supported:** Stolte’s illustrated trawl bundles show height through extended sonar shadows. |
| `net_flat_or_collapsed` | A low-relief, slack or flattened net candidate, suggested by patch texture, net-like edges or trailing lines. | **Hypothesis:** no direct source for the proposed flat-net signature; little or no shadow is an inference. |
| `net_standing_or_suspended` | A candidate net with linear or curtain geometry and evidence of height. | **Provisional; hypothesis:** only indirect line-detection evidence; no sonar signature study found. |
| `line_rope` | A thin linear feature consistent with rope, float/sink line or trawl line. | **Supported:** Stolte reports detection of gillnet and trawl-netting lines. |
| `trap_pot` | A candidate crab, lobster or fish trap. | **Supported:** trap/pot observations are cited; some evidence is search-only, and pot–rock confusion is reported. |

### Disaster debris

These are **proposed response-oriented categories**, informed by survey practice. The plan cites Tohoku, Katrina/Rita and Sandy practice; the research notes distinguish retrieved metadata from search-only reports and state that no formal public classification scheme was established.

| Label | One-line definition | Evidence status and qualification |
|---|---|---|
| `vessel_wreck` | A candidate sunken boat or ship, with hull-like form. | **Provisional proposal:** informed by survey practice, not a validated signature scheme. |
| `container_box` | A regular rectangular, container-like object. | **Provisional proposal:** container survey reports provide supporting context. |
| `vehicle_like` | A compact object interpreted as vehicle-like rather than identified as a vehicle. | **Provisional proposal:** Tohoku vehicle reporting is supporting context. |
| `large_structure_block` | A large block-like structure, such as a candidate caisson, slab or pier section. | **Provisional proposal:** caisson reporting provides supporting context. |
| `rubble_field` | A cluster of many small hard targets, represented by an extent polygon. | **Provisional proposal:** no building-rubble signature description was found. |
| `pipe_cable_linear` | A linear feature consistent with pipe, cable, chain or hose. | **Provisional proposal:** research notes cite mapping classes but say cable classes were not retrieved. |
| `tree_log_vegetation` | An elongated, tapering or branching vegetation-like contact. | **Provisional, unverified signature:** mark low confidence. |

### General

| Label | One-line definition | Evidence status and qualification |
|---|---|---|
| `compact_debris` | A small compact manmade-object candidate, such as an anchor, tyre or drum. | **Supported:** Stolte’s reported object/confuser list. |
| `rock_boulder` | A contact interpreted as a natural rock or boulder. | **Supported:** identified as a confuser in the cited research. |
| `natural_seabed_texture` | Reef edge, flora or sediment change used as a hard negative. | **Supported:** Stolte describes these confusers. |
| `unknown_manmade_contact` | A contact interpreted as manmade whose finer identity cannot be assigned. | **Provisional design/abstention label:** not a verified object signature. |
| `unknown` | A contact that cannot be classified from the available evidence. | **Required design/abstention label:** retained for calibrated outputs. |

Research section 4 also proposes `wreck_or_large_hull` for vessel, aircraft or large structure. Plan section 8.4 uses the more detailed disaster labels above. **The alias/migration mapping is a team decision pending**; do not silently create competing versions.

### UXO-mode attributes

| Attribute | One-line definition | Evidence status and qualification |
|---|---|---|
| `cylinder_like` | A cylinder-like shape descriptor, not a ghost-gear or UXO identity class. | **Proposed design**, informed by the UXO convention. |
| Size descriptors | Recorded dimensions or size descriptors, not object identities. | **Supported:** Cenos requires contact dimensions. |
| `pUXO_candidate` | A flag for a potential UXO candidate requiring assessment, not confirmed UXO. | **Supported terminology; proposed schema field:** Cenos distinguishes initial picks from subsequent pUXO assessment. |

Do not infer ferrous content from side-scan alone. The notes permit `ferrous_indication` only with co-registered magnetometer data.

### Ambiguous splits: merge to the parent

When evidence cannot support a fine split, use the agreed parent. The attachments give:

`vessel_wreck` versus `container_box` → `large_manmade_object`

The merge applies when the split probability is below a **stated threshold**. No threshold or complete parent hierarchy is supplied. These are team decisions pending; do not invent a probability cutoff or treat confidence bands as probabilities. Until the parent mapping is agreed, use an appropriate abstention label and explain the ambiguity.

## 3. Net-state labelling: record observables

Keep net-state judgements separate from claimed identity.

| Net state | Observable basis |
|---|---|
| Standing/suspended candidate | Height inferred from shadow together with linear or curtain geometry. |
| Flat/collapsed candidate | No measurable height, together with a textured bright/dark patch showing net-like edges or trailing lines. |
| Bundled/snagged candidate | Measurable height and an irregular mass, often at a structure. |
| Unknown | The available image does not support a state assignment. |

The notes propose height thresholds but do not supply a NetSight threshold or measurement protocol. Both are **team decisions pending**. Do not estimate unsupported precision.

**“Collapsed nets cast little or no shadow” is a hypothesis to be tested, not an established rule. Shadow must never be used as a hard filter.** Do not discard a potential net because it lacks a shadow, or label a patch as a net solely because it lacks one. Soft sediment is a documented reflectivity confuser.

`net_standing_or_suspended` remains **provisional**. Do not claim validated detection performance for it. The notes require diver/ROV imagery for confirmation of the standing state.

## 4. Drawing annotations

Annotate visible evidence without adding imagined boundaries.

| Issue | Instruction |
|---|---|
| Boxes versus polygons | The general choice is **team decision pending**. |
| `rubble_field` | Use a polygon/extent, not a single point. |
| Object plus shadow | Whether to include the shadow within a box or polygon is **team decision pending**. Record relevant shadow evidence in remarks. |
| Minimum annotation size | A general chip/pixel or physical-size minimum is **team decision pending**. |
| Overlapping objects | Instance separation, overlapping geometry and occlusion rules are **team decisions pending**; flag ambiguous cases for review. |

In **UXO mode**, the adopted Cenos convention picks contacts larger than **1.0 m in any dimension**. This is not a universal ghost-gear annotation cutoff. UXO assessment must not replace individual picks with a boulder-field classification or automatically discard `rock_boulder` contacts; the model may rank them.

### 4.1 Box convention: recommendation and the public datasets (2026-11-08)

**Recommendation (team to confirm):** box the object only, shadow excluded; record shadow
evidence separately. Reasons: (1) the evidence module (`netsight.evidence`) measures the shadow
beyond the box's far-range edge, so a box that already contains the shadow hides it; (2) the
public datasets disagree, and mixed conventions turn correct detections into scored misses at
IoU 0.5 (measured below).

| Dataset | What the boxes cover (as observed) | Consequence |
|---|---|---|
| GhostVision (most recordings) | Trap/pot, roughly square (median aspect 0.9-1.1) | Reference convention |
| GhostVision Contact | Boxes 1.32x wider than tall | Pixel-geometry (sensor) shift, not a labelling choice; flagged by the geometry gate |
| SubPipe | Seabed beside the pipe, not the pipe + shadow the model finds | AP at IoU 0.5 near 0 for v0.1, 0.52 at IoU 0.3; report SubPipe at IoU 0.3 until relabelled |
| AquaScan | Human-sized targets, elongated (aspect 2-4) | Consistent within the dataset |
| Mine detection | MILCO/NOMBO, aspect ~1.6-1.9; shadow inclusion not documented | Check a sample before merging conventions |
| SCTD | Wrecks / planes / people, varied | Research-only; consistent within the dataset |
| NOAA chips | 10 m square around the charted position | Candidates only: extent must be redrawn in review |

Relabelling to one convention uses the pre-labelling route: model proposal -> SAM2 tightening ->
human accept/adjust/reject.

## 5. Fields recorded per label

| Field | What to record |
|---|---|
| Contact ID | Identifier linking observations and evidence for the contact. |
| Image/chip ID | Identifier of the image being annotated. |
| Class | Family and fine label, or agreed parent/abstention label. |
| Net state | Observable state, or unknown/not applicable. |
| Confidence band | `low`, `medium` or `high`. |
| Ground-truth kind | Exactly one of the three kinds in Section 1. |
| Source dataset | Dataset identifier and relevant source record. |
| Licence tier | `commercial`, `conditional` or `research_only`. |
| Annotator ID | Identifier of the person creating the label. |
| Date | Annotation date. |
| Free-text remarks | Evidence, ambiguity, confusers, verification references and unresolved issues. |

Cenos specifies low/medium/high confidence, with criteria defined by the survey contractor. **NetSight’s band criteria are pending.** Do not invent numerical equivalents or treat “high” as physical confirmation.

Licence tier must come from the dataset’s approved rights record, not an annotator’s guess. Escalate missing or unclear rights information before training use.

## 6. Quality control

Use the following review workflow; sampling rates, agreement metrics and acceptance thresholds remain to be agreed:

1. **Double-label a sample independently.** Preserve both original annotations.
2. **Measure inter-annotator agreement.** Review family, fine class, net state and confidence disagreements separately; assess geometry once drawing rules are fixed.
3. **Resolve disagreements through review.** Compare visible evidence and provenance. Refer unresolved cases to the designated expert reviewer rather than forcing consensus on identity.
4. **Retain uncertainty.** Use a parent or abstention label where the evidence cannot resolve a split.
5. **Record adjudication.** Preserve the original labels, final decision and reason; update guidance when a recurring ambiguity is resolved.

Agreement between annotators is not physical verification. Audit ground-truth kinds and licence tiers as well as class choices.

**Never mix `research_only` datasets into commercial training sets.** Keep provenance traceable through exports. Use `conditional` data only under its approved conditions.

## 7. Safe wording for labels and remarks

Prefer:

- “Candidate contact” or “potential ghost-gear contact.”
- “Potential UXO (pUXO) candidate, unverified.”
- “Textured patch with trailing lines; net identity uncertain.”
- “Calibrated probability that this contact is [class], estimated on [dataset]; not a confirmed identification.”

Never write **“confirmed ghost net” without diver/ROV verification**. Do not describe an expert interpretation or model output as “AI-verified.”

Avoid “cleared,” “clear of nets/UXO,” “safe to dredge/anchor/dive,” “no objects present,” “100% detection” and “guaranteed.” Absence of a label is not proof of absence. Coverage statements must remain tied to recorded survey conditions, target size and confidence; do not invent these values.

The notes recommend: “Not for navigation. Not a clearance certificate. No survey system can guarantee detection of all features.” They identify “not a clearance certificate” as suggested wording, not a retrieved quotation.

## 8. Open questions

- Who approves expert dispositions and adjudicates disputed labels?
- What are the parent hierarchy, merge thresholds and legacy-label mappings?
- What height measurement protocol and net-state thresholds will be used?
- When should boxes or polygons include shadows?
- What are the minimum-size, overlap and occlusion rules outside UXO mode?
- What defines low/medium/high confidence?
- What double-labelling sample, agreement metrics and acceptance thresholds are required?
- How will verification records, conditional licences and unresolved provenance be represented in the annotation tool?