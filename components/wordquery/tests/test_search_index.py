import json
import sqlite3
from dataclasses import replace
from pathlib import Path

import pytest

from wordquery_jp.lexicon.builder import BuildConfig, build_database
from wordquery_jp.models import SearchOptions, TagFilter
from wordquery_jp.repository import load_snapshot
from wordquery_jp.search import SearchService
from wordquery_jp.search_index import build_search_index, file_hash, index_path


@pytest.fixture
def database(tmp_path):
    fixtures = Path(__file__).parent / "fixtures"
    path = tmp_path / "lexicon.sqlite3"
    build_database(BuildConfig(output=path, sudachi=fixtures / "sudachi_raw.csv",
                               additions=fixtures / "manual_additions.tsv"))
    return path


@pytest.mark.parametrize("tags", [(), (TagFilter("proper_type", "place"),)])
def test_index_preserves_all_search_results_and_original_database(database, tags):
    original_hash = file_hash(database)
    old = SearchService(load_snapshot(database))
    built = build_search_index(database)
    assert built["status"] == "built"
    new = SearchService(load_snapshot(database))
    assert new.snapshot.auxiliary.search_index == index_path(database)
    options = SearchOptions(include_proper=True, include_function=True, tag_filters=tags,
                            limit=3000, sort_mode="commonness")
    for mode, queries in [
        ("pattern", ["*", "とう*", "*う", "?ねこ", "???", "?????", "と*う"]),
        ("regex", ["^とう.*$", "う$", "(とう|ねこ)$", "^[あ-ん]{3}$"]),
        ("anagram", ["とうきょう", "ねこ"]),
        ("reading", ["ねこ", "とう"]),
    ]:
        for query in queries:
            before = getattr(old, mode + "_search")(query, options=options)
            after = getattr(new, mode + "_search")(query, options=options)
            assert replace(before, duration_ms=0) == replace(after, duration_ms=0)
    for match_type in ["exact", "prefix", "suffix"]:
        before = old.reading_search("う", match_type, options)
        after = new.reading_search("う", match_type, options)
        assert replace(before, duration_ms=0) == replace(after, duration_ms=0)
    assert file_hash(database) == original_hash
    assert build_search_index(database)["status"] == "already_exists"


def test_wrong_dictionary_index_is_rejected(database):
    build_search_index(database)
    with sqlite3.connect(database) as connection:
        connection.execute("UPDATE words SET priority=priority+1")
    with pytest.raises(ValueError, match="does not match"):
        load_snapshot(database)


def test_declared_missing_index_blocks_loading(database):
    (database.parent / "manifest.json").write_text(json.dumps({
        "search_index": {"filename": index_path(database).name, "sha256": "missing"},
    }))
    with pytest.raises(ValueError, match="missing"):
        load_snapshot(database)


def test_suffix_query_uses_index(database):
    build_search_index(database)
    with sqlite3.connect(index_path(database)) as connection:
        plan = connection.execute("EXPLAIN QUERY PLAN SELECT id FROM words "
                                  "INDEXED BY auxiliary_suffix WHERE reversed_reading>=? "
                                  "AND reversed_reading<? AND reading_length=?",
                                  ("こね", "こね\U0010ffff", 3)).fetchall()
    assert any("SEARCH words USING INDEX auxiliary_suffix" in row[3] for row in plan)


def test_failed_build_is_never_published(database, monkeypatch):
    from wordquery_jp import search_index
    def fail(*a, **kw):
        raise ValueError("validation failed")
    monkeypatch.setattr(search_index, "validate_search_index", fail)
    with pytest.raises(ValueError):
        build_search_index(database)
    assert not index_path(database).exists()
    assert not list(database.parent.glob(".search-index-*"))
