"""Exercise the real Flask search boundary against a frozen lexicon, offline."""

from __future__ import annotations

import argparse
import json
import resource
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def check_release(database: Path) -> dict:
    from flask import Flask

    from app.wordquery.blueprint import register_wordquery

    started = time.monotonic()
    app = Flask("app", root_path=str(ROOT / "app"))
    register_wordquery(app, {
        "TESTING": True,
        "WORDQUERY_DB": str(database.resolve()),
        "WORDQUERY_PUBLIC": False,
        "WORDQUERY_ENFORCE_FRESHNESS": False,
    })
    load_seconds = time.monotonic() - started
    client = app.test_client()
    cases = [
        ("pattern", {"mode": "pattern", "query": "ね?"}, "猫"),
        ("anagram", {"mode": "anagram", "query": "ねこ"}, "猫"),
        ("regex", {"mode": "regex", "query": "^ねこ$"}, "猫"),
        ("reviewed-onomatopoeia", {
            "mode": "reading", "query": "くわっくわっ", "match_type": "exact",
        }, "くわっくわっ"),
        ("reviewed-compound", {
            "mode": "reading", "query": "なにけん", "match_type": "exact",
        }, "何県"),
        ("auxiliary", {
            "mode": "reading", "query": "とうきょう", "match_type": "exact",
            "vocabulary_layers": ["auxiliary"],
            "include_proper": True,
            "include_function": True,
        }, None),
    ]
    results = []
    for name, payload, expected in cases:
        started = time.monotonic()
        response = client.post("/wordquery/api/search", json={
            "version": 5, "limit": 300, **payload,
        })
        duration_ms = (time.monotonic() - started) * 1000
        body = response.get_json() or {}
        rows = body.get("results", [])
        expected_found = (
            any(row.get("vocabulary_layer") == "auxiliary" for row in rows)
            if expected is None else any(row["surface"] == expected for row in rows)
        )
        results.append({
            "case": name, "http_status": response.status_code,
            "duration_ms": round(duration_ms, 2), "result_count": len(rows),
            "expected_found": expected_found,
            "passed": response.status_code == 200 and expected_found and duration_ms < 1500,
            "error": body.get("error"),
        })
    page = client.get("/wordquery/")
    sources = client.get("/wordquery/sources")
    invalid = client.post("/wordquery/api/search", json={
        "version": 5, "mode": "regex", "query": "[",
    })
    boundaries = {
        "page": page.status_code == 200,
        "sources": sources.status_code == 200,
        "invalid_regex": invalid.status_code == 400,
        "preview_noindex": page.headers.get("X-Robots-Tag") == "noindex, nofollow",
    }
    return {
        "passed": all(row["passed"] for row in results) and all(boundaries.values()),
        "database": str(database),
        "metadata": app.extensions.get("wordquery_metadata"),
        "load_seconds": round(load_seconds, 3),
        "peak_rss_mib": round(resource.getrusage(resource.RUSAGE_SELF).ru_maxrss / 1024, 1),
        "cases": results,
        "boundaries": boundaries,
        "scope": "Local Flask test client; excludes browser rendering and hosting capacity.",
    }


def main() -> int:
    sys.path.insert(0, str(ROOT))
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--database", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    if not args.database.is_file():
        parser.error("Database does not exist")
    if args.output.exists():
        parser.error("Output already exists; choose a new report path")
    report = check_release(args.database)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(report, ensure_ascii=False, indent=2))
    return 0 if report["passed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
