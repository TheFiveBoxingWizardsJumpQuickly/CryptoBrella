import pytest

from wordquery_jp.models import TagFilter
from wordquery_jp.query import (
    SEARCH_REQUEST_VERSION,
    RequestValidationError,
    parse_search_request,
    serialize_search_request,
)


def parse(payload):
    return parse_search_request(payload, max_length=200, limit=100)


def request(**changes):
    return {"version": SEARCH_REQUEST_VERSION, "mode": "reading", "query": "ネ", **changes}


def test_reading_conditions_and_defaults():
    result = parse(request(match_type="prefix", length="3", length_unit="mora",
                           include_proper=True, must_include="コ", fold_small_kana=True))
    assert result.match_type == "prefix"
    assert result.length == 3
    assert result.length_unit == "mora"
    assert result.must_include == "こ"
    assert result.include_proper
    assert result.fold_small_kana
    assert result.limit == 100
    assert result.sort_mode == "commonness"
    assert result.vocabulary_layers == ("core",)


def test_effective_conditions_round_trip():
    result = parse(request(length=2))
    serialized = serialize_search_request(result)
    assert serialized == {
        "version": SEARCH_REQUEST_VERSION, "mode": "reading", "query": "ネ",
        "match_type": "contains", "length": 2, "length_unit": "kana",
        "fold_small_kana": False, "include_proper": False, "include_function": False,
        "limit": 100, "sort": "commonness", "vocabulary_layers": ["core"],
    }
    assert parse(serialized) == result


def test_layers_tags_and_deprioritization_round_trip():
    result = parse(request(
        sort="kana", vocabulary_layers=["core", "auxiliary", "core"],
        tag_filters=[{"axis": " proper_type ", "value": " place "}],
        deprioritize_vocabulary_layers=["auxiliary"],
        deprioritize_tag_filters=[{"axis": " domain ", "value": " computing "}],
    ))
    assert result.sort_mode == "kana"
    assert result.vocabulary_layers == ("core", "auxiliary")
    assert result.tag_filters == (TagFilter("proper_type", "place"),)
    assert result.deprioritize_tag_filters == (TagFilter("domain", "computing"),)
    assert parse(serialize_search_request(result)) == result


@pytest.mark.parametrize("mode", ["reading", "pattern", "regex", "anagram"])
def test_modes_round_trip(mode):
    result = parse(request(mode=mode, query="ね?" if mode == "pattern" else "ね"))
    serialized = serialize_search_request(result)
    assert ("match_type" in serialized) == (mode == "reading")
    assert ("fold_small_kana" in serialized) == (mode in {"reading", "pattern"})
    assert parse(serialized) == result


@pytest.mark.parametrize("mode", ["reading", "pattern"])
def test_small_kana_option_round_trip(mode):
    result = parse(request(mode=mode, fold_small_kana=True))
    assert parse(serialize_search_request(result)).fold_small_kana


@pytest.mark.parametrize("version", [None, True, "7", 1.5, 999])
def test_invalid_version(version):
    with pytest.raises(RequestValidationError, match="version"):
        parse(request(version=version))


@pytest.mark.parametrize(
    ("changes", "message"),
    [
        ({"mode": "unknown"}, "モード"),
        ({"query": None}, "文字列"),
        ({"sort": "recommended"}, "並べ替え"),
        ({"vocabulary_layers": []}, "1つ以上"),
        ({"vocabulary_layers": ["unknown"]}, "語彙層"),
        ({"tag_filters": [{"axis": "domain", "value": ""}]}, "1から100文字"),
        ({"deprioritize_vocabulary_layers": ["auxiliary"]}, "検索対象"),
        ({"length_unit": "codepoint"}, "文字数の数え方"),
        ({"length": 0}, "文字数"),
        ({"length": True}, "文字数"),
        ({"length": 201}, "文字数"),
        ({"include_proper": "yes"}, "trueまたはfalse"),
        ({"fold_small_kana": "yes"}, "trueまたはfalse"),
        ({"mode": "regex", "fold_small_kana": True}, "パターン検索"),
        ({"mode": "anagram", "fold_small_kana": True}, "パターン検索"),
        ({"mode": "pattern", "match_type": "exact"}, "一致の指定"),
        ({"match_type": "unknown"}, "一致の指定"),
        ({"must_include": 1}, "かな"),
        ({"must_exclude": "猫"}, "かな"),
    ],
)
def test_invalid_conditions(changes, message):
    with pytest.raises(RequestValidationError, match=message):
        parse(request(**changes))
