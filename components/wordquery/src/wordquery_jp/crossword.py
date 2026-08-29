"""Matching and explanation for structured crossword-cell conditions."""

from __future__ import annotations

from .models import CrosswordCell
from .units import GridProfile, tokenize_normalized_reading


def matches_crossword(
    normalized_reading: str,
    cells: tuple[CrosswordCell, ...],
    profile: GridProfile,
) -> bool:
    tokens = tokenize_normalized_reading(
        normalized_reading,
        "grid",
        grid_profile=profile,
    )
    if len(tokens) != len(cells):
        return False
    for token, cell in zip(tokens, cells, strict=True):
        if cell.kind == "unknown":
            continue
        if cell.kind == "exact" and token != cell.values[0]:
            return False
        if cell.kind == "include" and token not in cell.values:
            return False
        if cell.kind == "exclude" and token in cell.values:
            return False
    return True


def describe_crossword(cells: tuple[CrosswordCell, ...]) -> str:
    descriptions: list[str] = []
    for index, cell in enumerate(cells, start=1):
        if cell.kind == "unknown":
            condition = "不明"
        elif cell.kind == "exact":
            condition = f"「{cell.values[0]}」"
        elif cell.kind == "include":
            condition = f"「{'・'.join(cell.values)}」の候補"
        else:
            condition = f"「{'・'.join(cell.values)}」以外"
        descriptions.append(f"{index}マス目 {condition}")
    return f"クロスワード{len(cells)}マス: " + " / ".join(descriptions)


def fixed_prefix(cells: tuple[CrosswordCell, ...]) -> tuple[str | None, str | None]:
    values: list[str] = []
    for cell in cells:
        if cell.kind != "exact":
            break
        values.append(cell.values[0])
    prefix = "".join(values)
    if not prefix:
        return None, None
    return prefix, "exact" if len(values) == len(cells) else "prefix"
