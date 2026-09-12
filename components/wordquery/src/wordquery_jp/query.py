"""Validation and serialization for the current search request."""

from __future__ import annotations

from collections.abc import Mapping
from typing import cast

from .models import (
    MatchType,
    SearchMode,
    SearchRequest,
    SortMode,
    TagFilter,
    VocabularyLayer,
)
from .normalization import normalize_reading
from .units import LengthUnit

SEARCH_REQUEST_VERSION = 7

_MODES = frozenset({"reading", "pattern", "regex", "anagram"})
_READING_MATCH_TYPES = frozenset({"contains", "prefix", "suffix", "exact"})
_LENGTH_UNITS = frozenset({"kana", "mora", "surface"})
_SORT_MODES = frozenset({"commonness", "dictionary_priority", "kana"})
_VOCABULARY_LAYERS = frozenset({"core", "auxiliary"})
_MAX_TAG_FILTERS = 10
_MAX_TAG_COMPONENT_LENGTH = 100


class RequestValidationError(ValueError):
    pass


def parse_search_request(
    payload: Mapping[str, object],
    *,
    max_length: int,
    limit: int,
) -> SearchRequest:
    """Validate the search conditions used by the UI and operational tools."""

    version = _version(payload.get("version"))
    mode, query, match_type = _canonical_mode(payload)
    length = _length(payload.get("length"), max_length)
    length_unit = _length_unit(payload.get("length_unit", "kana"))
    fold_small_kana = _boolean(payload, "fold_small_kana")
    if fold_small_kana and mode not in {"reading", "pattern"}:
        raise RequestValidationError("小書きかなの同一視はパターン検索で使用できます。")
    sort_mode = _sort_mode(payload.get("sort", "commonness"))
    vocabulary_layers = _vocabulary_layers(payload.get("vocabulary_layers", ["core"]))
    tag_filters = _tag_filters(payload.get("tag_filters", []), label="絞り込み")
    deprioritize_vocabulary_layers = _optional_vocabulary_layers(
        payload.get("deprioritize_vocabulary_layers", [])
    )
    if not set(deprioritize_vocabulary_layers).issubset(vocabulary_layers):
        raise RequestValidationError("後回しにする語彙層は検索対象の語彙層から指定してください。")
    deprioritize_tag_filters = _tag_filters(
        payload.get("deprioritize_tag_filters", []), label="後回し"
    )

    return SearchRequest(
        version=version,
        mode=mode,
        query=query,
        match_type=match_type,
        length=length,
        length_unit=length_unit,
        fold_small_kana=fold_small_kana,
        include_proper=_boolean(payload, "include_proper"),
        include_function=_boolean(payload, "include_function"),
        must_include=_optional_reading(payload, "must_include", "追加で含む"),
        must_exclude=_optional_reading(payload, "must_exclude", "含まない"),
        limit=limit,
        sort_mode=sort_mode,
        vocabulary_layers=vocabulary_layers,
        tag_filters=tag_filters,
        deprioritize_vocabulary_layers=deprioritize_vocabulary_layers,
        deprioritize_tag_filters=deprioritize_tag_filters,
    )


def serialize_search_request(search_request: SearchRequest) -> dict[str, object]:
    """Return the stable, versioned JSON representation used in API responses."""

    serialized: dict[str, object] = {
        "version": search_request.version,
        "mode": search_request.mode,
        "query": search_request.query,
        "length_unit": search_request.length_unit,
        "include_proper": search_request.include_proper,
        "include_function": search_request.include_function,
        "limit": search_request.limit,
    }
    if search_request.mode == "reading":
        serialized["match_type"] = search_request.match_type
    if search_request.mode in {"reading", "pattern"}:
        serialized["fold_small_kana"] = search_request.fold_small_kana
    if search_request.length is not None:
        serialized["length"] = search_request.length
    if search_request.must_include is not None:
        serialized["must_include"] = search_request.must_include
    if search_request.must_exclude is not None:
        serialized["must_exclude"] = search_request.must_exclude
    serialized["sort"] = search_request.sort_mode
    serialized["vocabulary_layers"] = list(search_request.vocabulary_layers)
    if search_request.tag_filters:
        serialized["tag_filters"] = [
            {"axis": item.axis, "value": item.value} for item in search_request.tag_filters
        ]
    if search_request.deprioritize_vocabulary_layers:
        serialized["deprioritize_vocabulary_layers"] = list(
            search_request.deprioritize_vocabulary_layers
        )
    if search_request.deprioritize_tag_filters:
        serialized["deprioritize_tag_filters"] = [
            {"axis": item.axis, "value": item.value}
            for item in search_request.deprioritize_tag_filters
        ]
    return serialized


def _version(raw_version: object) -> int:
    if type(raw_version) is not int or raw_version != SEARCH_REQUEST_VERSION:
        raise RequestValidationError("検索条件のversionが正しくありません。")
    return raw_version


def _sort_mode(raw_mode: object) -> SortMode:
    if not isinstance(raw_mode, str) or raw_mode not in _SORT_MODES:
        raise RequestValidationError("並べ替え方法が正しくありません。")
    return cast(SortMode, raw_mode)


def _vocabulary_layers(raw_layers: object) -> tuple[VocabularyLayer, ...]:
    if not isinstance(raw_layers, list) or not raw_layers:
        raise RequestValidationError("語彙層は1つ以上の配列で指定してください。")
    if any(not isinstance(layer, str) or layer not in _VOCABULARY_LAYERS for layer in raw_layers):
        raise RequestValidationError("語彙層が正しくありません。")
    return tuple(dict.fromkeys(cast(list[VocabularyLayer], raw_layers)))


def _optional_vocabulary_layers(raw_layers: object) -> tuple[VocabularyLayer, ...]:
    if not isinstance(raw_layers, list):
        raise RequestValidationError("後回しにする語彙層は配列で指定してください。")
    if any(not isinstance(layer, str) or layer not in _VOCABULARY_LAYERS for layer in raw_layers):
        raise RequestValidationError("後回しにする語彙層が正しくありません。")
    return tuple(dict.fromkeys(cast(list[VocabularyLayer], raw_layers)))


def _tag_filters(raw_filters: object, *, label: str) -> tuple[TagFilter, ...]:
    if not isinstance(raw_filters, list) or len(raw_filters) > _MAX_TAG_FILTERS:
        raise RequestValidationError(
            f"{label}の「タグ」は{_MAX_TAG_FILTERS}件以内の配列で指定してください。"
        )
    filters: list[TagFilter] = []
    for raw_filter in raw_filters:
        if not isinstance(raw_filter, dict):
            raise RequestValidationError(f"{label}の「タグ」が正しくありません。")
        axis = raw_filter.get("axis")
        value = raw_filter.get("value")
        if not isinstance(axis, str) or not isinstance(value, str):
            raise RequestValidationError(
                f"{label}の「タグ」の軸と値を文字列で指定してください。"
            )
        axis = axis.strip()
        value = value.strip()
        if (
            not axis
            or not value
            or len(axis) > _MAX_TAG_COMPONENT_LENGTH
            or len(value) > _MAX_TAG_COMPONENT_LENGTH
        ):
            raise RequestValidationError(
                f"{label}の「タグ」の軸と値は1から100文字で指定してください。"
            )
        tag_filter = TagFilter(axis=axis, value=value)
        if tag_filter not in filters:
            filters.append(tag_filter)
    return tuple(filters)


def _canonical_mode(
    payload: Mapping[str, object],
) -> tuple[SearchMode, str, MatchType]:
    raw_mode = payload.get("mode")
    if not isinstance(raw_mode, str) or raw_mode not in _MODES:
        raise RequestValidationError("検索モードが正しくありません。")
    query = _query(payload.get("query"))
    if raw_mode == "reading":
        match_type = _match_type(payload.get("match_type", "contains"))
    else:
        if "match_type" in payload:
            raise RequestValidationError("一致の指定はパターンでだけ使用できます。")
        match_type = "contains"
    return cast(SearchMode, raw_mode), query, match_type


def _query(raw_query: object) -> str:
    if not isinstance(raw_query, str):
        raise RequestValidationError("入力値は文字列で指定してください。")
    return raw_query


def _match_type(raw_match_type: object) -> MatchType:
    if not isinstance(raw_match_type, str) or raw_match_type not in _READING_MATCH_TYPES:
        raise RequestValidationError("一致の指定が正しくありません。")
    return cast(MatchType, raw_match_type)


def _length(raw_length: object, max_length: int) -> int | None:
    if raw_length in (None, ""):
        return None
    if isinstance(raw_length, bool) or not isinstance(raw_length, (int, str)):
        raise RequestValidationError("文字数は1以上の整数で指定してください。")
    if isinstance(raw_length, str) and not raw_length.isdecimal():
        raise RequestValidationError("文字数は1以上の整数で指定してください。")
    length = int(raw_length)
    if length < 1 or length > max_length:
        raise RequestValidationError(f"文字数は1から{max_length}までで指定してください。")
    return length


def _length_unit(raw_unit: object) -> LengthUnit:
    if not isinstance(raw_unit, str) or raw_unit not in _LENGTH_UNITS:
        raise RequestValidationError("文字数の数え方が正しくありません。")
    return cast(LengthUnit, raw_unit)


def _boolean(payload: Mapping[str, object], key: str) -> bool:
    raw_value = payload.get(key, False)
    if not isinstance(raw_value, bool):
        raise RequestValidationError(f"{key}はtrueまたはfalseで指定してください。")
    return raw_value


def _optional_reading(payload: Mapping[str, object], key: str, label: str) -> str | None:
    raw_value = payload.get(key)
    if raw_value in (None, ""):
        return None
    if not isinstance(raw_value, str):
        raise RequestValidationError(f"絞り込みの「{label}」には、かなを入力してください。")
    try:
        return normalize_reading(raw_value)
    except ValueError as exc:
        raise RequestValidationError(
            f"絞り込みの「{label}」には、かなを入力してください。"
        ) from exc
