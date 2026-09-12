"""Search-only kana equivalence; stored readings keep their original small kana."""

import re

_SMALL_TO_FULL = dict(zip("ぁぃぅぇぉゃゅょっゎゕゖ", "あいうえおやゆよつわかけ", strict=True))
_FOLD = str.maketrans(_SMALL_TO_FULL)
_VARIANTS = {char: small + full for small, full in _SMALL_TO_FULL.items()
             for char in (small, full)}


def fold_reading(reading: str) -> str:
    """Fold an already normalized reading without changing its character offsets."""
    return reading.translate(_FOLD)


def kana_variants(character: str) -> str:
    return _VARIANTS.get(character, character)


def literal_pattern(reading: str) -> str:
    """Escape literal kana and expand small/full equivalents into character classes."""
    return "".join("[" + kana_variants(char) + "]" if char in _VARIANTS
                   else re.escape(char) for char in reading)
