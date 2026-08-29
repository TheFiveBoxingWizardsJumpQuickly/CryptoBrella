"""Reproducible lexicon samples and independent-review diagnostics."""

from __future__ import annotations

import csv
import hashlib
import json
import random
import sqlite3
from collections import Counter
from pathlib import Path

SAMPLE_SCHEMA_VERSION = "1.0"
RUBRIC_VERSION = "1.0"

PILOT_PROFILE = {
    "sudachi_only": 10,
    "jmdict_only": 10,
    "multi_source": 10,
}

# Risk-based rather than population-proportional: Sudachi-only entries receive
# half of the review budget because this is the least corroborated accepted layer.
BASELINE_PROFILE = {
    "sudachi_only": 150,
    "jmdict_only": 75,
    "multi_source": 75,
}

SAMPLE_FIELDS = [
    "sample_schema_version",
    "sample_id",
    "database_input_hash",
    "sampling_seed",
    "stratum",
    "population_size",
    "sample_size",
    "sample_weight",
    "surface",
    "reading",
    "normalized_reading",
    "claimed_category",
    "status",
    "pos",
    "priority",
    "sources",
]

# Source, priority, stratum and population fields are intentionally absent: judges
# see the entry itself, not signals that could encourage deference to a source.
JUDGMENT_FIELDS = [
    "rubric_version",
    "sample_id",
    "surface",
    "reading",
    "normalized_reading",
    "claimed_category",
    "pos",
    "reviewer",
    "reviewer_kind",
    "model_version",
    "prompt_version",
    "lexicality",
    "reading_match",
    "headword_form",
    "form_integrity",
    "expected_category",
    "category_match",
    "overall_label",
    "confidence",
    "reason_codes",
    "review_note",
]

AXIS_FIELDS = (
    "lexicality",
    "reading_match",
    "headword_form",
    "form_integrity",
    "category_match",
)
ENTRY_FIELDS = (
    "sample_id",
    "surface",
    "reading",
    "normalized_reading",
    "claimed_category",
    "pos",
)
JUDGMENT_VALUE_FIELDS = (
    *AXIS_FIELDS,
    "expected_category",
    "overall_label",
    "confidence",
    "reason_codes",
    "review_note",
)
AXIS_VALUES = {"pass", "fail", "uncertain"}
LABEL_VALUES = {"valid", "invalid", "uncertain"}
CATEGORY_VALUES = {"general", "proper", "function", "uncertain"}


def write_stratified_review_sample(
    database: str | Path,
    output: str | Path,
    *,
    sizes: dict[str, int] | None = None,
    seed: int = 0,
    overwrite: bool = False,
) -> dict[str, object]:
    """Write a stable accepted-general sample across provenance layers."""
    requested = sizes or BASELINE_PROFILE
    unknown = set(requested) - set(BASELINE_PROFILE)
    if unknown:
        raise ValueError(f"不明な評価層です: {', '.join(sorted(unknown))}")
    if any(size < 0 for size in requested.values()):
        raise ValueError("サンプル件数は0以上で指定してください。")

    rows, input_hash = _general_rows(database)
    grouped: dict[str, list[dict[str, object]]] = {name: [] for name in BASELINE_PROFILE}
    for row in rows:
        stratum = _source_stratum(set(str(row["sources"]).split(",")))
        if stratum in grouped:
            grouped[stratum].append(row)

    selected_rows: list[dict[str, object]] = []
    populations: dict[str, int] = {}
    selected_counts: dict[str, int] = {}
    for stratum in BASELINE_PROFILE:
        candidates = sorted(
            grouped[stratum],
            key=lambda row: (
                str(row["surface"]),
                str(row["normalized_reading"]),
                int(row["id"]),
            ),
        )
        population = len(candidates)
        count = min(requested.get(stratum, 0), population)
        populations[stratum] = population
        selected_counts[stratum] = count
        randomizer = random.Random(f"{seed}:{stratum}:{input_hash}")
        chosen = randomizer.sample(candidates, count)
        for row in chosen:
            selected_rows.append(
                {
                    "sample_schema_version": SAMPLE_SCHEMA_VERSION,
                    "sample_id": _sample_id(row),
                    "database_input_hash": input_hash,
                    "sampling_seed": seed,
                    "stratum": stratum,
                    "population_size": population,
                    "sample_size": count,
                    "sample_weight": f"{population / count:.8f}" if count else "0",
                    "surface": row["surface"],
                    "reading": row["reading"],
                    "normalized_reading": row["normalized_reading"],
                    "claimed_category": row["category"],
                    "status": row["status"],
                    "pos": row["pos"],
                    "priority": row["priority"],
                    "sources": row["sources"],
                }
            )

    selected_rows.sort(key=lambda row: (str(row["stratum"]), str(row["sample_id"])))
    _write_tsv(output, SAMPLE_FIELDS, selected_rows, overwrite=overwrite)
    return {
        "sample_schema_version": SAMPLE_SCHEMA_VERSION,
        "database_input_hash": input_hash,
        "output": str(output),
        "seed": seed,
        "populations": populations,
        "selected": selected_counts,
        "total": len(selected_rows),
    }


def write_judgment_template(
    sample: str | Path,
    output: str | Path,
    *,
    reviewer: str,
    reviewer_kind: str,
    model_version: str,
    prompt_version: str,
    overwrite: bool = False,
) -> int:
    """Create a blind judgment template without provenance or sampling signals."""
    metadata = (reviewer, reviewer_kind, model_version, prompt_version)
    if not all(value.strip() for value in metadata):
        raise ValueError("評価者・種別・モデル・プロンプト版は必須です。")
    if reviewer_kind not in {"llm", "human"}:
        raise ValueError("評価者種別は llm または human で指定してください。")
    rows = _read_sample(sample)
    rendered: list[dict[str, object]] = []
    for row in rows:
        rendered.append(
            {
                "rubric_version": RUBRIC_VERSION,
                **{field: row[field] for field in ENTRY_FIELDS},
                "reviewer": reviewer,
                "reviewer_kind": reviewer_kind,
                "model_version": model_version,
                "prompt_version": prompt_version,
                **{field: "" for field in JUDGMENT_VALUE_FIELDS},
            }
        )
    _write_tsv(output, JUDGMENT_FIELDS, rendered, overwrite=overwrite)
    return len(rendered)


def compare_judgments(
    sample: str | Path, judgment_files: list[str | Path]
) -> dict[str, object]:
    """Validate and compare two or more independent judgments without gating."""
    if len(judgment_files) < 2:
        raise ValueError("比較には2つ以上の判定ファイルが必要です。")
    sample_rows = _read_sample(sample)
    sample_by_id = _unique_rows(sample_rows, "sample_id", "サンプル")
    judges = [_load_judgments(path, sample_by_id) for path in judgment_files]
    reviewer_names = [str(judge["reviewer"]) for judge in judges]
    if len(set(reviewer_names)) != len(reviewer_names):
        raise ValueError("判定ファイル間でreviewerが重複しています。")

    complete_rows = [judge["complete_rows"] for judge in judges]
    common_ids = set.intersection(*(set(rows) for rows in complete_rows))
    agreement: dict[str, dict[str, object]] = {}
    for axis in (*AXIS_FIELDS, "overall_label"):
        agreed = sum(
            len({rows[sample_id][axis] for rows in complete_rows}) == 1
            for sample_id in common_ids
        )
        agreement[axis] = _rate_summary(agreed, len(common_ids))

    consensus = Counter[str]()
    per_stratum: dict[str, Counter[str]] = {}
    disagreement_ids: list[str] = []
    weighted_valid = 0.0
    weighted_resolved = 0.0
    weighted_total = 0.0
    for sample_id in sorted(common_ids):
        labels = {rows[sample_id]["overall_label"] for rows in complete_rows}
        sample_row = sample_by_id[sample_id]
        stratum = sample_row["stratum"]
        counts = per_stratum.setdefault(stratum, Counter())
        weight = float(sample_row["sample_weight"])
        weighted_total += weight
        if len(labels) != 1:
            outcome = "disagreement"
            disagreement_ids.append(sample_id)
        else:
            outcome = labels.pop()
            if outcome in {"valid", "invalid"}:
                weighted_resolved += weight
                if outcome == "valid":
                    weighted_valid += weight
        consensus[outcome] += 1
        counts[outcome] += 1

    resolved = consensus["valid"] + consensus["invalid"]
    is_risk_panel = bool(sample_rows) and all(
        row.get("sample_kind") == "risk_panel"
        and row.get("diagnostic_only") == "true"
        for row in sample_rows
    )
    diagnostic = {
        "resolved": resolved,
        "record_precision": consensus["valid"] / resolved if resolved else None,
        "uncertain_rate": consensus["uncertain"] / len(common_ids) if common_ids else None,
        "disagreement_rate": consensus["disagreement"] / len(common_ids) if common_ids else None,
    }
    if is_risk_panel:
        diagnostic["population_estimate"] = False
        diagnostic["note"] = (
            "risk panels are overlapping diagnostic samples and are not weighted "
            "or extrapolated to the lexicon population"
        )
    else:
        diagnostic["population_weighted_record_precision"] = (
            weighted_valid / weighted_resolved if weighted_resolved else None
        )
        diagnostic["population_weighted_uncertain_or_disagreement_rate"] = (
            (weighted_total - weighted_resolved) / weighted_total if weighted_total else None
        )
    return {
        "review_schema_version": SAMPLE_SCHEMA_VERSION,
        "rubric_version": RUBRIC_VERSION,
        "diagnostic_only": True,
        "sample_count": len(sample_rows),
        "judges": [judge["summary"] for judge in judges],
        "common_complete": len(common_ids),
        "agreement": agreement,
        "consensus": dict(sorted(consensus.items())),
        "diagnostic": diagnostic,
        "per_stratum": {
            name: dict(sorted(counts.items())) for name, counts in sorted(per_stratum.items())
        },
        "disagreement_ids": disagreement_ids,
    }


def write_comparison(
    report: dict[str, object], output: str | Path, *, overwrite: bool = False
) -> None:
    path = Path(output)
    _ensure_writable(path, overwrite)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def _general_rows(database: str | Path) -> tuple[list[dict[str, object]], str]:
    connection = sqlite3.connect(f"file:{Path(database).resolve()}?mode=ro", uri=True)
    connection.row_factory = sqlite3.Row
    metadata = dict(connection.execute("SELECT key, value FROM metadata"))
    rows = connection.execute(
        """
        SELECT w.id, w.surface, w.reading, w.normalized_reading, w.category,
               w.status, w.pos, w.priority,
               GROUP_CONCAT(DISTINCT p.source) AS sources
        FROM words w JOIN provenance p ON p.word_id = w.id
        WHERE w.status = 'accepted' AND w.category = 'general'
        GROUP BY w.id
        ORDER BY w.surface, w.normalized_reading, w.id
        """
    ).fetchall()
    connection.close()
    rendered = []
    for raw_row in rows:
        row = dict(raw_row)
        row["sources"] = ",".join(sorted(str(row["sources"]).split(",")))
        rendered.append(row)
    return rendered, metadata.get("input_hash", "unknown")


def _source_stratum(sources: set[str]) -> str:
    if "manual" in sources:
        return "manual"
    if {"jmdict", "sudachidict"} <= sources:
        return "multi_source"
    if "jmdict" in sources:
        return "jmdict_only"
    if "sudachidict" in sources:
        return "sudachi_only"
    return "other"


def _sample_id(row: dict[str, object]) -> str:
    value = "\0".join(
        (str(row["surface"]), str(row["normalized_reading"]), str(row["category"]))
    )
    return hashlib.sha256(value.encode()).hexdigest()[:24]


def _read_sample(path: str | Path) -> list[dict[str, str]]:
    rows = _read_tsv(path, required=set(SAMPLE_FIELDS))
    for row in rows:
        if row["sample_schema_version"] != SAMPLE_SCHEMA_VERSION:
            raise ValueError(f"未対応のサンプルスキーマです: {row['sample_schema_version']}")
        expected_id = _sample_id(
            {
                "surface": row["surface"],
                "normalized_reading": row["normalized_reading"],
                "category": row["claimed_category"],
            }
        )
        if row["sample_id"] != expected_id:
            raise ValueError(f"サンプル内容とIDが一致しません: {row['sample_id']}")
    _unique_rows(rows, "sample_id", "サンプル")
    return rows


def _load_judgments(
    path: str | Path, sample_by_id: dict[str, dict[str, str]]
) -> dict[str, object]:
    rows = _read_tsv(path, required=set(JUDGMENT_FIELDS))
    by_id = _unique_rows(rows, "sample_id", f"判定ファイル {path}")
    unknown = set(by_id) - set(sample_by_id)
    if unknown:
        raise ValueError(f"サンプルにないIDがあります: {', '.join(sorted(unknown))}")
    reviewers = {row["reviewer"].strip() for row in rows}
    if len(reviewers) != 1 or not next(iter(reviewers), ""):
        raise ValueError(f"{path}: reviewerは1ファイルにつき1名で指定してください。")
    complete_rows: dict[str, dict[str, str]] = {}
    for sample_id, row in by_id.items():
        for field in ENTRY_FIELDS:
            if row[field] != sample_by_id[sample_id][field]:
                raise ValueError(f"{path}: {sample_id} の{field}がサンプルと一致しません。")
        _validate_judgment(row, path)
        populated = [bool(row[field].strip()) for field in JUDGMENT_VALUE_FIELDS]
        if any(populated) and not all(populated):
            raise ValueError(f"{path}: {sample_id} の判定が途中です。")
        if all(populated):
            complete_rows[sample_id] = row
    reviewer = reviewers.pop()
    summary = {
        "path": str(path),
        "reviewer": reviewer,
        "reviewer_kind": _single_value(rows, "reviewer_kind", path),
        "model_version": _single_value(rows, "model_version", path),
        "prompt_version": _single_value(rows, "prompt_version", path),
        "rows": len(rows),
        "complete": len(complete_rows),
    }
    return {"reviewer": reviewer, "summary": summary, "complete_rows": complete_rows}


def _validate_judgment(row: dict[str, str], path: str | Path) -> None:
    if row["rubric_version"] != RUBRIC_VERSION:
        raise ValueError(f"{path}: 未対応のrubric_versionです: {row['rubric_version']}")
    if row["reviewer_kind"] not in {"llm", "human"}:
        raise ValueError(f"{path}: reviewer_kindはllmまたはhumanです。")
    for field in AXIS_FIELDS:
        value = row[field].strip()
        if value and value not in AXIS_VALUES:
            raise ValueError(f"{path}: {field} の値が不正です: {value}")
    expected_category = row["expected_category"].strip()
    if expected_category and expected_category not in CATEGORY_VALUES:
        raise ValueError(f"{path}: expected_category の値が不正です: {expected_category}")
    label = row["overall_label"].strip()
    if label and label not in LABEL_VALUES:
        raise ValueError(f"{path}: overall_label の値が不正です: {label}")
    confidence = row["confidence"].strip()
    if confidence:
        try:
            confidence_number = float(confidence)
        except ValueError as exc:
            raise ValueError(f"{path}: confidenceは0から1の数値です。") from exc
        if not 0 <= confidence_number <= 1:
            raise ValueError(f"{path}: confidenceは0から1の数値です。")
    if not label:
        return
    axis_values = [row[field].strip() for field in AXIS_FIELDS]
    derived = (
        "invalid"
        if "fail" in axis_values
        else "uncertain"
        if "uncertain" in axis_values
        else "valid"
    )
    if label != derived:
        raise ValueError(f"{path}: 必須軸から導かれるoverall_labelは{derived}です。")
    category_match = row["category_match"].strip()
    claimed = row["claimed_category"]
    if expected_category == "uncertain" and category_match != "uncertain":
        raise ValueError(f"{path}: カテゴリ不明時はcategory_matchもuncertainです。")
    if expected_category in CATEGORY_VALUES - {"uncertain"}:
        expected_match = "pass" if expected_category == claimed else "fail"
        if category_match != expected_match:
            raise ValueError(f"{path}: expected_categoryとcategory_matchが矛盾しています。")


def _single_value(rows: list[dict[str, str]], field: str, path: str | Path) -> str:
    values = {row[field].strip() for row in rows}
    if len(values) != 1 or not next(iter(values), ""):
        raise ValueError(f"{path}: {field}は1ファイルで同一の必須値です。")
    return values.pop()


def _rate_summary(numerator: int, denominator: int) -> dict[str, object]:
    return {
        "agreed": numerator,
        "compared": denominator,
        "rate": numerator / denominator if denominator else None,
    }


def _unique_rows(
    rows: list[dict[str, str]], key: str, label: str
) -> dict[str, dict[str, str]]:
    result: dict[str, dict[str, str]] = {}
    for row in rows:
        value = row.get(key, "").strip()
        if not value:
            raise ValueError(f"{label}に{key}がない行があります。")
        if value in result:
            raise ValueError(f"{label}に重複IDがあります: {value}")
        result[value] = row
    return result


def _read_tsv(path: str | Path, *, required: set[str]) -> list[dict[str, str]]:
    with Path(path).open(encoding="utf-8", newline="") as handle:
        reader = csv.DictReader(handle, delimiter="\t")
        missing = required - set(reader.fieldnames or ())
        if missing:
            raise ValueError(f"{path}: 必須列がありません: {', '.join(sorted(missing))}")
        return list(reader)


def _write_tsv(
    path: str | Path,
    fieldnames: list[str],
    rows: list[dict[str, object]],
    *,
    overwrite: bool,
) -> None:
    output = Path(path)
    _ensure_writable(output, overwrite)
    output.parent.mkdir(parents=True, exist_ok=True)
    with output.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames, delimiter="\t")
        writer.writeheader()
        writer.writerows(rows)


def _ensure_writable(path: Path, overwrite: bool) -> None:
    if path.exists() and not overwrite:
        raise FileExistsError(f"既存ファイルを上書きしません: {path}（--forceで上書き）")
