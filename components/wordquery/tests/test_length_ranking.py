"""Length ranking must agree with an exhaustive, unoptimized search."""

import sqlite3
from dataclasses import replace

import pytest

from wordquery_jp.lexicon.schema import SCHEMA
from wordquery_jp.models import SearchOptions, TagFilter
from wordquery_jp.pattern import compile_reading_pattern
from wordquery_jp.repository import load_snapshot
from wordquery_jp.search import SearchService, SearchTimedOut
from wordquery_jp.search_index import build_search_index


@pytest.fixture
def service(tmp_path):
    database = tmp_path / "lexicon.sqlite3"
    with sqlite3.connect(database) as connection:
        connection.executescript(SCHEMA)
        connection.execute("INSERT INTO metadata VALUES ('schema_version', '3')")
        for identifier in range(1, 121):
            reading = ("あいう", "ねねこ", "あぃう", "あああ", "あ\nう", "あいうえ")[identifier % 6]
            category = ("general", "proper", "function")[identifier % 3]
            connection.execute(
                "INSERT INTO words VALUES (?,?,?,?,?,?,?,?,?)",
                (identifier, f"語{identifier}", reading, reading, "", category, "",
                 identifier % 5, "accepted" if identifier % 7 == 0 else "candidate"),
            )
            for source in ("fixture-a", "fixture-b") if identifier % 4 == 0 else ("fixture-a",):
                connection.execute(
                    "INSERT INTO provenance(word_id, source, source_entry_id) VALUES (?,?,?)",
                    (identifier, source, str(identifier)),
                )
            if identifier % 2 == 0:
                connection.execute(
                    "INSERT INTO word_tags VALUES (?,?,?,?,?,?,?,?)",
                    (identifier, "domain", "test", "fixture-a", str(identifier), "fixture", "", ""),
                )
    build_search_index(database)
    return SearchService(load_snapshot(database))


def exhaustive(service, options, pattern="???"):
    plan = compile_reading_pattern(pattern, fold_small_kana=options.fold_small_kana)
    return service._search_compiled(
        plan.compiled, plan.normalized_pattern, options,
        auxiliary_records=service._auxiliary_records(options),
        include_match_spans=False, condition_description=plan.description,
    )


@pytest.mark.parametrize("sort", ["kana", "commonness", "dictionary_priority"])
@pytest.mark.parametrize("limit", [1, 7, 3000])
@pytest.mark.parametrize("include_function", [False, True])
@pytest.mark.parametrize("deprioritize", [(), ("core",), ("auxiliary",)])
def test_length_ranking_preserves_complete_response(service, sort, limit,
                                                    include_function, deprioritize):
    options = SearchOptions(
        include_proper=True, include_function=include_function, sort_mode=sort,
        limit=limit, deprioritize_vocabulary_layers=deprioritize,
    )
    actual = service.pattern_search("???", options)
    expected = exhaustive(service, options)
    assert replace(actual, duration_ms=0) == replace(expected, duration_ms=0)


@pytest.mark.parametrize("options", [
    SearchOptions(include_proper=True, must_include="ね"),
    SearchOptions(include_proper=True, must_exclude="ね"),
    SearchOptions(include_proper=True, must_include="い", fold_small_kana=True),
    SearchOptions(include_proper=True, reading_length=2, length_unit="mora"),
    SearchOptions(include_proper=True, reading_length=3, length_unit="surface"),
    SearchOptions(include_proper=True, reading_length=3),
    SearchOptions(include_proper=True, tag_filters=(TagFilter("domain", "test"),)),
    SearchOptions(include_proper=True, deprioritize_tag_filters=(TagFilter("domain", "test"),)),
    SearchOptions(include_proper=True, vocabulary_layers=("core",)),
    SearchOptions(include_proper=True, vocabulary_layers=("auxiliary",), limit=3),
    SearchOptions(include_proper=True, fold_small_kana=True, limit=3),
    SearchOptions(include_proper=False),
])
def test_length_ranking_respects_filters_and_layers(service, options):
    assert replace(service.pattern_search("???", options), duration_ms=0) == replace(
        exhaustive(service, options), duration_ms=0,
    )


def test_length_ranking_without_matches(service):
    options = SearchOptions(include_proper=True, vocabulary_layers=("auxiliary",))
    actual = service.pattern_search("?" * 8, options)
    assert actual.total == 0
    assert actual.results == ()
    assert not actual.truncated


def test_length_ranking_sql_obeys_search_deadline(service, monkeypatch):
    from wordquery_jp import repository, search_budget

    current_time = 0.0
    original_open = repository._open_read_only

    def open_with_expiring_budget(path):
        connection = original_open(path)

        def expire():
            nonlocal current_time
            current_time = 10.0
            return search_budget.expired()

        connection.set_progress_handler(expire, 1)
        return connection

    monkeypatch.setattr(search_budget.time, "monotonic", lambda: current_time)
    monkeypatch.setattr(repository, "_open_read_only", open_with_expiring_budget)
    with pytest.raises(SearchTimedOut):
        service.pattern_search("???", SearchOptions(include_proper=True))
