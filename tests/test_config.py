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
