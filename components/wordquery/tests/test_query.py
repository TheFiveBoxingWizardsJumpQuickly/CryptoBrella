import pytest

from wordquery_jp.models import CrosswordCell, TagFilter
from wordquery_jp.query import (
    RequestValidationError,
    parse_search_request,
    serialize_search_request,
)


def parse(payload, *, legacy_kind=None):
    return parse_search_request(
        payload,
        max_length=200,
        limit=100,
        legacy_kind=legacy_kind,
    )


def test_canonical_reading_request_is_validated_and_normalized():
    request = parse(
        {
            "version": 1,
            "mode": "reading",
            "query": "ネ",
            "match_type": "prefix",
            "length": "3",
            "length_unit": "mora",
            "include_proper": True,
            "must_include": "コ",
        }
    )

    assert request.version == 1
    assert request.mode == "reading"
    assert request.match_type == "prefix"
    assert request.length == 3
    assert request.length_unit == "mora"
    assert request.must_include == "こ"
    assert request.include_proper is True
    assert request.limit == 100
    assert request.sort_mode == "dictionary_priority"


def test_version_2_defaults_to_commonness_and_serializes_sort_mode():
    request = parse(
        {
            "version": 2,
            "mode": "reading",
            "query": "ネ",
            "sort": "kana",
        }
    )

    assert request.sort_mode == "kana"
    assert serialize_search_request(request)["sort"] == "kana"

    defaulted = parse({"version": 2, "mode": "reading", "query": "ネ"})
    assert defaulted.sort_mode == "commonness"


def test_version_3_separates_vocabulary_layers_and_tag_filters():
    request = parse(
        {
            "version": 3,
            "mode": "reading",
            "query": "ね",
            "include_proper": True,
            "vocabulary_layers": ["core", "auxiliary", "core"],
            "tag_filters": [
                {"axis": " proper_type ", "value": " place "},
                {"axis": "domain", "value": "computing"},
            ],
        }
    )

    assert request.vocabulary_layers == ("core", "auxiliary")
    assert request.tag_filters == (
        TagFilter("proper_type", "place"),
        TagFilter("domain", "computing"),
    )
    assert serialize_search_request(request) == {
        "version": 3,
        "mode": "reading",
        "query": "ね",
        "match_type": "contains",
        "length_unit": "kana",
        "grid_profile": "separate",
        "include_proper": True,
        "include_function": False,
        "limit": 100,
        "sort": "commonness",
        "vocabulary_layers": ["core", "auxiliary"],
        "tag_filters": [
            {"axis": "proper_type", "value": "place"},
            {"axis": "domain", "value": "computing"},
        ],
    }

    defaulted = parse({"version": 3, "mode": "reading", "query": "ね"})
    assert defaulted.vocabulary_layers == ("core",)


def test_version_4_deprioritizes_layers_and_tags_without_filtering():
    request = parse(
        {
            "version": 4,
            "mode": "reading",
            "query": "ね",
            "include_proper": True,
            "vocabulary_layers": ["core", "auxiliary"],
            "deprioritize_vocabulary_layers": ["auxiliary"],
            "deprioritize_tag_filters": [
                {"axis": " domain ", "value": " computing "},
            ],
        }
    )

    assert request.deprioritize_vocabulary_layers == ("auxiliary",)
    assert request.deprioritize_tag_filters == (TagFilter("domain", "computing"),)
    assert serialize_search_request(request)["deprioritize_vocabulary_layers"] == [
        "auxiliary"
    ]
    assert serialize_search_request(request)["deprioritize_tag_filters"] == [
        {"axis": "domain", "value": "computing"}
    ]


def test_version_5_adds_plain_pattern_without_regex_match_type():
    request = parse(
        {
            "version": 5,
            "mode": "pattern",
            "query": "ネ?[こご]",
            "sort": "commonness",
        }
    )

    assert request.mode == "pattern"
    assert request.query == "ネ?[こご]"
    assert request.match_type == "contains"
    assert serialize_search_request(request) == {
        "version": 5,
        "mode": "pattern",
        "query": "ネ?[こご]",
        "length_unit": "kana",
        "grid_profile": "separate",
        "include_proper": False,
        "include_function": False,
        "limit": 100,
        "sort": "commonness",
        "vocabulary_layers": ["core"],
    }

    with pytest.raises(RequestValidationError, match="version 5"):
        parse({"version": 4, "mode": "pattern", "query": "ね?"})
    with pytest.raises(RequestValidationError, match="一致の指定"):
        parse(
            {
                "version": 5,
                "mode": "pattern",
                "query": "ね?",
                "match_type": "exact",
            }
        )


def test_version_6_adds_structured_crossword_cells_and_derives_grid_length():
    request = parse(
        {
            "version": 6,
            "mode": "crossword",
            "grid_profile": "combine_phonetic",
            "grid_cells": [
                {"kind": "exact", "values": ["キャ"]},
                {"kind": "unknown"},
                {"kind": "include", "values": ["ト", "ど", "ト"]},
                {"kind": "exclude", "values": ["ン"]},
            ],
            "sort": "commonness",
        }
    )

    assert request.mode == "crossword"
    assert request.query == ""
    assert request.length == 4
    assert request.length_unit == "grid"
    assert request.grid_cells == (
        CrosswordCell("exact", ("きゃ",)),
        CrosswordCell("unknown"),
        CrosswordCell("include", ("と", "ど")),
        CrosswordCell("exclude", ("ん",)),
    )
    assert serialize_search_request(request) == {
        "version": 6,
        "mode": "crossword",
        "query": "",
        "grid_cells": [
            {"kind": "exact", "values": ["きゃ"]},
            {"kind": "unknown"},
            {"kind": "include", "values": ["と", "ど"]},
            {"kind": "exclude", "values": ["ん"]},
        ],
        "length": 4,
        "length_unit": "grid",
        "grid_profile": "combine_phonetic",
        "include_proper": False,
        "include_function": False,
        "limit": 100,
        "sort": "commonness",
        "vocabulary_layers": ["core"],
    }


@pytest.mark.parametrize(
    ("payload", "message"),
    [
        (
            {"version": 5, "mode": "crossword", "grid_cells": [{"kind": "unknown"}]},
            "version 6",
        ),
        ({"version": 6, "mode": "crossword", "grid_cells": []}, "1から200件"),
        (
            {
                "version": 6,
                "mode": "crossword",
                "grid_cells": [{"kind": "unknown", "values": ["ね"]}],
            },
            "文字を指定できません",
        ),
        (
            {
                "version": 6,
                "mode": "crossword",
                "grid_cells": [{"kind": "exact", "values": ["きゃ"]}],
            },
            "1マス",
        ),
        (
            {
                "version": 6,
                "mode": "crossword",
                "query": "ね",
                "grid_cells": [{"kind": "unknown"}],
            },
            "queryではなく",
        ),
        (
            {
                "version": 6,
                "mode": "crossword",
                "length": 2,
                "grid_cells": [{"kind": "unknown"}],
            },
            "マス数",
        ),
        (
            {
                "version": 6,
                "mode": "reading",
                "query": "ね",
                "grid_cells": [{"kind": "unknown"}],
            },
            "クロスワード検索モード",
        ),
    ],
)
def test_invalid_crossword_cells_are_rejected(payload, message):
    with pytest.raises(RequestValidationError, match=message):
        parse(payload)


@pytest.mark.parametrize(("mode", "match_type"), [("regex", "regex"), ("anagram", "contains")])
def test_canonical_non_reading_modes_have_fixed_execution(mode, match_type):
    request = parse({"version": 1, "mode": mode, "query": "ねこ"})

    assert request.mode == mode
    assert request.match_type == match_type


def test_grid_profile_requires_grid_length_unit():
    request = parse(
        {
            "version": 1,
            "mode": "reading",
            "query": "",
            "length": 3,
            "length_unit": "grid",
            "grid_profile": "combine_phonetic",
        }
    )
    assert request.grid_profile == "combine_phonetic"

    with pytest.raises(RequestValidationError, match="文字数の数え方が「マス数」"):
        parse(
            {
                "version": 1,
                "mode": "reading",
                "query": "",
                "length_unit": "mora",
                "grid_profile": "combine_phonetic",
            }
        )


@pytest.mark.parametrize(
    ("payload", "message"),
    [
        ({"mode": "reading", "query": "ね"}, "version"),
        ({"version": 7, "mode": "reading", "query": "ね"}, "対応していない"),
        ({"version": 1, "mode": "unknown", "query": "ね"}, "モード"),
        (
            {"version": 1, "mode": "reading", "query": "ね", "sort": "commonness"},
            "version 2",
        ),
        (
            {"version": 2, "mode": "reading", "query": "ね", "sort": "recommended"},
            "並べ替え",
        ),
        (
            {
                "version": 2,
                "mode": "reading",
                "query": "ね",
                "vocabulary_layers": ["core"],
            },
            "version 3",
        ),
        (
            {
                "version": 3,
                "mode": "reading",
                "query": "ね",
                "vocabulary_layers": [],
            },
            "1つ以上",
        ),
        (
            {
                "version": 3,
                "mode": "reading",
                "query": "ね",
                "tag_filters": [{"axis": "domain", "value": ""}],
            },
            "1から100文字",
        ),
        (
            {
                "version": 3,
                "mode": "reading",
                "query": "ね",
                "deprioritize_vocabulary_layers": ["auxiliary"],
            },
            "version 4",
        ),
        (
            {
                "version": 4,
                "mode": "reading",
                "query": "ね",
                "vocabulary_layers": ["core"],
                "deprioritize_vocabulary_layers": ["auxiliary"],
            },
            "検索対象",
        ),
        (
            {"version": 1, "mode": "reading", "query": "ね", "length_unit": "codepoint"},
            "文字数の数え方",
        ),
        (
            {"version": 1, "mode": "reading", "query": "ね", "include_proper": "yes"},
            "trueまたはfalse",
        ),
    ],
)
def test_invalid_canonical_requests_are_rejected(payload, message):
    with pytest.raises(RequestValidationError, match=message):
        parse(payload)


def test_legacy_requests_convert_to_versioned_requests():
    reading = parse(
        {"query": "ね", "match_type": "contains", "length": 2},
        legacy_kind="regex",
    )
    regex = parse({"pattern": "^ね"}, legacy_kind="regex")
    anagram = parse({"text": "ねこ"}, legacy_kind="anagram")

    assert (reading.version, reading.mode, reading.query) == (1, "reading", "ね")
    assert (regex.version, regex.mode, regex.query) == (1, "regex", "^ね")
    assert (anagram.version, anagram.mode, anagram.query) == (1, "anagram", "ねこ")


def test_serialization_exposes_effective_request_without_empty_filters():
    request = parse(
        {
            "version": 1,
            "mode": "reading",
            "query": "ネ",
            "length": 2,
        }
    )

    assert serialize_search_request(request) == {
        "version": 1,
        "mode": "reading",
        "query": "ネ",
        "match_type": "contains",
        "length": 2,
        "length_unit": "kana",
        "grid_profile": "separate",
        "include_proper": False,
        "include_function": False,
        "limit": 100,
    }
