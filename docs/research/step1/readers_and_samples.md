# NetSight Step 1 - Readers, licences and sample files

Researched 2026-11-06. VERIFIED = I opened the page/file/PyPI JSON in this session. UNVERIFIED = from search snippet or prior knowledge; open it before relying on it.
Limitation: WebFetch summarises pages through a small model, so "VERIFIED" for GitHub pages means the page was read, not that every line was checked by eye. Raw source files (xtf_io.py, xtf_ctypes.py, enumerations.py) and the JSF PDF were read directly.

---------------------------------------------------------------------------
## 1. pyxtf

- Repo: https://github.com/oysstu/pyxtf  (VERIFIED)
- Licence: MIT, "Copyright (c) 2024 Oystein Sture" (raw LICENSE file opened, VERIFIED). Safe to link.
- PyPI: https://pypi.org/project/pyxtf/ (VERIFIED via PyPI JSON)
  - Latest: 1.5.0, uploaded 2026-04-14. History: 1.4.0 2023-12-01, 1.4.1 2024-04-24, 1.4.2 2024-07-10.
  - Files: `pyxtf-1.5.0-py3-none-any.whl` (26,741 bytes) + sdist. Pure Python wheel, so it installs on any Python incl. 3.12/3.13 on Windows without compiling.
  - requires_python: not set. requires_dist: `numpy>=1.11` (no upper cap, so numpy 2.x is allowed); matplotlib only in the `plotting` extra.
  - UNVERIFIED: I did not actually run `uv pip install pyxtf` on 3.12/3.13 or test it against numpy 2. Step 1 should include that smoke test. Source uses `np.frombuffer`, ctypes, `pickle`; nothing obviously numpy-2-hostile was seen, but not tested.
- Open issues (6, VERIFIED titles only): #59 to_bytes for non-sonar ping headers; #37 infer SampleFormat on write; #25 write example failing; #14 index-file/file mismatch check; #10 naming confusion with another XTF lib; #6 XTF_HEADER(67). None about numpy 2 or Python 3.12/3.13.

### Core API (from raw source, VERIFIED)

```python
import pyxtf
(file_header, packets) = pyxtf.xtf_read('yourfile.xtf')           # README form (also accepts verbose=True per README)
sonar_packets = packets[pyxtf.XTFHeaderType.sonar]                  # list of XTFPingHeader
print(sonar_packets[0])
```
Public names (`pyxtf/__init__.py`): everything from `pyxtf.enumerations`, `pyxtf.xtf_ctypes`, plus `xtf_read`, `xtf_read_gen`, `concatenate_channel`.

Signatures:
- `xtf_read(path: str, types: List[XTFHeaderType] = None) -> Tuple[XTFFileHeader, Dict[XTFHeaderType, List[Any]]]`. Dict keyed by `XTFHeaderType(packet.HeaderType)` (or `.unknown`); values are lists in file order. Pass `types=[XTFHeaderType.sonar, XTFHeaderType.attitude]` to skip the rest (faster).
- `xtf_read_gen(path, types=None, save_index=False)` generator: yields file header first, then packets. Use this for big files (streaming).
- `concatenate_channel(pings: List[XTFPingHeader], file_header: XTFFileHeader, channel: int, weighted: bool = False) -> np.ndarray`  2D array, one row per ping. Pads stbd on right, port on left, others both sides. `weighted=True` multiplies each row by `2 ** -ping_chan_headers[channel].Weight`.

Ping access:
- `ping.ping_chan_headers` : list of `XTFPingChanHeader`, one per channel (len = `ping.NumChansToFollow`).
- `ping.data` : list of numpy arrays, one per channel (sonar type). dtype is chosen from `file_header.sonar_info[i].SampleFormat` first (2->uint32, 3->uint16, 5->float32, 8->uint8) then falls back to `BytesPerSample` (1->uint8, 2->uint16, 4->uint32, 8->uint64). Sample count = `NumSamples` if >0 else `sonar_info[i].Reserved` (old files).
- Per-channel info lives in `file_header.sonar_info[i]` (an `XTFChanInfo`), and `ChanInfo` in the raw header.
- Channel type: `XTFChannelType` subbottom=0, port=1, stbd=2, bathy=3 (`file_header.sonar_info[i].TypeOfChannel`).

### Exact field names

`XTFFileHeader` (pack=1): FileFormat, SystemType, RecordingProgramName, RecordingProgramVersion, SonarName, SonarType, NoteString, ThisFileName, NavUnits (0 meters, 3 latlon), NumberOfSonarChannels, NumberOfBathymetryChannels, NumberOfSnippetChannels, NumberOfForwardLookArrays, NumberOfEchoStrengthChannels, NumberOfInterferometryChannels, ReferencePointHeight, ProjectionType, SpheriodType (sic), NavigationLatency, OriginY, OriginX, NavOffsetY/X/Z/Yaw, MRUOffsetY/X/Z/Yaw/Pitch/Roll, ChanInfo (x6).

`XTFChanInfo`: TypeOfChannel, SubChannelNumber, CorrectionFlags (1 slant_range, 2 ground_range), UniPolar, BytesPerSample, Reserved, ChannelName, VoltScale, Frequency (float), HorizBeamAngle, TiltAngle, BeamWidth, OffsetX/Y/Z, OffsetYaw/Pitch/Roll, BeamsPerArray, SampleFormat, ReservedArea2.

`XTFPingHeader` (ping header, per sonar packet): MagicNumber, HeaderType, SubChannelNumber, NumChansToFollow, Reserved1, NumBytesThisRecord, **Year, Month, Day, Hour, Minute, Second, HSeconds, JulianDay**, EventNumber, **PingNumber**, **SoundVelocity**, OceanTide, Reserved2, ConductivityFreq, TemperatureFreq, PressureFreq, PressureTemp, Conductivity, WaterTemperature, Pressure, ComputedSoundVelocity, MagX/Y/Z, AuxVal1..6, SpeedLog, Turbidity, **ShipSpeed, ShipGyro, ShipYcoordinate, ShipXcoordinate** (doubles; Y=lat, X=lon when NavUnits=3), ShipAltitude, ShipDepth, FixTimeHour/Minute/Second/Hsecond, **SensorSpeed**, KP, **SensorYcoordinate, SensorXcoordinate** (doubles), SonarStatus, RangeToFish, BearingToFish, CableOut, **Layback**, CableTension, **SensorDepth, SensorPrimaryAltitude**, SensorAuxAltitude, **SensorPitch, SensorRoll, SensorHeading**, Heave, Yaw, AttitudeTimeTag, DOT, NavFixMilliseconds, ComputerClockHour/Minute/Second/Hsec, FishPositionDeltaX/Y, FishPositionErrorCode, OptionalOffset, CableOutHundredths, ReservedSpace2.

`XTFPingChanHeader`: ChannelNumber, DownsampleMethod (2 max, 4 rms), **SlantRange**, GroundRange, TimeDelay, TimeDuration, SecondsPerPing, ProcessingFlags (4 tvg, 8 bac_gac, 16 filter), **Frequency** (uint16, Hz), InitialGainCode, GainCode, BandWidth, ContactNumber, ContactClassification, ContactSubNumber, ContactType, **NumSamples**, MillivoltScale, ContactTimeOffTrack, ContactCloseNumber, Reserved2, FixedVSOP, **Weight** (int16, value N -> multiply by 2^-N), ReservedSpace.

Bytes per sample: `BytesPerSample` is in `XTFChanInfo` (file header), not in the ping channel header. Frequency: both `XTFChanInfo.Frequency` (float) and `XTFPingChanHeader.Frequency` (uint16).

Other packets: `XTFAttitudeData` (HeaderType 3): EpochMicroseconds, SourceEpoch, Pitch, Roll, Heave, Yaw, TimeTag, Heading, Year, Month, Day, Hour, Minute, Second, Millisecond. `XTFHeaderNavigation` (HeaderType 42 `navigation`): Year..Second, Microsecond, SourceEpoch, TimeTag, RawYcoordinate, RawXcoordinate, RawAltitude, TimeFlag.

`XTFHeaderType` ints: sonar=0, notes=1, bathy=2, attitude=3, forward=4, ... navigation=42, time=50, ... edgetech_4600=73, ... unknown=65536. `XTFManufacturerID`: edgetech=3, klein=4, etc.

### Known bugs / limitations (VERIFIED from reading xtf_io.py)
1. `xtf_read_gen` raises `NotImplementedError` if the file header reports more than 6 channels.
2. Unknown / unimplemented packet types produce a `warn()` and come back as `XTFUnknownPacket` (not an error).
3. `save_index=True` writes a `.pyxtf_idx` pickle next to the file and loads it later with `pickle.load` -> arbitrary code execution if the index is untrusted. Do not use `save_index` (or never load index files that did not come from us). Index is not checked against the file (issue #14).
4. `concatenate_channel` sorts the input `pings` list in place (mutates caller) and returns rows in REVERSE time order (`pings[::-1]`). Pass a copy; re-reverse if you want chronological order.
5. Possible bug in `concatenate_channel` padding branch: when pings differ in length and one equals the max length, `pad_div` is 0 and `out_array[i, -0:] = 0` zeroes the whole row. Prefer our own padding/stacking (it is ~15 lines) or test this case.
6. Unsupported `BytesPerSample` (not 1,2,4,8) -> uncaught KeyError. SampleFormat 0/1/4/6/7 fall back to BytesPerSample (so IBM-float/legacy data would be misread as ints).
7. Raw XTF has no GPS-quality flag; positions of 0.0 appear when nav is missing. Ship vs sensor coordinates: sonar towfish position is `Sensor*coordinate`; `Ship*` is the vessel. Which one is filled depends on the acquisition software (Klein SonarPro vs EdgeTech Discover) - must be handled in QC.
8. Reading is whole-file into memory with `xtf_read`; use `xtf_read_gen` or `types=` for large files.

Recommendation: use pyxtf for parsing, but wrap it (own `read_xtf()` returning NetSight's own dataclasses) so bugs 4-6 are contained.

---------------------------------------------------------------------------
## 2. EdgeTech JSF

### Specification
- VERIFIED (downloaded and text-extracted): **JSF Rev 1.8, Document No. 990-0000048-1000, October 2009**. https://www.ldeo.columbia.edu/res/pi/MB-System/mbweb/formatdoc/JSF_format_Rev18.pdf (180 KB). Also Rev 1.7 (Nov 2006): .../JSF_format_Rev17.pdf (UNVERIFIED beyond search snippet). Index of formats: https://www.ldeo.columbia.edu/res/pi/MB-System/mbweb/formatdoc/index.html
- Newer: "EdgeTech JSF DATA FILE Description 0004824 Rev 1.20 (March 2016)" mirror: https://awi-test.eprints-hosting.org/44080/1/EdgeTech-JSF-DATA-FILE-Description-0004824_Rev_1_20.pdf  - the mirror returned an Anubis bot-block to my fetcher, so contents UNVERIFIED (open in a browser). Geosvy/jsfmesgtype README cites REV_1.18. Official source: EdgeTech (edgetech.com support / "JSF File and Message Descriptions"); the public docs are freely downloadable but carry no open licence - cite, do not redistribute the PDF in the repo.
- The spec is little-endian. Offsets below are from Rev 1.8; Rev 1.20 adds fields but keeps these. Always check the 16-byte header `protocol version`.

### 16-byte message header (VERIFIED, Rev 1.8)
| Bytes | Type | Field |
|---|---|---|
| 0-1 | uint16 | start marker = 0x1601 (bytes 01 16 on disk) |
| 2 | uint8 | protocol version (e.g. 10) |
| 3 | uint8 | session id (ignore) |
| 4-5 | uint16 | message type (80 = sonar data) |
| 6 | uint8 | command type (2 = normal data source; ignore when reading files) |
| 7 | uint8 | subsystem: 0 sub-bottom, 20 single/low-freq side-scan, 21 high-freq side-scan, 100 raw serial, 101 parsed serial |
| 8 | uint8 | channel: side-scan 0 = port, 1 = starboard; serial = port number |
| 9 | uint8 | sequence number |
| 10-11 | uint16 | reserved |
| 12-15 | uint32 | byte count of the following message (use to skip unknown types) |
Python: `struct.Struct('<HBBHBBBBHI')` = H(marker) B(ver) B(session) H(type) B(cmd) B(subsys) B(chan) B(seq) H(res) I(size) -> 2+1+1+2+1+1+1+1+2+4 = 16 bytes (computed by hand from the table, not yet run against a real file).

### Message 80 (Sonar Data), 240-byte header then samples (VERIFIED offsets, Rev 1.8)
| Bytes | Type | Field / note |
|---|---|---|
| 0-3 | int32 | Ping time, seconds since 1970-01-01 UTC (valid from protocol v8) |
| 4-7 | uint32 | Starting depth (window offset) in samples |
| 8-11 | uint32 | Ping number |
| 16-17 | uint16 | MSBs: bits 0-3 start-freq MSB, 4-7 end-freq MSB, 8-11 samples-in-packet MSB (extends 16-bit values to 20 bits; protocol v10) |
| 28-29 | int16 | ID code (always 1) |
| 30-31 | uint16 | Validity flags: b0 lat/lon-or-XY, b1 course, b2 speed, b3 heading, b4 pressure, b5 pitch/roll, b6 altitude, b8 water temp, b9 depth, b10 annotation, b11 cable counter, b12 KP, b13 position interpolated |
| 34-35 | int16 | Data format: 0 = 1 int16 per sample (envelope); 1 = 2 int16 per sample (analytic: real, imag); (note in spec: 2 = RAW) |
| 36-37, 38-39 | int16 | antenna-to-tow-point offset aft / starboard, cm |
| 44-47 | float32 | KP (km of pipe) |
| 80-83 | int32 | X (mm or dm) or Longitude in 1/10000 arc-minutes |
| 84-87 | int32 | Y (mm or dm) or Latitude in 1/10000 arc-minutes |
| 88-89 | int16 | Coordinate units: 1 = X,Y mm; 2 = lon/lat in arc-minutes x 1e-4; 3 = X,Y dm |
| 90-113 | uint8[24] | Annotation string |
| 114-115 | uint16 | Number of samples in this packet (+ MSB from bytes 16-17) |
| 116-119 | uint32 | **Sampling interval in nanoseconds** |
| 120-121 | uint16 | ADC gain factor |
| 122-123 | int16 | User transmit level (0-100 %) |
| 126-127 | uint16 | Tx pulse start frequency, units of 10 Hz (daHz) |
| 128-129 | uint16 | Tx pulse end frequency, daHz |
| 130-131 | uint16 | Sweep length, ms |
| 132-135 | int32 | Pressure, milli-PSI |
| 136-139 | int32 | Depth, mm |
| 140-141 | uint16 | Sample frequency Hz mod 65536 (half rate for RAW) |
| 144-147 | int32 | **Altitude in mm** (0 = not filled) |
| 156-167 | int16 x6 | Year, day, hour, minute, second, time basis (spec says do not use; use bytes 0-3 + 200-203) |
| 168-169 | int16 | **Weighting factor N**; sample_value * 2^(-N) restores the true value (signed!) |
| 170-171 | int16 | Number of pulses in water |
| 172-173 | uint16 | **Compass heading**, 1/100 degree |
| 174-175 | int16 | **Pitch**, x 180/32768 deg, + = bow up |
| 176-177 | int16 | **Roll**, x 180/32768 deg, + = port up |
| 178-179 | int16 | Towfish electronics temperature, 1/10 C |
| 182-183 | int16 | Trigger source (0 internal, 1 external, 2 coupled) |
| 184-185 | uint16 | Mark number |
| 186-199 | int16 | NMEA fix time hour, minute, second, course, speed, day, year |
| 200-203 | uint32 | Milliseconds today (combine with year/day, or use mod 1000 with bytes 0-3) |
| 204-205 | uint16 | Max absolute ADC value |
| 210-215 | int8[6] | Sonar software version (ASCII) |
| 216-239 | misc | spherical correction factor, packet number, ADC decimation, water temp 1/10 C, layback (m), cable out (dm). The text-extraction of this block was ambiguous - UNVERIFIED exact offsets; take them from the PDF table or pyjsf's TraceHeader before use. |

Samples: start at byte 240 of the message; `n_samples * (1 or 2)` int16 values; byte count must equal `size - 240`. Scaled value = int16 * 2^(-N). Use `samples_per_packet` and "very large sample sizes need multiple packets" (packet number field).
Slant range per sample = `(start_depth_samples + i) * sample_interval_ns * 1e-9 * c / 2` (c = sound speed, use 1500 m/s unless a measured value is available; JSF has no sound-speed field in msg 80).
Side-scan convention: subsystem 20/21, channel 0 port / 1 stbd.

### Other messages (VERIFIED, Rev 1.8)
- 82: old side-scan data message, "no longer used".
- 2002 NMEA string: 0-3 int32 time s (1970), 4-7 int32 ms in second, 8 uint8 source (1 sonar, 2 Discover, 3 ETSI), 9-11 reserved, 12-end NMEA text without CR/LF.
- 2020 Pitch/Roll: 0-3 time s, 4-7 ms, then accel x/y/z, gyro x/y/z, **pitch** (x180/32768 deg, bow up +), **roll** (x180/32768, port up +), temperature (0.1 C), device info, **heave (mm)**, **heading (0.01 deg)**, valid flags (bit 6 pitch, 7 roll, 8 heave, 9 heading). Exact offsets of fields beyond ms (8-11) need the PDF table (text extraction was column-scrambled; UNVERIFIED offsets).
- 2060 pressure, 2080 DVL, 2090 situation message, 182 system information: exist, not needed in v1.
- Navigation: lat/lon in msg 80 is "last fix, not time-interpolated"; spec explicitly recommends using NMEA (2002) / attitude (2020) messages for accurate positioning. So a good JSF reader must parse 80 + 2002 (GGA/RMC/HDT via a small NMEA parser, `pynmea2` is MIT, UNVERIFIED) + 2020.

### Existing Python / other JSF readers
| Reader | Licence | Notes |
|---|---|---|
| **pyjsf** https://pypi.org/project/pyjsf/ , https://codeberg.org/actingthegroat/pyjsf | MIT (PyPI `license` field = "MIT", wheel contains LICENSE; VERIFIED via PyPI JSON; LICENSE text itself not opened) | v0.0.1, 2025-12-09, py3-none-any 6.9 KB, deps: numpy, py>=3.8. Messages: sonar_data_message (80), pressure_sensor_reading, nmea_string, pitch_roll_data. Subsystems lf_sss/hf_sss/vhf_sss. Targets "Rev. P". Brand new, one author, README shows two inconsistent function names (`read_jsf` vs `jsf_read`). Good as a cross-check, too immature to depend on. |
| **xtfjsf** | PyPI JSON 404; no such package found | UNVERIFIED / likely does not exist under that name. |
| **sidescantools** https://github.com/sonoware/sidescantools | **GPL-3.0** (VERIFIED) | reads .jsf and .xtf; do NOT link or copy. |
| **PINGVerter** https://pypi.org/project/pingverter/ | MIT (classifier, VERIFIED), v2.1.7 | Converts Humminbird/Lowrance/Garmin/Cerulean/EdgeTech JSF to PINGMapper format; deps numpy, pandas, pyproj, joblib, pillow. Not a general JSF API. |
| **Geosvy/jsfmesgtype** https://github.com/Geosvy/jsfmesgtype | Public domain (README, no LICENSE file; USGS WHCMSC) | Small C utility + `jsf2.h` header following spec Rev 1.18 - useful as a second reference for struct layout. |
| **MB-System** (mbsys_jstar, JSF format 132/133) | GPL-3 | reference only; call as a separate process if ever needed. |

### Recommendation (JSF)
Write a minimal in-house JSF reader (~150 lines, `struct` + `numpy.frombuffer`) from the spec: iterate headers, keep message types 80, 2002, 2020, skip everything else via the byte count. Reasons: the format is simple and public, the MIT pyjsf is v0.0.1, nothing else is both maintained and permissive, and we need QC-aware behaviour (validity flags, weighting, multi-packet pings, coordinate units, time from bytes 0-3 + 200-203). Use pyjsf output and the Rev 1.20 PDF as cross-checks in tests. Build a golden test from one real JSF file once we get one (see section 4: no public JSF found).

---------------------------------------------------------------------------
## 3. Licences

### Sonar readers / projects
| Project | Licence | Status |
|---|---|---|
| pyxtf | MIT | VERIFIED (LICENSE file) |
| pyjsf | MIT | VERIFIED (PyPI JSON) |
| xtfjsf | n/a | PyPI 404; not found |
| pygsf (pktrigg) https://github.com/pktrigg/pygsf | Apache-2.0 (sidebar) | VERIFIED page; LICENSE text not opened. NB: PyPI package named `pygsf` is a DIFFERENT unrelated project (QIN2DIM, GPL-3.0-or-later, VERIFIED) - never `pip install pygsf` for this. |
| gsfpy (UKHO) https://github.com/UKHO/gsfpy | MIT wrapper but bundles LGPL-2.1 shared lib (search snippet) | UNVERIFIED |
| "gsfu" | not found | No project of that name located |
| kmall (valschmidt) https://github.com/valschmidt/kmall | BSD-2-Clause | VERIFIED page. Pure-Python KMALL reader (multibeam; not needed for Step 1). |
| "pykmall" | not found as separate project | use valschmidt/kmall |
| oculus-python (PyPI, DTU GitLab https://gitlab.gbar.dtu.dk/fletho/oculus-python) | Apache (classifier), v0.0.2a1 | VERIFIED PyPI JSON; alpha |
| liboculus (apl-ocean-engineering) | BSD-3, but bundles Blueprint `Oculus.h` under GPLv3 | UNVERIFIED (search snippet) |
| PINGMapper | MIT (license_expression), v5.5.7 | VERIFIED PyPI JSON. Heavy deps (tensorflow in extra, opencv-python, GUI). Use as reference / data source, not a dependency. |
| PINGVerter | MIT | VERIFIED |
| MB-System | GPL-3 (README: "GNU GPL version 3", COPYING.md) | VERIFIED page; call only as subprocess |
| sidescantools | GPL-3.0 | VERIFIED |

### General libraries (all pulled from PyPI JSON where marked VERIFIED)
| Library | Licence | Status / flags |
|---|---|---|
| rasterio 1.5.2 | BSD-3-Clause; requires Python >=3.12; classifiers 3.12-3.14 | VERIFIED. Wheels bundle GDAL (its own MIT/X-style licence) - win_amd64 wheels expected but not confirmed in file list. |
| GDAL (osgeo) | MIT/X | UNVERIFIED (well known). `pip install gdal` on Windows is painful; prefer rasterio. |
| pyproj | MIT (PROJ is MIT) | UNVERIFIED |
| shapely | BSD-3-Clause (GEOS is LGPL-2.1, dynamically linked in wheels) | UNVERIFIED |
| numpy | BSD-3-Clause | UNVERIFIED |
| scipy | BSD-3-Clause | UNVERIFIED |
| scikit-learn | BSD-3-Clause | UNVERIFIED |
| faiss-cpu 1.15.1 | MIT; py>=3.10 | VERIFIED (license_expression MIT). Windows cp312/cp313 wheels seen for 1.11.0.post1; for 1.15.1 file list not confirmed. |
| opencv-python 5.0.0.93 (as shown by PyPI JSON) | Apache-2.0 | VERIFIED; requires numpy>=2 on py>=3.9. Bundles FFmpeg (LGPL) in wheels - fine for dynamic use, note in notices. Prefer `opencv-python-headless` for servers. |
| **PyMuPDF 2.1** | **"Dual Licensed - GNU AFFERO GPL 3.0 or Artifex Commercial License"** | VERIFIED - **FLAG: AGPL. Do not use in commercial code without buying a licence.** |
| pypdf | BSD-3-Clause | UNVERIFIED (well known) |
| pdfplumber | MIT | UNVERIFIED (builds on pdfminer.six, MIT) |
| FastAPI | MIT | UNVERIFIED (well known) |

Recommendation for PDF: pypdf (BSD) for text extraction/merge, or pdfplumber (MIT) for tables. Avoid PyMuPDF.

---------------------------------------------------------------------------
## 4. Sample files for automated tests

Key finding: I found NO small, openly licensed, directly downloadable XTF or JSF sample. The candidates below are either huge, NC-licensed, or unconfirmed. Plan: (a) generate synthetic XTF in CI with pyxtf's own writer (examples/write_xtf.py exists, VERIFIED listing), (b) ask for / record one tiny real XTF + JSF from the team's own survey data, (c) use the USGS GeoTIFF for mosaic tests.

| Item | URL | Size | Licence | Sensor | Status |
|---|---|---|---|---|---|
| **USGS H11322 1 m side-scan mosaic GeoTIFF (zip)**, Rhode Island Sound, UTM 19 NAD83 | https://pubs.usgs.gov/of/2008/1181/data/sidescan/utm/h11322_1m_sss_utm/h11322_1m_sss_utm.zip | **35,152,853 bytes (35 MB)** via HTTP HEAD, content-type application/zip | Public domain (USGS metadata: "freely redistributable with proper metadata and source attribution"; credit USGS and NOAA) | NOAA Ship RUDE, 2004 survey H11322 (sensor not read) | VERIFIED. Best GeoTIFF test input. Metadata page: .../h11322_1m_sss_utm.html |
| USGS Grand Bay (AL/MS) 2015-315-FA XTF | https://doi.org/10.5066/P9374DKQ -> https://coastal.er.usgs.gov/data-release/doi-P9374DKQ/ | `2015-315-FA_xtf.zip` **9.84 GB** (too big; whole set); `2015-315-FA_SSSMosaic.zip` 578.4 MB (GeoTIFF mosaic) | USGS public domain (data release; use constraints not read from page) | Klein 3900 side-scan (SonarPro XTF) | VERIFIED sizes from release page. Individual XTF lines inside the zip are likely ~tens of MB; could download once with a range request/partial extraction (zip central directory) and keep one line out of CI. |
| NOAA Hudson River raw XTF | ftp://ftp.coast.noaa.gov/pub/benthic/Side_Scan_Sonar_Backscatter_Data/NY_HudsonRiver_sss-xtf.zip | unknown | NOAA public domain (UNVERIFIED) | unknown | UNVERIFIED; host did not resolve from this machine (FTP). |
| NOAA NOS hydrographic survey XTF resources on catalog.data.gov (e.g. H11638, H11982, H11545) | https://catalog.data.gov/dataset/h11638-nos-hydrographic-survey-mississippi-sound-mississippi-2007-03-071 | unknown | NOAA public domain | various | UNVERIFIED search hits, sizes unknown. |
| Marine-Geo/IEDA dataset 6159 (NBP0505 raw towed side-scan, Chilean fjords, XTF) | https://www.marine-geo.org/tools/datasets/6159 , DOI 10.1594/IEDA/306159 | The "Data Files" section was empty on the page I fetched; only PDFs listed. No XTF URL or size found. | **CC BY-NC-SA 3.0 US (non-commercial, share-alike) - NOT suitable for a commercial repo or CI fixtures** | EdgeTech towed side-scan (XTF) | VERIFIED page; data link not found. Avoid. |
| pyxtf test data | https://github.com/oysstu/pyxtf | none found; examples dir has `plot_sonar_bathy.py`, `sonar_example.ipynb`, `write_xtf.py`, `xtf_to_image.py`, `xtf_to_tiff.py` (list may be incomplete) | MIT code | - | VERIFIED listing: no bundled sample file seen; `tests/` path returned 404. |
| PINGMapper example data (Humminbird .DAT/.SON/.IDX, Lowrance .sl2/.sl3) | https://github.com/CameronBodine/PINGMapper ; docs https://cameronbodine.github.io/PINGMapper/ ; handbook says example datasets are provided | not found | MIT (code); data licence unknown | Humminbird / Lowrance | UNVERIFIED location. Check the repo `procData`/docs "Tutorial" pages and Zenodo (10.5281/zenodo.6604785, 34.9 MB software zip, may contain samples). |
| JSF samples | - | - | - | - | NONE found. SonarWiz/Chesapeake demo data and EdgeTech sample downloads exist commercially (UNVERIFIED); simplest route is a few seconds of our own recording, or a synthetic JSF written by our own test helper from the spec. |
| DEMO_XTF | not located | - | - | - | UNVERIFIED / not found. |

---------------------------------------------------------------------------
## 5. Recommended minimal, licence-clean reader stack (Step 1)

Runtime dependencies (all permissive):
- `numpy` (BSD-3) - pin range `>=2.0,<3` (opencv 5 needs numpy>=2; pyxtf allows it - smoke test on 3.12 and 3.13).
- `pyxtf==1.5.0` (MIT, pure Python) for XTF, wrapped by our own reader; do not use `save_index`; do not rely on `concatenate_channel` padding.
- In-house JSF reader (`struct` + numpy, no extra dependency), written from Rev 1.8 / 1.20; optional `pynmea2` (MIT, UNVERIFIED) or a 30-line NMEA GGA/RMC/HDT parser.
- `rasterio>=1.5,<1.6` (BSD-3; Python >=3.12 only, matches our 3.12/3.13 target; wheels bundle GDAL) for GeoTIFF mosaics; `pyproj` (MIT) for CRS transforms; `shapely` (BSD-3) only if footprints are needed.
- Reading PDFs (if needed): `pypdf` (BSD-3). NOT PyMuPDF.
- FastAPI (MIT), scikit-learn/scipy (BSD) and faiss-cpu 1.15.1 (MIT) are fine when later steps need them; opencv via `opencv-python-headless` (Apache-2.0).

Dev/test only: `pytest`; `pyjsf==0.0.1` (MIT) purely as a cross-check oracle for the JSF reader (dev group, not shipped).

Never link: sidescantools (GPL-3), MB-System (GPL-3; subprocess only), PyMuPDF (AGPL), the PyPI `pygsf` (GPL-3 and unrelated), CC BY-NC-SA sample data (IEDA 6159) in the repo.

Pin policy: `uv add "pyxtf==1.5.0" "numpy>=2,<3" "rasterio>=1.5,<1.6" "pyproj"` then commit `uv.lock`. Versions above are what PyPI showed on 2026-11-06; run `uv lock` and one install on 3.12 and 3.13 on Windows to confirm wheel availability (UNVERIFIED for rasterio/faiss/opencv win_amd64 wheels).

## Open items for Step 1
1. Smoke-test `uv pip install pyxtf rasterio` on 3.12 and 3.13 (Windows).
2. Open the Rev 1.20 PDF in a browser and settle msg-80 bytes 216-239 and msg-2020 offsets (>= byte 8).
3. Obtain one tiny real XTF (e.g. extract one line from USGS 2015-315-FA zip via HTTP range) and one JSF from the team; confirm licence (USGS = public domain).
4. Check the USGS GeoTIFF's pixel type / CRS with rasterio before using it in tests.
