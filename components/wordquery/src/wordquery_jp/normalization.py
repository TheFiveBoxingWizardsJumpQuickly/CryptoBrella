"""Canonical normalization rules shared by import and query paths."""

from __future__ import annotations

import re
import unicodedata

_READING_RE = re.compile(r"[ぁ-ゖゝゞー]+\Z")
_KATAKANA_TRANSLATION = str.maketrans(
    {chr(codepoint): chr(codepoint - 0x60) for codepoint in range(0x30A1, 0x30F7)}
    | {"ヽ": "ゝ", "ヾ": "ゞ"}
)
_DICTIONARY_SEPARATOR_TRANSLATION = str.maketrans(
    {"・": "", "、": "", "。": "", "=": "", "〜": "ー", "~": "ー"}
)


class InvalidReading(ValueError):
    """Raised when an anagram input or dictionary reading is unsupported."""


def normalize_text(value: str) -> str:
    """Apply width normalization and convert katakana literals to hiragana."""
    return unicodedata.normalize("NFKC", value).translate(_KATAKANA_TRANSLATION)


def normalize_reading(value: str) -> str:
    normalized = normalize_text(value.strip())
    if not normalized:
        raise InvalidReading("かなを入力してください。")
    if not _READING_RE.fullmatch(normalized):
        raise InvalidReading("かなと長音記号だけを使用してください。")
    return normalized


def normalize_dictionary_reading(value: str) -> str:
    """Normalize trusted dictionary punctuation without changing its display reading.

    JMdict uses middle dots and Japanese punctuation as orthographic separators, and
    wave dashes as long-vowel marks. They are not anagram tiles, so only the generated
    search key removes or maps them. User input remains strict and never silently drops
    punctuation.
    """
    return normalize_reading(normalize_text(value).translate(_DICTIONARY_SEPARATOR_TRANSLATION))


def normalize_pattern(value: str) -> str:
    normalized = normalize_text(value.strip())
    if not normalized:
        raise ValueError("正規表現を入力してください。")
    return normalized


def anagram_signature(normalized_reading: str) -> str:
    """Stable, duplicate-preserving signature for exact anagrams."""
    return "".join(sorted(normalized_reading))
