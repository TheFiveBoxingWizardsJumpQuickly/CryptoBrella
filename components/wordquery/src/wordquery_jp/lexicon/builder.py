"""Deterministic lexicon merge and SQLite build."""

from __future__ import annotations

import csv
import hashlib
import json
import os
import sqlite3
import tempfile
import tomllib
from dataclasses import asdict, dataclass, field
from datetime import UTC, datetime
from itertools import chain
from pathlib import Path

from wordquery_jp.normalization import (
    InvalidReading,
    anagram_signature,
    normalize_dictionary_reading,
    normalize_reading,
)

from .importers import ImportedTag, ImportedWord, iter_jmdict, iter_sudachi_csv
from .policy import is_ascii_only_headword
from .schema import SCHEMA

CATEGORIES = {"general", "proper", "function"}


@dataclass(frozen=True, slots=True)
class BuildConfig:
    output: Path
    additions: Path = Path("data/manual/additions.tsv")
    corrections: Path = Path("data/manual/corrections.tsv")
    exclusions: Path = Path("data/manual/exclusions.tsv")
    tags: Path = Path("data/manual/tags.tsv")
    jmdict: Path | None = None
    sudachi: Path | None = None
    source_manifest: Path = Path("data/sources.toml")


@dataclass(slots=True)
class MergedWord:
    surface: str
    reading: str
    normalized_reading: str
    category: str
    pos: str
    priority: int
    status: str = "accepted"
    provenance: list[ImportedWord] = field(default_factory=list)
    manual_tags: list[tuple[str, ImportedTag]] = field(default_factory=list)


@dataclass(frozen=True, slots=True)
class BuildResult:
    output: Path
    accepted: int
    candidates: int
    issues: int
    input_hash: str


def build_database(config: BuildConfig) -> BuildResult:
    streams = []
    if config.jmdict:
        streams.append(iter_jmdict(config.jmdict))
    if config.sudachi:
        streams.append(iter_sudachi_csv(config.sudachi))
    streams.append(iter(_read_additions(config.additions)))

    exclusions = _read_exclusions(config.exclusions)
    corrections = _read_corrections(config.corrections)
    manual_tags = _read_manual_tags(config.tags)
    merged: dict[tuple[str, str], MergedWord] = {}
    issues: list[tuple[str, str, str, str]] = []
    digest = _input_digest(config)

    for original in chain.from_iterable(streams):
        _update_digest(digest, original)
        word = _apply_correction(original, corrections)
        if _is_excluded(word, exclusions):
            continue
        try:
            normalizer = (
                normalize_reading if word.source == "manual" else normalize_dictionary_reading
            )
            normalized = normalizer(word.reading)
        except InvalidReading as exc:
            kind = "invalid_reading" if word.source == "manual" else "unsupported_reading"
            issues.append((kind, word.source, word.source_entry_id, str(exc)))
            continue
        if not word.surface.strip():
            issues.append(("empty_surface", word.source, word.source_entry_id, "表記が空です"))
            continue
        if word.category not in CATEGORIES:
            issues.append(("invalid_category", word.source, word.source_entry_id, word.category))
            continue
        if word.source == "manual" and (not word.reason.strip() or not word.reference.strip()):
            issues.append(
                (
                    "missing_manual_evidence",
                    word.source,
                    word.source_entry_id,
                    "開発者追加にはreasonとreferenceが必要です",
                )
            )
            continue
        key = (word.surface.strip(), normalized)
        existing = merged.get(key)
        if existing is None:
            merged[key] = MergedWord(
                surface=word.surface.strip(),
                reading=word.reading.strip(),
                normalized_reading=normalized,
                category=word.category,
                pos=word.pos,
                priority=word.priority,
                status=_initial_status(word),
                provenance=[word],
            )
            continue
        existing.provenance.append(word)
        if word.source == "manual":
            existing.category = word.category
            existing.priority = word.priority
            existing.status = "accepted"
        else:
            existing.priority = max(existing.priority, word.priority)
        if word.pos and word.pos not in existing.pos:
            existing.pos = "; ".join(filter(None, [existing.pos, word.pos]))
        if existing.category != word.category and word.source != "manual":
            existing.category = _resolve_category(existing.category, word.category)
            if (
                existing.category != "proper"
                and not is_ascii_only_headword(existing.surface)
            ):
                existing.status = "accepted"

    _attach_manual_tags(merged, manual_tags, issues)
    input_hash = digest.hexdigest()
    _write_database(
        config.output,
        merged.values(),
        issues,
        input_hash,
        _source_metadata(config.source_manifest),
    )
    accepted = sum(word.status == "accepted" for word in merged.values())
    return BuildResult(
        output=config.output,
        accepted=accepted,
        candidates=len(merged) - accepted,
        issues=len(issues),
        input_hash=input_hash,
    )


def _write_database(
    output: Path,
    words: object,
    issues: list[tuple[str, str, str, str]],
    input_hash: str,
    source_metadata: dict[str, str],
) -> None:
    output.parent.mkdir(parents=True, exist_ok=True)
    descriptor, temporary_name = tempfile.mkstemp(
        prefix="lexicon-", suffix=".sqlite3", dir=output.parent
    )
    os.close(descriptor)
    temporary = Path(temporary_name)
    try:
        connection = sqlite3.connect(temporary)
        connection.executescript(SCHEMA)
        metadata = {
            "schema_version": "3",
            "built_at": datetime.now(UTC).isoformat(),
            "input_hash": input_hash,
            **source_metadata,
        }
        connection.executemany(
            "INSERT INTO metadata(key, value) VALUES (?, ?)",
            sorted(metadata.items()),
        )
        sorted_words = sorted(words, key=lambda item: (item.surface, item.normalized_reading))
        for word in sorted_words:
            cursor = connection.execute(
                """
                INSERT INTO words(surface, reading, normalized_reading, signature,
                                  category, pos, priority, status)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    word.surface,
                    word.reading,
                    word.normalized_reading,
                    anagram_signature(word.normalized_reading),
                    word.category,
                    word.pos,
                    word.priority,
                    word.status,
                ),
            )
            word_id = cursor.lastrowid
            provenance_rows = {
                (
                    word_id,
                    source.source,
                    source.source_entry_id,
                    source.surface,
                    source.reading,
                    source.category,
                    source.pos,
                    source.reason,
                    source.reference,
                )
                for source in word.provenance
            }
            connection.executemany(
                """
                INSERT INTO provenance(word_id, source, source_entry_id, surface, reading,
                                       category, pos, reason, reference)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                sorted(provenance_rows),
            )
            tag_rows = {
                (
                    word_id,
                    tag.axis,
                    tag.value,
                    source.source,
                    source.source_entry_id,
                    tag.evidence,
                    tag.reason,
                    tag.reference,
                )
                for source in word.provenance
                for tag in source.tags
            }
            tag_rows.update(
                (
                    word_id,
                    tag.axis,
                    tag.value,
                    "manual",
                    source_entry_id,
                    tag.evidence,
                    tag.reason,
                    tag.reference,
                )
                for source_entry_id, tag in word.manual_tags
            )
            connection.executemany(
                """
                INSERT INTO word_tags(word_id, axis, value, source, source_entry_id,
                                      evidence, reason, reference)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """,
                sorted(tag_rows),
            )
        connection.executemany(
            "INSERT INTO build_issues(kind, source, source_entry_id, detail) VALUES (?, ?, ?, ?)",
            issues,
        )
        connection.commit()
        connection.execute("PRAGMA integrity_check").fetchone()
        connection.close()
        temporary.replace(output)
    except Exception:
        temporary.unlink(missing_ok=True)
        raise


def _read_additions(path: Path) -> list[ImportedWord]:
    if not path.is_file():
        return []
    rows: list[ImportedWord] = []
    with path.open(encoding="utf-8", newline="") as handle:
        for index, row in enumerate(csv.DictReader(handle, delimiter="\t"), 2):
            if not any(row.values()):
                continue
            rows.append(
                ImportedWord(
                    surface=row["surface"],
                    reading=row["reading"],
                    category=row["category"],
                    pos=row.get("pos", ""),
                    priority=int(row.get("priority") or 0),
                    source="manual",
                    source_entry_id=f"additions:{index}",
                    reason=row.get("reason", ""),
                    reference=row.get("reference", ""),
                )
            )
    return rows


def _read_corrections(path: Path) -> list[dict[str, str]]:
    return _read_tsv(path)


def _read_exclusions(path: Path) -> list[dict[str, str]]:
    return _read_tsv(path)


def _read_manual_tags(path: Path) -> list[dict[str, str]]:
    return _read_tsv(path)


def _read_tsv(path: Path) -> list[dict[str, str]]:
    if not path.is_file():
        return []
    with path.open(encoding="utf-8", newline="") as handle:
        return [dict(row) for row in csv.DictReader(handle, delimiter="\t") if any(row.values())]


def _matches(word: ImportedWord, rule: dict[str, str]) -> bool:
    checks = {
        "source": word.source,
        "source_entry_id": word.source_entry_id,
        "surface": word.surface,
        "reading": word.reading,
    }
    specified = False
    for key, value in checks.items():
        expected = (rule.get(key) or "").strip()
        if expected:
            specified = True
            if value != expected:
                return False
    return specified


def _attach_manual_tags(
    merged: dict[tuple[str, str], MergedWord],
    rows: list[dict[str, str]],
    issues: list[tuple[str, str, str, str]],
) -> None:
    for index, row in enumerate(rows, 2):
        source_entry_id = f"tags:{index}"
        surface = (row.get("surface") or "").strip()
        reading = row.get("reading") or ""
        axis = (row.get("axis") or "").strip()
        value = (row.get("value") or "").strip()
        reason = (row.get("reason") or "").strip()
        reference = (row.get("reference") or "").strip()
        if not all((surface, reading, axis, value)):
            issues.append(
                (
                    "invalid_manual_tag",
                    "manual",
                    source_entry_id,
                    "surface、reading、axis、valueは必須です",
                )
            )
            continue
        if not reason or not reference:
            issues.append(
                (
                    "missing_manual_tag_evidence",
                    "manual",
                    source_entry_id,
                    "開発者タグにはreasonとreferenceが必要です",
                )
            )
            continue
        try:
            normalized = normalize_reading(reading)
        except InvalidReading as exc:
            issues.append(("invalid_manual_tag", "manual", source_entry_id, str(exc)))
            continue
        word = merged.get((surface, normalized))
        if word is None:
            issues.append(
                (
                    "manual_tag_target_missing",
                    "manual",
                    source_entry_id,
                    f"対象語がありません: {surface}/{normalized}",
                )
            )
            continue
        word.manual_tags.append(
            (
                source_entry_id,
                ImportedTag(
                    axis=axis,
                    value=value,
                    evidence=(row.get("evidence") or "").strip(),
                    reason=reason,
                    reference=reference,
                ),
            )
        )


def _is_excluded(word: ImportedWord, rules: list[dict[str, str]]) -> bool:
    return any(_matches(word, rule) for rule in rules)


def _apply_correction(word: ImportedWord, rules: list[dict[str, str]]) -> ImportedWord:
    matching = [rule for rule in rules if _matches(word, rule)]
    if not matching:
        return word
    if len(matching) > 1:
        raise ValueError(f"複数の訂正規則が一致しました: {word.source}:{word.source_entry_id}")
    rule = matching[0]
    return ImportedWord(
        surface=rule.get("new_surface") or rule.get("surface") or word.surface,
        reading=rule.get("new_reading") or rule.get("reading") or word.reading,
        category=rule.get("new_category") or rule.get("category") or word.category,
        pos=rule.get("new_pos") or rule.get("pos") or word.pos,
        priority=int(rule.get("new_priority") or rule.get("priority") or word.priority),
        source=word.source,
        source_entry_id=word.source_entry_id,
        reason=rule.get("reason") or word.reason,
        reference=rule.get("reference") or word.reference,
        tags=word.tags,
    )


def _input_digest(config: BuildConfig) -> object:
    digest = hashlib.sha256()
    for path in (
        config.additions,
        config.corrections,
        config.exclusions,
        config.tags,
        config.source_manifest,
    ):
        if path.is_file():
            digest.update(path.name.encode())
            digest.update(path.read_bytes())
    return digest


def _update_digest(digest: object, word: ImportedWord) -> None:
    serialized = asdict(word)
    digest.update(json.dumps(serialized, ensure_ascii=False, sort_keys=True).encode())


def _source_metadata(path: Path) -> dict[str, str]:
    if not path.is_file():
        return {}
    with path.open("rb") as handle:
        sources = tomllib.load(handle)
    return {
        f"source.{name}.version": str(config["version"])
        for name, config in sources.items()
        if isinstance(config, dict) and config.get("version")
    }


def _resolve_category(first: str, second: str) -> str:
    """Choose the least restrictive UI category for a multi-sense word."""
    rank = {"function": 0, "proper": 1, "general": 2}
    return max((first, second), key=rank.__getitem__)


def _initial_status(word: ImportedWord) -> str:
    if word.source == "sudachidict" and (
        word.category == "proper" or is_ascii_only_headword(word.surface)
    ):
        return "candidate"
    return "accepted"
