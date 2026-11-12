import json

import numpy as np
import pytest
import rasterio
from helpers.synth_xtf import write_synthetic_xtf
from rasterio.transform import from_origin

from netsight import cli
from netsight.cli import main

GOOD_REGISTER = """\
datasets:
  - id: a
    title: A
    source_url: https://x
    licence: CC-BY-4.0
    licence_status: verified
    commercial_use: "yes"
    tier: commercial
    files: []
"""


class FakeDist:
    def __init__(self, name, expression=""):
        self.metadata = {"Name": name, "License": "", "License-Expression": expression}
        self._classifiers = []

    def __getattr__(self, item):
        raise AttributeError(item)


def write_tiff(path):
    data = np.full((10, 20), 120, dtype=np.uint8)
    data[:3, :4] = 0
    with rasterio.open(
        path,
        "w",
        driver="GTiff",
        width=20,
        height=10,
        count=1,
        dtype="uint8",
        crs="EPSG:32619",
        transform=from_origin(300000.0, 4500000.0, 1.0, 1.0),
        nodata=0,
    ) as dst:
        dst.write(data, 1)
    return path


def test_version(capsys):
    with pytest.raises(SystemExit) as exc:
        main(["--version"])
    assert exc.value.code == 0
    assert capsys.readouterr().out.startswith("netsight 0.1.0")


def test_inspect_xtf(tmp_path, capsys):
    f = write_synthetic_xtf(tmp_path / "a.xtf", n_pings=4)
    assert main(["inspect", str(f)]) == 0
    out = json.loads(capsys.readouterr().out)
    assert out["format"] == "xtf" and out["n_pings"] == 4
    assert out["nav_source_counts"] == {"sensor": 4}
    assert out["altitude_m"]["missing"] == 0


def test_inspect_mosaic_includes_extra_and_notes(tmp_path, capsys):
    f = write_tiff(tmp_path / "m.tif")
    assert main(["inspect", str(f)]) == 0
    out = json.loads(capsys.readouterr().out)
    assert out["format"] == "geotiff" and out["shape"] == [10, 20]
    assert out["pixel_units"] == "metre" and out["pixel_size"] == [1.0, 1.0]
    assert out["extra"] == {"band": 1, "band_count": 1, "nodata_source": "declared"}
    assert "unknown gain" in " ".join(out["provenance"]["notes"])


def test_normalise_writes_outputs(tmp_path, capsys):
    f = write_synthetic_xtf(tmp_path / "b.xtf", n_pings=5)
    assert main(["normalise", str(f), "--out", str(tmp_path / "out")]) == 0
    meta = json.loads((tmp_path / "out" / "b_swath.json").read_text())
    assert meta["n_pings"] == 5
    assert (tmp_path / "out" / "b_swath.npz").is_file()
    printed = capsys.readouterr().out.splitlines()
    assert str(tmp_path / "out" / "b_swath.json") in printed
    assert str(tmp_path / "out" / "b_swath.npz") in printed


def test_normalise_rejects_bad_resolution(tmp_path, capsys):
    f = write_synthetic_xtf(tmp_path / "b.xtf", n_pings=3)
    assert main(["normalise", str(f), "--out", str(tmp_path / "o"), "--res", "-1"]) == 2
    assert "ground_res_m" in capsys.readouterr().err


def test_normalise_rejects_mosaic(tmp_path, capsys):
    f = write_tiff(tmp_path / "m.tif")
    assert main(["normalise", str(f), "--out", str(tmp_path / "o")]) == 2
    assert "mosaic" in capsys.readouterr().err


def test_licences_check_passes_on_repo_register(capsys):
    assert main(["licences"]) == 0
    assert "no GPL/AGPL" in capsys.readouterr().out


def test_licences_warns_on_unknown_licence_without_failing(capsys):
    # pyproject has no licence field, so the project itself is reported as unknown.
    assert main(["licences"]) == 0
    assert "warning: no licence metadata: netsight" in capsys.readouterr().err


def test_licences_allowlist_option_silences_warning(tmp_path, capsys):
    allow = tmp_path / "allow.yaml"
    allow.write_text(
        "allowlist:\n  - {name: netsight, reason: this project, no licence field yet}\n",
        encoding="utf-8",
    )
    assert main(["licences", "--allowlist", str(allow)]) == 0
    assert "no licence metadata: netsight" not in capsys.readouterr().err


def test_licences_forbidden_dependency_exits_1(monkeypatch, capsys):
    monkeypatch.setattr(cli, "installed_distributions", lambda: [FakeDist("bad", "GPL-3.0-only")])
    assert main(["licences"]) == 1
    assert "forbidden dependency licence: bad" in capsys.readouterr().out


def test_licences_allowlist_exempts_forbidden_dependency(monkeypatch, tmp_path, capsys):
    monkeypatch.setattr(cli, "installed_distributions", lambda: [FakeDist("bad", "GPL-3.0-only")])
    allow = tmp_path / "allow.yaml"
    allow.write_text("allowlist:\n  - {name: bad, reason: separate tool only}\n", encoding="utf-8")
    assert main(["licences", "--allowlist", str(allow)]) == 0


def test_licences_register_errors_exit_1(tmp_path, capsys):
    reg = tmp_path / "reg.yaml"
    reg.write_text("datasets:\n  - {id: a}\n", encoding="utf-8")
    assert main(["licences", "--register", str(reg)]) == 1
    assert "register: a: missing keys" in capsys.readouterr().out


def test_licences_good_custom_register(tmp_path, capsys):
    reg = tmp_path / "reg.yaml"
    reg.write_text(GOOD_REGISTER, encoding="utf-8")
    assert main(["licences", "--register", str(reg)]) == 0


def test_licences_malformed_register_exits_2(tmp_path, capsys):
    reg = tmp_path / "reg.yaml"
    reg.write_text("datasets: 3\n", encoding="utf-8")
    assert main(["licences", "--register", str(reg)]) == 2
    assert "error:" in capsys.readouterr().err


def test_licences_malformed_allowlist_exits_2(tmp_path, capsys):
    allow = tmp_path / "allow.yaml"
    allow.write_text("allowlist:\n  - {name: x}\n", encoding="utf-8")
    assert main(["licences", "--allowlist", str(allow)]) == 2
    assert "reason" in capsys.readouterr().err


def test_unsupported_format_returns_error(tmp_path, capsys):
    bad = tmp_path / "x.s7k"
    bad.write_bytes(b"")
    assert main(["inspect", str(bad)]) == 2
    assert "unsupported" in capsys.readouterr().err


def test_xtf_format_error_returns_error(tmp_path, capsys):
    bad = tmp_path / "empty.xtf"
    bad.write_bytes(b"")
    assert main(["inspect", str(bad)]) == 2
    err = capsys.readouterr().err
    assert err.startswith("error: empty.xtf:") and "pyxtf" in err


def test_missing_file_exits_2_without_traceback(tmp_path, capsys):
    assert main(["inspect", str(tmp_path / "nope.xtf")]) == 2
    err = capsys.readouterr().err
    assert err.startswith("error:") and "Traceback" not in err


def test_junk_tif_exits_2_without_traceback(tmp_path, capsys):
    bad = tmp_path / "junk.tif"
    bad.write_bytes(b"this is not a tiff at all")
    assert main(["inspect", str(bad)]) == 2
    err = capsys.readouterr().err
    assert err.startswith("error:") and "Traceback" not in err


def test_missing_tif_exits_2(tmp_path, capsys):
    assert main(["inspect", str(tmp_path / "gone.tif")]) == 2
    assert capsys.readouterr().err.startswith("error:")


def test_pyxtf_index_refusal_exits_2(tmp_path, capsys):
    f = write_synthetic_xtf(tmp_path / "i.xtf", n_pings=2)
    (tmp_path / "i.pyxtf_idx").write_bytes(b"not trusted")
    assert main(["inspect", str(f)]) == 2
    err = capsys.readouterr().err
    assert err.startswith("error:") and "pyxtf_idx" in err and "Traceback" not in err


def test_debug_flag_reraises(tmp_path):
    f = write_synthetic_xtf(tmp_path / "b.xtf", n_pings=3)
    argv = ["normalise", str(f), "--out", str(tmp_path / "o"), "--res", "-1"]
    with pytest.raises(ValueError, match="ground_res_m"):
        main(["--debug", *argv])


def test_debug_env_reraises(tmp_path, monkeypatch):
    monkeypatch.setenv("NETSIGHT_DEBUG", "1")
    with pytest.raises(FileNotFoundError):
        main(["inspect", str(tmp_path / "nope.xtf")])


def test_debug_env_unset_or_zero_converts(tmp_path, monkeypatch):
    monkeypatch.setenv("NETSIGHT_DEBUG", "0")
    assert main(["inspect", str(tmp_path / "nope.xtf")]) == 2


def test_finite_json_nulls_non_finite_nested():
    payload = {"a": float("nan"), "b": [1.0, float("inf"), {"c": -float("inf"), "d": 2}], "e": "x"}
    assert cli._finite_json(payload) == {"a": None, "b": [1.0, None, {"c": None, "d": 2}], "e": "x"}


def test_inspect_json_is_strict(monkeypatch, capsys):
    monkeypatch.setattr(cli, "open_survey", lambda p: object())
    monkeypatch.setattr(cli, "_summary", lambda o: {"v": float("nan"), "w": [float("inf")]})
    assert main(["inspect", "whatever"]) == 0
    out = capsys.readouterr().out
    assert json.loads(out, parse_constant=lambda c: pytest.fail(c)) == {"v": None, "w": [None]}


def test_help_documents_exit_codes(capsys):
    with pytest.raises(SystemExit) as exc:
        main(["--help"])
    assert exc.value.code == 0
    out = capsys.readouterr().out
    assert "exit codes" in out.lower() and "licence findings" in out and "bad input" in out


def _local_dr(data_root, survey, pages):
    from helpers.tiny_pdf import write_text_pdf

    dr = data_root / "raw" / "noaa" / survey / "DR"
    dr.mkdir(parents=True)
    write_text_pdf(dr / f"{survey}_DR.pdf", pages)


def test_noaa_contacts_from_local_dr(tmp_path, monkeypatch, capsys):
    monkeypatch.setenv("NETSIGHT_DATA_DIR", str(tmp_path))
    row = "227-034244S H33-I-E 12.133 28-48-19.481 91-16-40.857 Disproved"
    _local_dr(tmp_path, "H99999", [["Number of items investigated 1"], [row]])
    _local_dr(tmp_path, "H99998", [["Nothing tabulated here."]])
    out, summ = tmp_path / "c.csv", tmp_path / "s.csv"
    rc = main(
        [
            "noaa",
            "contacts",
            "H99999",
            "h99998",
            "--no-fetch",
            "--out",
            str(out),
            "--summary",
            str(summ),
        ]
    )
    assert rc == 0
    text = capsys.readouterr().out
    assert "H99999: 1 contact rows" in text and "H99998: 0 contact rows" in text
    assert "surveys with usable ground truth: 1 of 2" in text
    lines = out.read_text(encoding="utf-8").splitlines()
    assert len(lines) == 2 and "227-034244S" in lines[1]
    summary = summ.read_text(encoding="utf-8").splitlines()
    assert summary[0].startswith("survey_id,pages,items_investigated")
    assert len(summary) == 3


def test_noaa_contacts_missing_dr_exits_2(tmp_path, monkeypatch, capsys):
    monkeypatch.setenv("NETSIGHT_DATA_DIR", str(tmp_path))
    rc = main(["noaa", "contacts", "H99999", "--no-fetch", "--out", str(tmp_path / "c.csv")])
    assert rc == 2
    assert "no Descriptive Report PDF" in capsys.readouterr().err


def test_noaa_fetch_rejects_bad_id(tmp_path, monkeypatch, capsys):
    monkeypatch.setenv("NETSIGHT_DATA_DIR", str(tmp_path))
    assert main(["noaa", "fetch", "X123"]) == 2
    assert "not an H-survey id" in capsys.readouterr().err


def test_data_fetch_unknown_id_exits_2(tmp_path, monkeypatch, capsys):
    monkeypatch.setenv("NETSIGHT_DATA_DIR", str(tmp_path))
    assert main(["data", "fetch", "no_such_dataset"]) == 2
    assert "unknown dataset id" in capsys.readouterr().err


def test_data_fetch_refuses_blocked_dataset(tmp_path, monkeypatch, capsys):
    monkeypatch.setenv("NETSIGHT_DATA_DIR", str(tmp_path))
    reg = tmp_path / "reg.yaml"
    reg.write_text(
        "datasets:\n  - id: b\n    tier: research_only\n    licence_status: unclear\n"
        "    availability: blocked\n    files: []\n",
        encoding="utf-8",
    )
    assert main(["data", "fetch", "b", "--register", str(reg)]) == 2
    assert "blocked" in capsys.readouterr().err


def test_noaa_contacts_writes_feature_items(tmp_path, monkeypatch, capsys):
    monkeypatch.setenv("NETSIGHT_DATA_DIR", str(tmp_path))
    item = [
        "1.1)  DTON 1",
        "DANGER TO NAVIGATION",
        "Survey Position:  30 09' 14.9\" N, 085 40' 08.2\" W",
        "Least Depth:  3.42 m",
        "Remarks:",
        "Rock found by MBES.",
    ]
    _local_dr(tmp_path, "H99997", [["Feature Report"], item])
    feats = tmp_path / "f.csv"
    rc = main(
        [
            "noaa",
            "contacts",
            "H99997",
            "--no-fetch",
            "--out",
            str(tmp_path / "c.csv"),
            "--features",
            str(feats),
            "--summary",
            str(tmp_path / "s.csv"),
        ]
    )
    assert rc == 0
    text = capsys.readouterr().out
    assert "H99997: 0 contact rows, 1 feature items (1 decided)" in text
    assert "surveys with usable ground truth: 1 of 1" in text
    lines = feats.read_text(encoding="utf-8").splitlines()
    assert len(lines) == 2 and "verified" in lines[1]
    summary = (tmp_path / "s.csv").read_text(encoding="utf-8")
    assert "feature_items,feature_items_decided" in summary.splitlines()[0]


def test_noaa_contacts_skips_failed_survey_and_still_writes(tmp_path, monkeypatch, capsys):
    monkeypatch.setenv("NETSIGHT_DATA_DIR", str(tmp_path))
    row = "227-034244S H33-I-E 12.133 28-48-19.481 91-16-40.857 Disproved"
    _local_dr(tmp_path, "H99999", [[row]])
    out = tmp_path / "c.csv"
    rc = main(["noaa", "contacts", "H99999", "H99996", "--no-fetch", "--out", str(out)])
    assert rc == 2
    captured = capsys.readouterr()
    assert "H99996: skipped:" in captured.err and "no Descriptive Report PDF" in captured.err
    assert "surveys with usable ground truth: 1 of 1 processed (1 skipped)" in captured.out
    assert "227-034244S" in out.read_text(encoding="utf-8")
