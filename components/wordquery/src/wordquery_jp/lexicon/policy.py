"""Small, shared predicates for lexicon adoption policy."""

from __future__ import annotations


def is_ascii_only_headword(surface: str) -> bool:
    """Return whether a non-empty surface is ASCII-only and contains A-Z."""

    stripped = surface.strip()
    return bool(stripped) and stripped.isascii() and any(
        "a" <= character.lower() <= "z" for character in stripped
    )
