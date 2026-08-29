import pytest

from wordquery_jp.models import SearchRecord
from wordquery_jp.normalization import anagram_signature
from wordquery_jp.repository import SearchSnapshot
from wordquery_jp.search import QueryValidationError, SearchService


def record(identifier, surface, reading):
    return SearchRecord(
        id=identifier,
        surface=surface,
        reading=reading,
        normalized_reading=reading,
        signature=anagram_signature(reading),
        category="general",
        pos="",
        priority=10,
    )


@pytest.fixture
def service():
    records = (
        record(1, "猫", "ねこ"),
        record(2, "根語", "ねご"),
        record(3, "鼠", "ねずみ"),
        record(4, "小根", "こね"),
        record(5, "子", "こ"),
    )
    return SearchService(
        SearchSnapshot(records=records, anagrams={}, metadata={})
    )


@pytest.mark.parametrize(
    ("pattern", "expected"),
    [
        ("ね?", {"猫", "根語"}),
        ("ね[こご]", {"猫", "根語"}),
        ("ね[!こ]", {"根語"}),
        ("*ね", {"小根"}),
        ("?", {"子"}),
        ("ネ*", {"猫", "根語", "鼠"}),
        ("ねこ", {"猫"}),
    ],
)
def test_plain_pattern_grammar_matches_the_whole_normalized_reading(
    service,
    pattern,
    expected,
):
    response = service.pattern_search(pattern)

    assert {item.surface for item in response.results} == expected
    assert response.normalized_query == pattern.replace("ネ", "ね")
    assert response.condition_description.startswith("パターン全体:")
    assert response.match_spans == tuple(None for _ in response.results)


def test_pattern_description_uses_characters_as_the_public_unit(service):
    response = service.pattern_search("ね?[こご]*")

    assert response.condition_description == (
        "パターン全体: 「ね」 → 任意の1文字 → 「こ・ご」のいずれか1文字 → 任意の0文字以上"
    )


@pytest.mark.parametrize(
    ("pattern", "position"),
    [
        ("ね[こ", 1),
        ("ね[]", 2),
        ("ね[!]", 3),
        ("ね.こ", 1),
        ("ね!こ", 1),
        ("ね[こ?]", 3),
    ],
)
def test_pattern_syntax_errors_report_the_input_position(service, pattern, position):
    with pytest.raises(QueryValidationError) as captured:
        service.pattern_search(pattern)

    assert captured.value.position == position
    assert f"{position + 1}文字目" in str(captured.value)
