"""Transparent sort keys and explanations for search results."""

from __future__ import annotations

from .models import SearchRecord, SortMode


def sort_key(record: SearchRecord, sort_mode: SortMode) -> tuple[object, ...]:
    stable = (record.normalized_reading, record.surface, record.reading, record.id)
    if sort_mode == "kana":
        return stable
    if sort_mode == "commonness":
        return (-commonness_score(record), -record.priority, *stable)
    status_order = {"accepted": 0, "candidate": 1}
    category_order = {"general": 0, "proper": 1, "function": 2}
    return (
        -record.priority,
        status_order[record.status],
        category_order[record.category],
        *stable,
    )


def commonness_score(record: SearchRecord) -> int:
    """Combine dictionary priority with a small multi-source evidence bonus."""

    return record.priority + (10 if record.multiple_sources else 0)


def explain_sort(
    record: SearchRecord, sort_mode: SortMode
) -> tuple[int | None, tuple[str, ...]]:
    if sort_mode == "kana":
        return None, ("正規化した読み順",)
    if sort_mode == "dictionary_priority":
        return record.priority, (f"辞書優先度 {record.priority}",)

    reasons = [f"辞書優先度 {record.priority}"]
    if record.multiple_sources:
        reasons.append("複数出典で確認 +10")
    else:
        reasons.append("単一出典")
    if record.status == "candidate":
        reasons.append("補助候補")
    return commonness_score(record), tuple(reasons)
