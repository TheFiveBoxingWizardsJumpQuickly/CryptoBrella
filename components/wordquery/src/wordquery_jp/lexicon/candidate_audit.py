"""Reproducible structural audit of the SQLite-backed candidate lexicon."""

from __future__ import annotations

import json
import sqlite3
from collections import Counter
from dataclasses import dataclass
from pathlib import Path

from wordquery_jp.normalization import (
    InvalidReading,
    anagram_signature,
    normalize_dictionary_reading,
)

from .policy import is_ascii_only_headword

CANDIDATE_AUDIT_SCHEMA_VERSION = "1.1"
PROPER_TYPE_VALUES = {
    "character",
    "organization",
    "other",
    "person",
    "place",
    "product",
    "work",
}


@dataclass(frozen=True, slots=True)
class CandidateAuditResult:
    passed: bool
    report: dict[str, object]


def audit_auxiliary_candidates(database: str | Path) -> CandidateAuditResult:
    """Audit Sudachi-only proper-name and ASCII-headword candidates."""

    path = Path(database).resolve()
    connection = sqlite3.connect(f"file:{path}?mode=ro", uri=True)
    connection.row_factory = sqlite3.Row
    try:
        metadata = dict(connection.execute("SELECT key, value FROM metadata").fetchall())
        candidate_rows = connection.execute(
            """
            SELECT id, surface, reading, normalized_reading, signature,
                   category, pos, priority
            FROM words
            WHERE status = 'candidate'
            ORDER BY id
            """
        )
        candidate_count = 0
        invalid_readings = 0
        normalized_reading_mismatches = 0
        signature_mismatches = 0
        missing_surface = 0
        missing_pos = 0
        categories: Counter[str] = Counter()
        priorities: Counter[int] = Counter()
        positions: Counter[str] = Counter()
        proper_candidates = 0
        ascii_headword_candidates = 0
        overlapping_candidate_kinds = 0
        out_of_scope_candidates = 0
        for row in candidate_rows:
            candidate_count += 1
            surface = row["surface"]
            reading = row["reading"]
            normalized_reading = row["normalized_reading"]
            categories[row["category"]] += 1
            priorities[row["priority"]] += 1
            positions[row["pos"]] += 1
            is_proper = row["category"] == "proper"
            is_ascii_headword = is_ascii_only_headword(surface)
            proper_candidates += is_proper
            ascii_headword_candidates += is_ascii_headword
            overlapping_candidate_kinds += is_proper and is_ascii_headword
            out_of_scope_candidates += not (is_proper or is_ascii_headword)
            missing_surface += not bool(surface)
            missing_pos += not bool(row["pos"])
            try:
                expected_normalized = normalize_dictionary_reading(reading)
            except InvalidReading:
                invalid_readings += 1
                continue
            normalized_reading_mismatches += expected_normalized != normalized_reading
            signature_mismatches += (
                anagram_signature(normalized_reading) != row["signature"]
            )

        source_entries = _scalar(
            connection,
            """
            SELECT COUNT(*)
            FROM provenance p JOIN words w ON w.id = p.word_id
            WHERE w.status = 'candidate'
            """,
        )
        source_records = dict(
            connection.execute(
                """
                SELECT p.source, COUNT(DISTINCT w.id)
                FROM provenance p JOIN words w ON w.id = p.word_id
                WHERE w.status = 'candidate'
                GROUP BY p.source ORDER BY p.source
                """
            ).fetchall()
        )
        missing_provenance = _scalar(
            connection,
            """
            SELECT COUNT(*) FROM words w
            WHERE w.status = 'candidate'
              AND NOT EXISTS (
                  SELECT 1 FROM provenance p WHERE p.word_id = w.id
              )
            """,
        )
        without_sudachi_provenance = _scalar(
            connection,
            """
            SELECT COUNT(*) FROM words w
            WHERE w.status = 'candidate'
              AND NOT EXISTS (
                  SELECT 1 FROM provenance p
                  WHERE p.word_id = w.id AND p.source = 'sudachidict'
              )
            """,
        )
        with_non_sudachi_provenance = _scalar(
            connection,
            """
            SELECT COUNT(*) FROM words w
            WHERE w.status = 'candidate'
              AND EXISTS (
                  SELECT 1 FROM provenance p
                  WHERE p.word_id = w.id AND p.source != 'sudachidict'
              )
            """,
        )
        multiple_source_entries = _scalar(
            connection,
            """
            SELECT COUNT(*) FROM (
                SELECT w.id
                FROM words w JOIN provenance p ON p.word_id = w.id
                WHERE w.status = 'candidate'
                GROUP BY w.id HAVING COUNT(*) > 1
            )
            """,
        )

        proper_type_records = dict(
            connection.execute(
                """
                SELECT t.value, COUNT(DISTINCT w.id)
                FROM words w JOIN word_tags t ON t.word_id = w.id
                WHERE w.status = 'candidate' AND t.axis = 'proper_type'
                GROUP BY t.value ORDER BY t.value
                """
            ).fetchall()
        )
        missing_proper_type = _scalar(
            connection,
            """
            SELECT COUNT(*) FROM words w
            WHERE w.status = 'candidate'
              AND w.category = 'proper'
              AND NOT EXISTS (
                  SELECT 1 FROM word_tags t
                  WHERE t.word_id = w.id AND t.axis = 'proper_type'
              )
            """,
        )
        unsupported_proper_type = _count_records_with_type_values(
            connection,
            include=False,
        )
        specifically_classified = _count_records_with_type_values(
            connection,
            include=True,
        )
        only_other = _scalar(
            connection,
            """
            SELECT COUNT(*) FROM words w
            WHERE w.status = 'candidate'
              AND EXISTS (
                  SELECT 1 FROM word_tags t
                  WHERE t.word_id = w.id
                    AND t.axis = 'proper_type'
                    AND t.value = 'other'
              )
              AND NOT EXISTS (
                  SELECT 1 FROM word_tags t
                  WHERE t.word_id = w.id
                    AND t.axis = 'proper_type'
                    AND t.value != 'other'
              )
            """,
        )
        multiple_proper_types = _scalar(
            connection,
            """
            SELECT COUNT(*) FROM (
                SELECT w.id
                FROM words w JOIN word_tags t ON t.word_id = w.id
                WHERE w.status = 'candidate' AND t.axis = 'proper_type'
                GROUP BY w.id HAVING COUNT(DISTINCT t.value) > 1
            )
            """,
        )
        missing_proper_type_evidence = _scalar(
            connection,
            """
            SELECT COUNT(DISTINCT w.id)
            FROM words w JOIN word_tags t ON t.word_id = w.id
            WHERE w.status = 'candidate'
              AND t.axis = 'proper_type'
              AND t.evidence = ''
              AND t.reason = ''
              AND t.reference = ''
            """,
        )
    finally:
        connection.close()

    failures = _failures(
        candidate_count=candidate_count,
        out_of_scope_candidates=out_of_scope_candidates,
        missing_provenance=missing_provenance,
        without_sudachi_provenance=without_sudachi_provenance,
        with_non_sudachi_provenance=with_non_sudachi_provenance,
        missing_proper_type=missing_proper_type,
        unsupported_proper_type=unsupported_proper_type,
        missing_proper_type_evidence=missing_proper_type_evidence,
        invalid_readings=invalid_readings,
        normalized_reading_mismatches=normalized_reading_mismatches,
        signature_mismatches=signature_mismatches,
        missing_surface=missing_surface,
        missing_pos=missing_pos,
    )
    report: dict[str, object] = {
        "candidate_audit_schema_version": CANDIDATE_AUDIT_SCHEMA_VERSION,
        "passed": not failures,
        "failures": failures,
        "metadata": metadata,
        "scope": {
            "status": "candidate",
            "candidate_kinds": ["proper", "ascii_only_headword"],
            "expected_source": "sudachidict",
        },
        "counts": {
            "candidate_records": candidate_count,
            "source_entries": source_entries,
            "records_with_multiple_source_entries": multiple_source_entries,
            "categories": dict(sorted(categories.items())),
            "source_records": source_records,
            "priorities": {
                str(key): value for key, value in sorted(priorities.items())
            },
            "positions": dict(sorted(positions.items())),
            "candidate_kinds": {
                "proper": proper_candidates,
                "ascii_only_headword": ascii_headword_candidates,
                "overlap": overlapping_candidate_kinds,
            },
        },
        "completeness": {
            "missing_provenance": missing_provenance,
            "without_sudachi_provenance": without_sudachi_provenance,
            "with_non_sudachi_provenance": with_non_sudachi_provenance,
            "missing_surface": missing_surface,
            "missing_pos": missing_pos,
            "invalid_readings": invalid_readings,
            "normalized_reading_mismatches": normalized_reading_mismatches,
            "signature_mismatches": signature_mismatches,
            "missing_proper_type": missing_proper_type,
            "unsupported_proper_type": unsupported_proper_type,
            "missing_proper_type_evidence": missing_proper_type_evidence,
        },
        "classification": {
            "supported_proper_types": sorted(PROPER_TYPE_VALUES),
            "proper_type_records": proper_type_records,
            "specifically_classified_records": specifically_classified,
            "only_other_records": only_other,
            "multiple_proper_types": multiple_proper_types,
            "specific_coverage": (
                specifically_classified / proper_candidates
                if proper_candidates
                else None
            ),
            "note": (
                "proper_type_records counts records per tag and can exceed the "
                "candidate total when a record has multiple source-backed types"
            ),
        },
        "adoption_unit": {
            "kind": "merged_lexicon_record",
            "key": ["surface", "normalized_reading"],
            "source_entries": source_entries,
            "merged_records": candidate_count,
            "records_with_multiple_source_entries": multiple_source_entries,
            "quality_state": "candidate",
            "search_layer": "auxiliary",
            "promotion_policy": (
                "do not bulk-promote; retain source entries and require "
                "independent semantic evidence for accepted status"
            ),
        },
    }
    return CandidateAuditResult(passed=not failures, report=report)


def write_candidate_audit_report(
    result: CandidateAuditResult,
    output: str | Path,
) -> None:
    path = Path(output)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(result.report, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )


def _scalar(connection: sqlite3.Connection, query: str) -> int:
    return int(connection.execute(query).fetchone()[0])


def _count_records_with_type_values(
    connection: sqlite3.Connection,
    *,
    include: bool,
) -> int:
    values = sorted(PROPER_TYPE_VALUES - ({"other"} if include else set()))
    placeholders = ", ".join("?" for _ in values)
    operator = "IN" if include else "NOT IN"
    return int(
        connection.execute(
            f"""
            SELECT COUNT(*) FROM words w
            WHERE w.status = 'candidate'
              AND EXISTS (
                  SELECT 1 FROM word_tags t
                  WHERE t.word_id = w.id
                    AND t.axis = 'proper_type'
                    AND t.value {operator} ({placeholders})
              )
            """,
            values,
        ).fetchone()[0]
    )


def _failures(
    *,
    candidate_count: int,
    out_of_scope_candidates: int,
    missing_provenance: int,
    without_sudachi_provenance: int,
    with_non_sudachi_provenance: int,
    missing_proper_type: int,
    unsupported_proper_type: int,
    missing_proper_type_evidence: int,
    invalid_readings: int,
    normalized_reading_mismatches: int,
    signature_mismatches: int,
    missing_surface: int,
    missing_pos: int,
) -> list[str]:
    checks = (
        ("no_candidates", int(candidate_count == 0)),
        ("candidate_out_of_scope", out_of_scope_candidates),
        ("missing_provenance", missing_provenance),
        ("candidate_without_sudachi_provenance", without_sudachi_provenance),
        ("candidate_with_non_sudachi_provenance", with_non_sudachi_provenance),
        ("missing_proper_type", missing_proper_type),
        ("unsupported_proper_type", unsupported_proper_type),
        ("missing_proper_type_evidence", missing_proper_type_evidence),
        ("invalid_readings", invalid_readings),
        ("normalized_reading_mismatches", normalized_reading_mismatches),
        ("signature_mismatches", signature_mismatches),
        ("missing_surface", missing_surface),
        ("missing_pos", missing_pos),
    )
    return [f"{name}:{count}" for name, count in checks if count]
