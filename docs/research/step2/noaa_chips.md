# NOAA verified contacts -> candidate training chips (P6)

Date: 2026-11-08. Code: `python -m netsight.datasets.noaa_chips` (GPT-6.1-sol draft, reviewed).

- NCEI has **no raw side-scan (XTF) files** for our surveys with the most confirmed contacts, but
  publishes georeferenced side-scan mosaics (GeoTIFF + world file, 1 m pixels, 445-455 kHz).
  Downloaded: H12330 (4 tiles), H12357 (2), H12890 (2), ~330 MB, `raw/noaa/<survey>/TIFF`.
- Contacts from our NOAA tables (`processed/noaa/contacts.csv`, `features.csv`) are projected
  from WGS84 to the mosaic CRS; a 256 px chip and a 10 m candidate box are cut around each.
- Result (`processed/noaa_chips/<survey>`): H12330 24 chips (23 confirmed real), H12357 27 ok +
  12 outside data coverage (16 real), H12890 9 ok + 1 no data (9 real): **60 chips, 48 confirmed
  real objects**.
- Review fix: brightness is now stretched per chip (a whole-mosaic stretch washed H12357 white).

## Visual check (16 chips)

Some boxes sit on clear objects (small dark/bright targets, one with an acoustic shadow); others
land on featureless seabed. Many NOAA items were developed with multibeam or are below what a 1 m
mosaic resolves, so **these are candidates for human review, not labels**. At 1 m per pixel they
can teach large-object detection (wrecks, obstructions) only; crab-pot-scale debris needs
5-10 cm data (raw XTF, which NCEI does not provide for these surveys, or partner data).

Next: team review in X-AnyLabeling/CVAT (accept / move / reject); only reviewed chips may enter
training, as a separate large-object dataset with its own test survey.
