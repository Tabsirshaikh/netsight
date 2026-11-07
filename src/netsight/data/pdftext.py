"""PDF text extraction with pypdf (BSD-3). PyMuPDF is AGPL and must not be used."""

from __future__ import annotations

import logging
from pathlib import Path

from pypdf import PdfReader


def extract_pages(path: str | Path) -> list[str]:
    """Text of each page, in order. Pages without extractable text give an empty string."""
    logger = logging.getLogger("pypdf")
    previous = logger.level
    logger.setLevel(logging.ERROR)  # pypdf warns about unsupported font encodings on NOAA DRs
    try:
        reader = PdfReader(str(path))
        return [page.extract_text() or "" for page in reader.pages]
    finally:
        logger.setLevel(previous)
