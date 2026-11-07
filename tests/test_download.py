import hashlib
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

import pytest

from netsight.data.download import DownloadError, download, fetch_dataset_files, tier_dir
from netsight.data.noaa import list_folder, survey_folder_url

PAYLOAD = bytes(range(256)) * 400  # 102,400 bytes


class RangeHandler(BaseHTTPRequestHandler):
    files: dict[str, bytes] = {}
    # path -> number of upcoming requests to sabotage, and how: "short" sends a short body with
    # a matching Content-Length (clean early close), "cut" promises the full length but stops.
    faults: dict[str, list] = {}
    no_range: set[str] = set()  # paths served as if the server ignored Range headers
    range_requests = 0

    def do_GET(self):  # noqa: N802
        body = self.files.get(self.path)
        if body is None:
            self.send_response(404)
            self.end_headers()
            return
        rng = self.headers.get("Range")
        if rng and self.path not in self.no_range:
            first, _, last = rng.split("=")[1].partition("-")
            start = int(first)
            end = int(last) if last else len(body) - 1  # inclusive, as in HTTP
            self.send_response(206)
            self.send_header("Content-Range", f"bytes {start}-{end}/{len(body)}")
            body = body[start : end + 1]
            RangeHandler.range_requests += 1
        else:
            self.send_response(200)
        fault = self.faults.get(self.path)
        if fault and fault[0] > 0:
            fault[0] -= 1
            part = body[: len(body) // 3]
            self.send_header("Content-Length", str(len(part) if fault[1] == "short" else len(body)))
            self.end_headers()
            self.wfile.write(part)
            self.close_connection = True
            return
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def log_message(self, *args):
        pass


@pytest.fixture()
def server():
    RangeHandler.faults = {}
    RangeHandler.no_range = set()
    RangeHandler.range_requests = 0
    RangeHandler.files = {
        "/data.bin": PAYLOAD,
        "/listing/": (
            b'<html><body><a href="?C=N">Name</a> <a href="../">Parent</a>'
            b'<a href="BAG/">BAG/</a> 2020-05-21 14:52 - '
            b'<a href="H12243.pdf">H12243.pdf</a> 2012-03-26 16:29 1.8M '
            b'<a href="H12243_SSSAB_1m_455kHz_1of2.tiff">x</a> 2020-05-21 14:52 16M '
            b"</body></html>"
        ),
    }
    srv = ThreadingHTTPServer(("127.0.0.1", 0), RangeHandler)
    thread = threading.Thread(target=srv.serve_forever, daemon=True)
    thread.start()
    yield f"http://127.0.0.1:{srv.server_address[1]}"
    srv.shutdown()
    srv.server_close()


def test_download_verifies_size_and_md5(server, tmp_path):
    md5 = hashlib.md5(PAYLOAD).hexdigest()
    out = download(f"{server}/data.bin", tmp_path / "d.bin", size=len(PAYLOAD), md5=md5)
    assert out.read_bytes() == PAYLOAD
    assert not (tmp_path / "d.bin.part").exists()


def test_download_resumes_partial_file(server, tmp_path):
    (tmp_path / "d.bin.part").write_bytes(PAYLOAD[:40_000])
    out = download(f"{server}/data.bin", tmp_path / "d.bin", size=len(PAYLOAD))
    assert out.read_bytes() == PAYLOAD


def test_download_skips_existing_verified_file(server, tmp_path):
    target = tmp_path / "d.bin"
    target.write_bytes(PAYLOAD)
    md5 = hashlib.md5(PAYLOAD).hexdigest()
    assert download("http://127.0.0.1:9/never", target, size=len(PAYLOAD), md5=md5) == target


def test_download_rejects_bad_checksum_and_keeps_no_file(server, tmp_path):
    with pytest.raises(DownloadError, match="md5"):
        download(f"{server}/data.bin", tmp_path / "d.bin", md5="0" * 32)
    assert not (tmp_path / "d.bin").exists()


@pytest.mark.parametrize("mode", ["short", "cut"])
def test_download_resumes_after_dropped_connections(server, tmp_path, mode):
    # what happened with Zenodo: the server closed early on a large file
    RangeHandler.faults = {"/data.bin": [2, mode]}
    md5 = hashlib.md5(PAYLOAD).hexdigest()
    out = download(
        f"{server}/data.bin", tmp_path / "d.bin", size=len(PAYLOAD), md5=md5, retry_wait=0
    )
    assert out.read_bytes() == PAYLOAD
    RangeHandler.faults = {}


def test_download_keeps_partial_when_retries_run_out(server, tmp_path):
    RangeHandler.faults = {"/data.bin": [10, "short"]}
    with pytest.raises(DownloadError, match="incomplete"):
        download(f"{server}/data.bin", tmp_path / "d.bin", size=len(PAYLOAD), attempts=2,
                 retry_wait=0)
    part = tmp_path / "d.bin.part"
    assert part.exists() and 0 < part.stat().st_size < len(PAYLOAD)
    assert part.read_bytes() == PAYLOAD[: part.stat().st_size]  # resumable, not corrupt
    RangeHandler.faults = {}


def test_download_http_error(server, tmp_path):
    with pytest.raises(DownloadError):
        download(f"{server}/missing.bin", tmp_path / "m.bin")


def test_tier_dir_separates_research_only(tmp_path):
    assert tier_dir(tmp_path, {"id": "a", "tier": "commercial"}) == tmp_path / "raw" / "a"
    assert tier_dir(tmp_path, {"id": "b", "tier": "research_only"}) == (
        tmp_path / "raw" / "research_only" / "b"
    )


def test_fetch_dataset_files_refuses_blocked_entries(tmp_path):
    entry = {"id": "x", "tier": "commercial", "availability": "blocked", "files": []}
    with pytest.raises(DownloadError, match="blocked"):
        fetch_dataset_files(entry, tmp_path)


def test_fetch_dataset_files_downloads_selected_file(server, tmp_path):
    entry = {
        "id": "demo",
        "tier": "commercial",
        "files": [
            {"name": "data.bin", "url": f"{server}/data.bin", "size": len(PAYLOAD), "md5": None},
            {"name": "other.bin", "url": f"{server}/other.bin", "size": 1, "md5": None},
        ],
    }
    paths = fetch_dataset_files(entry, tmp_path, names=["data.bin"])
    assert paths == [tmp_path / "raw" / "demo" / "data.bin"]
    assert paths[0].read_bytes() == PAYLOAD


def test_survey_folder_url():
    assert survey_folder_url("H12333") == (
        "https://data.ngdc.noaa.gov/platforms/ocean/nos/coast/H12001-H14000/H12333/"
    )
    assert survey_folder_url("h11322").endswith("/H10001-H12000/H11322/")
    with pytest.raises(ValueError):
        survey_folder_url("X123")


def test_list_folder_parses_listing(server):
    entries = list_folder(f"{server}/listing/")
    names = [e["name"] for e in entries]
    assert names == ["BAG/", "H12243.pdf", "H12243_SSSAB_1m_455kHz_1of2.tiff"]
    assert entries[0]["is_dir"] is True and entries[1]["is_dir"] is False


# --- multi-connection downloads (servers that cap speed per connection, e.g. Zenodo) ------


@pytest.fixture(autouse=True)
def small_segments(monkeypatch):
    import netsight.data.download as dl

    monkeypatch.setattr(dl, "MIN_SEGMENT", 1024)  # let the 100 KB test file split


def test_segmented_download_assembles_the_file(server, tmp_path):
    md5 = hashlib.md5(PAYLOAD).hexdigest()
    out = download(f"{server}/data.bin", tmp_path / "d.bin", size=len(PAYLOAD), md5=md5,
                   connections=4, retry_wait=0)
    assert out.read_bytes() == PAYLOAD
    assert RangeHandler.range_requests >= 4
    assert not list(tmp_path.glob("d.bin.part*"))  # segments cleaned up


def test_segmented_download_continues_an_existing_partial(server, tmp_path):
    (tmp_path / "d.bin.part").write_bytes(PAYLOAD[:30_000])
    out = download(f"{server}/data.bin", tmp_path / "d.bin", size=len(PAYLOAD),
                   connections=3, retry_wait=0)
    assert out.read_bytes() == PAYLOAD


def test_segmented_download_resumes_a_dropped_segment(server, tmp_path):
    RangeHandler.faults = {"/data.bin": [3, "short"]}
    out = download(f"{server}/data.bin", tmp_path / "d.bin", size=len(PAYLOAD),
                   md5=hashlib.md5(PAYLOAD).hexdigest(), connections=4, retry_wait=0)
    assert out.read_bytes() == PAYLOAD


def test_segmented_download_falls_back_when_range_is_ignored(server, tmp_path):
    RangeHandler.no_range = {"/data.bin"}
    out = download(f"{server}/data.bin", tmp_path / "d.bin", size=len(PAYLOAD),
                   connections=4, retry_wait=0)
    assert out.read_bytes() == PAYLOAD


def test_segmented_download_needs_a_known_size(server, tmp_path):
    with pytest.raises(ValueError):
        download(f"{server}/data.bin", tmp_path / "d.bin", connections=4)


def test_segments_keep_going_while_each_attempt_makes_progress(server, tmp_path):
    # every request is cut short, but each one delivers new bytes: a slow, flaky link
    RangeHandler.faults = {"/data.bin": [40, "short"]}
    out = download(f"{server}/data.bin", tmp_path / "d.bin", size=len(PAYLOAD),
                   md5=hashlib.md5(PAYLOAD).hexdigest(), connections=2, attempts=3,
                   retry_wait=0)
    assert out.read_bytes() == PAYLOAD
