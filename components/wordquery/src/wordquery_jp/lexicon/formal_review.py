"""Independent uniform human-review samples and an exact precision gate."""

from __future__ import annotations

import hashlib
import json
import math
import random
from collections import Counter
from pathlib import Path

from .review import (
    SAMPLE_FIELDS,
    SAMPLE_SCHEMA_VERSION,
    _general_rows,
    _load_judgments,
    _read_sample,
    _read_tsv,
    _sample_id,
    _unique_rows,
    _write_tsv,
)

FORMAL_SAMPLE_SCHEMA_VERSION = "1.0"
FORMAL_GATE_SCHEMA_VERSION = "1.0"
FORMAL_SAMPLE_SIZES = {300, 473}
FORMAL_SAMPLE_FIELDS = [
    "formal_sample_schema_version",
    *SAMPLE_FIELDS,
    "sample_purpose",
    "sampling_method",
    "excluded_sample_hashes",
]
_SAMPLE_PURPOSE = "formal_confirmation"
_SAMPLING_METHOD = "uniform_without_replacement_excluding_exploration"


def write_formal_review_sample(
    database: str | Path,
    output: str | Path,
    *,
    exploration_samples: list[str | Path],
    size: int = 300,
    seed: int = 0,
    overwrite: bool = False,
) -> dict[str, object]:
    """Write a uniform general-word sample disjoint from exploration evidence."""

    if size not in FORMAL_SAMPLE_SIZES:
        allowed = ", ".join(str(value) for value in sorted(FORMAL_SAMPLE_SIZES))
        raise ValueError(f"正式確認標本の件数は{allowed}のいずれかです。")
    exploration_ids, exploration_hashes = _exploration_evidence(exploration_samples)
    rows, input_hash = _general_rows(database)
    selected, eligible_count = _select_rows(
        rows,
        input_hash=input_hash,
        excluded_ids=exploration_ids,
        size=size,
        seed=seed,
    )
    hashes_json = json.dumps(exploration_hashes, separators=(",", ":"))
    rendered = [
        {
            "formal_sample_schema_version": FORMAL_SAMPLE_SCHEMA_VERSION,
            "sample_schema_version": SAMPLE_SCHEMA_VERSION,
            "sample_id": _sample_id(row),
            "database_input_hash": input_hash,
            "sampling_seed": seed,
            "stratum": "formal_uniform",
            "population_size": eligible_count,
            "sample_size": size,
            "sample_weight": f"{eligible_count / size:.8f}",
            "surface": row["surface"],
            "reading": row["reading"],
            "normalized_reading": row["normalized_reading"],
            "claimed_category": row["category"],
            "status": row["status"],
            "pos": row["pos"],
            "priority": row["priority"],
            "sources": row["sources"],
            "sample_purpose": _SAMPLE_PURPOSE,
            "sampling_method": _SAMPLING_METHOD,
            "excluded_sample_hashes": hashes_json,
        }
        for row in selected
    ]
    rendered.sort(key=lambda row: str(row["sample_id"]))
    _write_tsv(
        output,
        FORMAL_SAMPLE_FIELDS,
        rendered,
        overwrite=overwrite,
    )
    return {
        "formal_sample_schema_version": FORMAL_SAMPLE_SCHEMA_VERSION,
        "database_input_hash": input_hash,
        "output": str(output),
        "seed": seed,
        "eligible_population": eligible_count,
        "selected": len(rendered),
        "exploration_ids": len(exploration_ids),
        "excluded_exploration_ids": len(rows) - eligible_count,
        "excluded_sample_hashes": exploration_hashes,
        "overlap_with_exploration": 0,
    }


def evaluate_formal_human_gate(
    database: str | Path,
    sample: str | Path,
    judgment: str | Path,
    *,
    exploration_samples: list[str | Path],
    target: float = 0.99,
    confidence: float = 0.95,
) -> dict[str, object]:
    """Validate formal evidence and apply a one-sided exact binomial lower bound."""

    if not 0 < target < 1:
        raise ValueError("正式ゲートの目標値は0から1の間で指定してください。")
    if not 0 < confidence < 1:
        raise ValueError("正式ゲートの信頼水準は0から1の間で指定してください。")
    sample_rows, sample_metadata = _validate_formal_sample(
        database,
        sample,
        exploration_samples=exploration_samples,
    )
    sample_by_id = _unique_rows(sample_rows, "sample_id", "正式確認標本")
    judge = _load_judgments(judgment, sample_by_id)
    summary = judge["summary"]
    if summary["reviewer_kind"] != "human":
        raise ValueError("正式ゲートにはreviewer_kind=humanの判定だけを使用できます。")

    complete_rows = judge["complete_rows"]
    label_counts = Counter(
        row["overall_label"] for row in complete_rows.values()
    )
    sample_size = len(sample_rows)
    complete = len(complete_rows)
    unresolved = label_counts["uncertain"]
    active = complete == sample_size and unresolved == 0
    valid = label_counts["valid"]
    invalid = label_counts["invalid"]
    observed = valid / sample_size if active else None
    alpha = 1 - confidence
    lower_bound = (
        clopper_pearson_lower_bound(valid, sample_size, alpha=alpha)
        if active
        else None
    )
    passed = bool(active and lower_bound is not None and lower_bound >= target)
    failures: list[str] = []
    if complete != sample_size:
        failures.append(f"incomplete:{complete}/{sample_size}")
    if unresolved:
        failures.append(f"uncertain:{unresolved}")
    if active and not passed:
        failures.append(f"lower_bound:{lower_bound:.8f}<{target:.8f}")

    return {
        "formal_gate_schema_version": FORMAL_GATE_SCHEMA_VERSION,
        "active": active,
        "passed": passed,
        "failures": failures,
        "method": "one-sided Clopper-Pearson exact binomial lower bound",
        "confidence": confidence,
        "target": target,
        "observed_precision": observed,
        "one_sided_95_lower_bound": lower_bound,
        "sample": sample_metadata,
        "review": {
            **summary,
            "valid": valid,
            "invalid": invalid,
            "uncertain": unresolved,
        },
    }


def clopper_pearson_lower_bound(
    successes: int,
    trials: int,
    *,
    alpha: float = 0.05,
) -> float:
    """Return the one-sided exact binomial lower confidence bound."""

    if (
        isinstance(successes, bool)
        or isinstance(trials, bool)
        or not isinstance(successes, int)
        or not isinstance(trials, int)
        or trials < 1
        or successes < 0
        or successes > trials
    ):
        raise ValueError("successesとtrialsの件数が正しくありません。")
    if not 0 < alpha < 1:
        raise ValueError("alphaは0から1の間で指定してください。")
    if successes == 0:
        return 0.0
    if successes == trials:
        return alpha ** (1 / trials)

    low = 0.0
    high = successes / trials
    for _ in range(100):
        midpoint = (low + high) / 2
        if _binomial_upper_tail(trials, successes, midpoint) < alpha:
            low = midpoint
        else:
            high = midpoint
    return (low + high) / 2


def write_formal_gate_report(
    report: dict[str, object],
    output: str | Path,
    *,
    overwrite: bool = False,
) -> None:
    path = Path(output)
    if path.exists() and not overwrite:
        raise FileExistsError(f"既存ファイルを上書きしません: {path}（--forceで上書き）")
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def _validate_formal_sample(
    database: str | Path,
    sample: str | Path,
    *,
    exploration_samples: list[str | Path],
) -> tuple[list[dict[str, str]], dict[str, object]]:
    _read_tsv(sample, required=set(FORMAL_SAMPLE_FIELDS))
    sample_rows = _read_sample(sample)
    if not sample_rows:
        raise ValueError("正式確認標本が空です。")
    if any(
        row["formal_sample_schema_version"] != FORMAL_SAMPLE_SCHEMA_VERSION
        for row in sample_rows
    ):
        raise ValueError("未対応の正式確認標本スキーマです。")
    for field, expected in (
        ("sample_purpose", _SAMPLE_PURPOSE),
        ("sampling_method", _SAMPLING_METHOD),
        ("stratum", "formal_uniform"),
        ("status", "accepted"),
        ("claimed_category", "general"),
    ):
        values = {row[field] for row in sample_rows}
        if values != {expected}:
            raise ValueError(f"正式確認標本の{field}が正しくありません。")

    sample_size = _single_integer(sample_rows, "sample_size")
    if sample_size not in FORMAL_SAMPLE_SIZES or sample_size != len(sample_rows):
        raise ValueError("正式確認標本の件数が300件または473件の完全標本ではありません。")
    seed = _single_integer(sample_rows, "sampling_seed")
    stored_input_hash = _single_value(sample_rows, "database_input_hash")
    population_size = _single_integer(sample_rows, "population_size")
    stored_hashes_raw = _single_value(sample_rows, "excluded_sample_hashes")
    try:
        stored_hashes = json.loads(stored_hashes_raw)
    except json.JSONDecodeError as exc:
        raise ValueError("正式確認標本の探索標本ハッシュが正しくありません。") from exc
    if not isinstance(stored_hashes, list) or any(
        not isinstance(value, str) for value in stored_hashes
    ):
        raise ValueError("正式確認標本の探索標本ハッシュが正しくありません。")

    exploration_ids, exploration_hashes = _exploration_evidence(exploration_samples)
    if stored_hashes != exploration_hashes:
        raise ValueError("正式確認標本に記録した探索標本と現在の探索標本が一致しません。")
    overlap = set(row["sample_id"] for row in sample_rows) & exploration_ids
    if overlap:
        raise ValueError(f"正式確認標本が探索標本と重複しています: {len(overlap)}件")

    database_rows, input_hash = _general_rows(database)
    if stored_input_hash != input_hash:
        raise ValueError("正式確認標本の辞書入力ハッシュが現在の辞書と一致しません。")
    expected_rows, eligible_count = _select_rows(
        database_rows,
        input_hash=input_hash,
        excluded_ids=exploration_ids,
        size=sample_size,
        seed=seed,
    )
    if population_size != eligible_count:
        raise ValueError("正式確認標本の母集団件数が現在の辞書と一致しません。")
    expected_by_id = {_sample_id(row): row for row in expected_rows}
    actual_by_id = _unique_rows(sample_rows, "sample_id", "正式確認標本")
    if set(actual_by_id) != set(expected_by_id):
        raise ValueError("正式確認標本をseed・辞書版・除外標本から再現できません。")
    for sample_id, row in actual_by_id.items():
        expected = expected_by_id[sample_id]
        field_pairs = {
            "surface": "surface",
            "reading": "reading",
            "normalized_reading": "normalized_reading",
            "claimed_category": "category",
            "status": "status",
            "pos": "pos",
            "priority": "priority",
            "sources": "sources",
        }
        for actual_field, expected_field in field_pairs.items():
            if row[actual_field] != str(expected[expected_field]):
                raise ValueError(
                    f"正式確認標本の{sample_id}の{actual_field}が現在の辞書と一致しません。"
                )
    return sample_rows, {
        "path": str(sample),
        "formal_sample_schema_version": FORMAL_SAMPLE_SCHEMA_VERSION,
        "database_input_hash": input_hash,
        "sampling_seed": seed,
        "sampling_method": _SAMPLING_METHOD,
        "eligible_population": eligible_count,
        "sample_size": sample_size,
        "exploration_ids": len(exploration_ids),
        "excluded_exploration_ids": len(database_rows) - eligible_count,
        "excluded_sample_hashes": exploration_hashes,
        "overlap_with_exploration": 0,
    }


def _select_rows(
    rows: list[dict[str, object]],
    *,
    input_hash: str,
    excluded_ids: set[str],
    size: int,
    seed: int,
) -> tuple[list[dict[str, object]], int]:
    candidates = [
        row
        for row in rows
        if _sample_id(row) not in excluded_ids
    ]
    candidates.sort(
        key=lambda row: (
            str(row["surface"]),
            str(row["normalized_reading"]),
            int(row["id"]),
        )
    )
    if len(candidates) < size:
        raise ValueError(
            f"正式確認標本を{size}件抽出できません。対象は{len(candidates)}件です。"
        )
    randomizer = random.Random(f"formal:{seed}:{input_hash}")
    return randomizer.sample(candidates, size), len(candidates)


def _exploration_evidence(
    paths: list[str | Path],
) -> tuple[set[str], list[str]]:
    if not paths:
        raise ValueError("正式確認標本には1つ以上の独立対象となる探索標本が必要です。")
    sample_ids: set[str] = set()
    hashes: list[str] = []
    for path in paths:
        rows = _read_sample(path)
        sample_ids.update(row["sample_id"] for row in rows)
        hashes.append(hashlib.sha256(Path(path).read_bytes()).hexdigest())
    return sample_ids, sorted(hashes)


def _single_value(rows: list[dict[str, str]], field: str) -> str:
    values = {row[field] for row in rows}
    if len(values) != 1 or not next(iter(values), ""):
        raise ValueError(f"正式確認標本の{field}は全行で同一の必須値です。")
    return values.pop()


def _single_integer(rows: list[dict[str, str]], field: str) -> int:
    raw_value = _single_value(rows, field)
    try:
        return int(raw_value)
    except ValueError as exc:
        raise ValueError(f"正式確認標本の{field}は整数で指定してください。") from exc


def _binomial_upper_tail(trials: int, successes: int, probability: float) -> float:
    if probability <= 0:
        return 0.0
    if probability >= 1:
        return 1.0
    log_probability = math.log(probability)
    log_failure = math.log1p(-probability)
    terms = [
        math.exp(
            math.lgamma(trials + 1)
            - math.lgamma(count + 1)
            - math.lgamma(trials - count + 1)
            + count * log_probability
            + (trials - count) * log_failure
        )
        for count in range(successes, trials + 1)
    ]
    return math.fsum(terms)
