"""Developer CLI for lexicon lifecycle operations."""

from __future__ import annotations

import argparse
import json
import logging
from pathlib import Path

from .benchmark import (
    evaluate_search_review,
    run_search_benchmark,
    write_benchmark_report,
    write_search_review_report,
    write_search_review_template,
)
from .lexicon.builder import BuildConfig, build_database
from .lexicon.candidate_audit import (
    audit_auxiliary_candidates,
    write_candidate_audit_report,
)
from .lexicon.fetch import fetch_source
from .lexicon.formal_review import (
    evaluate_formal_human_gate,
    write_formal_gate_report,
    write_formal_review_sample,
)
from .lexicon.quality import (
    compare_databases,
    evaluate_database,
    write_report,
    write_review_sample,
)
from .lexicon.review import (
    BASELINE_PROFILE,
    PILOT_PROFILE,
    compare_judgments,
    write_comparison,
    write_judgment_template,
    write_stratified_review_sample,
)
from .lexicon.risk_review import (
    compare_risk_judgments,
    write_risk_review_sample,
)
from .operations import (
    _run_smoke,
    check_update_storage,
    initialize_updates,
    rollback_lexicon,
    send_notification,
    status_report,
    update_lexicon,
)
from .search_index import build_search_index


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="wordquery-jp")
    subparsers = parser.add_subparsers(dest="command", required=True)

    build = subparsers.add_parser("build", help="検索用SQLite辞書を構築する")
    build.add_argument("--output", type=Path, default=Path("var/lexicon.sqlite3"))
    build.add_argument("--jmdict", type=Path)
    build.add_argument("--sudachi", type=Path)
    build.add_argument("--additions", type=Path, default=Path("data/manual/additions.tsv"))
    build.add_argument("--corrections", type=Path, default=Path("data/manual/corrections.tsv"))
    build.add_argument("--exclusions", type=Path, default=Path("data/manual/exclusions.tsv"))
    build.add_argument("--tags", type=Path, default=Path("data/manual/tags.tsv"))
    build.add_argument("--source-manifest", type=Path, default=Path("data/sources.toml"))

    update = subparsers.add_parser(
        "update", help="最新版JMdictを検証し、版付き辞書releaseとして採用する"
    )
    update.add_argument("--state-dir", type=Path, required=True)
    update.add_argument("--component-root", type=Path)
    update.add_argument("--force", action="store_true")
    update.add_argument("--dry-run", action="store_true")
    update.add_argument("--no-reload", action="store_true")
    index = subparsers.add_parser(
        "build-search-index", help="既存辞書の検索索引を生成（DB変更なし）"
    )
    index.add_argument("--database", type=Path, required=True)
    check_search = subparsers.add_parser("check-search", help="既存辞書で検索検査だけを再実行する")
    check_search.add_argument("--database", type=Path, required=True)

    initialize = subparsers.add_parser(
        "initialize-updates", help="評価済み辞書を更新の基準版にする"
    )
    initialize.add_argument("--state-dir", type=Path, required=True)
    initialize.add_argument("--database", type=Path, required=True)
    initialize.add_argument("--component-root", type=Path)
    rollback = subparsers.add_parser("rollback", help="期限内の直前版に戻す（期限は延長しない）")
    rollback.add_argument("--state-dir", type=Path, required=True)
    rollback.add_argument("--no-reload", action="store_true")
    subparsers.add_parser("notify-test", help="管理者への更新通知メールをテスト送信する")

    status = subparsers.add_parser("status", help="公開辞書の更新状態を表示する")
    status.add_argument("--state-dir", type=Path, required=True)
    storage = subparsers.add_parser("check-storage", help="更新用の空き容量を確認（変更なし）")
    storage.add_argument("--state-dir", type=Path, required=True)

    evaluate = subparsers.add_parser("evaluate", help="品質ゲートを評価する")
    evaluate.add_argument("--database", type=Path, default=Path("var/lexicon.sqlite3"))
    evaluate.add_argument("--output", type=Path, default=Path("reports/quality.json"))
    evaluate.add_argument("--sample", type=Path, default=Path("reports/review-sample.tsv"))

    validate = subparsers.add_parser("validate", help="品質ゲートのみを検証する")
    validate.add_argument("--database", type=Path, default=Path("var/lexicon.sqlite3"))
    for quality_command in (evaluate, validate):
        quality_command.add_argument("--formal-sample", type=Path)
        quality_command.add_argument("--formal-judgment", type=Path)
        quality_command.add_argument(
            "--exploration-sample",
            type=Path,
            action="append",
            default=[],
        )

    diff = subparsers.add_parser("diff", help="2つの生成辞書を比較する")
    diff.add_argument("before", type=Path)
    diff.add_argument("after", type=Path)
    diff.add_argument("--output", type=Path)

    fetch = subparsers.add_parser("fetch", help="マニフェスト指定の外部辞書を取得する")
    fetch.add_argument("source")
    fetch.add_argument("--manifest", type=Path, default=Path("data/sources.toml"))
    fetch.add_argument("--destination", type=Path, default=Path("data/raw"))

    review_sample = subparsers.add_parser(
        "review-sample", help="出典層別の一般語評価サンプルを作る"
    )
    review_sample.add_argument("--database", type=Path, default=Path("var/lexicon.sqlite3"))
    review_sample.add_argument("--output", type=Path, required=True)
    review_sample.add_argument("--profile", choices=("pilot", "baseline"), default="baseline")
    review_sample.add_argument("--seed", type=int, default=0)
    review_sample.add_argument("--force", action="store_true")

    review_template = subparsers.add_parser(
        "review-template", help="出典情報を伏せた評価者別TSVを作る"
    )
    review_template.add_argument("sample", type=Path)
    review_template.add_argument("--output", type=Path, required=True)
    review_template.add_argument("--reviewer", required=True)
    review_template.add_argument("--reviewer-kind", choices=("llm", "human"), required=True)
    review_template.add_argument("--model-version", required=True)
    review_template.add_argument("--prompt-version", required=True)
    review_template.add_argument("--force", action="store_true")

    review_compare = subparsers.add_parser(
        "review-compare", help="独立した複数の語彙判定を検証・比較する"
    )
    review_compare.add_argument("sample", type=Path)
    review_compare.add_argument("judgments", type=Path, nargs="+")
    review_compare.add_argument("--output", type=Path, required=True)
    review_compare.add_argument("--force", action="store_true")

    formal_sample = subparsers.add_parser(
        "formal-review-sample", help="探索標本と独立した一様無作為の人間確認標本を作る"
    )
    formal_sample.add_argument(
        "--database", type=Path, default=Path("var/lexicon.sqlite3")
    )
    formal_sample.add_argument("--output", type=Path, required=True)
    formal_sample.add_argument(
        "--exploration-sample",
        type=Path,
        action="append",
        required=True,
    )
    formal_sample.add_argument("--size", type=int, choices=(300, 473), default=300)
    formal_sample.add_argument("--seed", type=int, default=0)
    formal_sample.add_argument("--force", action="store_true")

    formal_gate = subparsers.add_parser(
        "formal-review-gate", help="独立人間確認標本の片側95%%信頼下限を判定する"
    )
    formal_gate.add_argument("sample", type=Path)
    formal_gate.add_argument("judgment", type=Path)
    formal_gate.add_argument(
        "--database", type=Path, default=Path("var/lexicon.sqlite3")
    )
    formal_gate.add_argument(
        "--exploration-sample",
        type=Path,
        action="append",
        required=True,
    )
    formal_gate.add_argument("--output", type=Path, required=True)
    formal_gate.add_argument("--force", action="store_true")

    candidate_audit = subparsers.add_parser(
        "candidate-audit", help="補助候補の完全性・分類範囲・採用単位を監査する"
    )
    candidate_audit.add_argument(
        "--database", type=Path, default=Path("var/lexicon.sqlite3")
    )
    candidate_audit.add_argument(
        "--output", type=Path, default=Path("reports/candidate-audit.json")
    )

    risk_sample = subparsers.add_parser(
        "risk-review-sample", help="母集団推定と分離した語彙リスク標本を作る"
    )
    risk_sample.add_argument(
        "--database", type=Path, default=Path("var/lexicon.sqlite3")
    )
    risk_sample.add_argument("--output", type=Path, required=True)
    risk_sample.add_argument("--per-panel", type=int, default=30)
    risk_sample.add_argument("--seed", type=int, default=0)
    risk_sample.add_argument("--force", action="store_true")

    risk_compare = subparsers.add_parser(
        "risk-review-compare", help="独立したリスク標本判定を診断専用で比較する"
    )
    risk_compare.add_argument("sample", type=Path)
    risk_compare.add_argument("judgments", type=Path, nargs="+")
    risk_compare.add_argument("--output", type=Path, required=True)
    risk_compare.add_argument("--force", action="store_true")

    search_benchmark = subparsers.add_parser(
        "search-benchmark", help="代表問題の先頭10件と既知解への到達を記録する"
    )
    search_benchmark.add_argument(
        "--database", type=Path, default=Path("var/lexicon.sqlite3")
    )
    search_benchmark.add_argument("--cases", type=Path, required=True)
    search_benchmark.add_argument(
        "--output", type=Path, default=Path("reports/search-benchmark.json")
    )
    search_benchmark.add_argument(
        "--review-template", type=Path, default=Path("reports/search-review.tsv")
    )
    search_benchmark.add_argument("--timeout", type=float, default=2.0)
    search_benchmark.add_argument("--force", action="store_true")

    search_review = subparsers.add_parser(
        "search-review", help="入力済みの先頭10件人手評価を検証・集計する"
    )
    search_review.add_argument("benchmark", type=Path)
    search_review.add_argument("review", type=Path)
    search_review.add_argument("--output", type=Path, required=True)
    search_review.add_argument("--force", action="store_true")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    if args.command == "build":
        result = build_database(
            BuildConfig(
                output=args.output,
                additions=args.additions,
                corrections=args.corrections,
                exclusions=args.exclusions,
                tags=args.tags,
                jmdict=args.jmdict,
                sudachi=args.sudachi,
                source_manifest=args.source_manifest,
            )
        )
        print(
            f"built={result.output} accepted={result.accepted} "
            f"candidates={result.candidates} issues={result.issues} hash={result.input_hash}"
        )
        return 0
    if args.command == "build-search-index":
        logging.basicConfig(level=logging.INFO, format="%(message)s")
        print(json.dumps(build_search_index(args.database), ensure_ascii=False, indent=2))
        return 0
    if args.command == "check-search":
        report = _run_smoke(args.database)
        print(json.dumps(report, ensure_ascii=False, indent=2))
        return 1 if report["failures"] else 0
    if args.command == "notify-test":
        sent = send_notification(
            "WordQuery update notification test", "Notification delivery test."
        )
        print("Sent; confirm receipt." if sent else "SMTP configuration is missing.")
        return 0 if sent else 1
    if args.command == "rollback":
        rollback_lexicon(args.state_dir, reload_webapp=not args.no_reload)
        print("Rolled back; original freshness deadline retained.")
        return 0
    if args.command == "initialize-updates":
        initialize_updates(args.state_dir, args.database, root=args.component_root)
        print("Initialized. Freshness is not established; run update before public activation.")
        return 0
    if args.command == "update":
        logging.basicConfig(level=logging.INFO, format="%(message)s")
        result = update_lexicon(
            args.state_dir,
            root=args.component_root,
            force=args.force,
            dry_run=args.dry_run,
            reload_webapp=not args.no_reload,
        )
        print(
            json.dumps(
                {
                    "status": result.status,
                    "release_id": result.release_id,
                    "detail": result.detail,
                },
                ensure_ascii=False,
                indent=2,
            )
        )
        return 1 if result.status == "quarantined" else 0
    if args.command == "status":
        report = status_report(args.state_dir)
        print(json.dumps(report, ensure_ascii=False, indent=2))
        return 0 if report["fresh"] else 1
    if args.command == "check-storage":
        print(json.dumps(check_update_storage(args.state_dir), indent=2))
        return 0
    if args.command in {"evaluate", "validate"}:
        result = evaluate_database(
            args.database,
            formal_sample=args.formal_sample,
            formal_judgment=args.formal_judgment,
            exploration_samples=args.exploration_sample,
        )
        if args.command == "evaluate":
            write_report(result, args.output)
            write_review_sample(args.database, args.sample)
            print(f"report={args.output} sample={args.sample} passed={result.passed}")
        else:
            print(json.dumps(result.report, ensure_ascii=False, indent=2))
        return 0 if result.passed else 1
    if args.command == "diff":
        result = compare_databases(args.before, args.after)
        serialized = json.dumps(result, ensure_ascii=False, indent=2) + "\n"
        if args.output:
            args.output.parent.mkdir(parents=True, exist_ok=True)
            args.output.write_text(serialized, encoding="utf-8")
        else:
            print(serialized, end="")
        return 0
    if args.command == "fetch":
        result = fetch_source(args.source, manifest=args.manifest, destination=args.destination)
        print(
            f"source={result.source} path={result.path} sha256={result.sha256} "
            f"verified={result.verified}"
        )
        return 0
    if args.command == "review-sample":
        profile = PILOT_PROFILE if args.profile == "pilot" else BASELINE_PROFILE
        result = write_stratified_review_sample(
            args.database,
            args.output,
            sizes=profile,
            seed=args.seed,
            overwrite=args.force,
        )
        print(json.dumps(result, ensure_ascii=False, indent=2))
        return 0
    if args.command == "review-template":
        count = write_judgment_template(
            args.sample,
            args.output,
            reviewer=args.reviewer,
            reviewer_kind=args.reviewer_kind,
            model_version=args.model_version,
            prompt_version=args.prompt_version,
            overwrite=args.force,
        )
        print(f"template={args.output} rows={count}")
        return 0
    if args.command == "review-compare":
        report = compare_judgments(args.sample, args.judgments)
        write_comparison(report, args.output, overwrite=args.force)
        print(json.dumps(report, ensure_ascii=False, indent=2))
        return 0
    if args.command == "formal-review-sample":
        result = write_formal_review_sample(
            args.database,
            args.output,
            exploration_samples=args.exploration_sample,
            size=args.size,
            seed=args.seed,
            overwrite=args.force,
        )
        print(json.dumps(result, ensure_ascii=False, indent=2))
        return 0
    if args.command == "formal-review-gate":
        report = evaluate_formal_human_gate(
            args.database,
            args.sample,
            args.judgment,
            exploration_samples=args.exploration_sample,
        )
        write_formal_gate_report(report, args.output, overwrite=args.force)
        print(json.dumps(report, ensure_ascii=False, indent=2))
        return 0 if report["passed"] else 1
    if args.command == "candidate-audit":
        result = audit_auxiliary_candidates(args.database)
        write_candidate_audit_report(result, args.output)
        print(f"report={args.output} passed={result.passed}")
        return 0 if result.passed else 1
    if args.command == "risk-review-sample":
        result = write_risk_review_sample(
            args.database,
            args.output,
            per_panel=args.per_panel,
            seed=args.seed,
            overwrite=args.force,
        )
        print(json.dumps(result, ensure_ascii=False, indent=2))
        return 0
    if args.command == "risk-review-compare":
        report = compare_risk_judgments(args.sample, args.judgments)
        write_comparison(report, args.output, overwrite=args.force)
        print(json.dumps(report, ensure_ascii=False, indent=2))
        return 0
    if args.command == "search-benchmark":
        if not args.force:
            existing = [path for path in (args.output, args.review_template) if path.exists()]
            if existing:
                paths = ", ".join(str(path) for path in existing)
                raise FileExistsError(
                    f"既存ファイルを上書きしません: {paths}（--forceで上書き）"
                )
        report = run_search_benchmark(
            args.database,
            args.cases,
            timeout_seconds=args.timeout,
        )
        write_benchmark_report(report, args.output, overwrite=args.force)
        review_rows = write_search_review_template(
            report,
            args.review_template,
            overwrite=args.force,
        )
        print(
            json.dumps(
                {
                    **report["summary"],
                    "output": str(args.output),
                    "review_template": str(args.review_template),
                    "review_rows": review_rows,
                },
                ensure_ascii=False,
                indent=2,
            )
        )
        return 0
    if args.command == "search-review":
        benchmark = json.loads(args.benchmark.read_text(encoding="utf-8"))
        report = evaluate_search_review(benchmark, args.review)
        write_search_review_report(report, args.output, overwrite=args.force)
        print(json.dumps(report, ensure_ascii=False, indent=2))
        return 0
    raise AssertionError(f"Unhandled command: {args.command}")


if __name__ == "__main__":
    raise SystemExit(main())
