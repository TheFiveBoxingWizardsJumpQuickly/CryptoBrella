"""Tokenization and counting for Japanese search units."""

from __future__ import annotations

import unicodedata
from dataclasses import dataclass
from typing import Literal

import regex

from .normalization import normalize_reading

LengthUnit = Literal["kana", "mora", "surface", "grid"]
ReadingUnit = Literal["kana", "mora", "grid"]
GridProfileName = Literal["separate", "combine_phonetic", "combine_all_small"]

_LENGTH_UNITS = frozenset({"kana", "mora", "surface", "grid"})
_READING_UNITS = frozenset({"kana", "mora", "grid"})
_GRAPHEME_PATTERN = regex.compile(r"\X", regex.VERSION1)
_PHONETIC_SMALL_KANA = frozenset("ぁぃぅぇぉゃゅょゎ")
_ALL_SMALL_KANA = _PHONETIC_SMALL_KANA | frozenset("っゕゖ")


@dataclass(frozen=True, slots=True)
class GridProfile:
    """Versioned rule for joining small kana to the preceding crossword cell."""

    name: str
    combine_with_previous: frozenset[str]


GRID_SEPARATE = GridProfile(name="separate", combine_with_previous=frozenset())
GRID_COMBINE_PHONETIC = GridProfile(
    name="combine_phonetic",
    combine_with_previous=_PHONETIC_SMALL_KANA,
)
GRID_COMBINE_ALL_SMALL = GridProfile(
    name="combine_all_small",
    combine_with_previous=_ALL_SMALL_KANA,
)
GRID_PROFILES: dict[GridProfileName, GridProfile] = {
    "separate": GRID_SEPARATE,
    "combine_phonetic": GRID_COMBINE_PHONETIC,
    "combine_all_small": GRID_COMBINE_ALL_SMALL,
}


def resolve_grid_profile(name: GridProfileName) -> GridProfile:
    """Resolve a stable public profile name to its tokenization rules."""

    try:
        return GRID_PROFILES[name]
    except KeyError as exc:
        raise ValueError(f"未対応のマス規則です: {name}") from exc


def tokenize(
    value: str,
    unit: LengthUnit,
    *,
    grid_profile: GridProfile = GRID_SEPARATE,
) -> tuple[str, ...]:
    """Normalize and split a value into the requested search units.

    Reading-based units use the strict reading normalization shared by dictionary and
    query paths. Surface units preserve script while applying NFKC, then split extended
    grapheme clusters so canonically equivalent combining-mark input counts equally.
    """

    if unit not in _LENGTH_UNITS:
        raise ValueError(f"未対応の検索単位です: {unit}")
    if unit == "surface":
        normalized_surface = unicodedata.normalize("NFKC", value)
        return tuple(_GRAPHEME_PATTERN.findall(normalized_surface))

    return tokenize_normalized_reading(
        normalize_reading(value),
        unit,
        grid_profile=grid_profile,
    )


def tokenize_normalized_reading(
    normalized_reading: str,
    unit: ReadingUnit,
    *,
    grid_profile: GridProfile = GRID_SEPARATE,
) -> tuple[str, ...]:
    """Split a canonical dictionary reading without normalizing it again.

    Callers must pass a value already produced by ``normalize_reading`` or the lexicon
    builder. Canonical readings contain no combining marks, so the kana fast path can
    safely split by code point.
    """

    if unit not in _READING_UNITS:
        raise ValueError(f"この検索では使えない数え方です: {unit}")
    graphemes = tuple(normalized_reading)
    if unit == "kana":
        return graphemes
    if unit == "mora":
        return _combine_with_previous(graphemes, _PHONETIC_SMALL_KANA)
    return _combine_with_previous(graphemes, grid_profile.combine_with_previous)


def count_units(
    value: str,
    unit: LengthUnit,
    *,
    grid_profile: GridProfile = GRID_SEPARATE,
) -> int:
    """Return the number of tokens produced by :func:`tokenize`."""

    return len(tokenize(value, unit, grid_profile=grid_profile))


def count_normalized_reading_units(
    normalized_reading: str,
    unit: ReadingUnit,
    *,
    grid_profile: GridProfile = GRID_SEPARATE,
) -> int:
    """Count units in an already canonical reading, using an O(1) kana fast path."""

    if unit not in _READING_UNITS:
        raise ValueError(f"この検索では使えない数え方です: {unit}")
    if unit == "kana":
        return len(normalized_reading)
    return len(
        tokenize_normalized_reading(
            normalized_reading,
            unit,
            grid_profile=grid_profile,
        )
    )


def _combine_with_previous(
    graphemes: tuple[str, ...], continuations: frozenset[str]
) -> tuple[str, ...]:
    tokens: list[str] = []
    for grapheme in graphemes:
        if tokens and grapheme in continuations:
            tokens[-1] += grapheme
        else:
            tokens.append(grapheme)
    return tuple(tokens)
