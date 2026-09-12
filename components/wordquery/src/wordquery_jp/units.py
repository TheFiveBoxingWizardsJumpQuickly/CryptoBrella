"""Tokenization and counting for Japanese search units."""

from __future__ import annotations

import unicodedata
from typing import Literal

import regex

from .normalization import normalize_reading

LengthUnit = Literal["kana", "mora", "surface"]
ReadingUnit = Literal["kana", "mora"]

_LENGTH_UNITS = frozenset({"kana", "mora", "surface"})
_READING_UNITS = frozenset({"kana", "mora"})
_GRAPHEME_PATTERN = regex.compile(r"\X", regex.VERSION1)
_PHONETIC_SMALL_KANA = frozenset("ぁぃぅぇぉゃゅょゎ")


def tokenize(
    value: str,
    unit: LengthUnit,
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
    )


def tokenize_normalized_reading(
    normalized_reading: str,
    unit: ReadingUnit,
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
    return _combine_with_previous(graphemes, _PHONETIC_SMALL_KANA)


def count_units(
    value: str,
    unit: LengthUnit,
) -> int:
    """Return the number of tokens produced by :func:`tokenize`."""

    return len(tokenize(value, unit))


def count_normalized_reading_units(
    normalized_reading: str,
    unit: ReadingUnit,
) -> int:
    """Count units in an already canonical reading, using an O(1) kana fast path."""

    if unit not in _READING_UNITS:
        raise ValueError(f"この検索では使えない数え方です: {unit}")
    if unit == "kana":
        return len(normalized_reading)
    return len(tokenize_normalized_reading(normalized_reading, unit))


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
