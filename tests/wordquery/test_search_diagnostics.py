import json
import subprocess
import sys
from pathlib import Path

from wordquery_jp.lexicon.builder import BuildConfig, build_database

from tools.diagnose_wordquery_search import CASES, markdown, measure

ROOT = Path(__file__).resolve().parents[2]


def test_representative_suite_preserves_results_across_budgets(tmp_path):
    database = tmp_path / "lexicon.sqlite3"
    build_database(BuildConfig(
        output=database,
        additions=ROOT / "components/wordquery/tests/fixtures/manual_additions.tsv",
    ))
    report = measure(database, 1.5, 4, 10)
    assert len(report["rows"]) == len(CASES) * 3
    assert all(row["status"] == "completed" for row in report["rows"])
    assert all(row["matches_reference"] for row in report["rows"])
    assert report["regex_guard"]["status"] == "interrupted_as_expected"
    assert "本番速度の再現ではありません" in markdown(report)


def test_custom_invalid_regex_is_reported_separately_from_timeout(tmp_path):
    database = tmp_path / "lexicon.sqlite3"
    build_database(BuildConfig(
        output=database,
        additions=ROOT / "components/wordquery/tests/fixtures/manual_additions.tsv",
    ))
    output = tmp_path / "diagnosis.json"
    command = [
        sys.executable, str(ROOT / "tools/diagnose_wordquery_search.py"),
        "--database", str(database), "--mode", "regex", "--query", "[",
        "--output", str(output),
    ]
    subprocess.run(command, check=True, capture_output=True)
    report = json.loads(output.read_text(encoding="utf-8"))
    assert len(report["rows"]) == 3
    assert all(row["status"] == "invalid_query" for row in report["rows"])
    summary = output.with_suffix(".md").read_text(encoding="utf-8")
    assert "入力エラー" in summary
    assert "一致 0件 / 不一致 0件 / 未判定 2件" in summary
    original = output.read_bytes()
    repeated = subprocess.run(command, check=False, capture_output=True)
    assert repeated.returncode != 0
    assert output.read_bytes() == original
