"""Reproducible diagnostic risk panels for independent lexicon review."""

from __future__ import annotations

import random
import sqlite3
import unicodedata
from collections import Counter
from pathlib import Path

from wordquery_jp.units import count_normalized_reading_units

from .review import (
    SAMPLE_FIELDS,
    SAMPLE_SCHEMA_VERSION,
    _load_judgments,
    _read_sample,
    _read_tsv,
    _sample_id,
    _unique_rows,
    _write_tsv,
    compare_judgments,
)

RISK_SAMPLE_SCHEMA_VERSION = "1.0"
RISK_CRITERIA_VERSION = "1.0"
LONG_READING_MINIMUM = 15
RISK_PANELS = (
    "alnum_or_symbol_general",
    "candidate_other",
    "long_reading_general",
    "proper_pos_general",
)
RISK_SAMPLE_FIELDS = [
    "risk_sample_schema_version",
    *SAMPLE_FIELDS,
    "sample_kind",
    "criteria_version",
    "risk_flags",
    "selected_for",
    "diagnostic_only",
]


def write_risk_review_sample(
    database: str | Path,
    output: str | Path,
    *,
    per_panel: int = 30,
    seed: int = 0,
    overwrite: bool = False,
) -> dict[str, object]:
    """Draw overlapping risk panels and emit each selected record only once."""

    if isinstance(per_panel, bool) or not isinstance(per_panel, int) or per_panel < 1:
        raise ValueError("リスクパネルの抽出件数は1以上の整数で指定してください。")
    connection = sqlite3.connect(
        f"file:{Path(database).resolve()}?mode=ro",
        uri=True,
    )
    connection.row_factory = sqlite3.Row
    try:
        metadata = dict(connection.execute("SELECT key, value FROM metadata"))
        input_hash = metadata.get("input_hash")
        if not input_hash:
            raise ValueError("辞書にinput_hashがありません。")
        panels, flags_by_id = _risk_populations(connection)
        all_risk_ids = set().union(*panels.values())
        selected_for: dict[int, set[str]] = {}
        drawn: dict[str, int] = {}
        for panel in RISK_PANELS:
            population = panels[panel]
            count = min(per_panel, len(population))
            drawn[panel] = count
            randomizer = random.Random(
                f"risk:{seed}:{panel}:{input_hash}:{RISK_CRITERIA_VERSION}"
            )
            for word_id in randomizer.sample(population, count):
                selected_for.setdefault(word_id, set()).add(panel)

        selected_ids = sorted(selected_for)
        if not selected_ids:
            raise ValueError("リスクパネルの対象語がありません。")
        selected_rows = _selected_rows(connection, selected_ids)
    finally:
        connection.close()

    sample_size = len(selected_rows)
    rendered = []
    for row in selected_rows:
        word_id = int(row["id"])
        rendered.append(
            {
                "risk_sample_schema_version": RISK_SAMPLE_SCHEMA_VERSION,
                "sample_schema_version": SAMPLE_SCHEMA_VERSION,
                "sample_id": _sample_id(row),
                "database_input_hash": input_hash,
                "sampling_seed": seed,
                "stratum": "risk_panel",
                "population_size": len(all_risk_ids),
                "sample_size": sample_size,
                "sample_weight": "1",
                "surface": row["surface"],
                "reading": row["reading"],
                "normalized_reading": row["normalized_reading"],
                "claimed_category": row["category"],
                "status": row["status"],
                "pos": row["pos"],
                "priority": row["priority"],
                "sources": row["sources"],
                "sample_kind": "risk_panel",
                "criteria_version": RISK_CRITERIA_VERSION,
                "risk_flags": "|".join(sorted(flags_by_id[word_id])),
                "selected_for": "|".join(sorted(selected_for[word_id])),
                "diagnostic_only": "true",
            }
        )
    rendered.sort(key=lambda row: str(row["sample_id"]))
    _write_tsv(
        output,
        RISK_SAMPLE_FIELDS,
        rendered,
        overwrite=overwrite,
    )
    draw_count = sum(drawn.values())
    risk_flag_sample_counts = {
        panel: sum(
            panel in str(row["risk_flags"]).split("|")
            for row in rendered
        )
        for panel in RISK_PANELS
    }
    return {
        "risk_sample_schema_version": RISK_SAMPLE_SCHEMA_VERSION,
        "criteria_version": RISK_CRITERIA_VERSION,
        "database_input_hash": input_hash,
        "output": str(output),
        "seed": seed,
        "per_panel": per_panel,
        "long_reading_minimum": LONG_READING_MINIMUM,
        "populations": {
            panel: len(panels[panel]) for panel in RISK_PANELS
        },
        "union_population": len(all_risk_ids),
        "drawn": drawn,
        "draw_count": draw_count,
        "unique_selected": sample_size,
        "selection_overlap": draw_count - sample_size,
        "risk_flag_sample_counts": risk_flag_sample_counts,
        "multi_flag_records": sum(
            "|" in str(row["risk_flags"]) for row in rendered
        ),
        "diagnostic_only": True,
        "population_estimate": False,
    }


def compare_risk_judgments(
    sample: str | Path,
    judgment_files: list[str | Path],
) -> dict[str, object]:
    """Compare independent judgments without producing a population estimate."""

    sample_rows = _validate_risk_sample(sample)
    base = compare_judgments(sample, judgment_files)
    sample_by_id = _unique_rows(sample_rows, "sample_id", "リスク標本")
    judges = [_load_judgments(path, sample_by_id) for path in judgment_files]
    complete_rows = [judge["complete_rows"] for judge in judges]
    common_ids = set.intersection(*(set(rows) for rows in complete_rows))
    per_flag: dict[str, Counter[str]] = {
        panel: Counter() for panel in RISK_PANELS
    }
    for sample_id in sorted(common_ids):
        labels = {rows[sample_id]["overall_label"] for rows in complete_rows}
        outcome = labels.pop() if len(labels) == 1 else "disagreement"
        for flag in sample_by_id[sample_id]["risk_flags"].split("|"):
            per_flag[flag][outcome] += 1

    diagnostic = base["diagnostic"]
    diagnostic.pop("population_weighted_record_precision", None)
    diagnostic.pop(
        "population_weighted_uncertain_or_disagreement_rate",
        None,
    )
    diagnostic["population_estimate"] = False
    diagnostic["note"] = (
        "risk panels are overlapping diagnostic samples and are not weighted "
        "or extrapolated to the lexicon population"
    )
    base.update(
        {
            "risk_sample_schema_version": RISK_SAMPLE_SCHEMA_VERSION,
            "sample_kind": "risk_panel",
            "criteria_version": RISK_CRITERIA_VERSION,
            "per_risk_flag": {
                panel: dict(sorted(counts.items()))
                for panel, counts in per_flag.items()
            },
            "risk_flag_sample_counts": {
                panel: sum(
                    panel in row["risk_flags"].split("|")
                    for row in sample_rows
                )
                for panel in RISK_PANELS
            },
        }
    )
    return base


def _risk_populations(
    connection: sqlite3.Connection,
) -> tuple[dict[str, list[int]], dict[int, set[str]]]:
    panels: dict[str, list[int]] = {panel: [] for panel in RISK_PANELS}
    flags_by_id: dict[int, set[str]] = {}
    rows = connection.execute(
        """
        SELECT id, surface, normalized_reading, pos
        FROM words
        WHERE status = 'accepted' AND category = 'general'
        ORDER BY id
        """
    )
    for row in rows:
        word_id = int(row["id"])
        flags: set[str] = set()
        if _has_alnum_or_symbol(row["surface"]):
            flags.add("alnum_or_symbol_general")
        if (
            count_normalized_reading_units(
                row["normalized_reading"],
                "kana",
            )
            >= LONG_READING_MINIMUM
        ):
            flags.add("long_reading_general")
        if "固有名詞" in row["pos"]:
            flags.add("proper_pos_general")
        for flag in flags:
            panels[flag].append(word_id)
        if flags:
            flags_by_id[word_id] = flags

    candidate_other_ids = [
        int(row[0])
        for row in connection.execute(
            """
            SELECT w.id
            FROM words w
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
            ORDER BY w.id
            """
        )
    ]
    panels["candidate_other"] = candidate_other_ids
    for word_id in candidate_other_ids:
        flags_by_id[word_id] = {"candidate_other"}
    return panels, flags_by_id


def _selected_rows(
    connection: sqlite3.Connection,
    word_ids: list[int],
) -> list[dict[str, object]]:
    placeholders = ", ".join("?" for _ in word_ids)
    rows = connection.execute(
        f"""
        SELECT w.id, w.surface, w.reading, w.normalized_reading, w.category,
               w.status, w.pos, w.priority,
               GROUP_CONCAT(DISTINCT p.source) AS sources
        FROM words w JOIN provenance p ON p.word_id = w.id
        WHERE w.id IN ({placeholders})
        GROUP BY w.id
        ORDER BY w.id
        """,
        word_ids,
    ).fetchall()
    rendered = []
    for raw_row in rows:
        row = dict(raw_row)
        row["sources"] = ",".join(sorted(str(row["sources"]).split(",")))
        rendered.append(row)
    if len(rendered) != len(word_ids):
        raise ValueError("選択したリスク項目の来歴が不足しています。")
    return rendered


def _validate_risk_sample(
    sample: str | Path,
) -> list[dict[str, str]]:
    _read_tsv(sample, required=set(RISK_SAMPLE_FIELDS))
    rows = _read_sample(sample)
    if not rows:
        raise ValueError("リスク標本が空です。")
    for row in rows:
        if row["risk_sample_schema_version"] != RISK_SAMPLE_SCHEMA_VERSION:
            raise ValueError("未対応のリスク標本スキーマです。")
        if row["sample_kind"] != "risk_panel":
            raise ValueError("リスク標本のsample_kindが正しくありません。")
        if row["criteria_version"] != RISK_CRITERIA_VERSION:
            raise ValueError("未対応のリスク基準版です。")
        if row["diagnostic_only"] != "true":
            raise ValueError("リスク標本はdiagnostic_only=trueである必要があります。")
        flags = set(row["risk_flags"].split("|"))
        selected_for = set(row["selected_for"].split("|"))
        if not flags or not flags <= set(RISK_PANELS):
            raise ValueError("リスク標本のrisk_flagsが正しくありません。")
        if not selected_for or not selected_for <= flags:
            raise ValueError("リスク標本のselected_forが正しくありません。")
        if row["sample_weight"] != "1":
            raise ValueError("リスク標本へ母集団重みを設定できません。")
    _single_value(rows, "database_input_hash")
    _single_value(rows, "sampling_seed")
    _single_value(rows, "population_size")
    _single_value(rows, "sample_size")
    if int(rows[0]["sample_size"]) != len(rows):
        raise ValueError("リスク標本のsample_sizeが実際の行数と一致しません。")
    return rows


def _single_value(rows: list[dict[str, str]], field: str) -> str:
    values = {row[field] for row in rows}
    if len(values) != 1 or not next(iter(values), ""):
        raise ValueError(f"リスク標本の{field}は全行で同一の必須値です。")
    return values.pop()


def _has_alnum_or_symbol(surface: str) -> bool:
    normalized = unicodedata.normalize("NFKC", surface)
    return any(character.isascii() and character.isalnum() for character in normalized) or any(
        unicodedata.category(character)[0] in {"P", "S"} for character in surface
    )
