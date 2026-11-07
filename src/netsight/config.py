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
