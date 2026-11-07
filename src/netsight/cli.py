"""NetSight command line: inspect, normalise, licences."""

from __future__ import annotations

import argparse
import json
import math
import os
import sys
from pathlib import Path

import numpy as np

from netsight import __version__
from netsight.governance.licences import (
    default_allowlist_path,
    default_register_path,
    forbidden_dependencies,
    installed_distributions,
    load_allowlist,
    load_register,
    unknown_licence_dependencies,
    validate_register,
)
from netsight.io import UnsupportedFormatError, open_survey
from netsight.io.mosaic import Mosaic
from netsight.io.xtf import UnsafeIndexFileError
from netsight.normalise.swath import normalise_record

EXIT_EPILOG = """exit codes:
  0  ok
  1  licence findings (register errors or forbidden dependencies)
  2  bad input or processing error (message on stderr; use --debug for a traceback)
"""


def _finite_json(obj):
    """Return obj with every non-finite float (nested in dicts/lists/tuples) replaced by None."""
    if isinstance(obj, float):
        return obj if math.isfinite(obj) else None
    if isinstance(obj, dict):
        return {k: _finite_json(v) for k, v in obj.items()}
    if isinstance(obj, (list, tuple)):
        return [_finite_json(v) for v in obj]
    return obj


def _dumps(obj) -> str:
    return json.dumps(_finite_json(obj), indent=2, default=str, allow_nan=False)


def _summary(obj) -> dict:
    if isinstance(obj, Mosaic):
        return {
            "format": "geotiff",
            "shape": list(obj.array.shape),
            "pixel_size": list(obj.pixel_size),
            "pixel_units": obj.pixel_units,
            "valid_fraction": obj.valid_fraction,
            "extra": obj.extra,
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
    print(_dumps(_summary(open_survey(args.path))))
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
    npz_path = swath.to_npz(out_dir / f"{stem}_swath.npz")
    meta_path = out_dir / f"{stem}_swath.json"
    meta_path.write_text(_dumps(swath.metadata()), encoding="utf-8")
    print(meta_path)
    print(npz_path)
    return 0


def _cmd_licences(args) -> int:
    errors = validate_register(load_register(args.register))
    allowlist = load_allowlist(args.allowlist)
    dists = installed_distributions()
    bad = forbidden_dependencies(dists, allowlist)
    unknown = unknown_licence_dependencies(dists, allowlist)
    for e in errors:
        print(f"register: {e}")
    for name, text in bad:
        print(f"forbidden dependency licence: {name}: {text}")
    for name in unknown:
        print(f"warning: no licence metadata: {name}", file=sys.stderr)
    if not errors and not bad:
        print("licence register valid; no GPL/AGPL dependencies installed")
    return 1 if errors or bad else 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="netsight",
        description="NetSight sonar assurance tools",
        epilog=EXIT_EPILOG,
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument(
        "--debug",
        action="store_true",
        help="show full tracebacks instead of error messages (or set NETSIGHT_DEBUG=1)",
    )
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
    p_lic = sub.add_parser(
        "licences", help="validate the dataset licence register and dependency licences"
    )
    p_lic.add_argument("--register", default=str(default_register_path()))
    p_lic.add_argument(
        "--allowlist",
        default=str(default_allowlist_path()),
        help="reviewed dependencies exempt from the licence scan",
    )
    p_lic.set_defaults(func=_cmd_licences)
    args = parser.parse_args(argv)
    debug = args.debug or os.environ.get("NETSIGHT_DEBUG", "") not in ("", "0")
    try:
        return args.func(args)
    except (UnsupportedFormatError, ValueError, OSError, UnsafeIndexFileError) as exc:
        if debug:
            raise
        print(f"error: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
