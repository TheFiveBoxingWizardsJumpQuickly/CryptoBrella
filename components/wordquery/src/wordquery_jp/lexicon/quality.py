"""Structural, regression, and update quality reports."""

from __future__ import annotations

import csv
import json
import random
import sqlite3
from collections import Counter
from dataclasses import dataclass
from pathlib import Path

from wordquery_jp.lexicon.formal_review import evaluate_formal_human_gate
from wordquery_jp.normalization import (
    InvalidReading,
    normalize_dictionary_reading,
    normalize_reading,
)
from wordquery_jp.units import count_normalized_reading_units


@dataclass(frozen=True, slots=True)
class QualityResult:
    passed: bool
    report: dict[str, object]


def evaluate_database(
    database: str | Path,
    *,
    accepted_gold: str | Path = "data/gold/accepted.tsv",
    rejected_gold: str | Path = "data/gold/rejected.tsv",
    formal_sample: str | Path | None = None,
    formal_judgment: str | Path | None = None,
    exploration_samples: list[str | Path] | None = None,
) -> QualityResult:
    connection = sqlite3.connect(database)
    connection.row_factory = sqlite3.Row
    integrity = connection.execute("PRAGMA integrity_check").fetchone()[0]
    words = connection.execute("SELECT * FROM words ORDER BY id").fetchall()
    issue_counts = dict(
        connection.execute(
            "SELECT kind, COUNT(*) FROM build_issues GROUP BY kind ORDER BY kind"
        ).fetchall()
    )
    missing_provenance = connection.execute(
        """
        SELECT COUNT(*) FROM words w
        WHERE NOT EXISTS (SELECT 1 FROM provenance p WHERE p.word_id = w.id)
        """
    ).fetchone()[0]
    metadata = dict(connection.execute("SELECT key, value FROM metadata").fetchall())
    source_counts = dict(
        connection.execute(
            """
            SELECT p.source, COUNT(DISTINCT p.word_id)
            FROM provenance p JOIN words w ON w.id = p.word_id
            WHERE w.status = 'accepted'
            GROUP BY p.source ORDER BY p.source
            """
        ).fetchall()
    )
    multi_source = connection.execute(
        """
        SELECT COUNT(*) FROM (
            SELECT p.word_id FROM provenance p JOIN words w ON w.id = p.word_id
            WHERE w.status = 'accepted'
            GROUP BY p.word_id HAVING COUNT(DISTINCT p.source) > 1
        )
        """
    ).fetchone()[0]
    normalized_reading_collisions = connection.execute(
        """
        SELECT COUNT(*) FROM (
            SELECT p.word_id
            FROM provenance p
            GROUP BY p.word_id
            HAVING COUNT(DISTINCT p.reading) > 1
        )
        """
    ).fetchone()[0]
    normalized_reading_collision_examples = [
        dict(row)
        for row in connection.execute(
            """
            SELECT w.surface, w.normalized_reading,
                   GROUP_CONCAT(DISTINCT p.reading) AS original_readings
            FROM words w JOIN provenance p ON p.word_id = w.id
            GROUP BY w.id
            HAVING COUNT(DISTINCT p.reading) > 1
            ORDER BY w.surface, w.normalized_reading
            LIMIT 100
            """
        ).fetchall()
    ]
    tag_counts = dict(
        connection.execute(
            "SELECT axis, COUNT(*) FROM word_tags GROUP BY axis ORDER BY axis"
        ).fetchall()
    )
    missing_tag_evidence = connection.execute(
        """
        SELECT COUNT(*) FROM word_tags
        WHERE evidence = '' AND reason = '' AND reference = ''
        """
    ).fetchone()[0]
    connection.close()

    category_counts = Counter(row["category"] for row in words if row["status"] == "accepted")
    length_counts = Counter(
        count_normalized_reading_units(row["normalized_reading"], "kana")
        for row in words
        if row["status"] == "accepted"
    )
    invalid_readings = 0
    for row in words:
        try:
            normalize_dictionary_reading(row["reading"])
        except InvalidReading:
            invalid_readings += 1

    word_keys = {
        (row["surface"], row["normalized_reading"], row["category"])
        for row in words
        if row["status"] == "accepted"
    }
    missing_gold = []
    for row in _read_tsv(Path(accepted_gold)):
        try:
            key = (row["surface"], normalize_reading(row["reading"]), row["category"])
        except InvalidReading:
            missing_gold.append(f"invalid-gold:{row.get('surface', '')}")
            continue
        if key not in word_keys:
            missing_gold.append("/".join(key))

    rejected_present = []
    for row in _read_tsv(Path(rejected_gold)):
        try:
            normalized = normalize_reading(row["reading"])
        except InvalidReading:
            continue
        if any(key[0] == row["surface"] and key[1] == normalized for key in word_keys):
            rejected_present.append(f"{row['surface']}/{normalized}")

    if (formal_sample is None) != (formal_judgment is None):
        raise ValueError("正式ゲートにはformal_sampleとformal_judgmentの両方が必要です。")
    if formal_sample is None:
        formal_gate: dict[str, object] = {
            "formal_gate_schema_version": "1.0",
            "active": False,
            "passed": False,
            "failures": ["evidence_not_provided"],
            "method": "one-sided Clopper-Pearson exact binomial lower bound",
            "confidence": 0.95,
            "target": 0.99,
            "observed_precision": None,
            "one_sided_95_lower_bound": None,
        }
    else:
        formal_gate = evaluate_formal_human_gate(
            database,
            formal_sample,
            formal_judgment,
            exploration_samples=exploration_samples or [],
        )

    failures = []
    if integrity != "ok":
        failures.append(f"integrity:{integrity}")
    if missing_provenance:
        failures.append(f"missing_provenance:{missing_provenance}")
    if missing_tag_evidence:
        failures.append(f"missing_tag_evidence:{missing_tag_evidence}")
    if invalid_readings:
        failures.append(f"invalid_readings:{invalid_readings}")
    blocking_issue_count = sum(
        count for kind, count in issue_counts.items() if kind != "unsupported_reading"
    )
    if blocking_issue_count:
        failures.append(f"build_issues:{blocking_issue_count}")
    if missing_gold:
        failures.append(f"missing_gold:{len(missing_gold)}")
    if rejected_present:
        failures.append(f"rejected_present:{len(rejected_present)}")
    if formal_gate["active"] and not formal_gate["passed"]:
        failures.append(
            "formal_human_precision:"
            f"{formal_gate['one_sided_95_lower_bound']:.8f}<"
            f"{formal_gate['target']:.8f}"
        )

    report: dict[str, object] = {
        "passed": not failures,
        "failures": failures,
        "metadata": metadata,
        "counts": {
            "accepted": sum(row["status"] == "accepted" for row in words),
            "candidates": sum(row["status"] == "candidate" for row in words),
            "categories": dict(sorted(category_counts.items())),
            "reading_lengths": {str(key): value for key, value in sorted(length_counts.items())},
            "build_issues": issue_counts,
            "blocking_build_issues": blocking_issue_count,
            "sources": source_counts,
            "multi_source": multi_source,
            "normalized_reading_collisions": normalized_reading_collisions,
            "tags": tag_counts,
            "missing_tag_evidence": missing_tag_evidence,
            "missing_provenance": missing_provenance,
            "invalid_readings": invalid_readings,
        },
        "normalization_audit": {
            "records_with_multiple_original_readings": normalized_reading_collisions,
            "examples": normalized_reading_collision_examples,
        },
        "regression": {
            "missing_accepted": missing_gold,
            "present_rejected": rejected_present,
        },
        "formal_human_review": formal_gate,
    }
    return QualityResult(passed=not failures, report=report)


def write_report(result: QualityResult, output: str | Path) -> None:
    path = Path(output)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(result.report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )


def write_review_sample(database: str | Path, output: str | Path, per_category: int = 20) -> None:
    connection = sqlite3.connect(database)
    connection.row_factory = sqlite3.Row
    rows = connection.execute(
        """
        SELECT w.surface, w.reading, w.category, w.pos, w.priority,
               GROUP_CONCAT(DISTINCT p.source) AS sources
        FROM words w JOIN provenance p ON p.word_id = w.id
        WHERE w.status = 'accepted'
        GROUP BY w.id
        ORDER BY w.id
        """
    ).fetchall()
    connection.close()
    randomizer = random.Random(0)
    grouped: dict[str, list[sqlite3.Row]] = {}
    for row in rows:
        grouped.setdefault(row["category"], []).append(row)
    selected = []
    for category in sorted(grouped):
        candidates = grouped[category]
        selected.extend(randomizer.sample(candidates, min(per_category, len(candidates))))

    path = Path(output)
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as handle:
        fieldnames = [
            "surface",
            "reading",
            "category",
            "pos",
            "priority",
            "sources",
            "valid",
            "note",
        ]
        writer = csv.DictWriter(handle, fieldnames=fieldnames, delimiter="\t")
        writer.writeheader()
        for row in selected:
            writer.writerow({**dict(row), "valid": "", "note": ""})


def compare_databases(before: str | Path, after: str | Path) -> dict[str, object]:
    old = _word_map(before)
    new = _word_map(after)
    old_keys, new_keys = set(old), set(new)
    return {
        "added": [new[key] for key in sorted(new_keys - old_keys)],
        "removed": [old[key] for key in sorted(old_keys - new_keys)],
        "changed": [
            {"before": old[key], "after": new[key]}
            for key in sorted(old_keys & new_keys)
            if old[key] != new[key]
        ],
    }


def _word_map(database: str | Path) -> dict[tuple[str, str], dict[str, object]]:
    connection = sqlite3.connect(database)
    connection.row_factory = sqlite3.Row
    rows = connection.execute(
        "SELECT surface, normalized_reading, category, pos, priority, status FROM words"
    ).fetchall()
    connection.close()
    return {(row["surface"], row["normalized_reading"]): dict(row) for row in rows}


def _read_tsv(path: Path) -> list[dict[str, str]]:
    if not path.is_file():
        return []
    with path.open(encoding="utf-8", newline="") as handle:
        return list(csv.DictReader(handle, delimiter="\t"))
