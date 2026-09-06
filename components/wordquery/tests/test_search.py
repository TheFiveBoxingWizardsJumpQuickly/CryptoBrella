from dataclasses import replace
from pathlib import Path

import pytest

from wordquery_jp.models import (
    CrosswordCell,
    SearchOptions,
    SearchRecord,
    SearchRequest,
    TagEvidence,
    TagFilter,
    VocabularyTag,
)
from wordquery_jp.normalization import anagram_signature
from wordquery_jp.pattern import compile_reading_pattern
from wordquery_jp.repository import SearchSnapshot
from wordquery_jp.search import QueryValidationError, SearchService, SearchTimedOut
from wordquery_jp.sorting import sort_key

FIXTURES = Path(__file__).parent / "fixtures"


def record(
    identifier,
    surface,
    reading,
    category="general",
    priority=10,
    multiple_sources=False,
):
    return SearchRecord(
        id=identifier,
        surface=surface,
        reading=reading,
        normalized_reading=reading,
        signature=anagram_signature(reading),
        category=category,
        pos="",
        priority=priority,
        multiple_sources=multiple_sources,
    )


@pytest.fixture
def service():
    records = (
        record(1, "猫", "ねこ", priority=90),
        record(2, "こね", "こね", priority=20),
        record(3, "東京", "とうきょう", "proper", 80),
        record(4, "の", "の", "function", 80),
    )
    grouped = {}
    for item in records:
        grouped.setdefault(item.signature, []).append(item)
    snapshot = SearchSnapshot(
        records=records,
        anagrams={key: tuple(value) for key, value in grouped.items()},
        metadata={},
    )
    return SearchService(snapshot)


def test_regex_is_partial_and_normalizes_katakana(service):
    response = service.regex_search("ネ")
    assert [result.surface for result in response.results] == ["猫", "こね"]
    assert response.match_spans == ((0, 1), (1, 2))


def test_regex_anchors_request_full_match(service):
    assert service.regex_search("^ね$").total == 0
    assert service.regex_search("^ねこ$").total == 1


@pytest.mark.parametrize(
    "pattern", ["?ねこ", "*ねこ", "???", "[こや]ねこ", "[!や]ねこ", "?*?", "ね*こ", "*ねこ?"]
)
def test_pattern_length_and_suffix_prefilters_preserve_full_regex_results(pattern):
    rows = tuple(record(i, reading, reading) for i, reading in enumerate(
        ["ねこ", "こねこ", "やまねこ", "やねこ", "ねこねこ", "ねこあ", "こ", "いぬ"]
    ))
    service = SearchService(SearchSnapshot(records=rows, anagrams={}, metadata={}))
    expected = service.regex_search(compile_reading_pattern(pattern).compiled.pattern)
    actual = service.pattern_search(pattern)
    assert actual.results == expected.results
    assert actual.total == expected.total


def test_leading_wildcard_limits_candidates_by_length_and_suffix():
    rows = tuple(record(i, reading, reading) for i, reading in enumerate(
        ["ねこ", "こねこ", "やまねこ", "やねこ", "いぬあ"]
    ))
    service = SearchService(SearchSnapshot(records=rows, anagrams={}, metadata={}))
    candidates = service._pattern_core_candidates(compile_reading_pattern("?ねこ"))
    assert {row.normalized_reading for row in candidates} == {"こねこ", "やねこ"}


@pytest.mark.parametrize(
    ("mode", "query", "expected_scanned"),
    [("exact", "ねこ", 1), ("prefix", "ね", 1), ("exact", "なし", 0),
     ("pattern", "ね?", 1)],
)
def test_literal_prefix_queries_skip_unrelated_core_records(
    service, monkeypatch, mode, query, expected_scanned
):
    scanned = []
    original = service._filtered

    def counted(records, *args, **kwargs):
        records = tuple(records)
        scanned.extend(records)
        return original(records, *args, **kwargs)

    monkeypatch.setattr(service, "_filtered", counted)
    response = (
        service.pattern_search(query) if mode == "pattern"
        else service.reading_search(query, mode)
    )
    assert len(scanned) == expected_scanned
    assert response.total == expected_scanned


@pytest.mark.parametrize("match_type", ["contains", "prefix", "suffix", "exact"])
def test_literal_search_preserves_regex_reference_results_and_spans(service, match_type):
    for query in ("ね", "ねこ", "こ", "なし"):
        pattern = {
            "contains": query, "prefix": "^" + query,
            "suffix": query + "$", "exact": "^" + query + "$",
        }[match_type]
        expected = service.regex_search(pattern)
        actual = service.reading_search(query, match_type)
        assert actual.results == expected.results
        assert actual.match_spans == expected.match_spans
        assert actual.total == expected.total


def test_plain_reading_match_types_do_not_interpret_regex(service):
    assert [item.surface for item in service.reading_search("ね", "contains").results] == [
        "猫",
        "こね",
    ]
    assert [item.surface for item in service.reading_search("ね", "prefix").results] == ["猫"]
    assert [item.surface for item in service.reading_search("ね", "suffix").results] == ["こね"]
    assert [item.surface for item in service.reading_search("ねこ", "exact").results] == ["猫"]
    with pytest.raises(QueryValidationError):
        service.reading_search(".", "contains")


def test_reading_length_filter(service):
    options = SearchOptions(include_proper=True, reading_length=5)
    response = service.reading_search("う", "contains", options)

    assert [item.surface for item in response.results] == ["東京"]

    length_only = service.reading_search("", options=SearchOptions(reading_length=2))
    assert [item.surface for item in length_only.results] == ["猫", "こね"]


def test_length_units_and_grid_profiles_are_applied():
    item = record(1, "キャット", "きゃっと")
    snapshot = SearchSnapshot(
        records=(item,),
        anagrams={item.signature: (item,)},
        metadata={},
    )
    service = SearchService(snapshot)

    assert service.reading_search(
        "", options=SearchOptions(reading_length=4, length_unit="kana")
    ).total == 1
    assert service.reading_search(
        "", options=SearchOptions(reading_length=3, length_unit="mora")
    ).total == 1
    assert service.reading_search(
        "", options=SearchOptions(reading_length=4, length_unit="surface")
    ).total == 1
    assert service.reading_search(
        "",
        options=SearchOptions(
            reading_length=2,
            length_unit="grid",
            grid_profile="combine_all_small",
        ),
    ).total == 1


def test_versioned_request_dispatches_through_search_service(service):
    response = service.execute(
        SearchRequest(
            version=1,
            mode="reading",
            query="う",
            length=4,
            length_unit="mora",
            include_proper=True,
        )
    )

    assert [item.surface for item in response.results] == ["東京"]


def test_crossword_request_dispatches_structured_cells_and_common_filters(service):
    response = service.execute(
        SearchRequest(
            version=6,
            mode="crossword",
            query="",
            length=5,
            length_unit="grid",
            grid_cells=(
                CrosswordCell("exact", ("と",)),
                CrosswordCell("exact", ("う",)),
                CrosswordCell("unknown"),
                CrosswordCell("include", ("ょ", "お")),
                CrosswordCell("exclude", ("ん",)),
            ),
            include_proper=True,
            must_include="きょ",
        )
    )

    assert [item.surface for item in response.results] == ["東京"]
    assert response.match_spans == (None,)
    assert response.condition_description == (
        "クロスワード5マス: 1マス目 「と」 / 2マス目 「う」 / "
        "3マス目 不明 / 4マス目 「ょ・お」の候補 / 5マス目 「ん」以外"
    )


def test_reading_include_and_exclude_filters(service):
    included = service.reading_search("ね", options=SearchOptions(must_include="こ"))
    excluded = service.reading_search("ね", options=SearchOptions(must_exclude="こ"))

    assert [item.surface for item in included.results] == ["猫", "こね"]
    assert excluded.total == 0


def test_invalid_regex(service):
    with pytest.raises(QueryValidationError):
        service.regex_search("[")

    with pytest.raises(QueryValidationError):
        service.reading_search("ね", "unknown")


def test_category_filters_are_opt_in(service):
    assert service.regex_search(".").total == 2
    options = SearchOptions(include_proper=True, include_function=True)
    assert service.regex_search(".", options).total == 4


def test_core_layer_and_tags_can_be_filtered_without_a_database():
    tagged = replace(
        record(1, "送りレジスタ", "おくりれじすた"),
        tags=(
            VocabularyTag(
                "domain",
                "computing",
                (TagEvidence("jmdict", "1", "computing"),),
            ),
        ),
    )
    untagged = record(2, "送り仮名", "おくりがな")
    snapshot = SearchSnapshot(
        records=(tagged, untagged),
        anagrams={},
        metadata={},
    )
    search = SearchService(snapshot)

    response = search.reading_search(
        "",
        options=SearchOptions(tag_filters=(TagFilter("domain", "computing"),)),
    )

    assert [item.surface for item in response.results] == ["送りレジスタ"]
    assert response.results[0].tags[0].value == "computing"


def test_sort_modes_are_explicit_and_commonness_explains_its_signals():
    high_priority = record(1, "甲", "こう", priority=90)
    multi_source = record(2, "乙", "おつ", priority=85, multiple_sources=True)
    snapshot = SearchSnapshot(
        records=(high_priority, multi_source),
        anagrams={},
        metadata={},
    )
    service = SearchService(snapshot)

    commonness = service.reading_search(
        "", options=SearchOptions(reading_length=2, sort_mode="commonness")
    )
    assert [item.surface for item in commonness.results] == ["乙", "甲"]
    assert commonness.sort_scores[0] == 95
    assert commonness.sort_reasons[0] == (
        "辞書優先度 85",
        "複数出典で確認 +10",
    )

    dictionary_priority = service.reading_search(
        "", options=SearchOptions(reading_length=2, sort_mode="dictionary_priority")
    )
    assert [item.surface for item in dictionary_priority.results] == ["甲", "乙"]

    kana = service.reading_search(
        "", options=SearchOptions(reading_length=2, sort_mode="kana")
    )
    assert [item.surface for item in kana.results] == ["乙", "甲"]
    assert kana.sort_scores[0] is None
    assert kana.sort_reasons[0] == ("正規化した読み順",)


def test_commonness_does_not_penalize_category_or_candidate_status():
    auxiliary_proper = replace(
        record(1, "固有候補", "ああ", category="proper", priority=50),
        status="candidate",
    )
    accepted_general = record(2, "一般語", "いい", priority=50)

    assert sorted(
        (accepted_general, auxiliary_proper),
        key=lambda item: sort_key(item, "commonness"),
    ) == [auxiliary_proper, accepted_general]


@pytest.mark.parametrize("sort_mode", ["commonness", "dictionary_priority", "kana"])
def test_deprioritize_tag_is_an_independent_ranking_group(sort_mode):
    tagged_high = replace(
        record(1, "専門語", "ああ", priority=100),
        tags=(
            VocabularyTag(
                "domain",
                "computing",
                (TagEvidence("jmdict", "1", "computing"),),
            ),
        ),
    )
    ordinary_low = record(2, "一般語", "んん", priority=1)
    snapshot = SearchSnapshot(
        records=(tagged_high, ordinary_low),
        anagrams={},
        metadata={},
    )
    search = SearchService(snapshot)

    response = search.regex_search(
        ".",
        SearchOptions(
            limit=1,
            sort_mode=sort_mode,
            deprioritize_tag_filters=(TagFilter("domain", "computing"),),
        ),
    )

    assert response.total == 2
    assert [item.surface for item in response.results] == ["一般語"]
    assert response.deprioritize_reasons == ((),)


def test_deprioritize_auxiliary_keeps_candidate_but_places_it_last():
    auxiliary_high = replace(
        record(1, "補助語", "ああ", category="proper", priority=100),
        status="candidate",
    )
    core_low = record(2, "常駐語", "んん", priority=1)
    snapshot = SearchSnapshot(
        records=(auxiliary_high, core_low),
        anagrams={},
        metadata={},
    )
    search = SearchService(snapshot)

    response = search.regex_search(
        ".",
        SearchOptions(
            include_proper=True,
            deprioritize_vocabulary_layers=("auxiliary",),
        ),
    )

    assert [item.surface for item in response.results] == ["常駐語", "補助語"]
    assert response.deprioritize_reasons == ((), ("補助候補",))


def test_anagram_applies_deprioritize_group_before_selected_sort():
    tagged_high = replace(
        record(1, "相", "あい", priority=100),
        tags=(
            VocabularyTag(
                "usage",
                "rare",
                (TagEvidence("jmdict", "1", "rare"),),
            ),
        ),
    )
    ordinary_low = record(2, "愛", "いあ", priority=1)
    snapshot = SearchSnapshot(
        records=(tagged_high, ordinary_low),
        anagrams={tagged_high.signature: (tagged_high, ordinary_low)},
        metadata={},
    )
    search = SearchService(snapshot)

    response = search.anagram_search(
        "あい",
        SearchOptions(
            limit=1,
            sort_mode="commonness",
            deprioritize_tag_filters=(TagFilter("usage", "rare"),),
        ),
    )

    assert response.total == 2
    assert [item.surface for item in response.results] == ["愛"]


def test_exact_anagram_uses_all_characters(service):
    response = service.anagram_search("ねこ")
    assert {result.surface for result in response.results} == {"猫", "こね"}
    assert service.anagram_search("ね").total == 0

    kana = service.anagram_search("ねこ", SearchOptions(sort_mode="kana"))
    assert [result.surface for result in kana.results] == ["こね", "猫"]


def test_query_length_limit(service):
    with pytest.raises(QueryValidationError, match="入力は200文字までです。"):
        service.regex_search("あ" * 201)


def test_catastrophic_pattern_times_out():
    long_record = record(1, "長い", "あ" * 4000 + "い")
    snapshot = SearchSnapshot(
        records=(long_record,),
        anagrams={long_record.signature: (long_record,)},
        metadata={},
    )
    search = SearchService(snapshot, timeout_seconds=0.001, max_query_length=200)
    with pytest.raises(
        SearchTimedOut,
        match="検索処理が制限時間（0.001秒）を超えたため、中断しました。",
    ):
        search.regex_search("(あ|ああ)+$")


def test_auxiliary_candidates_are_queried_only_when_proper_nouns_are_enabled(
    tmp_path,
):
    from wordquery_jp.lexicon.builder import BuildConfig, build_database
    from wordquery_jp.repository import load_snapshot

    database = tmp_path / "auxiliary.sqlite3"
    build_database(
        BuildConfig(
            output=database,
            additions=tmp_path / "no-additions.tsv",
            sudachi=FIXTURES / "sudachi_raw.csv",
            source_manifest=tmp_path / "none.toml",
        )
    )
    search = SearchService(load_snapshot(database))

    assert search.reading_search("とうきょう", "exact").total == 0
    options = SearchOptions(include_proper=True)
    response = search.reading_search("とうきょう", "exact", options)
    assert [item.surface for item in response.results] == ["東京"]
    assert response.results[0].status == "candidate"
    assert search.reading_search("とう", "prefix", options).total == 1
    assert search.reading_search("きょう", "contains", options).total == 1
    assert search.reading_search("う", "suffix", options).total == 1
    assert search.reading_search(
        "", options=SearchOptions(include_proper=True, reading_length=5)
    ).total == 1
    assert [item.surface for item in search.regex_search("^とうきょう$", options).results] == [
        "東京"
    ]
    assert [item.surface for item in search.anagram_search("とうきょう", options).results] == [
        "東京"
    ]
    assert [
        item.surface for item in search.pattern_search("とう?ょう", options).results
    ] == ["東京"]
    assert [
        item.surface
        for item in search.crossword_search(
            (
                CrosswordCell("exact", ("と",)),
                CrosswordCell("exact", ("う",)),
                CrosswordCell("unknown"),
                CrosswordCell("exact", ("ょ",)),
                CrosswordCell("exact", ("う",)),
            ),
            "separate",
            options,
        ).results
    ] == ["東京"]


def test_auxiliary_layer_and_tags_are_independent_filters(tmp_path):
    from wordquery_jp.lexicon.builder import BuildConfig, build_database
    from wordquery_jp.repository import load_snapshot

    database = tmp_path / "auxiliary-tags.sqlite3"
    build_database(
        BuildConfig(
            output=database,
            additions=tmp_path / "no-additions.tsv",
            sudachi=FIXTURES / "sudachi_raw.csv",
            source_manifest=tmp_path / "none.toml",
        )
    )
    search = SearchService(load_snapshot(database))

    core_only = SearchOptions(
        include_proper=True,
        vocabulary_layers=("core",),
        tag_filters=(TagFilter("proper_type", "place"),),
    )
    auxiliary_only = replace(core_only, vocabulary_layers=("auxiliary",))
    wrong_tag = replace(
        auxiliary_only,
        tag_filters=(TagFilter("proper_type", "person"),),
    )
    incompatible_tags = replace(
        auxiliary_only,
        tag_filters=(
            TagFilter("proper_type", "place"),
            TagFilter("proper_type", "person"),
        ),
    )

    assert search.reading_search("とうきょう", "exact", core_only).total == 0
    assert [
        item.surface
        for item in search.reading_search("とうきょう", "exact", auxiliary_only).results
    ] == ["東京"]
    assert search.reading_search("とうきょう", "exact", wrong_tag).total == 0
    assert search.reading_search("とうきょう", "exact", incompatible_tags).total == 0
