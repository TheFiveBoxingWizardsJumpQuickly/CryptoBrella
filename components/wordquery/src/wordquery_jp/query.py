"""Validation and compatibility conversion for versioned search requests."""

from __future__ import annotations

from collections.abc import Mapping
from typing import Literal, cast

from .models import (
    CrosswordCell,
    CrosswordCellKind,
    MatchType,
    SearchMode,
    SearchRequest,
    SortMode,
    TagFilter,
    VocabularyLayer,
)
from .normalization import normalize_reading
from .units import (
    GRID_PROFILES,
    GridProfile,
    GridProfileName,
    LengthUnit,
    resolve_grid_profile,
    tokenize,
)

SEARCH_REQUEST_VERSION = 6
LegacySearchKind = Literal["regex", "anagram"]

_MODES = frozenset({"reading", "pattern", "crossword", "regex", "anagram"})
_MATCH_TYPES = frozenset({"contains", "prefix", "suffix", "exact", "regex"})
_READING_MATCH_TYPES = frozenset({"contains", "prefix", "suffix", "exact"})
_LENGTH_UNITS = frozenset({"kana", "mora", "surface", "grid"})
_SORT_MODES = frozenset({"commonness", "dictionary_priority", "kana"})
_VOCABULARY_LAYERS = frozenset({"core", "auxiliary"})
_MAX_TAG_FILTERS = 10
_MAX_TAG_COMPONENT_LENGTH = 100
_MAX_GRID_CELL_VALUES = 20


class RequestValidationError(ValueError):
    pass


def parse_search_request(
    payload: Mapping[str, object],
    *,
    max_length: int,
    limit: int,
    legacy_kind: LegacySearchKind | None = None,
) -> SearchRequest:
    """Validate a canonical request or convert one of the two legacy API shapes."""

    version = _version(
        payload.get("version"),
        required=legacy_kind is None,
        default=1 if legacy_kind is not None else SEARCH_REQUEST_VERSION,
    )
    if legacy_kind is None:
        mode, query, match_type = _canonical_mode(payload, version)
    else:
        mode, query, match_type = _legacy_mode(payload, legacy_kind)

    length = _length(payload.get("length"), max_length)
    default_length_unit = "grid" if mode == "crossword" else "kana"
    length_unit = _length_unit(payload.get("length_unit", default_length_unit))
    grid_profile = _grid_profile(payload.get("grid_profile", "separate"))
    if length_unit != "grid" and grid_profile != "separate":
        raise RequestValidationError(
            "小書き文字の規則は、文字数の数え方が「マス数」の場合だけ指定できます。"
        )
    grid_cells = _crossword_cells(
        payload,
        mode=mode,
        version=version,
        profile=resolve_grid_profile(grid_profile),
        max_length=max_length,
    )
    if mode == "crossword":
        if query:
            raise RequestValidationError(
                "クロスワード検索ではqueryではなくgrid_cellsを指定してください。"
            )
        if length_unit != "grid":
            raise RequestValidationError(
                "クロスワード検索の長さ単位はgridを指定してください。"
            )
        if length is not None and length != len(grid_cells):
            raise RequestValidationError(
                "クロスワード検索の長さはgrid_cellsのマス数と一致させてください。"
            )
        length = len(grid_cells)

    if version == 1:
        if "sort" in payload:
            raise RequestValidationError("並べ替えは検索条件version 2で指定してください。")
        sort_mode: SortMode = "dictionary_priority"
    else:
        sort_mode = _sort_mode(payload.get("sort", "commonness"))

    if version < 3:
        if "vocabulary_layers" in payload or "tag_filters" in payload:
            raise RequestValidationError("語彙層とタグは検索条件version 3で指定してください。")
        vocabulary_layers: tuple[VocabularyLayer, ...] = ("core", "auxiliary")
        tag_filters: tuple[TagFilter, ...] = ()
    else:
        vocabulary_layers = _vocabulary_layers(payload.get("vocabulary_layers", ["core"]))
        tag_filters = _tag_filters(payload.get("tag_filters", []), label="絞り込み")

    if version < 4:
        if (
            "deprioritize_vocabulary_layers" in payload
            or "deprioritize_tag_filters" in payload
        ):
            raise RequestValidationError("後回し指定は検索条件version 4で指定してください。")
        deprioritize_vocabulary_layers: tuple[VocabularyLayer, ...] = ()
        deprioritize_tag_filters: tuple[TagFilter, ...] = ()
    else:
        deprioritize_vocabulary_layers = _optional_vocabulary_layers(
            payload.get("deprioritize_vocabulary_layers", [])
        )
        if not set(deprioritize_vocabulary_layers).issubset(vocabulary_layers):
            raise RequestValidationError(
                "後回しにする語彙層は検索対象の語彙層から指定してください。"
            )
        deprioritize_tag_filters = _tag_filters(
            payload.get("deprioritize_tag_filters", []),
            label="後回し",
        )

    return SearchRequest(
        version=version,
        mode=mode,
        query=query,
        match_type=match_type,
        length=length,
        length_unit=length_unit,
        grid_profile=grid_profile,
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
        grid_cells=grid_cells,
    )


def serialize_search_request(search_request: SearchRequest) -> dict[str, object]:
    """Return the stable, versioned JSON representation used in API responses."""

    serialized: dict[str, object] = {
        "version": search_request.version,
        "mode": search_request.mode,
        "query": search_request.query,
        "length_unit": search_request.length_unit,
        "grid_profile": search_request.grid_profile,
        "include_proper": search_request.include_proper,
        "include_function": search_request.include_function,
        "limit": search_request.limit,
    }
    if search_request.mode == "reading":
        serialized["match_type"] = search_request.match_type
    if search_request.mode == "crossword":
        serialized["grid_cells"] = [
            (
                {"kind": cell.kind}
                if cell.kind == "unknown"
                else {"kind": cell.kind, "values": list(cell.values)}
            )
            for cell in search_request.grid_cells
        ]
    if search_request.length is not None:
        serialized["length"] = search_request.length
    if search_request.must_include is not None:
        serialized["must_include"] = search_request.must_include
    if search_request.must_exclude is not None:
        serialized["must_exclude"] = search_request.must_exclude
    if search_request.version >= 2:
        serialized["sort"] = search_request.sort_mode
    if search_request.version >= 3:
        serialized["vocabulary_layers"] = list(search_request.vocabulary_layers)
        if search_request.tag_filters:
            serialized["tag_filters"] = [
                {"axis": item.axis, "value": item.value} for item in search_request.tag_filters
            ]
    if search_request.version >= 4:
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


def _version(raw_version: object, *, required: bool, default: int) -> int:
    if raw_version is None:
        if required:
            raise RequestValidationError("検索条件のversionを指定してください。")
        return default
    if isinstance(raw_version, bool) or not isinstance(raw_version, (int, str)):
        raise RequestValidationError("検索条件のversionが正しくありません。")
    if isinstance(raw_version, str) and not raw_version.isdecimal():
        raise RequestValidationError("検索条件のversionが正しくありません。")
    version = int(raw_version)
    if version not in range(1, SEARCH_REQUEST_VERSION + 1):
        raise RequestValidationError(f"対応していない検索条件versionです: {version}")
    return version


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
    version: int,
) -> tuple[SearchMode, str, MatchType]:
    raw_mode = payload.get("mode")
    if not isinstance(raw_mode, str) or raw_mode not in _MODES:
        raise RequestValidationError("検索モードが正しくありません。")
    if raw_mode == "pattern" and version < 5:
        raise RequestValidationError(
            "検索パターンは検索条件version 5で指定してください。"
        )
    if raw_mode == "crossword" and version < 6:
        raise RequestValidationError(
            "クロスワード検索は検索条件version 6で指定してください。"
        )
    query = _query(payload.get("query", "") if raw_mode == "crossword" else payload.get("query"))
    if raw_mode == "reading":
        match_type = _match_type(payload.get("match_type", "contains"), reading_only=True)
    else:
        if "match_type" in payload:
            raise RequestValidationError("一致の指定はパターンでだけ使用できます。")
        match_type = "regex" if raw_mode == "regex" else "contains"
    return cast(SearchMode, raw_mode), query, match_type


def _crossword_cells(
    payload: Mapping[str, object],
    *,
    mode: SearchMode,
    version: int,
    profile: GridProfile,
    max_length: int,
) -> tuple[CrosswordCell, ...]:
    if mode != "crossword":
        if "grid_cells" in payload:
            raise RequestValidationError(
                "grid_cellsはクロスワード検索モードでだけ指定できます。"
            )
        return ()
    if version < 6:
        raise RequestValidationError(
            "クロスワード検索は検索条件version 6で指定してください。"
        )
    raw_cells = payload.get("grid_cells")
    if (
        not isinstance(raw_cells, list)
        or not raw_cells
        or len(raw_cells) > max_length
    ):
        raise RequestValidationError(
            f"クロスワードのマスは1から{max_length}件の配列で指定してください。"
        )
    cells: list[CrosswordCell] = []
    for index, raw_cell in enumerate(raw_cells, start=1):
        cells.append(_crossword_cell(raw_cell, index=index, profile=profile))
    return tuple(cells)


def _crossword_cell(
    raw_cell: object,
    *,
    index: int,
    profile: GridProfile,
) -> CrosswordCell:
    if not isinstance(raw_cell, dict):
        raise RequestValidationError(f"クロスワードの{index}マス目が正しくありません。")
    raw_kind = raw_cell.get("kind")
    kinds = {"exact", "unknown", "include", "exclude"}
    if not isinstance(raw_kind, str) or raw_kind not in kinds:
        raise RequestValidationError(
            f"クロスワードの{index}マス目の種類が正しくありません。"
        )
    kind = cast(CrosswordCellKind, raw_kind)
    if kind == "unknown":
        if "value" in raw_cell or "values" in raw_cell:
            raise RequestValidationError(
                f"クロスワードの{index}マス目の不明条件には文字を指定できません。"
            )
        return CrosswordCell(kind)

    raw_values = raw_cell.get("values")
    if (
        not isinstance(raw_values, list)
        or not raw_values
        or len(raw_values) > _MAX_GRID_CELL_VALUES
        or any(not isinstance(value, str) for value in raw_values)
    ):
        raise RequestValidationError(
            f"クロスワードの{index}マス目は1から{_MAX_GRID_CELL_VALUES}個のかなを指定してください。"
        )
    if kind == "exact" and len(raw_values) != 1:
        raise RequestValidationError(
            f"クロスワードの{index}マス目の確定文字は1つ指定してください。"
        )

    values: list[str] = []
    for raw_value in cast(list[str], raw_values):
        try:
            tokens = tokenize(raw_value, "grid", grid_profile=profile)
        except ValueError as exc:
            raise RequestValidationError(
                f"クロスワードの{index}マス目にはかなを指定してください。"
            ) from exc
        if len(tokens) != 1:
            raise RequestValidationError(
                f"クロスワードの{index}マス目の各入力は、選択した小書き文字規則で"
                "1マスになる必要があります。"
            )
        if tokens[0] not in values:
            values.append(tokens[0])
    return CrosswordCell(kind, tuple(values))


def _legacy_mode(
    payload: Mapping[str, object], kind: LegacySearchKind
) -> tuple[SearchMode, str, MatchType]:
    if kind == "anagram":
        return "anagram", _query(payload.get("text")), "contains"
    if "query" in payload or "match_type" in payload:
        match_type = _match_type(payload.get("match_type", "contains"))
        mode: SearchMode = "regex" if match_type == "regex" else "reading"
        return mode, _query(payload.get("query", "")), match_type
    return "regex", _query(payload.get("pattern")), "regex"


def _query(raw_query: object) -> str:
    if not isinstance(raw_query, str):
        raise RequestValidationError("入力値は文字列で指定してください。")
    return raw_query


def _match_type(raw_match_type: object, *, reading_only: bool = False) -> MatchType:
    allowed = _READING_MATCH_TYPES if reading_only else _MATCH_TYPES
    if not isinstance(raw_match_type, str) or raw_match_type not in allowed:
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


def _grid_profile(raw_profile: object) -> GridProfileName:
    if not isinstance(raw_profile, str) or raw_profile not in GRID_PROFILES:
        raise RequestValidationError("クロスワードのマス規則が正しくありません。")
    return cast(GridProfileName, raw_profile)


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
