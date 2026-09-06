"""Offline search-budget diagnostics; no deployment, dictionary writes or service changes."""

from __future__ import annotations

import argparse
import hashlib
import json
import math
import os
import subprocess
import sys
import time
from datetime import UTC, datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
CASES = [
    ("reading-contains", "reading", "ねこ"),
    ("pattern-exact", "pattern", "ねこ"),
    ("pattern-prefix", "pattern", "とう*"),
    ("pattern-one-prefix", "pattern", "と*"),
    ("pattern-leading-one", "pattern", "?ねこ"),
    ("pattern-leading-many", "pattern", "*ねこ"),
    ("pattern-no-literal", "pattern", "???"),
    ("regex-repeat", "regex", "^とう*$"),
    ("regex-prefix", "regex", "^とう.*$"),
    ("regex-suffix", "regex", "ねこ$"),
    ("regex-unanchored", "regex", "ねこ"),
    ("regex-no-literal", "regex", "^[あ-ん]{3}$"),
    ("regex-fallback", "regex", "(とう|ねこ)$"),
    ("anagram", "anagram", "ねこ"),
]


def default_database() -> Path:
    if os.environ.get("WORDQUERY_DB"):
        return Path(os.environ["WORDQUERY_DB"]).resolve()
    local = ROOT / "var/wordquery/dev.json"
    if local.is_file():
        return (ROOT / json.loads(local.read_text(encoding="utf-8"))["database"]).resolve()
    return ROOT / "var/wordquery/current/lexicon.sqlite3"


def source_fingerprint() -> str:
    digest = hashlib.sha256()
    for path in sorted((ROOT / "components/wordquery/src").rglob("*.py")):
        digest.update(str(path.relative_to(ROOT)).encode())
        digest.update(path.read_bytes())
    return digest.hexdigest()


def peak_rss_mib() -> float | None:
    try:
        import resource
    except ImportError:
        return None  # Windows: no additional dependency required for diagnostics.
    peak = resource.getrusage(resource.RUSAGE_SELF).ru_maxrss
    return round(peak / (1024 ** 2 if sys.platform == "darwin" else 1024), 1)


def run_case(service, request) -> dict:
    from wordquery_jp.search import QueryValidationError, SearchTimedOut
    from wordquery_jp.search_budget import RegexMatchTimedOut

    started = time.perf_counter()
    cpu_started = time.process_time()
    try:
        response = service.execute(request)
        # Compare counts, ordered result identities and highlighting without
        # saving the dictionary content in the diagnostic report.
        identity = [
            (row.id, row.surface, row.reading, span)
            for row, span in zip(response.results, response.match_spans, strict=True)
        ]
        result = {
            "status": "completed", "total": response.total,
            "returned": len(response.results), "truncated": response.truncated,
            "result_digest": hashlib.sha256(
                json.dumps(identity, ensure_ascii=False).encode()
            ).hexdigest(),
        }
    except SearchTimedOut as exc:
        result = {"status": "timed_out", "error": str(exc),
                  "timeout_kind": "regex_match" if isinstance(exc, RegexMatchTimedOut) else "search"}
    except QueryValidationError as exc:
        result = {"status": "invalid_query", "error": str(exc)}
    result["wall_ms"] = round((time.perf_counter() - started) * 1000, 3)
    result["cpu_ms"] = round((time.process_time() - cpu_started) * 1000, 3)
    return result


def regex_guard_probe() -> dict:
    import regex

    started = time.perf_counter()
    try:
        regex.compile("(あ|ああ)+$").search("あ" * 4000 + "い", timeout=0.02)
    except TimeoutError:
        status = "interrupted_as_expected"
    else:
        status = "not_interrupted"
    return {
        "status": status, "budget_seconds": 0.02,
        "wall_ms": round((time.perf_counter() - started) * 1000, 3),
        "scope": "Synthetic single-string engine guard, not production dictionary data.",
    }


def measure(
    database: Path, budget: float, stress: float, reference_budget: float,
    cases: list[tuple[str, str, str]] | None = None,
    include_auxiliary: bool = False, limit: int = 3000,
) -> dict:
    from wordquery_jp.query import parse_search_request
    from wordquery_jp.repository import load_snapshot
    from wordquery_jp.search import SearchService

    started = time.perf_counter()
    snapshot = load_snapshot(database)
    service = SearchService(snapshot)
    startup = time.perf_counter() - started
    profiles = [("reference", reference_budget), ("normal", budget), ("stress", budget / stress)]
    rows = []
    for case_id, mode, query in CASES if cases is None else cases:
        payload = {"version": 6, "mode": mode, "query": query,
                   "vocabulary_layers": ["core", "auxiliary"] if include_auxiliary else ["core"],
                   "include_proper": include_auxiliary, "sort": "commonness"}
        if mode == "reading":
            payload["match_type"] = "contains"
        request = parse_search_request(
            payload,
            max_length=200, limit=limit,
        )
        baseline = None
        for profile, effective_budget in profiles:
            print(f"{case_id}: {profile}", file=sys.stderr, flush=True)
            service.timeout_seconds = effective_budget
            result = run_case(service, request)
            if profile == "reference":
                baseline = result
            same_results = None
            if baseline["status"] == result["status"] == "completed":
                same_results = (
                    baseline["total"] == result["total"]
                    and baseline["result_digest"] == result["result_digest"]
                )
            rows.append({
                "case": case_id, "mode": mode, "query": query, "profile": profile,
                "budget_seconds": effective_budget, **result,
                "matches_reference": same_results,
                "completes_with_reference_budget": baseline["status"] == "completed",
            })
    return {
        "schema_version": 1, "created_at": datetime.now(UTC).isoformat(),
        "database": str(database), "metadata": snapshot.metadata,
        "source_fingerprint": source_fingerprint(),
        "python": sys.version, "platform": sys.platform,
        "startup_seconds": round(startup, 3),
        "peak_rss_mib": peak_rss_mib(),
        "budget_seconds": budget, "stress_factor": stress,
        "reference_budget_seconds": reference_budget,
        "include_auxiliary": include_auxiliary, "result_limit": limit,
        "regex_timeout_seconds": service.regex_timeout_seconds,
        "method": "Reduced-deadline stress, not CPU throttling or hosting emulation.",
        "scope": "Search core; excludes HTTP, browser, concurrency and hosting memory limits.",
        "caveats": [
            "Reference runs precede normal/stress runs, so filesystem caches may be warmer.",
            "A reference timeout does not by itself identify a pathological regular expression.",
            "Pending source edits are included; fingerprint identifies the tested working tree.",
        ],
        "rows": rows, "regex_guard": regex_guard_probe(),
    }


def markdown(report: dict) -> str:
    lines = [
        "# WordQuery ローカル診断", "",
        "stressは計算を遅くせず、時間予算を短くする試験です。本番速度の再現ではありません。",
        "referenceは長めの予算で、同じ条件が完了できるかを確認します。", "",
        (f'時間予算: reference={report["reference_budget_seconds"]:g}秒 / '
        f'normal={report["budget_seconds"]:g}秒 / '
         f'stress={report["budget_seconds"] / report["stress_factor"]:g}秒'), "",
        "| 条件 | モード | reference | normal | stress |",
        "|---|---|---:|---:|---:|",
    ]
    case_rows = [row for row in report["rows"] if row["profile"] == "reference"]
    for case in case_rows:
        case_id, mode, query = case["case"], case["mode"], case["query"]
        values = []
        for row in [item for item in report["rows"] if item["case"] == case_id]:
            values.append(
                f'{row["wall_ms"]:.1f}ms / {row["total"]}件'
                if row["status"] == "completed" else
                "時間切れ" if row["status"] == "timed_out" else "入力エラー"
            )
        display_query = query.replace("|", "&#124;").replace("`", "&#96;").replace("\n", " ")
        lines.append(f"| `{display_query}` | {mode} | " + " | ".join(values) + " |")
    comparisons = [row["matches_reference"] for row in report["rows"]
                   if row["profile"] != "reference"]
    lines.extend([
        "", (f"- referenceとの結果比較: 一致 {comparisons.count(True)}件 / "
             f"不一致 {comparisons.count(False)}件 / 未判定 {comparisons.count(None)}件"),
        "- 合成データでの重いRegexの中断: " + report["regex_guard"]["status"],
        f'- 補助語彙: {report["include_auxiliary"]} / 表示上限: {report["result_limit"]}件',
        "- referenceでも時間切れの場合、正規表現単体の問題かはこの結果だけでは断定できません。",
        "- 起動時間・CPU時間・ソース識別値などの詳細は同名のJSONを参照してください。", "",
    ])
    return "\n".join(lines)


def main() -> int:
    sys.path.insert(0, str(ROOT))
    from component_paths import activate_wordquery

    activate_wordquery()
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--database", type=Path, default=default_database())
    parser.add_argument("--budget", type=float, default=5)
    parser.add_argument("--include-auxiliary", action="store_true")
    parser.add_argument("--limit", type=int, default=3000)
    parser.add_argument("--stress-factor", type=float, default=4)
    parser.add_argument("--reference-budget", type=float, default=10)
    parser.add_argument("--hard-limit", type=float, default=180)
    parser.add_argument("--output", type=Path)
    parser.add_argument("--mode", choices=["reading", "pattern", "regex", "anagram"])
    parser.add_argument("--query", help="Run one custom query instead of the representative suite")
    parser.add_argument("--worker", action="store_true", help=argparse.SUPPRESS)
    args = parser.parse_args()
    if not args.database.is_file():
        parser.error("Dictionary not found; specify --database or configure var/wordquery/dev.json")
    if not (all(math.isfinite(value) for value in (
        args.budget, args.reference_budget, args.stress_factor, args.hard_limit,
    )) and 0 < args.budget <= args.reference_budget and args.stress_factor >= 1
            and args.hard_limit > 0):
        parser.error("Require 0 < budget <= reference-budget, stress-factor >= 1, hard-limit > 0")
    if (args.mode is None) != (args.query is None):
        parser.error("Specify --mode and --query together")
    if not 1 <= args.limit <= 3000:
        parser.error("Require 1 <= limit <= 3000")
    if args.worker:
        print(json.dumps(measure(
            args.database, args.budget, args.stress_factor, args.reference_budget,
            None if args.mode is None else [("custom", args.mode, args.query)],
            args.include_auxiliary, args.limit,
        ), ensure_ascii=False))
        return 0
    output = args.output or ROOT / "reports" / (
        "wordquery-diagnostic-" + datetime.now(UTC).strftime("%Y%m%d-%H%M%S") + ".json"
    )
    if output.suffix != ".json" or output.exists() or output.with_suffix(".md").exists():
        parser.error("Choose a new .json output path (existing reports are not overwritten)")
    command = [
        sys.executable, str(Path(__file__).resolve()), "--worker", "--database",
        str(args.database.resolve()), "--budget", str(args.budget), "--stress-factor",
        str(args.stress_factor), "--reference-budget", str(args.reference_budget),
        "--limit", str(args.limit),
    ]
    if args.include_auxiliary:
        command.append("--include-auxiliary")
    if args.mode is not None:
        command.extend(["--mode", args.mode, "--query", args.query])
    try:
        worker = subprocess.run(command, stdout=subprocess.PIPE, encoding="utf-8",
                                timeout=args.hard_limit, check=True,
                                env={**os.environ, "PYTHONIOENCODING": "utf-8"})
    except subprocess.TimeoutExpired:
        parser.exit(2, "Diagnostic worker stopped at the hard limit; no completion claimed.\n")
    except subprocess.CalledProcessError as exc:
        parser.exit(2, f"Diagnostic worker failed: exit {exc.returncode}\n")
    report = json.loads(worker.stdout)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    summary = markdown(report)
    output.with_suffix(".md").write_text(summary, encoding="utf-8")
    print(summary)
    print(f"Reports: {output} / {output.with_suffix('.md')}")
    # Expected diagnostic timeouts are observations, not a release pass/fail gate.
    return int(any(row["matches_reference"] is False for row in report["rows"])
               or report["regex_guard"]["status"] != "interrupted_as_expected")


if __name__ == "__main__":
    raise SystemExit(main())
