import sqlite3
from itertools import product

import pytest

from wordquery_jp.lexicon.builder import BuildConfig, build_database
from wordquery_jp.models import SearchOptions, SearchRecord
from wordquery_jp.normalization import anagram_signature
from wordquery_jp.pattern import compile_reading_pattern
from wordquery_jp.repository import SearchSnapshot, load_snapshot
from wordquery_jp.search import SearchService
from wordquery_jp.search_index import build_search_index

PAIRS = list(zip("ぁぃぅぇぉゃゅょっゎゕゖ", "あいうえおやゆよつわかけ", strict=True))


def service_for(readings):
    rows = tuple(SearchRecord(i, reading, reading, reading, anagram_signature(reading),
                              "general", "名詞", 10) for i, reading in enumerate(readings))
    return SearchService(SearchSnapshot(rows, {}, {}))


@pytest.mark.parametrize(("small", "full"), PAIRS)
def test_all_pairs_match_in_both_directions_without_changing_results(small, full):
    readings = {"け" + small + "ん", "け" + full + "ん"}
    service = service_for(sorted(readings))
    for char in (small, full):
        query = "け" + char + "ん"
        assert service.reading_search(query, "exact").total == 1
        response = service.reading_search(query, "exact", SearchOptions(fold_small_kana=True))
        assert {row.reading for row in response.results} == readings
        assert response.match_spans == ((0, 3), (0, 3))
        assert service.pattern_search(query, SearchOptions(fold_small_kana=True)).total == 2


@pytest.mark.parametrize(("pattern", "expected"), [
    ("きゃ?と", {"きゃっと", "きやつと"}),
    ("き[ゃ]?と", {"きゃっと", "きやつと"}),
    ("き[!ゃ]*", {"きよつと"}),
    ("*っと", {"きゃっと", "きやつと", "きよつと"}),
    ("きゃ*", {"きゃっと", "きやつと"}),
])
def test_patterns_and_negated_sets(pattern, expected):
    service = service_for(["きゃっと", "きやつと", "きよつと"])
    result = service.pattern_search(pattern, SearchOptions(fold_small_kana=True))
    assert {row.reading for row in result.results} == expected


@pytest.mark.parametrize(("match_type", "query", "span"), [
    ("contains", "ヤツ", (1, 3)), ("prefix", "キヤ", (0, 2)),
    ("suffix", "ツト", (2, 4)), ("exact", "ｷﾔﾂﾄ", (0, 4)),
])
def test_reading_match_types_preserve_offsets(match_type, query, span):
    service = service_for(["きゃっと"])
    result = service.reading_search(query, match_type, SearchOptions(fold_small_kana=True))
    assert result.total == 1
    assert result.match_spans == (span,)


def test_filters_and_counts_use_the_intended_reading():
    service = service_for(["きゃっと", "きやつと", "きゃっど", "きゃっとー"])
    options = SearchOptions(fold_small_kana=True, must_include="やつ", must_exclude="ど",
                            reading_length=3, length_unit="mora")
    assert [row.reading for row in service.pattern_search("*", options).results] == ["きゃっと"]
    assert service.pattern_search("*", SearchOptions(fold_small_kana=True,
                                                    must_exclude="やつ")).total == 0
    for query in ["きやつど", "きやつとー", "きやつと"]:
        result = service.reading_search(query, "exact", SearchOptions(fold_small_kana=True))
        assert result.total >= 1
    assert service.reading_search("きやつとお", "exact",
                                  SearchOptions(fold_small_kana=True)).total == 0


@pytest.mark.parametrize("indexed", [False, True])
def test_auxiliary_equivalence_and_filters_do_not_lose_candidates(tmp_path, indexed):
    additions = tmp_path / "words.tsv"
    additions.write_text(
        "surface\treading\tcategory\tpos\tpriority\treason\treference\n"
        "東京\tとうきょう\tproper\t名詞\t50\ttest\ttest\n",
        encoding="utf-8",
    )
    database = tmp_path / "lexicon.sqlite3"
    build_database(BuildConfig(output=database, additions=additions))
    with sqlite3.connect(database) as connection:
        connection.execute("UPDATE words SET status = 'candidate'")
    if indexed:
        build_search_index(database)
    service = SearchService(load_snapshot(database))
    options = SearchOptions(include_proper=True, fold_small_kana=True, must_include="きよ")
    for match_type, query in [("exact", "とうきよう"), ("contains", "きよ"),
                              ("prefix", "とうきよ"), ("suffix", "きよう")]:
        assert service.reading_search(query, match_type, options).total == 1
    for pattern in ["とうきよう", "とうきよ*", "*きよう", "とう[き]?う"]:
        assert service.pattern_search(pattern, options).total == 1
    excluded = SearchOptions(include_proper=True, fold_small_kana=True, must_exclude="きよ")
    assert service.pattern_search("*", excluded).total == 0


def test_prefilters_match_exhaustive_scan_for_equivalent_patterns():
    service = service_for(["".join(chars) for chars in product("つっやゃか", repeat=3)])
    options = SearchOptions(fold_small_kana=True, limit=1000)
    for pattern in ["つ*", "*っ", "かつ?", "?やか", "[!っ]??", "[つや]*", "???", "つやか"]:
        plan = compile_reading_pattern(pattern, fold_small_kana=True)
        expected = {row.id for row in service.snapshot.records
                    if plan.compiled.fullmatch(row.normalized_reading)}
        actual = service.pattern_search(pattern, options)
        assert {row.id for row in actual.results} == expected
