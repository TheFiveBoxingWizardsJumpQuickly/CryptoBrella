"""SQLite-backed immutable search snapshots."""

from __future__ import annotations

import sqlite3
from collections import defaultdict
from collections.abc import Callable, Iterator
from dataclasses import dataclass
from pathlib import Path

from .models import (
    MatchType,
    RecordStatus,
    SearchOptions,
    SearchRecord,
    SourceRecord,
    TagEvidence,
    TagFilter,
    VocabularyTag,
)
from .search_budget import expired
from .search_hints import SearchHints
from .search_index import validate_search_index
from .sqlite_paths import absolute_read_only_uri


class LexiconUnavailable(RuntimeError):
    """The generated lexicon cannot be loaded."""


SUPPORTED_SCHEMA_VERSIONS = frozenset({"3"})


@dataclass(frozen=True, slots=True)
class SearchSnapshot:
    records: tuple[SearchRecord, ...]
    anagrams: dict[str, tuple[SearchRecord, ...]]
    metadata: dict[str, str]
    auxiliary: AuxiliaryLexicon | None = None
    database: Path | None = None


@dataclass(frozen=True, slots=True)
class AuxiliaryLexicon:
    """SQLite-backed candidates that are intentionally not resident in memory."""

    database: Path
    count: int
    search_index: Path | None = None

    def iter_records(
        self,
        *,
        normalized_query: str | None = None,
        match_type: MatchType | None = None,
        signature: str | None = None,
        options: SearchOptions | None = None,
        hints: SearchHints | None = None,
        reading_matcher: Callable[[str], bool] | None = None,
    ) -> Iterator[SearchRecord]:
        conditions = ["status = 'candidate'"]
        parameters: list[object] = []
        if signature is not None:
            conditions.append("signature = ?")
            parameters.append(signature)
        elif normalized_query is not None and match_type is not None:
            _append_reading_constraint(
                conditions, parameters, normalized_query, match_type,
                indexed=self.search_index is not None,
            )
        if hints is not None:
            if hints.suffixes:
                alternatives = []
                for suffix in hints.suffixes:
                    constraint: list[str] = []
                    _append_reading_constraint(constraint, parameters, suffix, "suffix",
                                               indexed=self.search_index is not None)
                    alternatives.append("(" + " AND ".join(constraint) + ")")
                conditions.append("(" + " OR ".join(alternatives) + ")")
            if hints.prefix:
                _append_reading_constraint(conditions, parameters, hints.prefix, "prefix")
            if hints.suffix:
                _append_reading_constraint(conditions, parameters, hints.suffix, "suffix",
                                           indexed=self.search_index is not None)
            if hints.contains:
                _append_reading_constraint(conditions, parameters, hints.contains, "contains")
            if hints.exact_length is not None:
                conditions.append("reading_length = ?" if self.search_index
                                  else "length(normalized_reading) = ?")
                parameters.append(hints.exact_length)
            elif hints.minimum_length:
                conditions.append("reading_length >= ?" if self.search_index
                                  else "length(normalized_reading) >= ?")
                parameters.append(hints.minimum_length)
        if options is not None:
            if not options.include_function:
                conditions.append("category != 'function'")
            if options.must_include:
                conditions.append("instr(normalized_reading, ?) > 0")
                parameters.append(options.must_include)
            if options.must_exclude:
                conditions.append("instr(normalized_reading, ?) = 0")
                parameters.append(options.must_exclude)
            if options.reading_length is not None and options.length_unit == "kana":
                conditions.append("reading_length = ?" if self.search_index
                                  else "length(normalized_reading) = ?")
                parameters.append(options.reading_length)
            _append_tag_constraints(
                conditions, parameters, options.tag_filters, word_alias="words"
            )

        connection = _open_read_only(self.search_index or self.database)
        matcher_error: Exception | None = None
        if reading_matcher is not None:
            def match_reading(reading: str) -> bool:
                nonlocal matcher_error
                try:
                    return reading_matcher(reading)
                except Exception as exc:
                    matcher_error = exc
                    raise
            connection.create_function("wordquery_match", 1, match_reading)
            conditions.append("wordquery_match(normalized_reading)")
        try:
            if self.search_index and options is not None and options.tag_filters:
                # Tags remain in the authoritative DB.
                connection.execute("ATTACH DATABASE ? AS lexicon",
                                   (absolute_read_only_uri(self.database),))
            index_hint = ""
            if self.search_index:
                if signature is not None:
                    index_hint = " INDEXED BY auxiliary_signature"
                elif hints and hints.suffixes:
                    # Allow SQLite's MULTI-INDEX OR plan for the disjoint ranges.
                    pass
                elif match_type == "suffix" or (hints and hints.suffix):
                    index_hint = " INDEXED BY auxiliary_suffix"
                elif match_type in {"prefix", "exact"} or (hints and hints.prefix):
                    index_hint = " INDEXED BY auxiliary_prefix"
                elif ((hints and hints.exact_length is not None)
                      or (options and options.reading_length is not None
                          and options.length_unit == "kana")):
                    index_hint = " INDEXED BY auxiliary_length"
            multiple_sources = ("multiple_sources" if self.search_index else """(
                SELECT COUNT(DISTINCT p.source) >= 2 FROM provenance p WHERE p.word_id = words.id
            )""")
            cursor = connection.execute(
                f"""
                SELECT id, surface, reading, normalized_reading, signature,
                       category, pos, priority, status,
                       {multiple_sources} AS multiple_sources
                FROM words{index_hint}
                WHERE {" AND ".join(conditions)}
                ORDER BY id
                """,
                parameters,
            )
            for row in cursor:
                # This SELECT has a fixed projection. Avoid constructing a dict
                # for every auxiliary hit (length-only queries can hit 100k+).
                yield SearchRecord(*row[:9], multiple_sources=bool(row[9]))
        except sqlite3.OperationalError as exc:
            if matcher_error is not None:
                raise matcher_error from exc
            raise
        finally:
            connection.close()


def load_snapshot(database: str | Path) -> SearchSnapshot:
    path = Path(database)
    if not path.is_file():
        raise LexiconUnavailable(f"検索辞書がありません: {path}")
    try:
        connection = _open_read_only(path)
        connection.row_factory = sqlite3.Row
        metadata = dict(connection.execute("SELECT key, value FROM metadata").fetchall())
        schema_version = metadata.get("schema_version")
        if schema_version not in SUPPORTED_SCHEMA_VERSIONS:
            supported = ", ".join(sorted(SUPPORTED_SCHEMA_VERSIONS))
            raise LexiconUnavailable(
                f"未対応の検索辞書スキーマです: {schema_version!r}（対応: {supported}）"
            )
        rows = connection.execute(
            """
            SELECT id, surface, reading, normalized_reading, signature,
                   category, pos, priority, status,
                   EXISTS (
                       SELECT 1
                       FROM provenance p1
                       JOIN provenance p2
                         ON p2.word_id = p1.word_id
                        AND p2.source != p1.source
                       WHERE p1.word_id = words.id
                   ) AS multiple_sources
            FROM words
            WHERE status = 'accepted'
            ORDER BY id
            """
        ).fetchall()
        candidate_count = connection.execute(
            "SELECT COUNT(*) FROM words WHERE status = 'candidate'"
        ).fetchone()[0]
    except sqlite3.Error as exc:
        raise LexiconUnavailable(f"検索辞書を読み込めません: {exc}") from exc
    finally:
        if "connection" in locals():
            connection.close()

    records = tuple(_record_from_row(row) for row in rows)
    grouped: dict[str, list[SearchRecord]] = defaultdict(list)
    for record in records:
        grouped[record.signature].append(record)
    anagrams = {
        key: tuple(sorted(values, key=_dictionary_priority_key))
        for key, values in grouped.items()
    }
    search_index = validate_search_index(path.resolve())
    auxiliary = (AuxiliaryLexicon(path.resolve(), candidate_count, search_index)
                 if candidate_count else None)
    return SearchSnapshot(
        records=records,
        anagrams=anagrams,
        metadata=metadata,
        auxiliary=auxiliary,
        database=path.resolve(),
    )


def load_tags(
    database: Path | None, word_ids: list[int]
) -> dict[int, tuple[VocabularyTag, ...]]:
    if database is None or not word_ids:
        return {}
    placeholders = ", ".join("?" for _ in word_ids)
    connection = _open_read_only(database)
    connection.row_factory = sqlite3.Row
    try:
        rows = connection.execute(
            f"""
            SELECT word_id, axis, value, source, source_entry_id, evidence,
                   reason, reference
            FROM word_tags
            WHERE word_id IN ({placeholders})
            ORDER BY word_id, axis, value, source, source_entry_id, evidence
            """,
            word_ids,
        ).fetchall()
    finally:
        connection.close()

    grouped: dict[int, dict[tuple[str, str], list[TagEvidence]]] = defaultdict(
        lambda: defaultdict(list)
    )
    for row in rows:
        grouped[row["word_id"]][(row["axis"], row["value"])].append(
            TagEvidence(
                source=row["source"],
                source_entry_id=row["source_entry_id"],
                evidence=row["evidence"],
                reason=row["reason"],
                reference=row["reference"],
            )
        )
    return {
        word_id: tuple(
            VocabularyTag(axis, value, tuple(evidence))
            for (axis, value), evidence in values.items()
        )
        for word_id, values in grouped.items()
    }


def load_sources(
    database: Path | None, word_ids: list[int]
) -> dict[int, tuple[SourceRecord, ...]]:
    if database is None or not word_ids:
        return {}
    placeholders = ", ".join("?" for _ in word_ids)
    connection = _open_read_only(database)
    connection.row_factory = sqlite3.Row
    try:
        rows = connection.execute(
            f"""
            SELECT word_id, source, source_entry_id, surface, reading, category, pos,
                   reason, reference
            FROM provenance
            WHERE word_id IN ({placeholders})
            ORDER BY word_id, source, source_entry_id
            """,
            word_ids,
        ).fetchall()
    finally:
        connection.close()
    grouped: dict[int, list[SourceRecord]] = defaultdict(list)
    for row in rows:
        grouped[row["word_id"]].append(
            SourceRecord(
                source=row["source"],
                source_entry_id=row["source_entry_id"],
                surface=row["surface"],
                reading=row["reading"],
                category=row["category"],
                pos=row["pos"],
                reason=row["reason"],
                reference=row["reference"],
            )
        )
    return {word_id: tuple(values) for word_id, values in grouped.items()}


def load_tagged_word_ids(
    database: Path | None,
    filters: tuple[TagFilter, ...],
    *,
    status: RecordStatus,
) -> set[int] | None:
    if not filters:
        return None
    if database is None:
        return None
    connection = _open_read_only(database)
    try:
        matching_ids: set[int] | None = None
        for tag_filter in filters:
            ids = {
                row[0]
                for row in connection.execute(
                    """
                    SELECT DISTINCT t.word_id
                    FROM word_tags t
                    JOIN words w ON w.id = t.word_id
                    WHERE t.axis = ? AND t.value = ? AND w.status = ?
                    """,
                    (tag_filter.axis, tag_filter.value, status),
                )
            }
            matching_ids = ids if matching_ids is None else matching_ids & ids
            if not matching_ids:
                break
        return matching_ids or set()
    finally:
        connection.close()


def _dictionary_priority_key(
    record: SearchRecord,
) -> tuple[int, int, int, str, str]:
    category_order = {"general": 0, "proper": 1, "function": 2}
    status_order = {"accepted": 0, "candidate": 1}
    return (
        -record.priority,
        status_order[record.status],
        category_order[record.category],
        record.surface,
        record.reading,
    )


def _record_from_row(row: sqlite3.Row) -> SearchRecord:
    values = dict(row)
    values["multiple_sources"] = bool(values.get("multiple_sources", False))
    return SearchRecord(**values)


def _open_read_only(path: Path) -> sqlite3.Connection:
    connection = sqlite3.connect(absolute_read_only_uri(path), uri=True)
    connection.set_progress_handler(expired, 1000)
    return connection


def _append_reading_constraint(
    conditions: list[str],
    parameters: list[object],
    normalized_query: str,
    match_type: MatchType,
    *, indexed: bool = False,
) -> None:
    if match_type == "exact":
        conditions.append("normalized_reading = ?")
        parameters.append(normalized_query)
    elif match_type == "prefix" and normalized_query:
        conditions.append("normalized_reading >= ? AND normalized_reading < ?")
        parameters.extend((normalized_query, normalized_query + "\U0010ffff"))
    elif match_type == "contains" and normalized_query:
        conditions.append("instr(normalized_reading, ?) > 0")
        parameters.append(normalized_query)
    elif match_type == "suffix" and normalized_query:
        if indexed:
            conditions.append("reversed_reading >= ? AND reversed_reading < ?")
            parameters.extend((normalized_query[::-1], normalized_query[::-1] + "\U0010ffff"))
        else:
            conditions.append("substr(normalized_reading, -length(?)) = ?")
            parameters.extend((normalized_query, normalized_query))


def _append_tag_constraints(
    conditions: list[str],
    parameters: list[object],
    filters: tuple[TagFilter, ...],
    *,
    word_alias: str,
) -> None:
    for tag_filter in filters:
        conditions.append(
            f"""
            EXISTS (
                SELECT 1 FROM word_tags t
                WHERE t.word_id = {word_alias}.id AND t.axis = ? AND t.value = ?
            )
            """
        )
        parameters.extend((tag_filter.axis, tag_filter.value))
