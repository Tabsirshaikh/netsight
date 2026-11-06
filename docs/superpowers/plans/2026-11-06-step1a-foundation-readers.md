# Step 1A — Foundation, Readers, QC and Normalisation Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** A tested Python package that reads side-scan sonar (XTF, JSF) and mosaics (GeoTIFF) into one sensor-neutral record, applies quality control and physics normalisation (ground range, gain, geometry channels, quality mask), keeps navigation provenance honest, and exposes it through a CLI and a licence register.

**Architecture:** `src/netsight` package. Readers (L0 adapters in the plan) map each file format onto `SonarRecord`/`Ping` dataclasses with sample arrays ordered near→far. Pure-function modules do geometry (bottom tracking, slant→ground range, grazing angle), radiometry (across-track equalisation, log), QC (dropout repair, quality mask Q) and navigation provenance. `normalise_record` composes them into a `NormalisedSwath` that later steps (detection, calibration, Pd) consume. Tests use synthetic XTF/JSF files generated on the fly, so CI needs no external data.

**Tech Stack:** Python ≥3.12, uv, numpy 2, pyxtf 1.5.0 (MIT), rasterio 1.5 (BSD-3), pyproj, PyYAML, pytest, ruff, GitHub Actions.

**Design source:** `docs/plan/final.md` §7.1 (layers L0–L1), §8.1 (ingest/QC/normalisation table), §10 (adopted features), §14 (stack and licences), §15 (WP0, WP1). Reader facts: `docs/research/step1/readers_and_samples.md`. Dataset facts: `docs/research/step1/datasets_detail.md`.

## Global Constraints

- Python `>=3.12`; must pass on Windows and Linux; managed with `uv`; dependencies pinned in `pyproject.toml` and `uv.lock`.
- Licences: no GPL/AGPL code may be imported or vendored. MB-System only ever as a separate process (not in this step). Never use PyMuPDF. `pyxtf==1.5.0` (MIT) is allowed.
- pyxtf: never pass `save_index=True`; refuse to read a file if a `.pyxtf_idx` file sits next to it (pyxtf would `pickle.load` it — arbitrary code execution); never use `pyxtf.concatenate_channel` (it mutates input, reverses order and can zero rows).
- Channel arrays are ordered **near → far**: index 0 is the sample nearest the sonar. JSF `start_depth` samples are prepended as NaN so index 0 is always slant range 0.
- Missing scalar values are `NaN`, never `0`. A missing position is `NaN` with `NavSource.MISSING` ("position withdrawn"); readers never substitute fixed or default positions.
- Data never goes in git. Data directory = env `NETSIGHT_DATA_DIR`, default `<repo parent>/netsight-data` (outside OneDrive).
- Unit tests use only synthetic data generated in `tests/helpers`; no network access in tests.
- Every commit message ends with the `Co-Authored-By:` trailer your environment specifies.
- Run `uv run pytest` and `uv run ruff check .` before every commit; both must pass.

## File Structure

| Path | Responsibility |
|---|---|
| `pyproject.toml`, `uv.lock` | Package metadata, pinned deps, pytest/ruff config, `netsight` console script |
| `.github/workflows/ci.yml` | Lint + tests on ubuntu/windows × py3.12/3.13 |
| `docs/data/README.md` | Data-directory rules |
| `src/netsight/__init__.py` | Version |
| `src/netsight/config.py` | Data directory resolution |
| `src/netsight/core/records.py` | `SensorType`, `NavSource`, `CoordKind`, `SensorDescriptor`, `Ping`, `Provenance`, `SonarRecord` |
| `src/netsight/core/hashing.py` | `file_sha256` |
| `src/netsight/navigation/provenance.py` | `PositionFix`, `offset_behind`, `select_position` |
| `src/netsight/io/xtf.py` | `read_xtf` (wraps pyxtf safely) |
| `src/netsight/io/jsf.py` | `read_jsf` (in-house reader from EdgeTech JSF Rev 1.8) |
| `src/netsight/io/mosaic.py` | `Mosaic`, `read_mosaic` |
| `src/netsight/io/__init__.py` | `open_survey` format dispatch |
| `src/netsight/geometry/slant.py` | `bottom_track`, `fuse_altitude`, `ground_range_grid`, `to_ground_range`, `grazing_angle_deg` |
| `src/netsight/radiometry/gain.py` | `across_track_equalise`, `to_log` |
| `src/netsight/qc/dropout.py` | `DropoutResult`, `repair_dropouts` |
| `src/netsight/qc/quality.py` | `QualityThresholds`, `SEVERITY`, `QualityMask`, `compute_quality` |
| `src/netsight/normalise/swath.py` | `TIERS_M`, `choose_ground_resolution`, `NormalisedSwath`, `normalise_record` |
| `src/netsight/governance/licences.py` | Register validation and dependency licence scan |
| `src/netsight/cli.py` | `netsight inspect|normalise|licences` |
| `licences/datasets.yaml` | Dataset licence register |
| `docs/policy/impartiality.md`, `docs/policy/data_rights_clause.md` | Governance texts (WP0) |
| `tests/helpers/synth_xtf.py`, `tests/helpers/synth_jsf.py`, `tests/helpers/swaths.py` | Synthetic data generators |
| `tests/test_*.py` | One test module per source module |

---

### Task 1: Project scaffold, config and CI

**Files:**
- Create: `pyproject.toml`, `.github/workflows/ci.yml`, `docs/data/README.md`, `src/netsight/__init__.py`, `src/netsight/config.py`, `tests/test_smoke.py`, `tests/test_config.py`, `tests/helpers/__init__.py`
- Modify: `README.md`

**Interfaces:**
- Produces: `netsight.__version__: str`; `netsight.config.repo_root() -> Path`; `netsight.config.data_dir() -> Path`

- [ ] **Step 1: Create `pyproject.toml`**

```toml
[project]
name = "netsight"
version = "0.1.0"
description = "Independent, sensor-neutral assurance for sonar survey contacts"
readme = "README.md"
requires-python = ">=3.12"
dependencies = [
    "numpy>=2,<3",
    "pyxtf==1.5.0",
    "rasterio>=1.5,<1.6",
    "pyproj>=3.6",
    "pyyaml>=6.0",
]

[project.scripts]
netsight = "netsight.cli:main"

[dependency-groups]
dev = ["pytest>=8", "ruff>=0.6"]

[build-system]
requires = ["hatchling>=1.25"]
build-backend = "hatchling.build"

[tool.hatch.build.targets.wheel]
packages = ["src/netsight"]

[tool.pytest.ini_options]
testpaths = ["tests"]
pythonpath = ["tests"]
addopts = "-q"

[tool.ruff]
line-length = 100
target-version = "py312"

[tool.ruff.lint]
select = ["E", "F", "I", "B", "UP"]
```

- [ ] **Step 2: Write the failing tests**

`tests/helpers/__init__.py` (empty file).

`tests/test_smoke.py`:

```python
import numpy as np


def test_package_imports_and_has_version():
    import netsight

    assert netsight.__version__ == "0.1.0"


def test_core_dependencies_import():
    import pyxtf  # noqa: F401
    import rasterio  # noqa: F401

    assert int(np.__version__.split(".")[0]) >= 2
```

`tests/test_config.py`:

```python
from pathlib import Path

from netsight import config


def test_data_dir_defaults_to_sibling_of_repo(monkeypatch):
    monkeypatch.delenv("NETSIGHT_DATA_DIR", raising=False)
    assert config.data_dir() == config.repo_root().parent / "netsight-data"


def test_data_dir_honours_env(monkeypatch, tmp_path):
    monkeypatch.setenv("NETSIGHT_DATA_DIR", str(tmp_path))
    assert config.data_dir() == Path(tmp_path)


def test_repo_root_contains_pyproject():
    assert (config.repo_root() / "pyproject.toml").is_file()
```

- [ ] **Step 3: Run to confirm failure**

Run: `uv sync --all-groups` then `uv run pytest tests/test_smoke.py tests/test_config.py`
Expected: FAIL with `ModuleNotFoundError: No module named 'netsight'`.

- [ ] **Step 4: Implement**

`src/netsight/__init__.py`:

```python
"""NetSight: independent, sensor-neutral assurance for sonar survey contacts."""

__version__ = "0.1.0"
```

`src/netsight/config.py`:

```python
"""Runtime configuration."""

from __future__ import annotations

import os
from pathlib import Path


def repo_root() -> Path:
    """Repository root (the directory holding pyproject.toml)."""
    return Path(__file__).resolve().parents[2]


def data_dir() -> Path:
    """Where raw and processed data live. Never inside the repository or OneDrive."""
    env = os.environ.get("NETSIGHT_DATA_DIR")
    return Path(env) if env else repo_root().parent / "netsight-data"
```

- [ ] **Step 5: Add CI, data README and dev instructions**

`.github/workflows/ci.yml`:

```yaml
name: ci
on:
  push:
  pull_request:
jobs:
  test:
    strategy:
      fail-fast: false
      matrix:
        os: [ubuntu-latest, windows-latest]
        python: ["3.12", "3.13"]
    runs-on: ${{ matrix.os }}
    steps:
      - uses: actions/checkout@v4
      - uses: astral-sh/setup-uv@v6
        with:
          python-version: ${{ matrix.python }}
      - run: uv sync --all-groups
      - run: uv run ruff check .
      - run: uv run pytest
```

`docs/data/README.md`:

```markdown
# Data rules

- Data never goes in git. `.gitignore` blocks common sonar and raster formats.
- Location: environment variable `NETSIGHT_DATA_DIR`, default `<repo parent>/netsight-data`.
  Keep it outside OneDrive or any synced folder.
- Layout: `raw/<source>/...` for downloads exactly as published, `processed/<source>/...` for our outputs.
- Every dataset must have an entry in `licences/datasets.yaml` before any file is used.
  Only `tier: commercial` entries may feed commercial model weights; `research_only` data stays
  in benchmarks and is never mixed into training sets.
- Unit tests never read from the data directory; they generate synthetic data.
```

Append to `README.md`:

```markdown

## Development

    uv sync --all-groups
    uv run pytest
    uv run ruff check .
    uv run netsight --help

Data lives outside the repo; see [docs/data/README.md](docs/data/README.md).
```

- [ ] **Step 6: Run tests and lint**

Run: `uv run pytest` then `uv run ruff check .`
Expected: 5 passed; ruff reports no errors.

- [ ] **Step 7: Commit**

```bash
git add pyproject.toml uv.lock .github docs/data README.md src tests
git commit -m "build: scaffold netsight package, config and CI"
```

---

### Task 2: Core records and hashing

**Files:**
- Create: `src/netsight/core/__init__.py` (empty), `src/netsight/core/records.py`, `src/netsight/core/hashing.py`, `tests/test_records.py`

**Interfaces:**
- Produces: enums `SensorType`, `NavSource` (`SENSOR`, `SHIP_LAYBACK`, `SHIP`, `MISSING`), `CoordKind` (`LATLON`, `PROJECTED`, `NONE`); dataclasses `SensorDescriptor(sensor_type, source_format, model=None, frequency_khz=None, n_channels=2, along_track_beamwidth_deg=None, across_track_beamwidth_deg=None)` with `.to_dict()`; `Ping(index, ping_number, time, x, y, coord_kind, nav_source, heading_deg, pitch_deg, roll_deg, altitude_m, slant_range_m, port, stbd, sound_velocity_ms=1500.0)` with `.n_samples`, `.sample_spacing_m`; `Provenance(source_path, sha256, reader, reader_version, notes=[])` with `.to_dict()`; `SonarRecord(sensor, pings, provenance)` with `.n_pings`, `.channel_matrix(side)`, `.nav_source_counts()`; `file_sha256(path) -> str`.

- [ ] **Step 1: Write the failing tests** — `tests/test_records.py`:

```python
import numpy as np
import pytest

from netsight.core.hashing import file_sha256
from netsight.core.records import (
    CoordKind,
    NavSource,
    Ping,
    Provenance,
    SensorDescriptor,
    SensorType,
    SonarRecord,
)


def make_ping(i=0, n=100, slant=50.0, source=NavSource.SENSOR):
    return Ping(
        index=i,
        ping_number=100 + i,
        time=np.datetime64("2026-11-06T12:00:00") + np.timedelta64(i, "s"),
        x=72.8,
        y=18.9,
        coord_kind=CoordKind.LATLON,
        nav_source=source,
        heading_deg=90.0,
        pitch_deg=0.0,
        roll_deg=0.0,
        altitude_m=5.0,
        slant_range_m=slant,
        port=np.arange(n),
        stbd=np.arange(n) + 1,
    )


def make_record(pings):
    return SonarRecord(
        sensor=SensorDescriptor(SensorType.SIDESCAN, "xtf", model="SYNTH", frequency_khz=455.0),
        pings=pings,
        provenance=Provenance("x.xtf", "abc", "test", "0"),
    )


def test_ping_converts_arrays_to_float32_and_computes_spacing():
    p = make_ping(n=500, slant=50.0)
    assert p.port.dtype == np.float32 and p.stbd.dtype == np.float32
    assert p.n_samples == 500
    assert p.sample_spacing_m == pytest.approx(0.1)


def test_ping_rejects_mismatched_or_empty_channels():
    with pytest.raises(ValueError):
        Ping(**{**make_ping().__dict__, "stbd": np.arange(5)})
    with pytest.raises(ValueError):
        Ping(**{**make_ping().__dict__, "port": np.array([]), "stbd": np.array([])})


def test_ping_rejects_non_positive_slant_range():
    with pytest.raises(ValueError):
        Ping(**{**make_ping().__dict__, "slant_range_m": 0.0})


def test_channel_matrix_stacks_in_ping_order():
    rec = make_record([make_ping(0), make_ping(1)])
    m = rec.channel_matrix("stbd")
    assert m.shape == (2, 100)
    assert m[0, 0] == 1.0
    with pytest.raises(ValueError):
        rec.channel_matrix("bow")


def test_channel_matrix_rejects_uneven_sample_counts():
    rec = make_record([make_ping(0, n=100), make_ping(1, n=120)])
    with pytest.raises(ValueError):
        rec.channel_matrix("port")


def test_nav_source_counts_and_descriptor_dict():
    rec = make_record([make_ping(0), make_ping(1, source=NavSource.MISSING)])
    assert rec.nav_source_counts() == {"sensor": 1, "missing": 1}
    assert rec.n_pings == 2
    d = rec.sensor.to_dict()
    assert d["sensor_type"] == "sidescan" and d["frequency_khz"] == 455.0


def test_file_sha256(tmp_path):
    f = tmp_path / "a.bin"
    f.write_bytes(b"netsight")
    assert file_sha256(f) == "210815b8e7b5cca0487bb1bd85ad8a96351e89483362785697e504008302e629"
```

- [ ] **Step 2: Run to confirm failure**

Run: `uv run pytest tests/test_records.py`
Expected: FAIL with `ModuleNotFoundError: No module named 'netsight.core'`.

- [ ] **Step 3: Implement**

`src/netsight/core/records.py`:

```python
"""Sensor-neutral records shared by every NetSight reader.

Conventions:
- Channel arrays run near -> far: index 0 is the sample nearest the sonar.
- Missing scalar values are NaN, never 0.
- Every position carries its source; a missing position is NaN with NavSource.MISSING.
"""

from __future__ import annotations

import math
from collections import Counter
from dataclasses import asdict, dataclass, field
from enum import StrEnum

import numpy as np


class SensorType(StrEnum):
    SIDESCAN = "sidescan"
    SAS = "sas"
    MBES_BACKSCATTER = "mbes_backscatter"
    FORWARD_LOOKING = "forward_looking"
    MOSAIC = "mosaic"


class NavSource(StrEnum):
    SENSOR = "sensor"  # sensor/towfish position recorded by the acquisition system
    SHIP_LAYBACK = "ship_layback"  # vessel position moved back along heading by recorded layback
    SHIP = "ship"  # vessel position only; towfish offset unknown
    MISSING = "missing"  # no usable position: position withdrawn


class CoordKind(StrEnum):
    LATLON = "latlon"  # x = longitude, y = latitude, degrees
    PROJECTED = "projected"  # x = easting, y = northing, metres
    NONE = "none"


@dataclass(frozen=True)
class SensorDescriptor:
    sensor_type: SensorType
    source_format: str
    model: str | None = None
    frequency_khz: float | None = None
    n_channels: int = 2
    along_track_beamwidth_deg: float | None = None
    across_track_beamwidth_deg: float | None = None

    def to_dict(self) -> dict:
        d = asdict(self)
        d["sensor_type"] = str(self.sensor_type)
        return d


@dataclass
class Ping:
    index: int
    ping_number: int
    time: np.datetime64
    x: float
    y: float
    coord_kind: CoordKind
    nav_source: NavSource
    heading_deg: float
    pitch_deg: float
    roll_deg: float
    altitude_m: float
    slant_range_m: float
    port: np.ndarray
    stbd: np.ndarray
    sound_velocity_ms: float = 1500.0

    def __post_init__(self) -> None:
        self.port = np.asarray(self.port, dtype=np.float32).ravel()
        self.stbd = np.asarray(self.stbd, dtype=np.float32).ravel()
        if self.port.size == 0 or self.port.size != self.stbd.size:
            raise ValueError(
                f"port and starboard need equal, non-zero sample counts "
                f"(got {self.port.size} and {self.stbd.size})"
            )
        if not (math.isfinite(self.slant_range_m) and self.slant_range_m > 0):
            raise ValueError(f"slant_range_m must be positive, got {self.slant_range_m}")

    @property
    def n_samples(self) -> int:
        return int(self.port.size)

    @property
    def sample_spacing_m(self) -> float:
        return self.slant_range_m / self.n_samples


@dataclass
class Provenance:
    source_path: str
    sha256: str
    reader: str
    reader_version: str
    notes: list[str] = field(default_factory=list)

    def to_dict(self) -> dict:
        return asdict(self)


@dataclass
class SonarRecord:
    sensor: SensorDescriptor
    pings: list[Ping]
    provenance: Provenance

    @property
    def n_pings(self) -> int:
        return len(self.pings)

    def channel_matrix(self, side: str) -> np.ndarray:
        """Stack one side's samples as (n_pings, n_samples), in ping order."""
        if side not in ("port", "stbd"):
            raise ValueError(f"side must be 'port' or 'stbd', got {side!r}")
        if not self.pings:
            return np.empty((0, 0), dtype=np.float32)
        counts = {p.n_samples for p in self.pings}
        if len(counts) != 1:
            raise ValueError(f"pings have different sample counts {sorted(counts)}; resample first")
        return np.stack([getattr(p, side) for p in self.pings])

    def nav_source_counts(self) -> dict[str, int]:
        return dict(Counter(str(p.nav_source) for p in self.pings))
```

`src/netsight/core/hashing.py`:

```python
"""File hashing for provenance."""

from __future__ import annotations

import hashlib
from pathlib import Path


def file_sha256(path: str | Path, chunk_size: int = 1 << 20) -> str:
    digest = hashlib.sha256()
    with open(path, "rb") as f:
        while block := f.read(chunk_size):
            digest.update(block)
    return digest.hexdigest()
```

- [ ] **Step 4: Run tests**

Run: `uv run pytest tests/test_records.py` → all pass. Then `uv run pytest` and `uv run ruff check .`.

- [ ] **Step 5: Commit**

```bash
git add src/netsight/core tests/test_records.py
git commit -m "feat(core): add sensor-neutral sonar records and file hashing"
```

---

### Task 3: Navigation provenance

**Files:**
- Create: `src/netsight/navigation/__init__.py` (empty), `src/netsight/navigation/provenance.py`, `tests/test_navigation.py`

**Interfaces:**
- Consumes: `NavSource`, `CoordKind` from Task 2.
- Produces: `PositionFix(x: float, y: float, source: NavSource, notes: tuple[str, ...])`; `offset_behind(x, y, distance_m, heading_deg, kind) -> tuple[float, float]`; `select_position(*, sensor_x, sensor_y, ship_x, ship_y, layback_m, heading_deg, coord_kind) -> PositionFix`; constants `NOTE_LAYBACK`, `NOTE_SHIP_ONLY`, `NOTE_WITHDRAWN`.

- [ ] **Step 1: Write the failing tests** — `tests/test_navigation.py`:

```python
import math

import pytest

from netsight.core.records import CoordKind, NavSource
from netsight.navigation.provenance import (
    NOTE_LAYBACK,
    NOTE_SHIP_ONLY,
    NOTE_WITHDRAWN,
    offset_behind,
    select_position,
)

BASE = dict(sensor_x=0.0, sensor_y=0.0, ship_x=0.0, ship_y=0.0, layback_m=0.0, heading_deg=0.0)


def test_sensor_position_preferred():
    fix = select_position(**{**BASE, "sensor_x": 72.8, "sensor_y": 18.9, "ship_x": 72.9, "ship_y": 19.0},
                          coord_kind=CoordKind.LATLON)
    assert (fix.x, fix.y, fix.source) == (72.8, 18.9, NavSource.SENSOR)
    assert fix.notes == ()


def test_ship_with_layback_moves_position_behind_heading():
    fix = select_position(**{**BASE, "ship_x": 0.0, "ship_y": 10.0, "layback_m": 100.0,
                             "heading_deg": 0.0}, coord_kind=CoordKind.LATLON)
    assert fix.source == NavSource.SHIP_LAYBACK
    assert fix.y == pytest.approx(10.0 - 100.0 / 111_320.0)
    assert fix.x == pytest.approx(0.0)
    assert NOTE_LAYBACK in fix.notes


def test_ship_without_layback_is_flagged():
    fix = select_position(**{**BASE, "ship_x": 72.8, "ship_y": 18.9}, coord_kind=CoordKind.LATLON)
    assert fix.source == NavSource.SHIP
    assert NOTE_SHIP_ONLY in fix.notes


def test_missing_position_is_withdrawn_not_defaulted():
    fix = select_position(**BASE, coord_kind=CoordKind.LATLON)
    assert fix.source == NavSource.MISSING
    assert math.isnan(fix.x) and math.isnan(fix.y)
    assert NOTE_WITHDRAWN in fix.notes


def test_out_of_range_latlon_is_invalid():
    fix = select_position(**{**BASE, "sensor_x": 500.0, "sensor_y": 18.9}, coord_kind=CoordKind.LATLON)
    assert fix.source == NavSource.MISSING


def test_projected_offset_in_metres():
    x, y = offset_behind(1000.0, 2000.0, 10.0, 90.0, CoordKind.PROJECTED)
    assert x == pytest.approx(990.0)
    assert y == pytest.approx(2000.0)
```

- [ ] **Step 2: Run to confirm failure**

Run: `uv run pytest tests/test_navigation.py` → FAIL (`No module named 'netsight.navigation'`).

- [ ] **Step 3: Implement** — `src/netsight/navigation/provenance.py`:

```python
"""Choose a ping position and record where it came from. Never invent positions."""

from __future__ import annotations

import math
from dataclasses import dataclass

from netsight.core.records import CoordKind, NavSource

METRES_PER_DEG_LAT = 111_320.0
NOTE_LAYBACK = "towfish position = vessel position moved back by layback along heading (catenary ignored)"
NOTE_SHIP_ONLY = "vessel position only; towfish offset unknown"
NOTE_WITHDRAWN = "no usable position; position withdrawn"


@dataclass(frozen=True)
class PositionFix:
    x: float
    y: float
    source: NavSource
    notes: tuple[str, ...] = ()


def _valid(x: float, y: float, kind: CoordKind) -> bool:
    if not (math.isfinite(x) and math.isfinite(y)):
        return False
    if x == 0.0 and y == 0.0:
        return False
    if kind == CoordKind.LATLON:
        return abs(y) <= 90.0 and abs(x) <= 180.0
    return True


def offset_behind(
    x: float, y: float, distance_m: float, heading_deg: float, kind: CoordKind
) -> tuple[float, float]:
    """Move a point `distance_m` metres opposite to `heading_deg` (degrees clockwise from north)."""
    h = math.radians(heading_deg)
    d_east = -distance_m * math.sin(h)
    d_north = -distance_m * math.cos(h)
    if kind == CoordKind.LATLON:
        dlon = d_east / (METRES_PER_DEG_LAT * math.cos(math.radians(y)))
        return x + dlon, y + d_north / METRES_PER_DEG_LAT
    return x + d_east, y + d_north


def select_position(
    *,
    sensor_x: float,
    sensor_y: float,
    ship_x: float,
    ship_y: float,
    layback_m: float,
    heading_deg: float,
    coord_kind: CoordKind,
) -> PositionFix:
    if _valid(sensor_x, sensor_y, coord_kind):
        return PositionFix(sensor_x, sensor_y, NavSource.SENSOR)
    if _valid(ship_x, ship_y, coord_kind):
        if math.isfinite(layback_m) and layback_m > 0 and math.isfinite(heading_deg):
            x, y = offset_behind(ship_x, ship_y, layback_m, heading_deg, coord_kind)
            return PositionFix(x, y, NavSource.SHIP_LAYBACK, (NOTE_LAYBACK,))
        return PositionFix(ship_x, ship_y, NavSource.SHIP, (NOTE_SHIP_ONLY,))
    return PositionFix(math.nan, math.nan, NavSource.MISSING, (NOTE_WITHDRAWN,))
```

- [ ] **Step 4: Run tests** — `uv run pytest tests/test_navigation.py` → pass; full suite and ruff pass.

- [ ] **Step 5: Commit**

```bash
git add src/netsight/navigation tests/test_navigation.py
git commit -m "feat(navigation): select ping positions with explicit provenance"
```

---

### Task 4: Synthetic XTF generator and XTF reader

**Files:**
- Create: `tests/helpers/synth_xtf.py`, `src/netsight/io/__init__.py` (temporary: empty file), `src/netsight/io/xtf.py`, `tests/test_xtf.py`

**Interfaces:**
- Consumes: Task 2 records, Task 3 `select_position`, `file_sha256`.
- Produces: `read_xtf(path) -> SonarRecord`; exceptions `UnsafeIndexFileError`, `XtfFormatError`; test helper `write_synthetic_xtf(path, **opts) -> Path` and `seabed_row(n_samples, spacing_m, altitude_m, ping=0) -> np.ndarray` (used again in Tasks 5 and 10).

- [ ] **Step 1: Write the synthetic generator** — `tests/helpers/synth_xtf.py`:

```python
"""Generate small, valid XTF files with pyxtf's own ctypes structures (no external data)."""

from __future__ import annotations

import ctypes
from collections.abc import Sequence
from pathlib import Path

import numpy as np
from pyxtf import XTFFileHeader, XTFPingChanHeader, XTFPingHeader

WATER_VALUE = 5.0


def seabed_row(n_samples: int, spacing_m: float, altitude_m: float, ping: int = 0) -> np.ndarray:
    """Water column (low) until slant range reaches altitude, then textured seabed.

    Texture depends on sample index (so neighbouring pings correlate, like real seabed) plus a
    small deterministic per-ping perturbation.
    """
    i = np.arange(n_samples)
    slant = (i + 0.5) * spacing_m
    texture = 40.0 * np.sin(i * 0.3) + 20.0 * np.cos(i * 0.07)
    rng = np.random.default_rng(1000 + ping)
    row = 200.0 + texture + rng.normal(0.0, 3.0, n_samples)
    row[slant < altitude_m] = WATER_VALUE
    return np.clip(row, 0, 65535)


def write_synthetic_xtf(
    path: str | Path,
    *,
    n_pings: int = 12,
    n_samples: int = 500,
    slant_range_m: float = 50.0,
    altitude_m: float = 5.0,
    nav: str = "sensor",  # "sensor" | "ship" | "ship_layback" | "missing"
    nav_units: int = 3,
    weight: int = 0,
    layback_m: float = 50.0,
    rolls: Sequence[float] | None = None,
    ping_numbers: Sequence[int] | None = None,
    seconds: Sequence[int] | None = None,
    channel_types: Sequence[int] = (1, 2),
) -> Path:
    path = Path(path)
    fh = XTFFileHeader()
    fh.FileFormat = 123
    fh.SystemType = 1
    fh.SonarName = b"SYNTH"
    fh.NumberOfSonarChannels = len(channel_types)
    fh.NavUnits = nav_units
    for i, ctype in enumerate(channel_types):
        ci = fh.ChanInfo[i]
        ci.TypeOfChannel = ctype
        ci.SubChannelNumber = i
        ci.BytesPerSample = 2
        ci.SampleFormat = 3  # uint16
        ci.Frequency = 455.0
    buf = bytearray(bytes(fh))
    spacing = slant_range_m / n_samples
    for p in range(n_pings):
        ph = XTFPingHeader()
        ph.MagicNumber = 0xFACE
        ph.HeaderType = 0
        ph.NumChansToFollow = len(channel_types)
        record = ctypes.sizeof(XTFPingHeader) + len(channel_types) * (
            ctypes.sizeof(XTFPingChanHeader) + n_samples * 2
        )
        pad = (-record) % 64
        ph.NumBytesThisRecord = record + pad
        sec = seconds[p] if seconds is not None else p
        ph.Year, ph.Month, ph.Day, ph.Hour, ph.Minute, ph.Second = 2026, 11, 6, 12, sec // 60, sec % 60
        ph.PingNumber = ping_numbers[p] if ping_numbers is not None else 100 + p
        lon, lat = 72.8 + p * 1e-5, 18.9
        if nav == "sensor":
            ph.SensorXcoordinate, ph.SensorYcoordinate = lon, lat
        elif nav in ("ship", "ship_layback"):
            ph.ShipXcoordinate, ph.ShipYcoordinate = lon, lat
            ph.Layback = layback_m if nav == "ship_layback" else 0.0
        ph.SensorPrimaryAltitude = altitude_m
        ph.SensorHeading = 90.0
        ph.SensorRoll = rolls[p] if rolls is not None else 0.0
        ph.SoundVelocity = 1500.0
        out = bytearray(bytes(ph))
        row = seabed_row(n_samples, spacing, altitude_m, ping=p)
        for c in range(len(channel_types)):
            ch = XTFPingChanHeader()
            ch.ChannelNumber = c
            ch.SlantRange = slant_range_m
            ch.NumSamples = n_samples
            ch.Frequency = 455
            ch.Weight = weight
            values = row * (2**weight) if weight else row
            out += bytes(ch) + np.clip(values, 0, 65535).astype(np.uint16).tobytes()
        out += b"\x00" * pad
        buf += out
    path.write_bytes(bytes(buf))
    return path
```

- [ ] **Step 2: Write the failing tests** — `tests/test_xtf.py`:

```python
import math

import numpy as np
import pytest
from helpers.synth_xtf import seabed_row, write_synthetic_xtf

from netsight.core.records import CoordKind, NavSource, SensorType
from netsight.io.xtf import UnsafeIndexFileError, XtfFormatError, read_xtf


def test_reads_pings_channels_and_sensor_nav(tmp_path):
    f = write_synthetic_xtf(tmp_path / "a.xtf", n_pings=6, n_samples=500)
    rec = read_xtf(f)
    assert rec.n_pings == 6
    assert rec.sensor.sensor_type == SensorType.SIDESCAN
    assert rec.sensor.source_format == "xtf"
    assert rec.sensor.model == "SYNTH"
    assert rec.sensor.frequency_khz == pytest.approx(455.0)
    p = rec.pings[0]
    assert p.nav_source == NavSource.SENSOR and p.coord_kind == CoordKind.LATLON
    assert p.x == pytest.approx(72.8) and p.y == pytest.approx(18.9)
    assert p.slant_range_m == pytest.approx(50.0)
    assert p.altitude_m == pytest.approx(5.0)
    expected = np.clip(seabed_row(500, 0.1, 5.0, ping=0), 0, 65535).astype(np.uint16)
    np.testing.assert_array_equal(p.port, expected.astype(np.float32))
    assert len(rec.provenance.sha256) == 64
    assert rec.provenance.reader == "netsight.io.xtf"


def test_weight_is_applied(tmp_path):
    f = write_synthetic_xtf(tmp_path / "w.xtf", n_pings=2, weight=2)
    p = read_xtf(f).pings[0]
    expected = np.clip(seabed_row(500, 0.1, 5.0, ping=0), 0, 65535).astype(np.uint16)
    np.testing.assert_allclose(p.port, expected, atol=1.0)  # uint16 truncation of 4x values


@pytest.mark.parametrize(
    ("nav", "source"),
    [("ship", NavSource.SHIP), ("ship_layback", NavSource.SHIP_LAYBACK), ("missing", NavSource.MISSING)],
)
def test_nav_sources(tmp_path, nav, source):
    rec = read_xtf(write_synthetic_xtf(tmp_path / f"{nav}.xtf", n_pings=3, nav=nav))
    assert {p.nav_source for p in rec.pings} == {source}
    if source == NavSource.MISSING:
        assert math.isnan(rec.pings[0].x)
    assert rec.nav_source_counts() == {str(source): 3}


def test_projected_nav_units(tmp_path):
    rec = read_xtf(write_synthetic_xtf(tmp_path / "m.xtf", n_pings=2, nav_units=0))
    assert rec.pings[0].coord_kind == CoordKind.PROJECTED


def test_pings_sorted_by_time(tmp_path):
    f = write_synthetic_xtf(tmp_path / "o.xtf", n_pings=3, seconds=[5, 1, 3], ping_numbers=[3, 1, 2])
    rec = read_xtf(f)
    assert [p.ping_number for p in rec.pings] == [1, 2, 3]
    assert [p.index for p in rec.pings] == [0, 1, 2]


def test_refuses_pickle_index_file(tmp_path):
    f = write_synthetic_xtf(tmp_path / "i.xtf", n_pings=2)
    (tmp_path / "i.pyxtf_idx").write_bytes(b"not trusted")
    with pytest.raises(UnsafeIndexFileError):
        read_xtf(f)


def test_requires_port_and_starboard(tmp_path):
    f = write_synthetic_xtf(tmp_path / "s.xtf", n_pings=2, channel_types=(0, 0))
    with pytest.raises(XtfFormatError):
        read_xtf(f)
```

- [ ] **Step 3: Run to confirm failure**

Run: `uv run pytest tests/test_xtf.py` → FAIL (`No module named 'netsight.io.xtf'`).

- [ ] **Step 4: Implement** — `src/netsight/io/xtf.py`:

```python
"""XTF side-scan reader. Wraps pyxtf (MIT) and contains its known hazards."""

from __future__ import annotations

import math
from collections import Counter
from importlib.metadata import version
from pathlib import Path

import numpy as np
import pyxtf

from netsight.core.hashing import file_sha256
from netsight.core.records import (
    CoordKind,
    Ping,
    Provenance,
    SensorDescriptor,
    SensorType,
    SonarRecord,
)
from netsight.navigation.provenance import select_position

PORT_CHANNEL_TYPE = 1
STBD_CHANNEL_TYPE = 2
LATLON_NAV_UNITS = 3


class UnsafeIndexFileError(RuntimeError):
    """A .pyxtf_idx file would be unpickled by pyxtf (arbitrary code execution)."""


class XtfFormatError(ValueError):
    pass


def _finite_or_nan(value: float) -> float:
    value = float(value)
    return value if math.isfinite(value) else math.nan


def _sound_velocity(raw: float) -> float:
    """XTF writers differ: some store one-way speed (~1500), some half of it (~750)."""
    sv = float(raw)
    if 1300.0 <= sv <= 1700.0:
        return sv
    if 650.0 <= sv <= 850.0:
        return 2.0 * sv
    return 1500.0


def read_xtf(path: str | Path) -> SonarRecord:
    p = Path(path)
    index_file = p.with_suffix(".pyxtf_idx")
    if index_file.exists():
        raise UnsafeIndexFileError(
            f"{index_file} exists; pyxtf would unpickle it. Delete it before reading {p.name}."
        )
    gen = pyxtf.xtf_read_gen(str(p), types=[pyxtf.XTFHeaderType.sonar])
    fh = next(gen)
    n_sonar = int(fh.NumberOfSonarChannels)
    channel_types = [int(fh.sonar_info[i].TypeOfChannel) for i in range(n_sonar)]
    try:
        port_i = channel_types.index(PORT_CHANNEL_TYPE)
        stbd_i = channel_types.index(STBD_CHANNEL_TYPE)
    except ValueError as exc:
        raise XtfFormatError(
            f"no port/starboard side-scan channel pair in {p.name} (channel types {channel_types})"
        ) from exc
    kind = CoordKind.LATLON if int(fh.NavUnits) == LATLON_NAV_UNITS else CoordKind.PROJECTED
    frequency = float(fh.sonar_info[port_i].Frequency) or None
    model = fh.SonarName.decode("ascii", errors="replace").strip("\x00 ") or None

    rows = []
    notes: Counter[str] = Counter()
    for pk in gen:
        if len(pk.data) <= max(port_i, stbd_i):
            notes["ping skipped: missing side-scan channel data"] += 1
            continue
        chans = pk.ping_chan_headers
        slant = float(chans[port_i].SlantRange)
        if not slant > 0:
            notes["ping skipped: non-positive slant range"] += 1
            continue
        port = pk.data[port_i].astype(np.float32)
        stbd = pk.data[stbd_i].astype(np.float32)
        if int(chans[port_i].Weight):
            port *= np.float32(2.0 ** -int(chans[port_i].Weight))
        if int(chans[stbd_i].Weight):
            stbd *= np.float32(2.0 ** -int(chans[stbd_i].Weight))
        if port.size != stbd.size:
            n = min(port.size, stbd.size)
            port, stbd = port[:n], stbd[:n]
            notes["ping truncated: unequal port/starboard sample counts"] += 1
        fix = select_position(
            sensor_x=float(pk.SensorXcoordinate),
            sensor_y=float(pk.SensorYcoordinate),
            ship_x=float(pk.ShipXcoordinate),
            ship_y=float(pk.ShipYcoordinate),
            layback_m=float(pk.Layback),
            heading_deg=float(pk.SensorHeading),
            coord_kind=kind,
        )
        for note in fix.notes:
            notes[note] += 1
        altitude = float(pk.SensorPrimaryAltitude)
        rows.append(
            dict(
                time=pk.get_time(),
                ping_number=int(pk.PingNumber),
                x=fix.x,
                y=fix.y,
                coord_kind=kind if fix.source != "missing" else CoordKind.NONE,
                nav_source=fix.source,
                heading_deg=_finite_or_nan(pk.SensorHeading),
                pitch_deg=_finite_or_nan(pk.SensorPitch),
                roll_deg=_finite_or_nan(pk.SensorRoll),
                altitude_m=altitude if math.isfinite(altitude) and altitude > 0 else math.nan,
                slant_range_m=slant,
                port=port,
                stbd=stbd,
                sound_velocity_ms=_sound_velocity(pk.SoundVelocity),
            )
        )
    rows.sort(key=lambda r: (r["time"], r["ping_number"]))
    pings = [Ping(index=i, **row) for i, row in enumerate(rows)]
    provenance = Provenance(
        source_path=str(p),
        sha256=file_sha256(p),
        reader="netsight.io.xtf",
        reader_version=f"pyxtf {version('pyxtf')}",
        notes=[f"{msg} ({count} pings)" for msg, count in sorted(notes.items())],
    )
    sensor = SensorDescriptor(
        sensor_type=SensorType.SIDESCAN,
        source_format="xtf",
        model=model,
        frequency_khz=frequency,
        n_channels=n_sonar,
    )
    return SonarRecord(sensor=sensor, pings=pings, provenance=provenance)
```

- [ ] **Step 5: Run tests** — `uv run pytest tests/test_xtf.py` → pass. If pyxtf emits a different exception for the `(0, 0)` channel case, keep `XtfFormatError` as the public error by catching it in `read_xtf`. Then full suite and ruff.

- [ ] **Step 6: Commit**

```bash
git add src/netsight/io tests/helpers/synth_xtf.py tests/test_xtf.py
git commit -m "feat(io): add safe XTF side-scan reader with nav provenance"
```

---

### Task 5: Synthetic JSF generator and in-house JSF reader

**Files:**
- Create: `tests/helpers/synth_jsf.py`, `src/netsight/io/jsf.py`, `tests/test_jsf.py`

**Interfaces:**
- Consumes: Task 2 records, `file_sha256`; test helper `seabed_row` from Task 4.
- Produces: `read_jsf(path, *, subsystem=None, sound_velocity_ms=1500.0) -> SonarRecord`; `JsfFormatError`; constants `HEADER`, `START_MARKER`, `MSG_SONAR`, `MSG_NMEA`; helpers `sonar_message(...)`, `nmea_message(...)`, `write_synthetic_jsf(path, ...)`.

Spec decisions (EdgeTech JSF Rev 1.8, doc 990-0000048-1000; offsets relative to the start of the message body, after the 16-byte header): ping time s @0 (int32), start depth samples @4 (uint32), ping number @8 (uint32), MSBs @16 (uint16; bits 8–11 extend the sample count), validity @30 (uint16: bit0 position, bit3 heading, bit5 pitch/roll, bit6 altitude), data format @34 (int16: 0 envelope, 1 analytic I/Q), X/lon @80 and Y/lat @84 (int32), coordinate units @88 (int16: 1 mm, 2 arc-minutes×1e-4, 3 dm), samples @114 (uint16), sample interval ns @116 (uint32), altitude mm @144 (int32), weighting N @168 (int16), heading 0.01° @172 (uint16), pitch @174 and roll @176 (int16, ×180/32768°), milliseconds today @200 (uint32); samples start at byte 240. Envelope samples are read as unsigned 16-bit (EdgeTech envelope is unsigned); analytic samples become magnitude. Offsets 216–239 are unverified and not used. Message 80 positions are "last fix, not time-interpolated" per the spec, so they are recorded as `NavSource.SHIP` with a note.

- [ ] **Step 1: Write the synthetic generator** — `tests/helpers/synth_jsf.py`:

```python
"""Write small JSF files from the EdgeTech JSF Rev 1.8 layout (no external data)."""

from __future__ import annotations

import struct
from collections.abc import Sequence
from pathlib import Path

import numpy as np
from helpers.synth_xtf import seabed_row

HEADER = struct.Struct("<HBBHBBBBHI")
VALID_POSITION, VALID_HEADING, VALID_PITCH_ROLL, VALID_ALTITUDE = 0x1, 0x8, 0x20, 0x40
SPACING_INTERVAL_NS = 133_333  # 0.1 m slant spacing at 1500 m/s


def _frame(msg_type: int, subsystem: int, channel: int, body: bytes) -> bytes:
    return HEADER.pack(0x1601, 10, 0, msg_type, 2, subsystem, channel, 0, 0, len(body)) + body


def sonar_message(
    *,
    ping_number: int,
    channel: int,
    subsystem: int = 20,
    n_samples: int = 400,
    interval_ns: int = SPACING_INTERVAL_NS,
    start_depth: int = 0,
    t_s: int = 1_793_000_000,
    ms_today: int = 0,
    lon: float = 72.8,
    lat: float = 18.9,
    position_valid: bool = True,
    altitude_m: float = 5.0,
    heading_deg: float = 90.0,
    pitch_deg: float = 0.0,
    roll_deg: float = 0.0,
    weight: int = 0,
    data_format: int = 0,
    samples: Sequence[float] | None = None,
) -> bytes:
    body = bytearray(240)
    struct.pack_into("<i", body, 0, t_s)
    struct.pack_into("<I", body, 4, start_depth)
    struct.pack_into("<I", body, 8, ping_number)
    struct.pack_into("<H", body, 16, ((n_samples >> 16) & 0xF) << 8)
    struct.pack_into("<h", body, 28, 1)
    validity = VALID_HEADING | VALID_PITCH_ROLL | VALID_ALTITUDE
    if position_valid:
        validity |= VALID_POSITION
    struct.pack_into("<H", body, 30, validity)
    struct.pack_into("<h", body, 34, data_format)
    struct.pack_into("<i", body, 80, round(lon * 600_000))
    struct.pack_into("<i", body, 84, round(lat * 600_000))
    struct.pack_into("<h", body, 88, 2)
    struct.pack_into("<H", body, 114, n_samples & 0xFFFF)
    struct.pack_into("<I", body, 116, interval_ns)
    struct.pack_into("<i", body, 144, round(altitude_m * 1000))
    struct.pack_into("<h", body, 168, weight)
    struct.pack_into("<H", body, 172, round(heading_deg * 100) % 36000)
    struct.pack_into("<h", body, 174, round(pitch_deg * 32768 / 180))
    struct.pack_into("<h", body, 176, round(roll_deg * 32768 / 180))
    struct.pack_into("<I", body, 200, ms_today)
    if samples is None:
        samples = seabed_row(n_samples, interval_ns * 1e-9 * 750.0, altitude_m, ping=ping_number)
    values = np.asarray(samples, dtype=np.float64) * (2**weight)
    if data_format == 0:
        payload = np.clip(values, 0, 65535).astype("<u2").tobytes()
    else:
        iq = np.stack([values, np.zeros_like(values)], axis=1)
        payload = np.clip(iq, -32768, 32767).astype("<i2").tobytes()
    return _frame(80, subsystem, channel, bytes(body) + payload)


def nmea_message(t_s: int, ms: int, text: str) -> bytes:
    body = struct.pack("<iiB3x", t_s, ms, 2) + text.encode("ascii")
    return _frame(2002, 100, 0, body)


def write_synthetic_jsf(
    path: str | Path,
    *,
    n_pings: int = 8,
    n_samples: int = 400,
    one_sided_pings: Sequence[int] = (),
    **sonar_kwargs,
) -> Path:
    path = Path(path)
    out = bytearray()
    for p in range(n_pings):
        for channel in (0, 1):
            if channel == 1 and p in one_sided_pings:
                continue
            out += sonar_message(
                ping_number=1000 + p, channel=channel, n_samples=n_samples, t_s=1_793_000_000 + p,
                **sonar_kwargs,
            )
    path.write_bytes(bytes(out))
    return path
```

- [ ] **Step 2: Write the failing tests** — `tests/test_jsf.py`:

```python
import math

import numpy as np
import pytest
from helpers.synth_jsf import nmea_message, sonar_message, write_synthetic_jsf
from helpers.synth_xtf import seabed_row

from netsight.core.records import CoordKind, NavSource
from netsight.io.jsf import JsfFormatError, read_jsf


def test_reads_two_sided_pings(tmp_path):
    rec = read_jsf(write_synthetic_jsf(tmp_path / "a.jsf", n_pings=5, n_samples=400))
    assert rec.n_pings == 5
    assert rec.sensor.source_format == "jsf"
    p = rec.pings[0]
    assert p.ping_number == 1000
    assert p.n_samples == 400
    assert p.slant_range_m == pytest.approx(400 * 133_333e-9 * 750.0)
    assert p.altitude_m == pytest.approx(5.0)
    assert p.heading_deg == pytest.approx(90.0)
    expected = np.clip(seabed_row(400, 133_333e-9 * 750.0, 5.0, ping=1000), 0, 65535).astype(np.uint16)
    np.testing.assert_array_equal(p.port, expected.astype(np.float32))


def test_position_from_message_80_is_flagged_as_ship(tmp_path):
    rec = read_jsf(write_synthetic_jsf(tmp_path / "p.jsf", n_pings=2))
    p = rec.pings[0]
    assert p.nav_source == NavSource.SHIP and p.coord_kind == CoordKind.LATLON
    assert p.x == pytest.approx(72.8, abs=1e-6) and p.y == pytest.approx(18.9, abs=1e-6)
    assert any("not time-interpolated" in n for n in rec.provenance.notes)


def test_nmea_fallback_when_position_invalid(tmp_path):
    f = tmp_path / "n.jsf"
    data = nmea_message(1_793_000_000, 0, "$GPGGA,120000.00,1854.00,N,07248.00,E,1,08,0.9,1.0,M,,M,,*47")
    data += sonar_message(ping_number=1, channel=0, position_valid=False)
    data += sonar_message(ping_number=1, channel=1, position_valid=False)
    f.write_bytes(data)
    p = read_jsf(f).pings[0]
    assert p.nav_source == NavSource.SHIP
    assert p.y == pytest.approx(18.9) and p.x == pytest.approx(72.8)


def test_missing_position_is_withdrawn(tmp_path):
    f = write_synthetic_jsf(tmp_path / "m.jsf", n_pings=2, position_valid=False)
    p = read_jsf(f).pings[0]
    assert p.nav_source == NavSource.MISSING and math.isnan(p.x)


def test_weighting_and_one_sided_pings(tmp_path):
    rec = read_jsf(write_synthetic_jsf(tmp_path / "w.jsf", n_pings=4, weight=1, one_sided_pings=(2,)))
    assert [p.ping_number for p in rec.pings] == [1000, 1001, 1003]
    assert any("one side only" in n for n in rec.provenance.notes)
    expected = np.clip(seabed_row(400, 133_333e-9 * 750.0, 5.0, ping=1000), 0, 65535).astype(np.uint16)
    np.testing.assert_allclose(rec.pings[0].port, expected, atol=1.0)


def test_start_depth_prepends_nan(tmp_path):
    rec = read_jsf(write_synthetic_jsf(tmp_path / "s.jsf", n_pings=1, start_depth=20))
    p = rec.pings[0]
    assert p.n_samples == 420
    assert np.isnan(p.port[:20]).all() and np.isfinite(p.port[20:]).all()


def test_analytic_format_becomes_magnitude(tmp_path):
    rec = read_jsf(write_synthetic_jsf(tmp_path / "iq.jsf", n_pings=1, data_format=1))
    assert (rec.pings[0].port >= 0).all()


def test_bad_marker_and_truncation_raise(tmp_path):
    bad = tmp_path / "bad.jsf"
    bad.write_bytes(b"\x00" * 32)
    with pytest.raises(JsfFormatError):
        read_jsf(bad)
    trunc = tmp_path / "trunc.jsf"
    trunc.write_bytes(sonar_message(ping_number=1, channel=0)[:-10])
    with pytest.raises(JsfFormatError):
        read_jsf(trunc)
```

- [ ] **Step 3: Run to confirm failure**

Run: `uv run pytest tests/test_jsf.py` → FAIL (`No module named 'netsight.io.jsf'`).

- [ ] **Step 4: Implement** — `src/netsight/io/jsf.py`:

```python
"""Minimal EdgeTech JSF side-scan reader, written from JSF Rev 1.8 (doc 990-0000048-1000)."""

from __future__ import annotations

import math
import struct
from collections import Counter
from dataclasses import dataclass
from pathlib import Path

import numpy as np

from netsight import __version__
from netsight.core.hashing import file_sha256
from netsight.core.records import (
    CoordKind,
    NavSource,
    Ping,
    Provenance,
    SensorDescriptor,
    SensorType,
    SonarRecord,
)

HEADER = struct.Struct("<HBBHBBBBHI")
START_MARKER = 0x1601
MSG_SONAR = 80
MSG_NMEA = 2002
SIDESCAN_SUBSYSTEMS = (20, 21)
SONAR_HEADER_BYTES = 240
NMEA_MAX_GAP_MS = 2000
NOTE_MSG80 = "JSF message-80 position is the last navigation fix, not time-interpolated; towfish offset unknown"
NOTE_NMEA = "position from nearest NMEA GGA fix within 2 s; towfish offset unknown"
NOTE_WITHDRAWN = "no usable position; position withdrawn"


class JsfFormatError(ValueError):
    pass


@dataclass
class _SonarMsg:
    subsystem: int
    channel: int
    ping_number: int
    time: np.datetime64
    start_depth: int
    interval_ns: int
    validity: int
    x_raw: int
    y_raw: int
    coord_units: int
    altitude_mm: int
    heading_raw: int
    pitch_raw: int
    roll_raw: int
    samples: np.ndarray


def _u(fmt: str, body: bytes, offset: int):
    return struct.unpack_from(fmt, body, offset)[0]


def _iter_messages(f):
    offset = 0
    while True:
        head = f.read(HEADER.size)
        if not head:
            return
        if len(head) < HEADER.size:
            raise JsfFormatError(f"truncated message header at byte {offset}")
        marker, _ver, _sess, msg_type, _cmd, subsystem, channel, _seq, _res, size = HEADER.unpack(head)
        if marker != START_MARKER:
            raise JsfFormatError(f"bad start marker 0x{marker:04x} at byte {offset}")
        body = f.read(size)
        if len(body) < size:
            raise JsfFormatError(f"truncated message body at byte {offset}")
        yield msg_type, subsystem, channel, body
        offset += HEADER.size + size


def _parse_sonar(subsystem: int, channel: int, body: bytes) -> _SonarMsg:
    if len(body) < SONAR_HEADER_BYTES:
        raise JsfFormatError("sonar message shorter than its 240-byte header")
    msbs = _u("<H", body, 16)
    n = _u("<H", body, 114) | (((msbs >> 8) & 0xF) << 16)
    data_format = _u("<h", body, 34)
    payload = memoryview(body)[SONAR_HEADER_BYTES:]
    if data_format == 0:
        need = n * 2
        if len(payload) < need:
            raise JsfFormatError("sample data shorter than declared")
        samples = np.frombuffer(payload[:need], dtype="<u2").astype(np.float32)
    elif data_format == 1:
        need = n * 4
        if len(payload) < need:
            raise JsfFormatError("sample data shorter than declared")
        iq = np.frombuffer(payload[:need], dtype="<i2").astype(np.float32).reshape(-1, 2)
        samples = np.hypot(iq[:, 0], iq[:, 1]).astype(np.float32)
    else:
        raise JsfFormatError(f"unsupported JSF data format {data_format}")
    weight = _u("<h", body, 168)
    if weight:
        samples = samples * np.float32(2.0**-weight)
    t = np.datetime64(_u("<i", body, 0), "s").astype("datetime64[ms]")
    t = t + np.timedelta64(_u("<I", body, 200) % 1000, "ms")
    return _SonarMsg(
        subsystem=subsystem,
        channel=channel,
        ping_number=_u("<I", body, 8),
        time=t,
        start_depth=_u("<I", body, 4),
        interval_ns=_u("<I", body, 116),
        validity=_u("<H", body, 30),
        x_raw=_u("<i", body, 80),
        y_raw=_u("<i", body, 84),
        coord_units=_u("<h", body, 88),
        altitude_mm=_u("<i", body, 144),
        heading_raw=_u("<H", body, 172),
        pitch_raw=_u("<h", body, 174),
        roll_raw=_u("<h", body, 176),
        samples=samples,
    )


def _coords(msg: _SonarMsg) -> tuple[float, float, CoordKind] | None:
    if not msg.validity & 0x1:
        return None
    if msg.coord_units == 2:
        return msg.x_raw / 600_000.0, msg.y_raw / 600_000.0, CoordKind.LATLON
    if msg.coord_units == 1:
        return msg.x_raw / 1000.0, msg.y_raw / 1000.0, CoordKind.PROJECTED
    if msg.coord_units == 3:
        return msg.x_raw / 10.0, msg.y_raw / 10.0, CoordKind.PROJECTED
    return None


def _nmea_degrees(field: str, degree_digits: int) -> float:
    return float(field[:degree_digits]) + float(field[degree_digits:]) / 60.0


def _parse_gga(text: str) -> tuple[float, float] | None:
    parts = text.strip().split("*")[0].split(",")
    if len(parts) < 7 or not parts[0].endswith("GGA") or parts[6] in ("", "0"):
        return None
    try:
        lat = _nmea_degrees(parts[2], 2)
        lon = _nmea_degrees(parts[4], 3)
    except ValueError:
        return None
    if parts[3] == "S":
        lat = -lat
    if parts[5] == "W":
        lon = -lon
    return lon, lat


def _with_start_depth(msg: _SonarMsg) -> np.ndarray:
    if msg.start_depth == 0:
        return msg.samples
    return np.concatenate([np.full(msg.start_depth, np.nan, dtype=np.float32), msg.samples])


def read_jsf(
    path: str | Path, *, subsystem: int | None = None, sound_velocity_ms: float = 1500.0
) -> SonarRecord:
    p = Path(path)
    sonar: list[_SonarMsg] = []
    gga: list[tuple[int, float, float]] = []
    with open(p, "rb") as f:
        for msg_type, subsys, channel, body in _iter_messages(f):
            if msg_type == MSG_SONAR and subsys in SIDESCAN_SUBSYSTEMS and channel in (0, 1):
                sonar.append(_parse_sonar(subsys, channel, body))
            elif msg_type == MSG_NMEA and len(body) > 12:
                fix = _parse_gga(body[12:].decode("ascii", "replace").strip("\x00\r\n "))
                if fix:
                    t_ms = _u("<i", body, 0) * 1000 + _u("<i", body, 4)
                    gga.append((t_ms, fix[0], fix[1]))
    if not sonar:
        raise JsfFormatError(f"no side-scan sonar messages (type 80, subsystem 20/21) in {p.name}")
    notes: Counter[str] = Counter()
    subsystems = sorted({m.subsystem for m in sonar})
    chosen = subsystem if subsystem is not None else subsystems[0]
    if len(subsystems) > 1:
        notes[f"subsystems present {subsystems}; using {chosen}"] += 1
    by_ping: dict[int, dict[int, _SonarMsg]] = {}
    for m in sonar:
        if m.subsystem == chosen:
            by_ping.setdefault(m.ping_number, {})[m.channel] = m
    gga.sort()
    gga_times = np.array([g[0] for g in gga], dtype=np.int64)

    rows = []
    for ping_number in sorted(by_ping):
        sides = by_ping[ping_number]
        if 0 not in sides or 1 not in sides:
            notes["ping skipped: one side only"] += 1
            continue
        pm, sm = sides[0], sides[1]
        port, stbd = _with_start_depth(pm), _with_start_depth(sm)
        n = min(port.size, stbd.size)
        port, stbd = port[:n], stbd[:n]
        coords = _coords(pm)
        if coords:
            x, y, kind = coords
            source = NavSource.SHIP
            notes[NOTE_MSG80] += 1
        else:
            x = y = math.nan
            kind, source = CoordKind.NONE, NavSource.MISSING
            if gga:
                t_ms = int(pm.time.astype("datetime64[ms]").astype(np.int64))
                j = int(np.argmin(np.abs(gga_times - t_ms)))
                if abs(int(gga_times[j]) - t_ms) <= NMEA_MAX_GAP_MS:
                    x, y = gga[j][1], gga[j][2]
                    kind, source = CoordKind.LATLON, NavSource.SHIP
                    notes[NOTE_NMEA] += 1
            if source == NavSource.MISSING:
                notes[NOTE_WITHDRAWN] += 1
        rows.append(
            dict(
                time=pm.time,
                ping_number=ping_number,
                x=x,
                y=y,
                coord_kind=kind,
                nav_source=source,
                heading_deg=pm.heading_raw / 100.0 if pm.validity & 0x8 else math.nan,
                pitch_deg=pm.pitch_raw * 180.0 / 32768.0 if pm.validity & 0x20 else math.nan,
                roll_deg=pm.roll_raw * 180.0 / 32768.0 if pm.validity & 0x20 else math.nan,
                altitude_m=pm.altitude_mm / 1000.0
                if pm.validity & 0x40 and pm.altitude_mm > 0
                else math.nan,
                slant_range_m=n * pm.interval_ns * 1e-9 * sound_velocity_ms / 2.0,
                port=port,
                stbd=stbd,
                sound_velocity_ms=sound_velocity_ms,
            )
        )
    rows.sort(key=lambda r: (r["time"], r["ping_number"]))
    pings = [Ping(index=i, **row) for i, row in enumerate(rows)]
    provenance = Provenance(
        source_path=str(p),
        sha256=file_sha256(p),
        reader="netsight.io.jsf",
        reader_version=f"netsight {__version__} (JSF Rev 1.8)",
        notes=[f"{msg} ({count} pings)" for msg, count in sorted(notes.items())],
    )
    sensor = SensorDescriptor(SensorType.SIDESCAN, "jsf", model="EdgeTech JSF", n_channels=2)
    return SonarRecord(sensor=sensor, pings=pings, provenance=provenance)
```

- [ ] **Step 5: Run tests** — `uv run pytest tests/test_jsf.py` → pass; then full suite and ruff. If the NMEA GGA checksum in the test is rejected, note that `_parse_gga` deliberately ignores checksums (data come from files, not live links); do not add checksum enforcement in this task.

- [ ] **Step 6: Commit**

```bash
git add src/netsight/io/jsf.py tests/helpers/synth_jsf.py tests/test_jsf.py
git commit -m "feat(io): add EdgeTech JSF side-scan reader from the public spec"
```

---

### Task 6: GeoTIFF mosaic reader and format dispatch

**Files:**
- Create: `src/netsight/io/mosaic.py`, `tests/test_mosaic.py`
- Modify: `src/netsight/io/__init__.py`

**Interfaces:**
- Consumes: `Provenance`, `file_sha256`, `read_xtf`, `read_jsf`.
- Produces: `Mosaic(array, transform, crs_wkt, pixel_size, pixel_units, provenance, gain_history_known=False)` with `.valid_fraction`; `read_mosaic(path, band=1) -> Mosaic`; `open_survey(path) -> SonarRecord | Mosaic`; `UnsupportedFormatError`.

- [ ] **Step 1: Write the failing tests** — `tests/test_mosaic.py`:

```python
import numpy as np
import pytest
import rasterio
from helpers.synth_xtf import write_synthetic_xtf
from rasterio.transform import from_origin

from netsight.core.records import SonarRecord
from netsight.io import UnsupportedFormatError, open_survey
from netsight.io.mosaic import Mosaic, read_mosaic


def write_tiff(path, crs="EPSG:32619", nodata=0):
    data = np.full((10, 20), 120, dtype=np.uint8)
    data[:3, :4] = 0
    with rasterio.open(
        path, "w", driver="GTiff", width=20, height=10, count=1, dtype="uint8",
        crs=crs, transform=from_origin(300000.0, 4500000.0, 1.0, 1.0), nodata=nodata,
    ) as dst:
        dst.write(data, 1)
    return path


def test_reads_mosaic_with_nodata_as_nan(tmp_path):
    m = read_mosaic(write_tiff(tmp_path / "m.tif"))
    assert m.array.shape == (10, 20) and m.array.dtype == np.float32
    assert np.isnan(m.array[0, 0]) and m.array[5, 5] == 120.0
    assert m.pixel_size == (1.0, 1.0) and m.pixel_units == "metre"
    assert m.valid_fraction == pytest.approx(1 - 12 / 200)
    assert m.gain_history_known is False
    assert "unknown gain" in " ".join(m.provenance.notes)


def test_geographic_mosaic_reports_degrees(tmp_path):
    m = read_mosaic(write_tiff(tmp_path / "g.tif", crs="EPSG:4326"))
    assert m.pixel_units == "degree"


def test_open_survey_dispatches(tmp_path):
    assert isinstance(open_survey(write_tiff(tmp_path / "x.tiff")), Mosaic)
    assert isinstance(open_survey(write_synthetic_xtf(tmp_path / "a.xtf", n_pings=2)), SonarRecord)
    with pytest.raises(UnsupportedFormatError):
        open_survey(tmp_path / "file.s7k")
```

- [ ] **Step 2: Run to confirm failure** — `uv run pytest tests/test_mosaic.py` → FAIL (import error).

- [ ] **Step 3: Implement**

`src/netsight/io/mosaic.py`:

```python
"""GeoTIFF side-scan / backscatter mosaic reader (vendor-neutral fallback input)."""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path

import numpy as np
import rasterio

from netsight.core.hashing import file_sha256
from netsight.core.records import Provenance

NOTE_GAIN = (
    "mosaic input: unknown gain/TVG history and no per-ping geometry; "
    "calibration on mosaics gets a lower claim level"
)


@dataclass
class Mosaic:
    array: np.ndarray
    transform: tuple[float, float, float, float, float, float]
    crs_wkt: str | None
    pixel_size: tuple[float, float]
    pixel_units: str
    provenance: Provenance
    gain_history_known: bool = False
    extra: dict = field(default_factory=dict)

    @property
    def valid_fraction(self) -> float:
        return float(np.isfinite(self.array).mean()) if self.array.size else 0.0


def read_mosaic(path: str | Path, band: int = 1) -> Mosaic:
    p = Path(path)
    with rasterio.open(p) as src:
        array = src.read(band, masked=True).astype(np.float32).filled(np.nan)
        transform = tuple(src.transform)[:6]
        crs = src.crs
        units = "degree" if crs is not None and crs.is_geographic else "metre"
        pixel_size = (abs(float(src.res[0])), abs(float(src.res[1])))
        crs_wkt = crs.to_wkt() if crs is not None else None
    notes = [NOTE_GAIN]
    if crs_wkt is None:
        notes.append("mosaic has no CRS")
    provenance = Provenance(str(p), file_sha256(p), "netsight.io.mosaic", f"rasterio {rasterio.__version__}", notes)
    return Mosaic(array, transform, crs_wkt, pixel_size, units, provenance)
```

`src/netsight/io/__init__.py`:

```python
"""Format adapters (layer L0): every reader returns NetSight's own records."""

from __future__ import annotations

from pathlib import Path

from netsight.core.records import SonarRecord
from netsight.io.jsf import read_jsf
from netsight.io.mosaic import Mosaic, read_mosaic
from netsight.io.xtf import read_xtf


class UnsupportedFormatError(ValueError):
    pass


def open_survey(path: str | Path) -> SonarRecord | Mosaic:
    suffix = Path(path).suffix.lower()
    if suffix == ".xtf":
        return read_xtf(path)
    if suffix == ".jsf":
        return read_jsf(path)
    if suffix in (".tif", ".tiff"):
        return read_mosaic(path)
    raise UnsupportedFormatError(f"unsupported survey format {suffix!r} (supported: .xtf .jsf .tif .tiff)")
```

- [ ] **Step 4: Run tests** — `uv run pytest tests/test_mosaic.py` → pass; full suite; ruff.

- [ ] **Step 5: Commit**

```bash
git add src/netsight/io tests/test_mosaic.py
git commit -m "feat(io): add GeoTIFF mosaic reader and format dispatch"
```

---

### Task 7: Bottom tracking, ground range and grazing angle

**Files:**
- Create: `src/netsight/geometry/__init__.py` (empty), `src/netsight/geometry/slant.py`, `tests/test_geometry.py`

**Interfaces:**
- Produces: `bottom_track(channel, sample_spacing_m, *, frac=0.5, run=3, smooth_pings=5, min_alt_m=0.3) -> np.ndarray`; `fuse_altitude(recorded, tracked, *, tol_m=1.0) -> tuple[np.ndarray, list[str]]` (sources `"recorded"`, `"bottom_track"`, `"missing"`); `ground_range_grid(max_ground_m, ground_res_m) -> np.ndarray`; `to_ground_range(row, sample_spacing_m, altitude_m, grid) -> np.ndarray`; `grazing_angle_deg(grid, altitude_m) -> np.ndarray`.

- [ ] **Step 1: Write the failing tests** — `tests/test_geometry.py`:

```python
import math

import numpy as np
import pytest
from helpers.synth_xtf import seabed_row

from netsight.geometry.slant import (
    bottom_track,
    fuse_altitude,
    grazing_angle_deg,
    ground_range_grid,
    to_ground_range,
)


def test_bottom_track_finds_first_seabed_return():
    m = np.stack([seabed_row(500, 0.1, 5.0, ping=i) for i in range(9)])
    alt = bottom_track(m, 0.1)
    assert alt.shape == (9,)
    np.testing.assert_allclose(alt, 5.0, atol=0.11)


def test_bottom_track_all_water_gives_nan():
    alt = bottom_track(np.zeros((3, 100)), 0.1)
    assert np.isnan(alt).all()


def test_fuse_altitude_prefers_agreeing_recorded_value():
    alt, src = fuse_altitude(np.array([5.0, 5.0, np.nan, 9.0]), np.array([5.2, np.nan, 4.8, 5.0]))
    np.testing.assert_allclose(alt, [5.0, 5.0, 4.8, 5.0])
    assert src == ["recorded", "recorded", "bottom_track", "bottom_track"]
    alt2, src2 = fuse_altitude(np.array([np.nan]), np.array([np.nan]))
    assert math.isnan(alt2[0]) and src2 == ["missing"]


def test_ground_range_conversion_leaves_nadir_gap_nan():
    row = seabed_row(500, 0.1, 5.0)
    grid = ground_range_grid(math.sqrt(50**2 - 5**2), 0.1)
    out = to_ground_range(row, 0.1, 5.0, grid)
    assert out.shape == grid.shape and out.dtype == np.float32
    assert np.isnan(out[:3]).all()  # inside the nadir gap
    assert np.isfinite(out[20:-2]).all()
    assert np.nanmean(out[20:]) == pytest.approx(np.mean(row[60:]), rel=0.05)


def test_ground_range_without_altitude_is_all_nan():
    grid = ground_range_grid(10.0, 0.5)
    assert np.isnan(to_ground_range(np.ones(100), 0.1, math.nan, grid)).all()


def test_grazing_angle():
    g = grazing_angle_deg(np.array([5.0, 50.0]), 5.0)
    assert g[0] == pytest.approx(45.0) and g[1] == pytest.approx(math.degrees(math.atan(0.1)))
```

- [ ] **Step 2: Run to confirm failure** — `uv run pytest tests/test_geometry.py` → FAIL.

- [ ] **Step 3: Implement** — `src/netsight/geometry/slant.py`:

```python
"""Side-scan geometry: altitude, slant-to-ground range and grazing angle (flat-seabed model)."""

from __future__ import annotations

import math
import warnings

import numpy as np


def _nan_median_filter(x: np.ndarray, window: int) -> np.ndarray:
    if window <= 1 or x.size == 0:
        return x.copy()
    half = window // 2
    padded = np.pad(x, half, mode="constant", constant_values=np.nan)
    windows = np.lib.stride_tricks.sliding_window_view(padded, 2 * half + 1)
    with warnings.catch_warnings():
        warnings.simplefilter("ignore", RuntimeWarning)
        return np.nanmedian(windows, axis=1)


def bottom_track(
    channel: np.ndarray,
    sample_spacing_m: float,
    *,
    frac: float = 0.5,
    run: int = 3,
    smooth_pings: int = 5,
    min_alt_m: float = 0.3,
) -> np.ndarray:
    """First seabed return per ping: first `run` consecutive samples above frac * 90th percentile."""
    data = np.nan_to_num(np.asarray(channel, dtype=np.float64), nan=0.0)
    n_pings = data.shape[0]
    start = int(math.ceil(min_alt_m / sample_spacing_m))
    alt = np.full(n_pings, np.nan)
    kernel = np.ones(run, dtype=np.int64)
    for i in range(n_pings):
        row = data[i]
        p90 = np.percentile(row, 90)
        if p90 <= 0:
            continue
        above = (row[start:] > frac * p90).astype(np.int64)
        if above.size < run:
            continue
        hits = np.nonzero(np.convolve(above, kernel, mode="valid") == run)[0]
        if hits.size:
            alt[i] = (hits[0] + start) * sample_spacing_m
    return _nan_median_filter(alt, smooth_pings)


def fuse_altitude(
    recorded: np.ndarray, tracked: np.ndarray, *, tol_m: float = 1.0
) -> tuple[np.ndarray, list[str]]:
    """Use the recorded altitude when it agrees with the bottom track (or no track exists)."""
    recorded = np.asarray(recorded, dtype=np.float64)
    tracked = np.asarray(tracked, dtype=np.float64)
    out = np.full(recorded.shape, np.nan)
    sources: list[str] = []
    for i, (rec, trk) in enumerate(zip(recorded, tracked, strict=True)):
        if math.isfinite(rec) and (not math.isfinite(trk) or abs(rec - trk) <= tol_m):
            out[i] = rec
            sources.append("recorded")
        elif math.isfinite(trk):
            out[i] = trk
            sources.append("bottom_track")
        else:
            sources.append("missing")
    return out, sources


def ground_range_grid(max_ground_m: float, ground_res_m: float) -> np.ndarray:
    n = int(math.ceil(max_ground_m / ground_res_m))
    return (np.arange(n) + 0.5) * ground_res_m


def to_ground_range(
    row: np.ndarray, sample_spacing_m: float, altitude_m: float, grid: np.ndarray
) -> np.ndarray:
    """Resample one near->far channel onto a ground-range grid. Nadir gap and gaps stay NaN."""
    out = np.full(grid.shape, np.nan, dtype=np.float32)
    if not (math.isfinite(altitude_m) and altitude_m > 0):
        return out
    row = np.asarray(row, dtype=np.float64)
    slant = (np.arange(row.size) + 0.5) * sample_spacing_m
    ok = (slant > altitude_m) & np.isfinite(row)
    if ok.sum() < 2:
        return out
    ground = np.sqrt(slant[ok] ** 2 - altitude_m**2)
    out[:] = np.interp(grid, ground, row[ok], left=np.nan, right=np.nan)
    return out


def grazing_angle_deg(grid: np.ndarray, altitude_m: float) -> np.ndarray:
    if not (math.isfinite(altitude_m) and altitude_m > 0):
        return np.full(np.shape(grid), np.nan, dtype=np.float32)
    return np.degrees(np.arctan2(altitude_m, np.asarray(grid, dtype=np.float64))).astype(np.float32)
```

- [ ] **Step 4: Run tests** — `uv run pytest tests/test_geometry.py` → pass; full suite; ruff.

- [ ] **Step 5: Commit**

```bash
git add src/netsight/geometry tests/test_geometry.py
git commit -m "feat(geometry): add bottom tracking, ground range and grazing angle"
```

---

### Task 8: Radiometric normalisation

**Files:**
- Create: `src/netsight/radiometry/__init__.py` (empty), `src/netsight/radiometry/gain.py`, `tests/test_gain.py`

**Interfaces:**
- Produces: `across_track_equalise(swath, *, block=200, eps=1e-6) -> np.ndarray`; `to_log(x, *, floor=1e-3) -> np.ndarray` (dB, `10*log10`).

- [ ] **Step 1: Write the failing tests** — `tests/test_gain.py`:

```python
import numpy as np
import pytest

from netsight.radiometry.gain import across_track_equalise, to_log


def test_equalisation_flattens_range_falloff():
    rng = np.random.default_rng(0)
    base = 100.0 + rng.normal(0, 5, (300, 200))
    falloff = 1.0 / (1.0 + np.arange(200) / 50.0)
    out = across_track_equalise(base * falloff, block=100)
    col_means = out.mean(axis=0)
    assert col_means.std() / col_means.mean() < 0.01
    assert out.dtype == np.float32


def test_equalisation_keeps_nan_columns_nan():
    sw = np.ones((10, 5))
    sw[:, 0] = np.nan
    out = across_track_equalise(sw)
    assert np.isnan(out[:, 0]).all() and np.isfinite(out[:, 1:]).all()


def test_to_log():
    out = to_log(np.array([1.0, 100.0, 0.0, np.nan]))
    assert out[0] == pytest.approx(0.0) and out[1] == pytest.approx(20.0)
    assert out[2] == pytest.approx(-30.0) and np.isnan(out[3])
```

- [ ] **Step 2: Run to confirm failure** — `uv run pytest tests/test_gain.py` → FAIL.

- [ ] **Step 3: Implement** — `src/netsight/radiometry/gain.py`:

```python
"""Radiometric normalisation for ground-range swaths (rows = pings, columns = range bins)."""

from __future__ import annotations

import warnings

import numpy as np


def across_track_equalise(swath: np.ndarray, *, block: int = 200, eps: float = 1e-6) -> np.ndarray:
    """Divide each range column by its mean over blocks of pings (empirical beam-pattern/TVG fix)."""
    data = np.asarray(swath, dtype=np.float64)
    out = np.full(data.shape, np.nan, dtype=np.float64)
    with warnings.catch_warnings():
        warnings.simplefilter("ignore", RuntimeWarning)
        for start in range(0, data.shape[0], block):
            chunk = data[start : start + block]
            col_mean = np.nanmean(chunk, axis=0)
            level = np.nanmean(col_mean)
            out[start : start + block] = chunk / (col_mean + eps) * level
    return out.astype(np.float32)


def to_log(x: np.ndarray, *, floor: float = 1e-3) -> np.ndarray:
    """Intensity to decibels; multiplicative speckle becomes additive. NaN stays NaN."""
    arr = np.asarray(x, dtype=np.float64)
    with np.errstate(invalid="ignore"):
        return (10.0 * np.log10(np.where(np.isnan(arr), np.nan, np.maximum(arr, floor)))).astype(
            np.float32
        )
```

- [ ] **Step 4: Run tests** — `uv run pytest tests/test_gain.py` → pass; full suite; ruff.

- [ ] **Step 5: Commit**

```bash
git add src/netsight/radiometry tests/test_gain.py
git commit -m "feat(radiometry): add across-track equalisation and log transform"
```

---

### Task 9: Geometry-preserving dropout repair

**Files:**
- Create: `src/netsight/qc/__init__.py` (empty), `src/netsight/qc/dropout.py`, `tests/test_dropout.py`

**Interfaces:**
- Produces: `DropoutResult(data, repaired_rows, gap_rows)`; `repair_dropouts(swath, *, zero_fraction=0.95, max_interp_rows=2) -> DropoutResult`. Bad rows = more than `zero_fraction` of samples equal 0 or NaN. Runs of ≤ `max_interp_rows` bad rows with valid rows on both sides are linearly interpolated (`repaired_rows`); longer runs or edge runs become NaN (`gap_rows` = "not searched").

- [ ] **Step 1: Write the failing tests** — `tests/test_dropout.py`:

```python
import numpy as np

from netsight.qc.dropout import repair_dropouts


def make():
    sw = np.tile(np.linspace(10, 20, 50), (20, 1))
    return sw


def test_isolated_bad_row_is_interpolated():
    sw = make()
    sw[3] = 0
    res = repair_dropouts(sw)
    np.testing.assert_allclose(res.data[3], sw[2])
    assert res.repaired_rows[3] and not res.gap_rows.any()


def test_long_gap_is_kept_as_not_searched():
    sw = make()
    sw[10:15] = 0
    res = repair_dropouts(sw)
    assert np.isnan(res.data[10:15]).all()
    assert res.gap_rows[10:15].all() and not res.repaired_rows.any()


def test_edge_bad_row_cannot_be_interpolated():
    sw = make()
    sw[0] = np.nan
    res = repair_dropouts(sw)
    assert res.gap_rows[0] and np.isnan(res.data[0]).all()


def test_good_data_untouched():
    sw = make()
    res = repair_dropouts(sw)
    np.testing.assert_array_equal(res.data, sw.astype(np.float32))
    assert not res.repaired_rows.any() and not res.gap_rows.any()
```

- [ ] **Step 2: Run to confirm failure** — `uv run pytest tests/test_dropout.py` → FAIL.

- [ ] **Step 3: Implement** — `src/netsight/qc/dropout.py`:

```python
"""Ping dropout handling: repair isolated bad rows, keep long gaps visible as not searched."""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np


@dataclass
class DropoutResult:
    data: np.ndarray
    repaired_rows: np.ndarray
    gap_rows: np.ndarray


def _runs(mask: np.ndarray) -> list[tuple[int, int]]:
    runs, start = [], None
    for i, bad in enumerate(mask):
        if bad and start is None:
            start = i
        elif not bad and start is not None:
            runs.append((start, i))
            start = None
    if start is not None:
        runs.append((start, mask.size))
    return runs


def repair_dropouts(
    swath: np.ndarray, *, zero_fraction: float = 0.95, max_interp_rows: int = 2
) -> DropoutResult:
    data = np.asarray(swath, dtype=np.float32).copy()
    n = data.shape[0]
    empty = (data == 0) | np.isnan(data)
    bad = empty.mean(axis=1) > zero_fraction
    repaired = np.zeros(n, dtype=bool)
    gap = np.zeros(n, dtype=bool)
    for start, stop in _runs(bad):
        length = stop - start
        if length <= max_interp_rows and start > 0 and stop < n:
            left, right = data[start - 1], data[stop]
            for k, row in enumerate(range(start, stop), start=1):
                w = k / (length + 1)
                data[row] = (1 - w) * left + w * right
            repaired[start:stop] = True
        else:
            data[start:stop] = np.nan
            gap[start:stop] = True
    return DropoutResult(data=data, repaired_rows=repaired, gap_rows=gap)
```

- [ ] **Step 4: Run tests** — `uv run pytest tests/test_dropout.py` → pass; full suite; ruff.

- [ ] **Step 5: Commit**

```bash
git add src/netsight/qc tests/test_dropout.py
git commit -m "feat(qc): add geometry-preserving dropout repair"
```

---

### Task 10: Quality mask Q

**Files:**
- Create: `src/netsight/qc/quality.py`, `tests/helpers/swaths.py`, `tests/test_quality.py`

**Interfaces:**
- Produces: `QualityThresholds(max_roll_deg=5.0, max_pitch_deg=5.0, max_attitude_rate_deg_s=3.0, max_altitude_jump_m=1.0, towfish_height_min_frac=0.08, towfish_height_max_frac=0.20, stripe_corr_min=0.2)`; `SEVERITY: dict[str, float]`; `QualityMask(q, flags)` with `.summary() -> dict`; `compute_quality(*, times, ping_numbers, roll_deg, pitch_deg, altitude_m, slant_range_m, swath, gap_rows, repaired_rows, nav_missing, thresholds=QualityThresholds()) -> QualityMask`. `Q = Π(1 − severity × flag)`; `ping_gap` and `nav_missing` are recorded with severity 0 (they affect coverage and position, not data quality).

Threshold notes: towfish height 8–20% of range follows NOAA HSSD §6.1.2.3; the other thresholds are starting values to be tuned on real data in Step 1B.

- [ ] **Step 1: Write the swath helper** — `tests/helpers/swaths.py`:

```python
import numpy as np


def smooth_swath(n_pings: int = 10, n_bins: int = 200, seed: int = 0) -> np.ndarray:
    """Along-track-correlated seabed: one texture row repeated with small noise."""
    rng = np.random.default_rng(seed)
    texture = 100.0 + 30.0 * np.sin(np.arange(n_bins) * 0.2)
    return texture + rng.normal(0.0, 1.0, (n_pings, n_bins))
```

- [ ] **Step 2: Write the failing tests** — `tests/test_quality.py`:

```python
import numpy as np
import pytest
from helpers.swaths import smooth_swath

from netsight.qc.quality import SEVERITY, compute_quality


def inputs(n=10):
    return dict(
        times=np.datetime64("2026-11-06T12:00:00") + np.arange(n).astype("timedelta64[s]"),
        ping_numbers=np.arange(100, 100 + n),
        roll_deg=np.zeros(n),
        pitch_deg=np.zeros(n),
        altitude_m=np.full(n, 5.0),
        slant_range_m=np.full(n, 50.0),
        swath=smooth_swath(n),
        gap_rows=np.zeros(n, bool),
        repaired_rows=np.zeros(n, bool),
        nav_missing=np.zeros(n, bool),
    )


def test_clean_data_scores_one():
    qm = compute_quality(**inputs())
    np.testing.assert_allclose(qm.q, 1.0)
    assert not any(f.any() for f in qm.flags.values())


def test_roll_spike_penalises_attitude_and_rate():
    kw = inputs()
    kw["roll_deg"][3] = 8.0
    qm = compute_quality(**kw)
    assert qm.flags["attitude"][3] and qm.flags["attitude_rate"][3] and qm.flags["attitude_rate"][4]
    assert qm.q[3] == pytest.approx((1 - SEVERITY["attitude"]) * (1 - SEVERITY["attitude_rate"]))
    assert qm.q[4] == pytest.approx(1 - SEVERITY["attitude_rate"])


def test_altitude_jump_missing_and_towfish_height():
    kw = inputs()
    kw["altitude_m"][5] = 12.0
    kw["altitude_m"][8] = np.nan
    qm = compute_quality(**kw)
    assert qm.flags["altitude_jump"][5] and qm.flags["altitude_jump"][6]
    assert qm.flags["towfish_height"][5]  # 12/50 = 0.24 > 0.20
    assert qm.flags["altitude_missing"][8]


def test_ping_gap_and_nav_missing_recorded_without_penalty():
    kw = inputs()
    kw["ping_numbers"][6:] += 5
    kw["nav_missing"][2] = True
    qm = compute_quality(**kw)
    assert qm.flags["ping_gap"][6] and qm.flags["nav_missing"][2]
    assert qm.q[6] == pytest.approx(1.0) and qm.q[2] == pytest.approx(1.0)


def test_stripe_row_flagged_but_not_its_neighbours():
    kw = inputs()
    kw["swath"][4] = np.random.default_rng(9).normal(100, 30, kw["swath"].shape[1])
    qm = compute_quality(**kw)
    assert qm.flags["stripe"][4]
    assert not qm.flags["stripe"][3] and not qm.flags["stripe"][5]


def test_dropout_gap_zeroes_q_and_summary_counts():
    kw = inputs()
    kw["gap_rows"][7] = True
    kw["repaired_rows"][1] = True
    qm = compute_quality(**kw)
    assert qm.q[7] == 0.0
    assert qm.q[1] == pytest.approx(1 - SEVERITY["repaired"])
    s = qm.summary()
    assert s["flag_counts"]["dropout"] == 1 and 0 < s["mean_q"] < 1
```

- [ ] **Step 3: Run to confirm failure** — `uv run pytest tests/test_quality.py` → FAIL.

- [ ] **Step 4: Implement** — `src/netsight/qc/quality.py`:

```python
"""Per-ping quality mask Q in [0, 1] with named reason flags."""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np

SEVERITY: dict[str, float] = {
    "attitude": 0.5,
    "attitude_rate": 0.5,
    "altitude_missing": 0.3,
    "altitude_jump": 0.7,
    "towfish_height": 0.3,
    "stripe": 0.6,
    "dropout": 1.0,
    "repaired": 0.2,
    "ping_gap": 0.0,
    "nav_missing": 0.0,
}


@dataclass(frozen=True)
class QualityThresholds:
    max_roll_deg: float = 5.0
    max_pitch_deg: float = 5.0
    max_attitude_rate_deg_s: float = 3.0
    max_altitude_jump_m: float = 1.0
    towfish_height_min_frac: float = 0.08  # NOAA HSSD 6.1.2.3: towfish 8-20% of range scale
    towfish_height_max_frac: float = 0.20
    stripe_corr_min: float = 0.2


@dataclass
class QualityMask:
    q: np.ndarray
    flags: dict[str, np.ndarray]

    def summary(self) -> dict:
        return {
            "mean_q": float(np.mean(self.q)) if self.q.size else float("nan"),
            "min_q": float(np.min(self.q)) if self.q.size else float("nan"),
            "flag_counts": {name: int(f.sum()) for name, f in self.flags.items()},
        }


def _row_corr(a: np.ndarray, b: np.ndarray) -> float:
    ok = np.isfinite(a) & np.isfinite(b)
    if ok.sum() < 10:
        return float("nan")
    a, b = a[ok], b[ok]
    if a.std() == 0 or b.std() == 0:
        return float("nan")
    return float(np.corrcoef(a, b)[0, 1])


def _stripe_rows(swath: np.ndarray, threshold: float) -> np.ndarray:
    n = swath.shape[0]
    out = np.zeros(n, dtype=bool)
    if n < 2:
        return out
    corr = np.array([_row_corr(swath[i], swath[i + 1]) for i in range(n - 1)])
    for i in range(n):
        neighbours = []
        if i > 0 and np.isfinite(corr[i - 1]):
            neighbours.append(corr[i - 1])
        if i < n - 1 and np.isfinite(corr[i]):
            neighbours.append(corr[i])
        out[i] = bool(neighbours) and all(c < threshold for c in neighbours)
    return out


def compute_quality(
    *,
    times: np.ndarray,
    ping_numbers: np.ndarray,
    roll_deg: np.ndarray,
    pitch_deg: np.ndarray,
    altitude_m: np.ndarray,
    slant_range_m: np.ndarray,
    swath: np.ndarray,
    gap_rows: np.ndarray,
    repaired_rows: np.ndarray,
    nav_missing: np.ndarray,
    thresholds: QualityThresholds = QualityThresholds(),
) -> QualityMask:
    th = thresholds
    n = len(ping_numbers)
    t = np.asarray(times, dtype="datetime64[ms]").astype(np.int64) / 1000.0
    dt = np.diff(t, prepend=t[0] if n else 0.0)
    dt[dt <= 0] = np.nan
    roll = np.asarray(roll_deg, dtype=np.float64)
    pitch = np.asarray(pitch_deg, dtype=np.float64)
    alt = np.asarray(altitude_m, dtype=np.float64)
    with np.errstate(invalid="ignore", divide="ignore"):
        d_att = np.fmax(np.abs(np.diff(roll, prepend=roll[:1])), np.abs(np.diff(pitch, prepend=pitch[:1])))
        ratio = alt / np.asarray(slant_range_m, dtype=np.float64)
        flags = {
            "attitude": (np.abs(roll) > th.max_roll_deg) | (np.abs(pitch) > th.max_pitch_deg),
            "attitude_rate": (d_att / dt) > th.max_attitude_rate_deg_s,
            "altitude_missing": ~np.isfinite(alt),
            "altitude_jump": np.abs(np.diff(alt, prepend=alt[:1])) > th.max_altitude_jump_m,
            "towfish_height": np.isfinite(ratio)
            & ((ratio < th.towfish_height_min_frac) | (ratio > th.towfish_height_max_frac)),
        }
    flags["stripe"] = _stripe_rows(np.asarray(swath, dtype=np.float64), th.stripe_corr_min)
    flags["dropout"] = np.asarray(gap_rows, dtype=bool)
    flags["repaired"] = np.asarray(repaired_rows, dtype=bool)
    pn = np.asarray(ping_numbers, dtype=np.int64)
    flags["ping_gap"] = np.concatenate([[False], np.diff(pn) > 1]) if n else np.zeros(0, bool)
    flags["nav_missing"] = np.asarray(nav_missing, dtype=bool)
    q = np.ones(n)
    for name, f in flags.items():
        q *= np.where(f, 1.0 - SEVERITY[name], 1.0)
    return QualityMask(q=q.astype(np.float32), flags=flags)
```

- [ ] **Step 5: Run tests** — `uv run pytest tests/test_quality.py` → pass; full suite; ruff.

- [ ] **Step 6: Commit**

```bash
git add src/netsight/qc/quality.py tests/helpers/swaths.py tests/test_quality.py
git commit -m "feat(qc): add per-ping quality mask with reason flags"
```

---

### Task 11: Normalised swath (integration of L1)

**Files:**
- Create: `src/netsight/normalise/__init__.py` (empty), `src/netsight/normalise/swath.py`, `tests/test_swath.py`

**Interfaces:**
- Consumes: Tasks 2, 7, 8, 9, 10.
- Produces: `TIERS_M: dict[str, float]` (`sas` 0.02, `sidescan_fine` 0.05, `sidescan` 0.10, `sidescan_coarse` 0.20, `mbes` 0.50); `choose_ground_resolution(native_spacing_m) -> float` (smallest tier ≥ native spacing, else the largest tier; never upsamples); `NormalisedSwath` (fields: `ground_res_m`, `ground_m`, `port`, `stbd`, `grazing_deg`, `not_searched_port`, `not_searched_stbd`, `altitude_m`, `altitude_source`, `x`, `y`, `coord_kind`, `nav_source`, `heading_deg`, `times`, `quality`, `sensor`, `provenance`) with `.metadata() -> dict` and `.to_npz(path) -> Path`; `normalise_record(record, *, ground_res_m=None, thresholds=QualityThresholds(), equalise=True) -> NormalisedSwath`. Arrays: `port`/`stbd`/`grazing_deg` shape `(n_pings, n_bins)`, near→far; `times` stored as `datetime64[ms]`.

- [ ] **Step 1: Write the failing tests** — `tests/test_swath.py`:

```python
import json
import math

import numpy as np
import pytest
from helpers.synth_xtf import write_synthetic_xtf

from netsight.io.xtf import read_xtf
from netsight.normalise.swath import choose_ground_resolution, normalise_record


def test_choose_ground_resolution_never_upsamples():
    assert choose_ground_resolution(0.1) == 0.10
    assert choose_ground_resolution(0.03) == 0.05
    assert choose_ground_resolution(0.015) == 0.02
    assert choose_ground_resolution(2.0) == 0.50


def test_normalise_synthetic_xtf(tmp_path):
    rec = read_xtf(write_synthetic_xtf(tmp_path / "a.xtf", n_pings=12, n_samples=500))
    sw = normalise_record(rec)
    n_bins = math.ceil(math.sqrt(50**2 - 5**2) / 0.1)
    assert sw.ground_res_m == 0.10
    assert sw.port.shape == (12, n_bins) and sw.stbd.shape == (12, n_bins)
    assert sw.grazing_deg.shape == (12, n_bins)
    np.testing.assert_allclose(sw.altitude_m, 5.0)
    assert set(sw.altitude_source) == {"recorded"}
    assert sw.not_searched_port[:, :3].all() and not sw.not_searched_port[:, 50:].any()
    np.testing.assert_allclose(sw.quality.q, 1.0)
    assert set(sw.nav_source) == {"sensor"}


def test_dropout_rows_become_not_searched(tmp_path):
    rec = read_xtf(write_synthetic_xtf(tmp_path / "d.xtf", n_pings=12))
    for p in rec.pings[4:8]:
        p.port[:] = 0
        p.stbd[:] = 0
    sw = normalise_record(rec)
    assert sw.not_searched_port[4:8].all() and sw.not_searched_stbd[4:8].all()
    assert (sw.quality.q[4:8] == 0).all()


def test_metadata_and_npz_round_trip(tmp_path):
    sw = normalise_record(read_xtf(write_synthetic_xtf(tmp_path / "m.xtf", n_pings=6)))
    meta = sw.metadata()
    json.dumps(meta)
    assert meta["n_pings"] == 6 and meta["ground_res_m"] == 0.10
    assert meta["sensor"]["source_format"] == "xtf"
    out = sw.to_npz(tmp_path / "m_swath.npz")
    with np.load(out) as z:
        np.testing.assert_array_equal(z["port"], sw.port)
        assert json.loads(str(z["metadata"]))["n_pings"] == 6


def test_no_altitude_anywhere_raises(tmp_path):
    rec = read_xtf(write_synthetic_xtf(tmp_path / "z.xtf", n_pings=3))
    for p in rec.pings:
        p.altitude_m = float("nan")
        p.port[:] = 0
        p.stbd[:] = 0
    with pytest.raises(ValueError, match="altitude"):
        normalise_record(rec)
```

- [ ] **Step 2: Run to confirm failure** — `uv run pytest tests/test_swath.py` → FAIL.

- [ ] **Step 3: Implement** — `src/netsight/normalise/swath.py`:

```python
"""Layer L1: turn a SonarRecord into a QC'd, ground-range, geometry-aware swath."""

from __future__ import annotations

import json
import math
import warnings
from collections import Counter
from dataclasses import dataclass
from pathlib import Path

import numpy as np

from netsight.core.records import Provenance, SensorDescriptor, SonarRecord
from netsight.geometry.slant import (
    bottom_track,
    fuse_altitude,
    grazing_angle_deg,
    ground_range_grid,
    to_ground_range,
)
from netsight.qc.dropout import repair_dropouts
from netsight.qc.quality import QualityMask, QualityThresholds, compute_quality
from netsight.radiometry.gain import across_track_equalise

TIERS_M: dict[str, float] = {
    "sas": 0.02,
    "sidescan_fine": 0.05,
    "sidescan": 0.10,
    "sidescan_coarse": 0.20,
    "mbes": 0.50,
}


def choose_ground_resolution(native_spacing_m: float) -> float:
    candidates = sorted(TIERS_M.values())
    for res in candidates:
        if res >= native_spacing_m * 0.999:
            return res
    return candidates[-1]


@dataclass
class NormalisedSwath:
    ground_res_m: float
    ground_m: np.ndarray
    port: np.ndarray
    stbd: np.ndarray
    grazing_deg: np.ndarray
    not_searched_port: np.ndarray
    not_searched_stbd: np.ndarray
    altitude_m: np.ndarray
    altitude_source: list[str]
    x: np.ndarray
    y: np.ndarray
    coord_kind: list[str]
    nav_source: list[str]
    heading_deg: np.ndarray
    times: np.ndarray
    quality: QualityMask
    sensor: SensorDescriptor
    provenance: Provenance

    def metadata(self) -> dict:
        return {
            "ground_res_m": self.ground_res_m,
            "n_pings": int(self.port.shape[0]),
            "n_bins": int(self.port.shape[1]),
            "sensor": self.sensor.to_dict(),
            "provenance": self.provenance.to_dict(),
            "quality": self.quality.summary(),
            "nav_source_counts": dict(Counter(self.nav_source)),
            "altitude_source_counts": dict(Counter(self.altitude_source)),
            "coord_kinds": sorted(set(self.coord_kind)),
            "time_start": str(self.times[0]) if self.times.size else None,
            "time_end": str(self.times[-1]) if self.times.size else None,
            "not_searched_fraction": float(
                (self.not_searched_port.mean() + self.not_searched_stbd.mean()) / 2
            ),
        }

    def to_npz(self, path: str | Path) -> Path:
        path = Path(path)
        np.savez_compressed(
            path,
            ground_m=self.ground_m,
            port=self.port,
            stbd=self.stbd,
            grazing_deg=self.grazing_deg,
            not_searched_port=self.not_searched_port,
            not_searched_stbd=self.not_searched_stbd,
            altitude_m=self.altitude_m,
            x=self.x,
            y=self.y,
            heading_deg=self.heading_deg,
            times_ms=self.times.astype("datetime64[ms]").astype(np.int64),
            quality_q=self.quality.q,
            **{f"flag_{k}": v for k, v in self.quality.flags.items()},
            metadata=np.array(json.dumps(self.metadata())),
        )
        return path


def normalise_record(
    record: SonarRecord,
    *,
    ground_res_m: float | None = None,
    thresholds: QualityThresholds = QualityThresholds(),
    equalise: bool = True,
) -> NormalisedSwath:
    if record.n_pings == 0:
        raise ValueError("record has no pings")
    port_raw = record.channel_matrix("port")
    stbd_raw = record.channel_matrix("stbd")
    pings = record.pings
    spacing = np.array([p.sample_spacing_m for p in pings])
    slant = np.array([p.slant_range_m for p in pings])

    port_fix = repair_dropouts(port_raw)
    stbd_fix = repair_dropouts(stbd_raw)
    gap_rows = port_fix.gap_rows | stbd_fix.gap_rows
    repaired_rows = (port_fix.repaired_rows | stbd_fix.repaired_rows) & ~gap_rows

    with warnings.catch_warnings():
        warnings.simplefilter("ignore", RuntimeWarning)
        combined = np.nanmean(np.stack([port_fix.data, stbd_fix.data]), axis=0)
    tracked = bottom_track(combined, float(np.median(spacing)))
    recorded = np.array([p.altitude_m for p in pings])
    altitude, altitude_source = fuse_altitude(recorded, tracked)
    if not np.isfinite(altitude).any():
        raise ValueError("no altitude available (recorded or bottom-tracked); cannot convert to ground range")

    res = ground_res_m or choose_ground_resolution(float(np.median(spacing)))
    max_ground = math.sqrt(float(slant.max()) ** 2 - float(np.nanmin(altitude)) ** 2)
    grid = ground_range_grid(max_ground, res)
    n, m = len(pings), grid.size
    port_g = np.full((n, m), np.nan, dtype=np.float32)
    stbd_g = np.full((n, m), np.nan, dtype=np.float32)
    grazing = np.full((n, m), np.nan, dtype=np.float32)
    for i in range(n):
        if gap_rows[i]:
            continue
        port_g[i] = to_ground_range(port_fix.data[i], spacing[i], altitude[i], grid)
        stbd_g[i] = to_ground_range(stbd_fix.data[i], spacing[i], altitude[i], grid)
        grazing[i] = grazing_angle_deg(grid, altitude[i])
    if equalise:
        port_g = across_track_equalise(port_g)
        stbd_g = across_track_equalise(stbd_g)
    not_port = ~np.isfinite(port_g) | gap_rows[:, None]
    not_stbd = ~np.isfinite(stbd_g) | gap_rows[:, None]

    quality = compute_quality(
        times=np.array([p.time for p in pings], dtype="datetime64[ms]"),
        ping_numbers=np.array([p.ping_number for p in pings]),
        roll_deg=np.array([p.roll_deg for p in pings]),
        pitch_deg=np.array([p.pitch_deg for p in pings]),
        altitude_m=altitude,
        slant_range_m=slant,
        swath=combined,
        gap_rows=gap_rows,
        repaired_rows=repaired_rows,
        nav_missing=np.array([str(p.nav_source) == "missing" for p in pings]),
        thresholds=thresholds,
    )
    return NormalisedSwath(
        ground_res_m=res,
        ground_m=grid,
        port=port_g,
        stbd=stbd_g,
        grazing_deg=grazing,
        not_searched_port=not_port,
        not_searched_stbd=not_stbd,
        altitude_m=altitude,
        altitude_source=altitude_source,
        x=np.array([p.x for p in pings]),
        y=np.array([p.y for p in pings]),
        coord_kind=[str(p.coord_kind) for p in pings],
        nav_source=[str(p.nav_source) for p in pings],
        heading_deg=np.array([p.heading_deg for p in pings]),
        times=np.array([p.time for p in pings], dtype="datetime64[ms]"),
        quality=quality,
        sensor=record.sensor,
        provenance=record.provenance,
    )
```

- [ ] **Step 4: Run tests** — `uv run pytest tests/test_swath.py` → pass; full suite; ruff. If the "dropout" test shows q≠0 because the stripe flag also triggers, that is expected (Q multiplies); the assertion `q == 0` still holds because the dropout severity is 1.0.

- [ ] **Step 5: Commit**

```bash
git add src/netsight/normalise tests/test_swath.py
git commit -m "feat(normalise): compose QC and geometry into a normalised swath"
```

---

### Task 12: Licence register, dependency licence scan and governance docs (WP0)

**Files:**
- Create: `licences/datasets.yaml`, `src/netsight/governance/__init__.py` (empty), `src/netsight/governance/licences.py`, `tests/test_licences.py`, `docs/policy/impartiality.md`, `docs/policy/data_rights_clause.md`

**Interfaces:**
- Produces: `load_register(path) -> list[dict]`; `validate_register(entries) -> list[str]` (error messages; empty = valid); `commercial_training_allowed(entry) -> bool`; `licence_strings(dist_metadata) -> list[str]`; `forbidden_dependencies(dists) -> list[tuple[str, str]]`; `installed_distributions() -> list`; `default_register_path() -> Path`.

Rules: required keys `id, title, source_url, licence, licence_status, commercial_use, tier, files`; `tier ∈ {commercial, conditional, research_only}`; `licence_status ∈ {verified, conflict, unconfirmed}`; ids unique; `tier: commercial` requires `licence_status: verified` and `commercial_use: "yes"`; `tier: research_only` requires `commercial_use ∈ {"no", "unknown"}`. A dependency is forbidden when its licence metadata mentions AGPL or GPL but not LGPL.

- [ ] **Step 1: Create the register** — copy the fenced `yaml` block at the end of `docs/research/step1/datasets_detail.md` verbatim into `licences/datasets.yaml` (it starts with `# NetSight dataset manifest` and contains 9 entries: `bodine_substrate`, `ghostvision_crabpot`, `subpipe_mini2`, `catalan_sss_ssl`, `bath_mannequin`, `dfki_uxo`, `jncc_cefas_raw_sss`, `ai4shipwrecks`, `nksid`). Then append this entry:

```yaml
  - id: noaa_hsurveys
    title: "NOAA NOS hydrographic surveys (NCEI): side-scan mosaics, backscatter, Descriptive Reports"
    source_url: https://data.ngdc.noaa.gov/platforms/ocean/nos/coast/
    licence: CC0-1.0
    licence_status: verified
    commercial_use: "yes"
    tier: commercial
    files: []   # per-survey files fetched in Step 1B
    format: "GeoTIFF side-scan mosaics (1 m), multibeam backscatter TIFF, BAG, DR PDF"
    labels: "contact dispositions inside Descriptive Reports (expert disposition, not physical verification)"
    notes: "Not for navigation. Mosaics are 1 m/pixel: too coarse for small-object detection."
```

- [ ] **Step 2: Write the failing tests** — `tests/test_licences.py`:

```python
from netsight.governance.licences import (
    commercial_training_allowed,
    default_register_path,
    forbidden_dependencies,
    load_register,
    validate_register,
)

GOOD = {
    "id": "a", "title": "A", "source_url": "https://x", "licence": "CC-BY-4.0",
    "licence_status": "verified", "commercial_use": "yes", "tier": "commercial", "files": [],
}


def test_real_register_is_valid():
    entries = load_register(default_register_path())
    assert validate_register(entries) == []
    ids = {e["id"] for e in entries}
    assert {"bodine_substrate", "ai4shipwrecks", "noaa_hsurveys"} <= ids


def test_validation_rules():
    assert validate_register([GOOD]) == []
    assert any("missing" in e for e in validate_register([{"id": "b"}]))
    bad_tier = {**GOOD, "tier": "free"}
    assert any("tier" in e for e in validate_register([bad_tier]))
    unverified_commercial = {**GOOD, "licence_status": "unconfirmed"}
    assert any("commercial" in e for e in validate_register([unverified_commercial]))
    research_yes = {**GOOD, "tier": "research_only", "licence_status": "unconfirmed"}
    assert any("research_only" in e for e in validate_register([research_yes]))
    assert any("duplicate" in e for e in validate_register([GOOD, GOOD]))


def test_commercial_training_gate():
    assert commercial_training_allowed(GOOD)
    assert not commercial_training_allowed({**GOOD, "tier": "conditional"})


class FakeDist:
    def __init__(self, name, licence="", classifiers=(), expression=""):
        self.metadata = {
            "Name": name, "License": licence, "License-Expression": expression,
        }
        self._classifiers = list(classifiers)

    def __getattr__(self, item):
        raise AttributeError(item)


def test_forbidden_dependency_detection():
    dists = [
        FakeDist("ok", expression="MIT"),
        FakeDist("lgpl", licence="GNU Lesser General Public License v2.1"),
        FakeDist("bad", expression="AGPL-3.0-only"),
        FakeDist("gpl", licence="GPL-3.0-or-later"),
        FakeDist("bundled", expression="BSD-3-Clause", licence="x" * 300 + " GNU General Public License"),
        FakeDist("classifier", classifiers=["License :: OSI Approved :: GNU General Public License v3 (GPLv3)"]),
    ]
    names = {n for n, _ in forbidden_dependencies(dists)}
    assert names == {"bad", "gpl", "classifier"}
```

- [ ] **Step 3: Run to confirm failure** — `uv run pytest tests/test_licences.py` → FAIL.

- [ ] **Step 4: Implement** — `src/netsight/governance/licences.py`:

```python
"""Licence register validation and dependency licence scan (WP0)."""

from __future__ import annotations

import re
from importlib import metadata as importlib_metadata
from pathlib import Path

import yaml

from netsight.config import repo_root

REQUIRED_KEYS = ("id", "title", "source_url", "licence", "licence_status", "commercial_use", "tier", "files")
TIERS = {"commercial", "conditional", "research_only"}
STATUSES = {"verified", "conflict", "unconfirmed"}
_GPL = re.compile(r"\bA?GPL|GNU (Affero )?General Public", re.IGNORECASE)
_LGPL = re.compile(r"\bLGPL|Lesser General Public", re.IGNORECASE)


def default_register_path() -> Path:
    return repo_root() / "licences" / "datasets.yaml"


def load_register(path: str | Path) -> list[dict]:
    with open(path, encoding="utf-8") as f:
        doc = yaml.safe_load(f) or {}
    return list(doc.get("datasets", []))


def validate_register(entries: list[dict]) -> list[str]:
    errors: list[str] = []
    seen: set[str] = set()
    for i, e in enumerate(entries):
        label = e.get("id", f"entry {i}")
        missing = [k for k in REQUIRED_KEYS if k not in e]
        if missing:
            errors.append(f"{label}: missing keys {missing}")
            continue
        if e["id"] in seen:
            errors.append(f"{label}: duplicate id")
        seen.add(e["id"])
        if e["tier"] not in TIERS:
            errors.append(f"{label}: tier must be one of {sorted(TIERS)}")
        if e["licence_status"] not in STATUSES:
            errors.append(f"{label}: licence_status must be one of {sorted(STATUSES)}")
        commercial_use = str(e["commercial_use"]).lower()
        if e["tier"] == "commercial" and (e["licence_status"] != "verified" or commercial_use != "yes"):
            errors.append(f"{label}: tier commercial needs licence_status verified and commercial_use yes")
        if e["tier"] == "research_only" and commercial_use not in ("no", "unknown"):
            errors.append(f"{label}: tier research_only needs commercial_use no or unknown")
    return errors


def commercial_training_allowed(entry: dict) -> bool:
    return entry.get("tier") == "commercial"


MAX_SHORT_LICENCE_FIELD = 200


def licence_strings(dist) -> list[str]:
    """SPDX expression if present (authoritative); else a short License field; plus classifiers.

    Long License fields are full licence texts that often quote bundled third-party licences
    (numpy wheels mention the GPL'd gfortran runtime, which carries a linking exception), so they
    are not scanned.
    """
    md = dist.metadata
    expression = md.get("License-Expression") or ""
    licence = md.get("License") or ""
    out = [expression] if expression else ([licence] if len(licence) <= MAX_SHORT_LICENCE_FIELD else [])
    classifiers = getattr(dist, "_classifiers", None)
    if classifiers is None:
        classifiers = (md.get_all("Classifier") or []) if hasattr(md, "get_all") else []
    out += [c for c in classifiers if c.startswith("License ::")]
    return [s for s in out if s]


def forbidden_dependencies(dists) -> list[tuple[str, str]]:
    bad = []
    for d in dists:
        for text in licence_strings(d):
            if _GPL.search(text) and not _LGPL.search(text):
                bad.append((d.metadata.get("Name", "?"), text))
                break
    return bad


def installed_distributions() -> list:
    return list(importlib_metadata.distributions())
```

- [ ] **Step 5: Write the governance documents**

`docs/policy/impartiality.md`:

```markdown
# NetSight impartiality policy (draft v0.1)

NetSight grades other parties' sonar survey output. Its value depends on being independent of them.
This policy follows the impartiality principles of ISO/IEC 17020 (inspection bodies); NetSight is not
accredited, and this document does not claim it is.

1. **No conflicted ownership.** NetSight accepts no equity, exclusivity or revenue share from a sonar
   manufacturer, survey software vendor or survey contractor whose output it assesses.
2. **Preferred payer.** Assessments are preferably commissioned by the party carrying the risk
   (developer, port, insurer, warranty surveyor, UXO consultant). When a contractor pays for an
   assessment of its own work, the report states this on its first page.
3. **Sensor neutrality.** NetSight supports several sonar formats and makes no claim on a sensor it
   has not validated; unvalidated sensors get the "indicative" or "withdrawn" claim level.
4. **Disclosure.** Every report lists who commissioned it, any relationship with the surveyed party,
   and the versions of data, models and calibrators used.
5. **No outcome-based fees.** Fees never depend on whether an area is reported as well or poorly searched.
6. **Reviewer independence.** A person who acquired or processed the survey does not review
   NetSight's assessment of it.
7. **Records.** Assessment records (inputs, outputs, reviewer actions) are kept append-only and
   hash-chained so they can be audited.
8. **Review.** This policy is reviewed before the first paid pilot and at least yearly afterwards.
```

`docs/policy/data_rights_clause.md`:

```markdown
# Template: data-rights clause for pilots and data-for-validation agreements (draft v0.1)

Not legal advice. Have a lawyer adapt it per jurisdiction before use.

**Purpose.** The Client provides sonar survey data and the investigation outcomes of contacts
(diver, ROV, clearance or retrieval results). NetSight provides an independent assessment report.

1. **Licence to use.** The Client grants NetSight a non-exclusive, royalty-free licence to use the
   supplied data to produce the report and to validate and improve NetSight's methods.
2. **Outcome records.** The Client will share, where available, the final outcome for each
   assessed contact (real object / not real / not investigated) within [N] days of investigation.
3. **Anonymisation.** NetSight may retain an anonymised record of each contact (image chip, sonar
   and survey conditions, outcome) with location precision reduced to [X km] and all client,
   project and vessel identifiers removed.
4. **No redistribution.** NetSight will not publish or share raw survey data or identifiable
   records without written consent.
5. **Restricted data.** Data designated as defence, security-sensitive or restricted under
   applicable law are processed only on the Client's premises ("model-to-data") and never retained.
6. **Deletion.** On request, NetSight deletes the Client's raw data; anonymised outcome records
   under clause 3 may be retained.
7. **Liability.** The report is a probabilistic second-opinion assessment of the supplied data. It
   does not certify the absence of objects. Residual risk is managed by the duty holder under the
   project's ALARP process.
```

- [ ] **Step 6: Run tests** — `uv run pytest tests/test_licences.py` → pass; full suite; ruff.

- [ ] **Step 7: Commit**

```bash
git add licences src/netsight/governance tests/test_licences.py docs/policy
git commit -m "feat(governance): add dataset licence register, licence scan and policies"
```

---

### Task 13: Command-line interface

**Files:**
- Create: `src/netsight/cli.py`, `tests/test_cli.py`

**Interfaces:**
- Consumes: `open_survey`, `normalise_record`, `Mosaic`, governance functions.
- Produces: `main(argv: list[str] | None = None) -> int` with subcommands:
  - `inspect PATH` → prints a JSON summary (`format`, `sensor`, `n_pings`, `time_start`, `time_end`, `nav_source_counts`, `altitude_m` stats, `provenance`) or, for mosaics, `shape`, `pixel_size`, `pixel_units`, `valid_fraction`;
  - `normalise PATH --out DIR [--res M]` → writes `<stem>_swath.npz` and `<stem>_swath.json`, prints the JSON path;
  - `licences [--register PATH]` → prints register errors and forbidden installed dependencies; exit 1 if any.

- [ ] **Step 1: Write the failing tests** — `tests/test_cli.py`:

```python
import json

from helpers.synth_xtf import write_synthetic_xtf

from netsight.cli import main


def test_inspect_xtf(tmp_path, capsys):
    f = write_synthetic_xtf(tmp_path / "a.xtf", n_pings=4)
    assert main(["inspect", str(f)]) == 0
    out = json.loads(capsys.readouterr().out)
    assert out["format"] == "xtf" and out["n_pings"] == 4
    assert out["nav_source_counts"] == {"sensor": 4}


def test_normalise_writes_outputs(tmp_path, capsys):
    f = write_synthetic_xtf(tmp_path / "b.xtf", n_pings=5)
    assert main(["normalise", str(f), "--out", str(tmp_path / "out")]) == 0
    meta = json.loads((tmp_path / "out" / "b_swath.json").read_text())
    assert meta["n_pings"] == 5
    assert (tmp_path / "out" / "b_swath.npz").is_file()


def test_licences_check_passes_on_repo_register(capsys):
    assert main(["licences"]) == 0


def test_unsupported_format_returns_error(tmp_path, capsys):
    bad = tmp_path / "x.s7k"
    bad.write_bytes(b"")
    assert main(["inspect", str(bad)]) == 2
    assert "unsupported" in capsys.readouterr().err
```

- [ ] **Step 2: Run to confirm failure** — `uv run pytest tests/test_cli.py` → FAIL.

- [ ] **Step 3: Implement** — `src/netsight/cli.py`:

```python
"""NetSight command line: inspect, normalise, licences."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import numpy as np

from netsight import __version__
from netsight.governance.licences import (
    default_register_path,
    forbidden_dependencies,
    installed_distributions,
    load_register,
    validate_register,
)
from netsight.io import UnsupportedFormatError, open_survey
from netsight.io.mosaic import Mosaic
from netsight.normalise.swath import normalise_record


def _summary(obj) -> dict:
    if isinstance(obj, Mosaic):
        return {
            "format": "geotiff",
            "shape": list(obj.array.shape),
            "pixel_size": list(obj.pixel_size),
            "pixel_units": obj.pixel_units,
            "valid_fraction": obj.valid_fraction,
            "provenance": obj.provenance.to_dict(),
        }
    alt = np.array([p.altitude_m for p in obj.pings], dtype=float)
    finite = alt[np.isfinite(alt)]
    return {
        "format": obj.sensor.source_format,
        "sensor": obj.sensor.to_dict(),
        "n_pings": obj.n_pings,
        "time_start": str(obj.pings[0].time) if obj.pings else None,
        "time_end": str(obj.pings[-1].time) if obj.pings else None,
        "nav_source_counts": obj.nav_source_counts(),
        "altitude_m": {
            "min": float(finite.min()) if finite.size else None,
            "median": float(np.median(finite)) if finite.size else None,
            "max": float(finite.max()) if finite.size else None,
            "missing": int((~np.isfinite(alt)).sum()),
        },
        "provenance": obj.provenance.to_dict(),
    }


def _cmd_inspect(args) -> int:
    print(json.dumps(_summary(open_survey(args.path)), indent=2, default=str))
    return 0


def _cmd_normalise(args) -> int:
    record = open_survey(args.path)
    if isinstance(record, Mosaic):
        print("normalise needs per-ping data (XTF or JSF), not a mosaic", file=sys.stderr)
        return 2
    swath = normalise_record(record, ground_res_m=args.res)
    out_dir = Path(args.out)
    out_dir.mkdir(parents=True, exist_ok=True)
    stem = Path(args.path).stem
    swath.to_npz(out_dir / f"{stem}_swath.npz")
    meta_path = out_dir / f"{stem}_swath.json"
    meta_path.write_text(json.dumps(swath.metadata(), indent=2, default=str), encoding="utf-8")
    print(meta_path)
    return 0


def _cmd_licences(args) -> int:
    errors = validate_register(load_register(args.register))
    bad = forbidden_dependencies(installed_distributions())
    for e in errors:
        print(f"register: {e}")
    for name, text in bad:
        print(f"forbidden dependency licence: {name}: {text}")
    if not errors and not bad:
        print("licence register valid; no GPL/AGPL dependencies installed")
    return 1 if errors or bad else 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="netsight", description="NetSight sonar assurance tools")
    parser.add_argument("--version", action="version", version=f"netsight {__version__}")
    sub = parser.add_subparsers(dest="command", required=True)
    p_inspect = sub.add_parser("inspect", help="summarise a survey file")
    p_inspect.add_argument("path")
    p_inspect.set_defaults(func=_cmd_inspect)
    p_norm = sub.add_parser("normalise", help="QC and ground-range normalise a survey file")
    p_norm.add_argument("path")
    p_norm.add_argument("--out", required=True)
    p_norm.add_argument("--res", type=float, default=None, help="ground resolution in metres")
    p_norm.set_defaults(func=_cmd_normalise)
    p_lic = sub.add_parser("licences", help="validate the dataset licence register and dependencies")
    p_lic.add_argument("--register", default=str(default_register_path()))
    p_lic.set_defaults(func=_cmd_licences)
    args = parser.parse_args(argv)
    try:
        return args.func(args)
    except (UnsupportedFormatError, ValueError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
```

- [ ] **Step 4: Run tests** — `uv run pytest tests/test_cli.py` → pass; full suite; ruff; and a manual smoke run: `uv run netsight --version` prints `netsight 0.1.0`.

- [ ] **Step 5: Commit**

```bash
git add src/netsight/cli.py tests/test_cli.py
git commit -m "feat(cli): add inspect, normalise and licences commands"
```

---

## Self-review notes (plan author)

- Spec coverage (final.md §8.1, WP0, WP1): readers for XTF/JSF/GeoTIFF (Tasks 4–6), nav provenance and "position withdrawn" (Task 3, readers), bottom tracking + slant→ground (Task 7), gain + log (Task 8), dropout repair adopted from Varuna (Task 9), Q mask incl. HSSD towfish-height rule (Task 10), resolution tiers and geometry channels (Task 11), licence register, impartiality policy, data-rights template (Task 12), CLI (Task 13). GSF/KMALL adapters, the NOAA DR parser and dataset downloaders are deliberately in Step 1B.
- Type consistency: `Ping` field names are used identically in readers, tests and `normalise_record`; `NavSource` values are compared as strings in `NormalisedSwath` (`"missing"`, `"sensor"`).
- Known simplifications to revisit with real data in Step 1B: flat-seabed geometry; QC thresholds; JSF message-80 offsets 216–239 unused; per-ping sample counts must be equal to stack channels.
