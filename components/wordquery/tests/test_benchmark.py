import csv
import json
from pathlib import Path

import pytest

from wordquery_jp.benchmark import (
    REVIEW_FIELDS,
    evaluate_search_review,
    load_benchmark_cases,
    run_search_benchmark,
    write_benchmark_report,
    write_search_review_template,
)
from wordquery_jp.lexicon.builder import BuildConfig, build_database
from wordquery_jp.search import SearchTimedOut

FIXTURES = Path(__file__).parent / "fixtures"


def write_cases(path, cases):
    path.write_text(
        json.dumps({"schema_version": 1, "cases": cases}, ensure_ascii=False),
        encoding="utf-8",
    )


def read_rows(path):
    with path.open(encoding="utf-8", newline="") as handle:
        return list(csv.DictReader(handle, delimiter="\t"))


def write_rows(path, rows):
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=REVIEW_FIELDS, delimiter="\t")
        writer.writeheader()
        writer.writerows(rows)


def test_search_benchmark_records_top_ten_target_reachability(tmp_path):
    database = tmp_path / "lexicon.sqlite3"
    build_database(
        BuildConfig(output=database, additions=FIXTURES / "manual_additions.tsv")
    )
    cases = tmp_path / "cases.json"
    write_cases(
        cases,
        [
            {
                "id": "READ-001",
                "purpose": "reading",
                "description": "完全一致で猫を探す",
                "request": {
                    "version": 4,
                    "mode": "reading",
                    "query": "ねこ",
                    "match_type": "exact",
                    "vocabulary_layers": ["core"],
                },
                "expected_surfaces": ["猫"],
            },
            {
                "id": "READ-002",
                "purpose": "reading",
                "description": "既知の答えが先頭10件にない例",
                "request": {
                    "version": 4,
                    "mode": "reading",
                    "query": "ねこ",
                    "match_type": "exact",
                    "vocabulary_layers": ["core"],
                },
                "expected_surfaces": ["存在しない語"],
            },
        ],
    )

    report = run_search_benchmark(database, cases, timeout_seconds=1.0)

    assert report["summary"] == {
        "case_count": 2,
        "completed_cases": 2,
        "timed_out_cases": 0,
        "cases_with_results": 2,
        "expected_top_10_hits": 1,
        "expected_top_10_rate": 0.5,
    }
    first = report["cases"][0]
    assert first["case_id"] == "READ-001"
    assert first["expected_rank"] == 1
    assert first["expected_top_10"] is True
    assert first["results"][0]["surface"] == "猫"
    assert first["results"][0]["sort_reasons"]

    output = tmp_path / "benchmark.json"
    write_benchmark_report(report, output)
    assert json.loads(output.read_text(encoding="utf-8"))["case_file_sha256"]
    with pytest.raises(FileExistsError, match="上書き"):
        write_benchmark_report(report, output)


def test_search_review_template_is_validated_and_summarized(tmp_path):
    database = tmp_path / "lexicon.sqlite3"
    build_database(
        BuildConfig(output=database, additions=FIXTURES / "manual_additions.tsv")
    )
    cases = tmp_path / "cases.json"
    write_cases(
        cases,
        [
            {
                "id": "ANAG-001",
                "purpose": "anagram",
                "description": "ねこの完全アナグラム",
                "request": {
                    "version": 4,
                    "mode": "anagram",
                    "query": "ねこ",
                    "vocabulary_layers": ["core"],
                },
                "expected_surfaces": ["猫", "こね"],
            }
        ],
    )
    report = run_search_benchmark(database, cases)
    review = tmp_path / "review.tsv"
    assert write_search_review_template(report, review) == len(
        report["cases"][0]["results"]
    )

    rows = read_rows(review)
    for row in rows:
        row.update(
            {
                "reviewer": "human-a",
                "review_date": "2026-07-26",
                "usefulness": "useful" if row["expected_match"] == "yes" else "not_useful",
                "elapsed_seconds": "4.5",
                "interaction_count": "2",
                "obstacle_codes": "none",
                "review_note": "fixture evaluation",
            }
        )
    write_rows(review, rows)

    summary = evaluate_search_review(report, review)

    assert summary["reviewer"] == "human-a"
    assert summary["case_count"] == 1
    assert summary["cases_with_useful_top_10"] == 1
    assert summary["cases"][0]["first_useful_rank"] == 1
    assert summary["cases"][0]["elapsed_seconds"] == 4.5

    rows[0]["surface"] = "改変"
    write_rows(review, rows)
    with pytest.raises(ValueError, match="surface"):
        evaluate_search_review(report, review)


def test_benchmark_cases_reject_duplicate_ids_and_unsupported_versions(tmp_path):
    cases = tmp_path / "cases.json"
    duplicate = {
        "id": "CASE-001",
        "purpose": "reading",
        "description": "重複",
        "request": {
            "version": 4,
            "mode": "reading",
            "query": "ねこ",
            "vocabulary_layers": ["core"],
        },
        "expected_surfaces": ["猫"],
    }
    write_cases(cases, [duplicate, duplicate])
    with pytest.raises(ValueError, match="重複"):
        load_benchmark_cases(cases)

    duplicate["id"] = "CASE-002"
    duplicate["request"]["version"] = 3
    write_cases(cases, [duplicate])
    with pytest.raises(ValueError, match="version 4"):
        load_benchmark_cases(cases)


def test_search_benchmark_records_timeout_without_aborting(tmp_path, monkeypatch):
    database = tmp_path / "lexicon.sqlite3"
    build_database(
        BuildConfig(output=database, additions=FIXTURES / "manual_additions.tsv")
    )
    cases = tmp_path / "cases.json"
    write_cases(
        cases,
        [
            {
                "id": "PATTERN-TIMEOUT-001",
                "purpose": "pattern",
                "description": "時間上限を記録する",
                "request": {
                    "version": 4,
                    "mode": "regex",
                    "query": "^ね.$",
                    "vocabulary_layers": ["core"],
                },
                "expected_surfaces": ["猫"],
            }
        ],
    )

    def time_out(*_args, **_kwargs):
        raise SearchTimedOut("時間上限")

    monkeypatch.setattr("wordquery_jp.benchmark.SearchService.execute", time_out)
    report = run_search_benchmark(database, cases)

    assert report["summary"]["timed_out_cases"] == 1
    assert report["cases"][0]["status"] == "timeout"
    assert report["cases"][0]["error"] == "時間上限"
    assert report["cases"][0]["results"] == []
