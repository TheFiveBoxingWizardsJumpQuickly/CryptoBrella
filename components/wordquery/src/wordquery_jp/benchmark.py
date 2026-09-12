"""Reproducible search benchmarks and human top-result review."""

from __future__ import annotations

import csv
import hashlib
import json
import re
import time
from collections import Counter
from dataclasses import dataclass
from datetime import date
from pathlib import Path
from statistics import fmean
from typing import Any

from .models import SearchRequest
from .query import RequestValidationError, parse_search_request, serialize_search_request
from .repository import load_snapshot
from .search import QueryValidationError, SearchService, SearchTimedOut

CASE_SCHEMA_VERSION = 1
BENCHMARK_SCHEMA_VERSION = 1
REVIEW_SCHEMA_VERSION = 1
TOP_RESULT_LIMIT = 10

PURPOSES = {
    "reading",
    "pattern",
    "crossword",
    "anagram",
    "proper_noun",
    "tagged_term",
}
USEFULNESS_VALUES = {"useful", "not_useful", "uncertain"}
OBSTACLE_CODES = {
    "none",
    "slow",
    "too_many_steps",
    "irrelevant_top_results",
    "missing_input_mode",
    "unclear_ranking",
    "other",
}

REVIEW_FIELDS = [
    "review_schema_version",
    "case_file_sha256",
    "database_input_hash",
    "case_id",
    "purpose",
    "description",
    "rank",
    "surface",
    "reading",
    "vocabulary_layer",
    "sort_score",
    "sort_reasons",
    "deprioritize_reasons",
    "expected_match",
    "reviewer",
    "review_date",
    "usefulness",
    "elapsed_seconds",
    "interaction_count",
    "obstacle_codes",
    "review_note",
]


@dataclass(frozen=True, slots=True)
class BenchmarkCase:
    case_id: str
    purpose: str
    description: str
    request: SearchRequest
    expected_surfaces: tuple[str, ...]


def load_benchmark_cases(path: str | Path) -> tuple[BenchmarkCase, ...]:
    """Load and validate versioned representative search cases."""

    source = Path(path)
    try:
        document = json.loads(source.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise ValueError(f"代表問題を読み込めません: {source}: {exc}") from exc
    if not isinstance(document, dict) or document.get("schema_version") != CASE_SCHEMA_VERSION:
        raise ValueError(
            f"代表問題のschema_versionは{CASE_SCHEMA_VERSION}を指定してください。"
        )
    raw_cases = document.get("cases")
    if not isinstance(raw_cases, list) or not raw_cases:
        raise ValueError("代表問題のcasesは1件以上の配列で指定してください。")

    cases: list[BenchmarkCase] = []
    seen_ids: set[str] = set()
    for raw_case in raw_cases:
        if not isinstance(raw_case, dict):
            raise ValueError("代表問題の各要素はJSONオブジェクトで指定してください。")
        case_id = _required_string(raw_case, "id", "代表問題ID")
        if not re.fullmatch(r"[A-Z][A-Z0-9-]{2,49}", case_id):
            raise ValueError(f"代表問題IDが正しくありません: {case_id}")
        if case_id in seen_ids:
            raise ValueError(f"代表問題IDが重複しています: {case_id}")
        seen_ids.add(case_id)

        purpose = _required_string(raw_case, "purpose", f"{case_id}のpurpose")
        if purpose not in PURPOSES:
            raise ValueError(f"{case_id}のpurposeが正しくありません: {purpose}")
        description = _required_string(raw_case, "description", f"{case_id}のdescription")
        expected_surfaces = _expected_surfaces(raw_case.get("expected_surfaces"), case_id)
        request_payload = raw_case.get("request")
        if not isinstance(request_payload, dict):
            raise ValueError(f"{case_id}のrequestはJSONオブジェクトで指定してください。")
        if "limit" in request_payload:
            raise ValueError(f"{case_id}のlimitは代表問題側では指定できません。")
        try:
            search_request = parse_search_request(
                request_payload,
                max_length=200,
                limit=TOP_RESULT_LIMIT,
            )
        except RequestValidationError as exc:
            raise ValueError(f"{case_id}の検索条件が正しくありません: {exc}") from exc
        cases.append(
            BenchmarkCase(
                case_id=case_id,
                purpose=purpose,
                description=description,
                request=search_request,
                expected_surfaces=expected_surfaces,
            )
        )
    return tuple(cases)


def run_search_benchmark(
    database: str | Path,
    cases_path: str | Path,
    *,
    timeout_seconds: float = 2.0,
) -> dict[str, object]:
    """Execute representative cases and record target reachability in the top ten."""

    if timeout_seconds <= 0:
        raise ValueError("検索時間上限は0より大きい値で指定してください。")
    cases = load_benchmark_cases(cases_path)
    snapshot = load_snapshot(database)
    service = SearchService(snapshot, timeout_seconds=timeout_seconds)
    rendered_cases: list[dict[str, object]] = []
    for case in cases:
        started = time.monotonic()
        try:
            response = service.execute(case.request)
        except SearchTimedOut as exc:
            rendered_cases.append(
                {
                    "case_id": case.case_id,
                    "purpose": case.purpose,
                    "description": case.description,
                    "request": serialize_search_request(case.request),
                    "expected_surfaces": list(case.expected_surfaces),
                    "expected_rank": None,
                    "expected_top_10": False,
                    "status": "timeout",
                    "error": str(exc),
                    "total": None,
                    "truncated": False,
                    "duration_ms": round((time.monotonic() - started) * 1000, 2),
                    "results": [],
                }
            )
            continue
        except (QueryValidationError, ValueError) as exc:
            raise ValueError(f"{case.case_id}の検索に失敗しました: {exc}") from exc
        results = []
        expected_rank: int | None = None
        for rank, (
            record,
            sort_score,
            sort_reasons,
            deprioritize_reasons,
        ) in enumerate(
            zip(
                response.results,
                response.sort_scores,
                response.sort_reasons,
                response.deprioritize_reasons,
                strict=True,
            ),
            start=1,
        ):
            expected_match = record.surface in case.expected_surfaces
            if expected_match and expected_rank is None:
                expected_rank = rank
            results.append(
                {
                    "rank": rank,
                    "surface": record.surface,
                    "reading": record.reading,
                    "category": record.category,
                    "vocabulary_layer": (
                        "auxiliary" if record.status == "candidate" else "core"
                    ),
                    "sort_score": sort_score,
                    "sort_reasons": list(sort_reasons),
                    "deprioritize_reasons": list(deprioritize_reasons),
                    "tags": [
                        {"axis": tag.axis, "value": tag.value} for tag in record.tags
                    ],
                    "expected_match": expected_match,
                }
            )
        rendered_cases.append(
            {
                "case_id": case.case_id,
                "purpose": case.purpose,
                "description": case.description,
                "request": serialize_search_request(case.request),
                "expected_surfaces": list(case.expected_surfaces),
                "expected_rank": expected_rank,
                "expected_top_10": expected_rank is not None,
                "status": "completed",
                "error": None,
                "total": response.total,
                "truncated": response.truncated,
                "duration_ms": round(response.duration_ms, 2),
                "results": results,
            }
        )

    case_count = len(rendered_cases)
    hits = sum(bool(case["expected_top_10"]) for case in rendered_cases)
    return {
        "benchmark_schema_version": BENCHMARK_SCHEMA_VERSION,
        "case_schema_version": CASE_SCHEMA_VERSION,
        "case_file": str(cases_path),
        "case_file_sha256": _sha256(cases_path),
        "database": str(database),
        "database_input_hash": snapshot.metadata.get("input_hash", "unknown"),
        "top_result_limit": TOP_RESULT_LIMIT,
        "summary": {
            "case_count": case_count,
            "completed_cases": sum(
                case["status"] == "completed" for case in rendered_cases
            ),
            "timed_out_cases": sum(case["status"] == "timeout" for case in rendered_cases),
            "cases_with_results": sum(bool(case["results"]) for case in rendered_cases),
            "expected_top_10_hits": hits,
            "expected_top_10_rate": hits / case_count if case_count else None,
        },
        "cases": rendered_cases,
    }


def write_benchmark_report(
    report: dict[str, object],
    output: str | Path,
    *,
    overwrite: bool = False,
) -> None:
    """Write a benchmark report without silently replacing prior evidence."""

    path = Path(output)
    _ensure_writable(path, overwrite)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def write_search_review_template(
    report: dict[str, object],
    output: str | Path,
    *,
    overwrite: bool = False,
) -> int:
    """Write a human-review TSV for the benchmark's displayed results."""

    _validate_benchmark_report(report)
    rows = _review_identity_rows(report)
    rendered = [
        {
            **row,
            "reviewer": "",
            "review_date": "",
            "usefulness": "",
            "elapsed_seconds": "",
            "interaction_count": "",
            "obstacle_codes": "",
            "review_note": "",
        }
        for row in rows
    ]
    _write_tsv(output, rendered, overwrite=overwrite)
    return len(rendered)


def evaluate_search_review(
    report: dict[str, object],
    review_path: str | Path,
) -> dict[str, object]:
    """Validate a completed human review and summarize top-ten usefulness."""

    _validate_benchmark_report(report)
    expected_rows = {
        (str(row["case_id"]), str(row["rank"])): row
        for row in _review_identity_rows(report)
    }
    rows = _read_review(review_path)
    actual_rows: dict[tuple[str, str], dict[str, str]] = {}
    identity_fields = REVIEW_FIELDS[:14]
    for row in rows:
        key = (row["case_id"], row["rank"])
        if key in actual_rows:
            raise ValueError(f"{review_path}: 評価行が重複しています: {key[0]} rank={key[1]}")
        if key not in expected_rows:
            raise ValueError(f"{review_path}: ベンチマークにない評価行です: {key[0]} rank={key[1]}")
        expected = expected_rows[key]
        for field in identity_fields:
            if row[field] != str(expected[field]):
                raise ValueError(
                    f"{review_path}: {key[0]} rank={key[1]} の{field}が"
                    "ベンチマークと一致しません。"
                )
        _validate_review_values(row, review_path)
        actual_rows[key] = row
    missing = set(expected_rows) - set(actual_rows)
    if missing:
        case_id, rank = sorted(missing)[0]
        raise ValueError(f"{review_path}: 評価行が不足しています: {case_id} rank={rank}")

    reviewer = _single_review_value(rows, "reviewer", review_path)
    review_date = _single_review_value(rows, "review_date", review_path)
    try:
        date.fromisoformat(review_date)
    except ValueError as exc:
        raise ValueError(f"{review_path}: review_dateはYYYY-MM-DDで指定してください。") from exc

    case_summaries: list[dict[str, object]] = []
    obstacle_counts: Counter[str] = Counter()
    first_useful_ranks: list[int] = []
    elapsed_values: list[float] = []
    interaction_total = 0
    for case in report["cases"]:
        case_id = str(case["case_id"])
        case_rows = [
            actual_rows[(case_id, str(identity["rank"]))]
            for identity in _review_identity_rows_for_case(report, case)
        ]
        elapsed = _single_numeric_value(case_rows, "elapsed_seconds", review_path, minimum=0)
        interactions = int(
            _single_numeric_value(case_rows, "interaction_count", review_path, minimum=1)
        )
        obstacles = _single_review_value(case_rows, "obstacle_codes", review_path)
        parsed_obstacles = _parse_obstacles(obstacles, review_path)
        obstacle_counts.update(code for code in parsed_obstacles if code != "none")
        useful_ranks = [
            int(row["rank"])
            for row in case_rows
            if row["usefulness"] == "useful" and int(row["rank"]) > 0
        ]
        first_useful_rank = min(useful_ranks) if useful_ranks else None
        if first_useful_rank is not None:
            first_useful_ranks.append(first_useful_rank)
        elapsed_values.append(elapsed)
        interaction_total += interactions
        counts = Counter(row["usefulness"] for row in case_rows)
        case_summaries.append(
            {
                "case_id": case_id,
                "first_useful_rank": first_useful_rank,
                "usefulness": dict(sorted(counts.items())),
                "elapsed_seconds": elapsed,
                "interaction_count": interactions,
                "obstacle_codes": parsed_obstacles,
            }
        )

    return {
        "review_schema_version": REVIEW_SCHEMA_VERSION,
        "diagnostic_only": True,
        "case_file_sha256": report["case_file_sha256"],
        "database_input_hash": report["database_input_hash"],
        "reviewer": reviewer,
        "review_date": review_date,
        "case_count": len(case_summaries),
        "cases_with_useful_top_10": len(first_useful_ranks),
        "mean_first_useful_rank": (
            fmean(first_useful_ranks) if first_useful_ranks else None
        ),
        "mean_elapsed_seconds": fmean(elapsed_values) if elapsed_values else None,
        "total_interactions": interaction_total,
        "obstacle_counts": dict(sorted(obstacle_counts.items())),
        "cases": case_summaries,
    }


def write_search_review_report(
    report: dict[str, object],
    output: str | Path,
    *,
    overwrite: bool = False,
) -> None:
    path = Path(output)
    _ensure_writable(path, overwrite)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def _review_identity_rows(report: dict[str, object]) -> list[dict[str, object]]:
    rows: list[dict[str, object]] = []
    for case in report["cases"]:
        rows.extend(_review_identity_rows_for_case(report, case))
    return rows


def _review_identity_rows_for_case(
    report: dict[str, object], case: dict[str, Any]
) -> list[dict[str, object]]:
    results = case["results"] or [
        {
            "rank": 0,
            "surface": "",
            "reading": "",
            "vocabulary_layer": "",
            "sort_score": None,
            "sort_reasons": [],
            "deprioritize_reasons": [],
            "expected_match": False,
        }
    ]
    return [
        {
            "review_schema_version": REVIEW_SCHEMA_VERSION,
            "case_file_sha256": report["case_file_sha256"],
            "database_input_hash": report["database_input_hash"],
            "case_id": case["case_id"],
            "purpose": case["purpose"],
            "description": case["description"],
            "rank": result["rank"],
            "surface": result["surface"],
            "reading": result["reading"],
            "vocabulary_layer": result["vocabulary_layer"],
            "sort_score": "" if result["sort_score"] is None else result["sort_score"],
            "sort_reasons": json.dumps(result["sort_reasons"], ensure_ascii=False),
            "deprioritize_reasons": json.dumps(
                result["deprioritize_reasons"], ensure_ascii=False
            ),
            "expected_match": "yes" if result["expected_match"] else "no",
        }
        for result in results
    ]


def _validate_benchmark_report(report: dict[str, object]) -> None:
    if report.get("benchmark_schema_version") != BENCHMARK_SCHEMA_VERSION:
        raise ValueError("未対応の検索ベンチマークスキーマです。")
    if not isinstance(report.get("cases"), list):
        raise ValueError("検索ベンチマークにcasesがありません。")
    if not isinstance(report.get("case_file_sha256"), str):
        raise ValueError("検索ベンチマークにcase_file_sha256がありません。")
    if not isinstance(report.get("database_input_hash"), str):
        raise ValueError("検索ベンチマークにdatabase_input_hashがありません。")


def _validate_review_values(row: dict[str, str], path: str | Path) -> None:
    if row["review_schema_version"] != str(REVIEW_SCHEMA_VERSION):
        raise ValueError(f"{path}: 未対応のreview_schema_versionです。")
    if not row["reviewer"].strip():
        raise ValueError(f"{path}: reviewerは必須です。")
    if not row["review_date"].strip():
        raise ValueError(f"{path}: review_dateは必須です。")
    if row["usefulness"] not in USEFULNESS_VALUES:
        raise ValueError(f"{path}: usefulnessが正しくありません: {row['usefulness']}")
    if row["rank"] == "0" and row["usefulness"] == "useful":
        raise ValueError(f"{path}: 結果0件の行をusefulにはできません。")
    _parse_number(row["elapsed_seconds"], "elapsed_seconds", path, minimum=0)
    interactions = _parse_number(row["interaction_count"], "interaction_count", path, minimum=1)
    if not interactions.is_integer():
        raise ValueError(f"{path}: interaction_countは整数で指定してください。")
    _parse_obstacles(row["obstacle_codes"], path)


def _parse_obstacles(value: str, path: str | Path) -> list[str]:
    codes = [code.strip() for code in value.split(";") if code.strip()]
    if not codes:
        raise ValueError(f"{path}: obstacle_codesはnoneまたは既定コードを指定してください。")
    unknown = set(codes) - OBSTACLE_CODES
    if unknown:
        raise ValueError(f"{path}: 未知のobstacle_codesです: {', '.join(sorted(unknown))}")
    if "none" in codes and len(codes) > 1:
        raise ValueError(f"{path}: noneと他のobstacle_codesは併用できません。")
    return list(dict.fromkeys(codes))


def _single_numeric_value(
    rows: list[dict[str, str]],
    field: str,
    path: str | Path,
    *,
    minimum: float,
) -> float:
    value = _single_review_value(rows, field, path)
    return _parse_number(value, field, path, minimum=minimum)


def _parse_number(
    value: str, field: str, path: str | Path, *, minimum: float
) -> float:
    try:
        number = float(value)
    except ValueError as exc:
        raise ValueError(f"{path}: {field}は数値で指定してください。") from exc
    if number < minimum:
        raise ValueError(f"{path}: {field}は{minimum}以上で指定してください。")
    return number


def _single_review_value(
    rows: list[dict[str, str]], field: str, path: str | Path
) -> str:
    values = {row[field].strip() for row in rows}
    if len(values) != 1 or not next(iter(values), ""):
        raise ValueError(f"{path}: {field}は対象内で同一の必須値です。")
    return values.pop()


def _read_review(path: str | Path) -> list[dict[str, str]]:
    with Path(path).open(encoding="utf-8", newline="") as handle:
        reader = csv.DictReader(handle, delimiter="\t")
        missing = set(REVIEW_FIELDS) - set(reader.fieldnames or ())
        if missing:
            raise ValueError(f"{path}: 必須列がありません: {', '.join(sorted(missing))}")
        return list(reader)


def _write_tsv(
    path: str | Path,
    rows: list[dict[str, object]],
    *,
    overwrite: bool,
) -> None:
    output = Path(path)
    _ensure_writable(output, overwrite)
    output.parent.mkdir(parents=True, exist_ok=True)
    with output.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=REVIEW_FIELDS, delimiter="\t")
        writer.writeheader()
        writer.writerows(rows)


def _required_string(row: dict[str, object], field: str, label: str) -> str:
    value = row.get(field)
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{label}は空でない文字列で指定してください。")
    return value.strip()


def _expected_surfaces(raw: object, case_id: str) -> tuple[str, ...]:
    if not isinstance(raw, list) or not raw:
        raise ValueError(f"{case_id}のexpected_surfacesは1件以上の配列で指定してください。")
    if any(not isinstance(value, str) or not value.strip() for value in raw):
        raise ValueError(f"{case_id}のexpected_surfacesに空でない文字列を指定してください。")
    values = tuple(dict.fromkeys(value.strip() for value in raw))
    if len(values) != len(raw):
        raise ValueError(f"{case_id}のexpected_surfacesが重複しています。")
    return values


def _sha256(path: str | Path) -> str:
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def _ensure_writable(path: Path, overwrite: bool) -> None:
    if path.exists() and not overwrite:
        raise FileExistsError(f"既存ファイルを上書きしません: {path}（--forceで上書き）")
