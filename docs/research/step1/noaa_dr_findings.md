# NOAA Descriptive Reports: what contact data is actually available (Step 1 research)

Date: 2026-11-06. Method: downloaded three Descriptive Report (DR) PDFs from NCEI, extracted text with
pypdf, had Gemini (via local OmniRoute, `gemini-3.8-flash-medium`) extract a structured summary with
verbatim quotes, then verified the key quotes against the extracted text with grep (all matched).

## Folder contents (VERIFIED by directory listing)

| Survey | Folders | Mosaics |
|---|---|---|
| H12243 | BAG, DR, GEODAS, TIDES, TIFF | `H12243_SSSAB_1m_455kHz_{1,2}of2.tiff` (16 MB each) |
| H12333 | BAG, Bottom_Samples, DR, GeoImagePDF, TIDES, TIFF, project_sketches | `H12333_SSSAB_1m_455kHz_{1..4}of4.tiff` (43-45 MB each) |
| H13684 | BAG, Bottom_Samples, DR (PDF + XML), GeoImagePDF, MBAB, TIFF | `H13684_SSSAB_1m_900kHz_{1,2}of2.tif` (75 MB, 15 MB) |

- Side-scan mosaics are **1 m per pixel**. A 1 m object is about one pixel: these mosaics cannot show
  the appearance of small debris. They are useful for coverage, seabed context and locating contacts.
- **No raw sonar (XTF) and no S-57 contact files** in the public folders checked.

## What the DR text contains (VERIFIED quotes)

- **H13684** (Central Chesapeake Bay, 2022-10-25 to 2023-04-29, R/V Oyster Bay II): Klein 4900 at
  900 kHz, "50-meter range scale", Complete Coverage Option B (100% SSS + concurrent multibeam). No
  contact table in the DR: "Associated contacts are provided within the SS Contacts S57." Ten Dangers
  to Navigation submitted as separate S-57 files (`H13684_DTON_*.000`). Fishing floats were
  correlated with multibeam returns and invalidated or retained.
- **H12243** (Gulf of Mexico, Klein 5000, 200% SSS + multibeam): 4 contacts investigated with
  multibeam; one obstruction on a pipeline (2.5 ft high) judged insignificant; platforms "verified
  with 200% SSS (no MBES)". Full contact list in "Separates V Side Scan Contact Listing and Images of
  Significant Contacts" (not in the NCEI folder).
- **H12333** (Gulf of Mexico, Klein 5000): "A list of all side scan sonar contacts is contained in
  Separate V". The DR itself has tables of investigated contacts with IDs (format `DDD-HHMMSS[P|S]`,
  12 distinct IDs), least depth, position and disposition: DTON, confirmed as insignificant,
  disproved, depression, "evident in SSS; no height off bottom in MB", obstruction retained.
  Two AWOIS charted wrecks were "disproved by 200% sidescan sonar" and deleted.

## Consequences for the plan

1. **Per survey, the DR text gives only the investigated/significant contacts (about 5-12), not all
   picked contacts.** Their outcomes are multibeam-developed (height measured) or disproved by 200%
   side scan: better than pure expert judgement, but still not diver/ROV physical verification.
2. **Full contact lists and raw XTF must be requested** from NOAA (`hsd.inquiries@noaa.gov`) or
   found in other archives. The plan's kill test ("at least 10 surveys with usable contact
   listings") should count DR-level investigated contacts separately from full lists.
3. **Calibration from public DRs alone is small-sample** (tens of surveys x ~10 contacts). It is a
   useful first, honest dataset (disposition categories are rich), and a reason to prioritise the
   NOAA request and partner data.
4. **Disposition vocabulary to support** (from H12333/H12243/H13684): DTON, insignificant,
   disproved (200% SSS), depression, evident in SSS with no height in MB, obstruction retained,
   charted feature remain / add / delete, fishing gear float invalidated / retained.

Raw Gemini outputs were kept in the session scratchpad only; facts above were re-verified.
