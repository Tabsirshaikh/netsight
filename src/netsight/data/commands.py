"""CLI subcommands for data: `netsight data fetch` and `netsight noaa fetch|contacts`."""

from __future__ import annotations

import csv
import sys
from pathlib import Path

from netsight.config import data_dir
from netsight.data.download import DownloadError, fetch_dataset_files
from netsight.data.noaa import fetch_survey
from netsight.data.noaa_dr import dr_summary, parse_contact_tables, write_contacts_csv
from netsight.data.noaa_features import parse_feature_items, write_features_csv
from netsight.data.pdftext import extract_pages
from netsight.governance.licences import default_register_path, load_register

SUMMARY_FIELDS = [
    "survey_id", "pages", "items_investigated", "contact_rows",
    "contact_list_in_separate", "sss_coverage_percent", "mentions_side_scan",
    "feature_items", "feature_items_decided",
]


def _cmd_data_fetch(args) -> int:
    entries = {e["id"]: e for e in load_register(args.register)}
    if args.dataset not in entries:
        raise ValueError(f"unknown dataset id {args.dataset!r}; known: {sorted(entries)}")
    for path in fetch_dataset_files(entries[args.dataset], data_dir(), names=args.file or None):
        print(path)
    return 0


def _cmd_noaa_fetch(args) -> int:
    parts = tuple(p.strip() for p in args.parts.split(",") if p.strip())
    for survey in args.surveys:
        for path in fetch_survey(survey, data_dir(), parts=parts):
            print(path)
    return 0


def _dr_pages(survey: str, fetch: bool) -> list[str]:
    dr_dir = data_dir() / "raw" / "noaa" / survey.upper() / "DR"
    pdfs = sorted(dr_dir.glob("*.pdf")) if dr_dir.is_dir() else []
    if not pdfs and fetch:
        fetch_survey(survey, data_dir(), parts=("DR",))
        pdfs = sorted(dr_dir.glob("*.pdf")) if dr_dir.is_dir() else []
    if not pdfs:
        raise ValueError(f"no Descriptive Report PDF in {dr_dir}")
    pages: list[str] = []
    for pdf in pdfs:
        pages.extend(extract_pages(pdf))
    return pages


def _cmd_noaa_contacts(args) -> int:
    """One bad survey is reported and skipped; outputs cover the rest; exit 2 if any failed."""
    rows, features, summaries, skipped = [], [], [], []
    for survey in args.surveys:
        sid = survey.upper()
        try:
            pages = _dr_pages(survey, fetch=not args.no_fetch)
        except (ValueError, OSError, DownloadError) as exc:
            print(f"{sid}: skipped: {exc}", file=sys.stderr)
            skipped.append(sid)
            continue
        survey_rows = parse_contact_tables(pages, sid)
        survey_features = parse_feature_items(pages, sid)
        decided = sum(1 for f in survey_features if f.is_real_object is not None)
        rows.extend(survey_rows)
        features.extend(survey_features)
        summary = dr_summary(pages, sid)
        summary["feature_items"] = len(survey_features)
        summary["feature_items_decided"] = decided
        summaries.append(summary)
        print(
            f"{sid}: {len(survey_rows)} contact rows, "
            f"{len(survey_features)} feature items ({decided} decided)"
        )
    print(write_contacts_csv(rows, args.out))
    if args.features:
        print(write_features_csv(features, args.features))
    if args.summary:
        summary_path = Path(args.summary)
        with open(summary_path, "w", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(f, fieldnames=SUMMARY_FIELDS)
            writer.writeheader()
            writer.writerows(summaries)
        print(summary_path)
    usable = sum(1 for s in summaries if s["contact_rows"] or s["feature_items_decided"])
    note = f" ({len(skipped)} skipped)" if skipped else ""
    print(f"surveys with usable ground truth: {usable} of {len(summaries)} processed{note}")
    return 2 if skipped else 0


def add_subcommands(sub) -> None:
    p_data = sub.add_parser("data", help="download registered datasets")
    data_sub = p_data.add_subparsers(dest="data_command", required=True)
    p_fetch = data_sub.add_parser("fetch", help="download a dataset from the licence register")
    p_fetch.add_argument("dataset", help="dataset id in licences/datasets.yaml")
    p_fetch.add_argument("--file", action="append", help="only this file (repeatable)")
    p_fetch.add_argument("--register", default=str(default_register_path()))
    p_fetch.set_defaults(func=_cmd_data_fetch)

    p_noaa = sub.add_parser("noaa", help="NOAA NCEI hydrographic surveys (CC0)")
    noaa_sub = p_noaa.add_subparsers(dest="noaa_command", required=True)
    p_nf = noaa_sub.add_parser("fetch", help="download survey folders (DR, TIFF, MBAB, BAG)")
    p_nf.add_argument("surveys", nargs="+")
    p_nf.add_argument("--parts", default="DR", help="comma-separated folders, e.g. DR,TIFF,MBAB")
    p_nf.set_defaults(func=_cmd_noaa_fetch)
    p_nc = noaa_sub.add_parser("contacts", help="build the contact-outcome table from DRs")
    p_nc.add_argument("surveys", nargs="+")
    p_nc.add_argument("--out", required=True, help="contact-outcome CSV to write")
    p_nc.add_argument("--features", help="optional CSV of Pydro Feature Report items")
    p_nc.add_argument("--summary", help="optional per-survey summary CSV")
    p_nc.add_argument("--no-fetch", action="store_true", help="use only local DR PDFs")
    p_nc.set_defaults(func=_cmd_noaa_contacts)
