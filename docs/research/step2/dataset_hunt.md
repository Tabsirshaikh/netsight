# Dataset hunt results (Step 2B)

Date: 2026-11-07. Method: `antigravity/gemini-3.8-flash-high` via OmniRoute ran an agent loop
(346 turns, 74 searches, 200 pages read, 171 fetched successfully, 18 distinct websites:
Zenodo, figshare, Hugging Face, GitHub, IEEE DataPort, Dryad, PANGAEA, SEANOE and others).
Each dataset had to be recorded with a word-for-word quote from a page actually fetched; the
script checked every quote against the saved page text.

**Reliability note.** Gemini's free-text final summary contradicted its own quote-checked
records (it gave AquaScan-1K a CC BY 4.0 licence and tyre/cylinder classes; the Zenodo API
says MIT and human surrogates; it invented licences for Marine-PULSE, NNSSS and SCTD, and
called UATD side-scan). Only the quote-checked records below are used, and licences are
confirmed from official metadata before any dataset enters `licences/datasets.yaml`.

Status: **verified** = licence checked by Claude from the repository's machine-readable
metadata; **hunt** = quote-checked by the hunt only; must be verified before use.

## Side-scan, labelled objects (detector training)

| Dataset | Labels | Licence | Status | Use |
|---|---|---|---|---|
| AquaScan-1K (Zenodo 18771165) | boxes, human surrogates, 455-1075 kHz | MIT | verified | product + research |
| Mine detection, Pessanha Santos (figshare 24574879) | boxes, mine-like shapes | CC BY 4.0 | verified | product + research |
| SWDD wall detection (Zenodo 13692547) | boxes, walls / structures | CC BY 4.0 | verified | **inspected: one survey, 75% augmented copies leaking across its splits; not for training, test-only (OOD)** |
| SCTD (GitHub MingqiangNing/SCTD) | boxes: shipwreck, aircraft, human | not stated | hunt | research only; ask authors |
| KADAL multi-source v6 (Hugging Face, gated) | boxes | card says Apache-2.0 | hunt | research only: re-packages other datasets |
| IEEE DataPort side-scan image (Can Lei) | image classes | CC BY | hunt | classification pretraining; registration needed |
| Marine-PULSE (Zenodo 7922705) | pipelines / structures | not stated | hunt | research only |
| NNSSS (GitHub aburguera/NNSSS) | segmentation masks | not stated | hunt | research only |

## Side-scan, raw files or mosaics (pipeline tests, seabed for target injection)

| Dataset | Content | Licence | Status |
|---|---|---|---|
| Green sturgeon, Humminbird 1.2 MHz (Dryad 10.7291/D1738V) | raw recordings, fish points | CC0 1.0 | hunt |
| Wendtorf / Bottsand Humminbird (Zenodo 16085852) | raw survey files, photos | CC BY 4.0 | hunt; access by request |
| Northern Adriatic mesophotic reefs (Zenodo 4608083) | Klein mosaics, fine resolution | CC BY 4.0 | hunt |
| Laoniu reef No.2 shipwreck (Zenodo 5558094) | sonar survey data, wreck site | CC BY 4.0 | hunt |

## Forward-looking and simulated sonar (later multi-sonar work, Step 4)

| Dataset | Content | Licence | Status |
|---|---|---|---|
| UATD (figshare 21331143) | forward-looking (Tritech), boxes | CC BY 4.0 | hunt |
| Caltech Fish Counting (data.caltech.edu g945x-41103) | ARIS/DIDSON video, boxes | MIT | hunt |
| SonarCloud, DFKI (Zenodo 16645568) | simulated FLS, 19 targets, 44 GB | CC BY 4.0 | hunt |
| AAU synthetic FLS (GitHub) | simulated FLS, masks | MIT | hunt |
| Marine debris FLS (GitHub mvaldenegro) | ARIS debris, masks | not stated | hunt; research only |
| Lake swimmer, ME diver (Hugging Face) | BlueView imaging sonar | CC BY-NC 4.0 | hunt; research only |
| Mullet schools ARIS (Zenodo 8384812) | points | CC BY 4.0 | hunt |

## Gaps

- No openly licensed **ghost-net or marine-debris side-scan box dataset** was found. GhostVision
  (crab pots, conditional licence) remains the only gear set; nets must come from our own
  labelling, target injection and the outreach requests.
- **Indian waters:** no open side-scan data found; NIOT / CSIR-NIO data is by institutional
  request only (see `docs/outreach/data_requests.md`).
- Add SCTD, Marine-PULSE, NNSSS and the marine-debris FLS authors to the outreach emails.
