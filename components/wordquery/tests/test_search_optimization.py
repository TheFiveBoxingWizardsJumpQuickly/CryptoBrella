from dataclasses import replace
from itertools import product

import pytest
import regex

from wordquery_jp.lexicon.builder import BuildConfig, build_database
from wordquery_jp.models import SearchOptions, SearchRecord
from wordquery_jp.repository import SearchSnapshot, _open_read_only, load_snapshot
from wordquery_jp.search import SearchService, SearchTimedOut
from wordquery_jp.search_budget import RegexMatchTimedOut, search_budget
from wordquery_jp.search_hints import SearchHints, regex_hints


def make_record(identifier, reading):
    return SearchRecord(identifier, reading, reading, reading, "", "general", "", 0)


@pytest.fixture
def search():
    readings = ["".join(chars) for n in range(1, 5) for chars in product("とうねこ", repeat=n)]
    rows = tuple(make_record(i, reading) for i, reading in enumerate(readings))
    return SearchService(SearchSnapshot(rows, {}, {}))


@pytest.mark.parametrize("pattern", [
    "^とう*$", "^とう.*$", "ねこ$", "ねこ", "^[あ-ん]{3}$", "^と?う$",
    "^と{0,2}う$", "^と{2,3}う+$", "^と{2}う{1,}$", "^と.*こ$", "とう*ねこ",
    "^.*$", "^$", "^とう|ねこ$", "(?m)^とう", "(?i)ねこ$",
    r"\Aとう.*\Z", "(?<=ね)こ", "(ねこ){e<=1}", "^とう*?$", "^とう++$",
    "^と[うこ]ね$", "^と[^う]ね$", "^と{0}こ$", "^と{201}$", "と(う|ね)こ",
    "(とう|ねこ)$", "(?:とう|ねこ)$", "^(とう|ねこ)$", "(こ|ねこ|こ)$",
    "(ねこ|こ)$", "(とう|)$", "(とう|ねこ)+$", "(?i)(とう|ねこ)$",
])
def test_regex_prefilters_preserve_counts_order_and_spans(search, pattern):
    options = SearchOptions(limit=17, sort_mode="kana")
    optimized = search.regex_search(pattern, options)
    baseline = search._search_compiled(regex.compile(pattern, regex.VERSION0), pattern, options)
    assert replace(optimized, duration_ms=0) == replace(baseline, duration_ms=0)


def test_unsupported_regex_has_no_hints():
    for pattern in ["^とう|ねこ$", "(?m)^ねこ$", r"^ね\w+$", "(ねこ){e<=1}"]:
        assert regex_hints(pattern) == SearchHints()
    assert regex_hints("^とう*$").prefix == "と"
    assert regex_hints("^とう.*$").prefix == "とう"
    assert regex_hints("ねこ$").suffix == "ねこ"


def test_suffix_index_returns_only_matching_readings(search):
    candidates = search._core_candidates("ねこ", "suffix")
    assert len(candidates) < len(search.snapshot.records)
    assert all(row.normalized_reading.endswith("ねこ") for row in candidates)


def test_literal_alternatives_use_union_of_suffix_candidates(search):
    hints = regex_hints("(こ|ねこ|こ)$")
    assert hints.suffixes == ("こ", "ねこ")
    rows = tuple(search._hint_candidates(hints))
    assert len(rows) == len({row.id for row in rows})
    assert {row.id for row in rows} == {
        row.id for row in search.snapshot.records if row.normalized_reading.endswith("こ")
    }


@pytest.mark.parametrize("sort_mode", ["kana", "commonness", "dictionary_priority"])
@pytest.mark.parametrize("query", ["?", "???", "?????"])
def test_length_only_pattern_preserves_results(search, sort_mode, query):
    from wordquery_jp.pattern import compile_reading_pattern
    plan = compile_reading_pattern(query)
    options = SearchOptions(sort_mode=sort_mode, limit=7)
    actual = search.pattern_search(query, options)
    expected = search._search_compiled(
        plan.compiled, plan.normalized_pattern, options,
        include_match_spans=False, condition_description=plan.description,
    )
    assert replace(actual, duration_ms=0) == replace(expected, duration_ms=0)


def test_length_only_pattern_does_not_invoke_regex(search, monkeypatch):
    def unexpected(*args):
        pytest.fail("Length-only pattern must not execute Regex per record")
    monkeypatch.setattr(search, "_regex_match", unexpected)
    assert search.pattern_search("???").total == 4 ** 3


def test_auxiliary_hints_preserve_results(tmp_path):
    from pathlib import Path
    fixtures = Path(__file__).parent / "fixtures"
    database = tmp_path / "lexicon.sqlite3"
    build_database(BuildConfig(output=database, sudachi=fixtures / "sudachi_raw.csv",
                               additions=fixtures / "manual_additions.tsv"))
    service = SearchService(load_snapshot(database))
    options = SearchOptions(include_proper=True, include_function=True, limit=3000)
    for pattern in ["^とう.*$", "う$", "^とう*$", "^[あ-ん]{5}$", "^と.*う$", "とう",
                    "(とう|ねこ)$"]:
        result = service.regex_search(pattern, options)
        baseline = service._search_compiled(
            regex.compile(pattern, regex.VERSION0), pattern, options,
            auxiliary_records=service._auxiliary_records(options),
        )
        assert replace(result, duration_ms=0) == replace(baseline, duration_ms=0)
    from wordquery_jp.pattern import compile_reading_pattern
    for query in ["???", "?????", "????????"]:
        plan = compile_reading_pattern(query)
        actual = service.pattern_search(query, options)
        baseline = service._search_compiled(
            plan.compiled, plan.normalized_pattern, options,
            auxiliary_records=service._auxiliary_records(options),
            include_match_spans=False, condition_description=plan.description,
        )
        assert replace(actual, duration_ms=0) == replace(baseline, duration_ms=0)


def test_auxiliary_regex_timeout_is_not_hidden_by_sqlite(tmp_path):
    import sqlite3
    from pathlib import Path
    fixtures = Path(__file__).parent / "fixtures"
    database = tmp_path / "lexicon.sqlite3"
    build_database(BuildConfig(output=database, sudachi=fixtures / "sudachi_raw.csv"))
    with sqlite3.connect(database) as connection:
        connection.execute("UPDATE words SET normalized_reading=? WHERE status='candidate'",
                           ("あ" * 4000 + "い",))
    service = SearchService(load_snapshot(database), regex_timeout_seconds=0.002)
    with pytest.raises(RegexMatchTimedOut):
        service.regex_search("(あ|ああ)+$", SearchOptions(
            include_proper=True, vocabulary_layers=("auxiliary",),
        ))


@pytest.mark.parametrize("sort_mode", ["kana", "commonness", "dictionary_priority"])
def test_top_k_matches_full_sort(search, sort_mode):
    from wordquery_jp.sorting import sort_key
    options = SearchOptions(sort_mode=sort_mode, limit=7)
    response = search.pattern_search("*", options)
    expected = sorted(search.snapshot.records, key=lambda row: (sort_key(row, sort_mode), row.id))
    assert response.results == tuple(expected[:7])
    assert response.total == len(expected)


def test_per_word_timeout_is_separate_from_search_deadline():
    row = make_record(1, "あ" * 4000 + "い")
    service = SearchService(SearchSnapshot((row,), {}, {}), regex_timeout_seconds=0.002)
    with pytest.raises(RegexMatchTimedOut, match="1語"):
        service.regex_search("(あ|ああ)+$")
    # A failed search must not leave its deadline in the next request.
    assert service.reading_search(row.reading[:1], "prefix").total == 1


@pytest.mark.parametrize("mode", ["regex", "pattern", "reading", "anagram"])
def test_all_search_modes_check_whole_operation_budget(search, monkeypatch, mode):
    from wordquery_jp import search_budget as budget_module
    ticks = iter(i * 0.01 for i in range(100000))
    monkeypatch.setattr(budget_module.time, "monotonic", lambda: next(ticks))
    search.timeout_seconds = 0.025
    # Even a filter excluding every row, or an anagram with no match, must check the deadline.
    with pytest.raises(SearchTimedOut):
        getattr(search, mode + "_search")("ねこ", options=SearchOptions(must_exclude="ね"))


def test_sqlite_progress_is_covered_by_search_budget(tmp_path, monkeypatch):
    from wordquery_jp import search_budget as budget_module
    ticks = iter(i * 0.01 for i in range(100000))
    database = tmp_path / "query.sqlite3"
    import sqlite3
    sqlite3.connect(database).close()

    class Probe:
        timeout_seconds = 0.05

        @search_budget
        def run(self):
            connection = _open_read_only(database)
            try:
                connection.execute(
                    "WITH RECURSIVE n(x) AS (VALUES(0) UNION ALL "
                    "SELECT x+1 FROM n WHERE x<10000000) SELECT sum(x) FROM n"
                ).fetchone()
            finally:
                connection.close()

    monkeypatch.setattr(budget_module.time, "monotonic", lambda: next(ticks))
    with pytest.raises(SearchTimedOut):
        Probe().run()
