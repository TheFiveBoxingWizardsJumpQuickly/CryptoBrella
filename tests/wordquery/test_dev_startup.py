import json
import os
import sqlite3
from pathlib import PureWindowsPath

import pytest
from wordquery_jp.sqlite_paths import absolute_read_only_uri, read_only_uri

from run_dev import configure_wordquery


def test_dev_dictionary_path_does_not_depend_on_working_directory(tmp_path, monkeypatch):
    monkeypatch.setattr(os, "environ", dict(os.environ))
    root = tmp_path / "project"
    config = root / "var/wordquery/dev.json"
    config.parent.mkdir(parents=True)
    config.write_text(json.dumps({
        "database": "data/lexicon.sqlite3",
        "release_mode": "reviewed",
        "load_mode": "lazy",
        "show_on_home": True,
        "enforce_freshness": False,
    }))
    for name in (
        "WORDQUERY_DB",
        "WORDQUERY_RELEASE_MODE",
        "WORDQUERY_LOAD_MODE",
        "WORDQUERY_SHOW_ON_HOME",
        "WORDQUERY_ENFORCE_FRESHNESS",
    ):
        monkeypatch.delenv(name, raising=False)
    monkeypatch.chdir(tmp_path)
    configure_wordquery(root)
    assert os.environ["WORDQUERY_DB"] == str(root / "data/lexicon.sqlite3")
    assert os.environ["WORDQUERY_RELEASE_MODE"] == "reviewed"
    assert os.environ["WORDQUERY_LOAD_MODE"] == "lazy"
    assert os.environ["WORDQUERY_SHOW_ON_HOME"] == "1"
    assert os.environ["WORDQUERY_ENFORCE_FRESHNESS"] == "0"
    monkeypatch.setenv("WORDQUERY_DB", "explicit.sqlite3")
    configure_wordquery(root, load_mode="disabled")
    assert os.environ["WORDQUERY_DB"] == "explicit.sqlite3"
    assert os.environ["WORDQUERY_LOAD_MODE"] == "disabled"
    assert os.environ["WORDQUERY_SHOW_ON_HOME"] == "0"


def test_sqlite_reserved_characters_and_read_only_mode(tmp_path):
    path = tmp_path / "辞書 #100%.sqlite3"
    with sqlite3.connect(path) as connection:
        connection.execute("CREATE TABLE example (value TEXT)")
    with sqlite3.connect(absolute_read_only_uri(path), uri=True) as connection:
        assert connection.execute("SELECT COUNT(*) FROM example").fetchone()[0] == 0
        with pytest.raises(sqlite3.OperationalError, match="readonly"):
            connection.execute("INSERT INTO example VALUES ('no')")


def test_unc_server_is_not_interpreted_as_sqlite_uri_authority():
    path = PureWindowsPath(r"\\wsl.localhost\Ubuntu\project\lexicon.sqlite3")
    assert read_only_uri(path) == (
        "file:%2F%2Fwsl.localhost/Ubuntu/project/lexicon.sqlite3?mode=ro&immutable=1"
    )
