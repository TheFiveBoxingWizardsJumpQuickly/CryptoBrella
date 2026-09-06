import hashlib
import json
import sqlite3
from datetime import UTC, datetime, timedelta
from pathlib import Path

import pytest
from flask import Flask
from wordquery_jp.lexicon.builder import BuildConfig, build_database
from wordquery_jp.operations import write_state

from app.wordquery.blueprint import register_wordquery

COMPONENT_ROOT = Path(__file__).resolve().parents[2] / "components" / "wordquery"
FIXTURES = COMPONENT_ROOT / "tests" / "fixtures"


@pytest.fixture(autouse=True)
def component_workdir(monkeypatch):
    monkeypatch.chdir(COMPONENT_ROOT)


def create_app(config):
    app = Flask("app")
    register_wordquery(app, config)
    return app


@pytest.fixture
def app(tmp_path):
    database = tmp_path / "lexicon.sqlite3"
    build_database(
        BuildConfig(output=database, additions=FIXTURES / "manual_additions.tsv")
    )
    return create_app(
        {
            "TESTING": True,
            "WORDQUERY_DB": database,
            "WORDQUERY_RATE_LIMIT": 20,
            "WORDQUERY_PUBLIC": True,
            "WORDQUERY_ENFORCE_FRESHNESS": False,
        }
    )


def test_search_budget_defaults(app):
    service = app.extensions["wordquery_service"]
    assert service.timeout_seconds == 5
    assert service.regex_timeout_seconds == 0.05


@pytest.mark.parametrize("single_match", [False, True])
def test_timeout_response_does_not_claim_partial_results(app, monkeypatch, single_match):
    from wordquery_jp.search_budget import RegexMatchTimedOut, SearchTimedOut

    def timeout(_request):
        error = RegexMatchTimedOut if single_match else SearchTimedOut
        raise error("検索を中断しました。")

    monkeypatch.setattr(app.extensions["wordquery_service"], "execute", timeout)
    response = app.test_client().post("/wordquery/api/search/anagram", json={"text": "ねこ"})
    assert response.status_code == 408
    assert response.json["error_code"] == (
        "regex_match_timeout" if single_match else "search_timeout"
    )
    assert "results" not in response.json


@pytest.mark.parametrize("fault", [None, "checksum", "unapproved", "input_hash", "missing"])
def test_reviewed_public_release_requires_matching_approved_manifest(app, fault):
    database = Path(app.config["WORDQUERY_DB"])
    with database.open("rb") as stream:
        digest = hashlib.file_digest(stream, "sha256").hexdigest()
    with sqlite3.connect(database) as connection:
        input_hash = dict(connection.execute("SELECT key, value FROM metadata"))["input_hash"]
    manifest = {
        "release_schema_version": 1,
        "database_sha256": "wrong" if fault == "checksum" else digest,
        "database_input_hash": "wrong" if fault == "input_hash" else input_hash,
        "formal_human_review": {"passed": fault != "unapproved"},
    }
    if fault != "missing":
        (database.parent / "manifest.json").write_text(json.dumps(manifest), encoding="utf-8")
    write_state(database.parent / "update-state", {
        "last_success_at": datetime.now(UTC).isoformat(), "active_input_hash": input_hash,
    })
    reviewed = create_app({
        "TESTING": True,
        "WORDQUERY_DB": database,
        "WORDQUERY_PUBLIC": True,
        "WORDQUERY_RELEASE_MODE": "reviewed",
        "WORDQUERY_ENFORCE_FRESHNESS": True,
        "WORDQUERY_STATE_DIR": database.parent / "update-state",
    })
    response = reviewed.test_client().post("/wordquery/api/search/anagram", json={"text": "ねこ"})
    assert response.status_code == (503 if fault else 200)
    assert "X-Robots-Tag" not in response.headers


def test_index_loads_dictionary(app):
    response = app.test_client().get("/wordquery/")
    assert response.status_code == 200
    page = response.get_data(as_text=True)
    assert "<title>WordQuery: JP</title>" in page
    assert '<h1><span>WordQuery</span><span class="product-suffix">: JP</span></h1>' in page
    assert "日本語候補検索" not in page
    assert "<summary>記法</summary>" in page
    assert "使い方・記法" not in page
    assert 'maxlength="200"' not in page
    assert "入力は200文字以内" not in page
    assert "正規表現検索は1.5秒以内" not in page
    assert "Pythonのregexモジュール互換" in page
    assert "結果は300件ずつ、最大3000件まで表示" in page
    assert '<option value="prefix">前方一致</option>' in page
    assert '<option value="suffix">後方一致</option>' in page
    assert '<option value="exact">完全一致</option>' in page
    assert 'role="tablist" aria-label="用途を選ぶ"' in page
    assert 'data-mode="reading">パターン</button>' in page
    assert 'data-mode="anagram">アナグラム</button>' in page
    assert 'data-mode="regex">Regex</button>' in page
    assert page.count('aria-controls="search-panel"') == 3
    assert page.count('id="result-header"') == 1
    assert 'state.mode === "anagram" ? "文字"' in page
    assert 'const regexMode = state.mode === "regex"' in page
    assert 'data-mode="crossword"' not in page
    assert 'data-mode="more"' not in page
    assert 'data-mode="pattern"' not in page
    assert 'data-mode="tools"' not in page
    assert 'data-advanced-mode' not in page
    assert '<option value="pattern">' not in page
    assert '<option value="regex">' not in page
    assert 'matchTypeField.classList.toggle("hidden", !readingMode || patternMode)' in page
    assert 'query.value.normalize("NFKC").replace(/[□_]/gu, "?")' in page
    assert 'const requestMode = () => wordUsesPattern() ? "pattern" : state.mode' in page
    assert 'id="crossword-builder"' not in page
    assert 'id="crossword-pattern"' not in page
    assert 'id="reading-length"' in page
    assert 'id="length-unit"' in page
    assert '<option value="mora">拍（モーラ）</option>' in page
    assert '<option value="surface">表記の文字数</option>' in page
    assert 'id="grid-profile"' not in page
    assert '<option value="grid">マス数</option>' not in page
    assert '<option value="combine_phonetic">拗音などを同じマス</option>' not in page
    assert 'id="must-include"' in page
    assert 'id="must-exclude"' in page
    assert 'id="refine-trigger"' in page
    assert ">その他の条件</button>" in page
    assert 'aria-selected="true"' in page
    assert 'id="query-error"' in page
    assert 'id="query-label">検索パターン</label>' in page
    assert 'id="primary-options" class="primary-options"' in page
    assert '<label for="match-type" id="match-type-field">一致' in page
    assert '<label for="reading-length" id="length-field">文字数' in page
    assert 'id="query-help"' not in page
    assert 'id="length-help"' not in page
    assert "読み / パターン" not in page
    assert "読みの一部に一致" not in page
    assert "読みを空欄にすると" not in page
    assert "（任意）" not in page
    assert '<label for="must-include">追加で含む' in page
    assert '<label for="must-exclude">含まない' in page
    assert 'id="show-more"' in page
    assert "const resultStep = 300" in page
    assert "const maximumResultLimit = 3000" in page
    assert "const initialResultLimit = Math.min(resultStep, maximumResultLimit)" in page
    assert "次の${nextCount}件を表示" in page
    assert "limit: requestedResultLimit" in page
    assert "さらに${Math.min(resultStep, remaining)}読み" not in page
    assert "指定した条件に一致する語はありません。" in page
    assert "window.history" not in page
    assert "URLSearchParams" not in page
    assert 'id="copy-search-url"' not in page
    assert 'id="condition-summary"' in page
    assert "<code>?</code>" in page
    assert "<code>[!かき]</code>" in page
    assert "error.position" in page
    assert 'id="include-proper"' not in page
    assert 'id="include-function"' not in page
    assert 'id="include-auxiliary"' not in page
    assert 'id="deprioritize-auxiliary"' not in page
    assert 'id="tag-axis"' not in page
    assert 'id="tag-value"' not in page
    assert 'id="tag-treatment"' in page
    assert '<details id="condition-options" class="condition-options">' in page
    assert "<summary>その他の条件</summary>" in page
    assert 'id="length-heading"' not in page
    assert 'id="refine-heading"' not in page
    assert 'id="condition-chips"' in page
    assert 'id="major-category"' in page
    assert '<option value="proper_type:person">人名</option>' in page
    assert '<option value="proper_type:place">地名</option>' in page
    assert '<option value="domain:computing">IT・コンピューター</option>' in page
    assert 'id="expert-tag-options"' not in page
    assert "上級タグを指定" not in page
    assert ">検索対象</legend>" not in page
    assert "const renderConditionChips = ()" in page
    assert "const clearCondition = (key)" in page
    assert 'conditions.push(["category", treatment])' in page
    assert 'button.dataset.clearCondition = key' in page
    assert "const selectedCategory = ()" in page
    assert 'category.axis === "proper_type"' in page
    assert '<option value="commonness">一般的な語を優先</option>' in page
    assert '<option value="dictionary_priority">辞書で優先される語</option>' in page
    assert '<option value="kana">読み順</option>' in page
    assert 'class="examples"' not in page
    assert 'id="condition-submit"' not in page
    assert 'fetch("/wordquery/api/search"' in page
    assert 'name="viewport"' in page


def test_preview_prefix_is_not_indexed(tmp_path):
    database = tmp_path / "lexicon.sqlite3"
    build_database(
        BuildConfig(output=database, additions=FIXTURES / "manual_additions.tsv")
    )
    preview_app = create_app(
        {
            "TESTING": True,
            "WORDQUERY_DB": database,
            "WORDQUERY_URL_PREFIX": "/preview-unguessable",
            "WORDQUERY_PUBLIC": False,
        }
    )

    response = preview_app.test_client().get("/preview-unguessable/")

    assert response.status_code == 200
    assert response.headers["X-Robots-Tag"] == "noindex, nofollow"


def test_public_search_stops_when_update_state_is_stale(tmp_path):
    database = tmp_path / "lexicon.sqlite3"
    state_dir = tmp_path / "state"
    build_database(
        BuildConfig(output=database, additions=FIXTURES / "manual_additions.tsv")
    )
    write_state(
        state_dir,
        {"last_success_at": (datetime.now(UTC) - timedelta(days=32)).isoformat()},
    )
    public_app = create_app(
        {
            "TESTING": True,
            "WORDQUERY_DB": database,
            "WORDQUERY_PUBLIC": True,
            "WORDQUERY_ENFORCE_FRESHNESS": True,
            "WORDQUERY_STATE_DIR": state_dir,
        }
    )

    page = public_app.test_client().get("/wordquery/")
    api = public_app.test_client().post(
        "/wordquery/api/search", json={"version": 1, "mode": "anagram", "query": "ねこ"}
    )

    assert page.status_code == 503
    assert api.status_code == 503
    assert api.json["error"] == "現在、不具合により検索を利用できません。"


@pytest.mark.parametrize("state_fault", ["expired", "mismatch", "missing", "malformed", "future"])
def test_freshness_checked_on_each_request_and_recovers_without_reload(app, tmp_path, state_fault):
    state_dir = tmp_path / "state"
    app.config.update(WORDQUERY_ENFORCE_FRESHNESS=True, WORDQUERY_STATE_DIR=state_dir)
    good = {"last_success_at": datetime.now(UTC).isoformat(),
            "active_input_hash": app.extensions["wordquery_metadata"]["input_hash"]}
    write_state(state_dir, good)
    client = app.test_client()
    assert client.get("/wordquery/").status_code == 200
    bad = dict(good)
    if state_fault == "expired":
        bad["last_success_at"] = (datetime.now(UTC) - timedelta(days=32)).isoformat()
    elif state_fault == "future":
        bad["last_success_at"] = (datetime.now(UTC) + timedelta(days=1)).isoformat()
    elif state_fault == "mismatch":
        bad["active_input_hash"] = "other-loaded-database"
    write_state(state_dir, bad)
    if state_fault == "missing":
        (state_dir / "state.json").unlink()
    elif state_fault == "malformed":
        (state_dir / "state.json").write_text("{")
    assert client.get("/wordquery/").status_code == 503
    assert client.post("/wordquery/api/search/anagram", json={"text": "ねこ"}).status_code == 503
    assert client.get("/wordquery/sources").status_code == 200
    write_state(state_dir, good)
    assert client.get("/wordquery/").status_code == 200


def test_public_ui_uses_reader_facing_terms(app):
    page = app.test_client().get("/wordquery/").get_data(as_text=True)

    assert "任意の1文字" in page
    assert "任意の0文字以上" in page
    assert "読み${readingLength.value}文字" in page
    assert '"文字数"' in page
    assert '${lengths.mora ?? "—"}モーラ' in page
    assert '"特徴"' in page
    assert '"分類情報の出典"' in page
    assert '"指定した分類のため後に表示"' in page
    for internal_term in (
        "任意の1かな",
        "任意の0かな以上",
        "推定一般度",
        "辞書優先度",
        '"タグ"',
        '"根拠"',
        '"基本辞書"',
        '"拡張辞書"',
        '"後方表示"',
        "EXAMPLES",
        "FILTERS",
    ):
        assert internal_term not in page


def test_regex_api_and_category_filter(app):
    client = app.test_client()
    response = client.post("/wordquery/api/search/regex", json={"pattern": "トウ"})
    assert response.status_code == 200
    assert response.json["total"] == 0
    response = client.post("/wordquery/api/search/regex", json={"pattern": "トウ", "include_proper": True})
    assert response.json["results"][0]["surface"] == "東京"
    assert response.json["results"][0]["status"] == "accepted"
    assert response.json["results"][0]["vocabulary_layer"] == "core"
    assert response.json["results"][0]["match_start"] == 0
    assert response.json["results"][0]["match_end"] == 2


@pytest.mark.parametrize(
    ("match_type", "query", "expected"),
    [
        ("contains", "ね", {"猫", "ネコ", "こね"}),
        ("prefix", "ね", {"猫", "ネコ"}),
        ("suffix", "ね", {"こね"}),
        ("exact", "ねこ", {"猫", "ネコ"}),
        ("regex", "^ね.*こ$", {"猫", "ネコ"}),
    ],
)
def test_reading_search_api_match_types(app, match_type, query, expected):
    response = app.test_client().post(
        "/wordquery/api/search/regex", json={"query": query, "match_type": match_type}
    )

    assert response.status_code == 200
    assert {item["surface"] for item in response.json["results"]} == expected


def test_reading_search_api_length_and_option_validation(app):
    client = app.test_client()
    response = client.post(
        "/wordquery/api/search/regex",
        json={"query": "ね", "match_type": "contains", "length": 2},
    )
    assert response.status_code == 200
    assert response.json["total"] == 3

    length_only = client.post(
        "/wordquery/api/search/regex",
        json={"query": "", "match_type": "contains", "length": 2},
    )
    assert length_only.status_code == 200
    assert length_only.json["total"] == 3

    assert client.post(
        "/wordquery/api/search/regex", json={"query": "ね", "match_type": "unknown"}
    ).status_code == 400
    assert client.post(
        "/wordquery/api/search/regex", json={"query": "ね", "match_type": "contains", "length": 0}
    ).status_code == 400


def test_versioned_search_api_supports_length_units(app):
    client = app.test_client()
    response = client.post(
        "/wordquery/api/search",
        json={
            "version": 1,
            "mode": "reading",
            "query": "う",
            "length": 4,
            "length_unit": "mora",
            "include_proper": True,
        },
    )

    assert response.status_code == 200
    assert [item["surface"] for item in response.json["results"]] == ["東京"]
    assert response.json["request"] == {
        "version": 1,
        "mode": "reading",
        "query": "う",
        "match_type": "contains",
        "length": 4,
        "length_unit": "mora",
        "grid_profile": "separate",
        "include_proper": True,
        "include_function": False,
        "limit": 3000,
    }

    surface = client.post(
        "/wordquery/api/search",
        json={
            "version": 1,
            "mode": "reading",
            "query": "う",
            "length": 2,
            "length_unit": "surface",
            "include_proper": True,
        },
    )
    assert [item["surface"] for item in surface.json["results"]] == ["東京"]


def test_version_2_api_exposes_selected_sort_and_reasons(app):
    response = app.test_client().post(
        "/wordquery/api/search",
        json={
            "version": 2,
            "mode": "reading",
            "query": "ね",
            "sort": "commonness",
        },
    )

    assert response.status_code == 200
    assert response.json["request"]["sort"] == "commonness"
    assert all(item["sort_score"] is not None for item in response.json["results"])
    assert all(item["sort_reasons"] for item in response.json["results"])


def test_version_3_api_filters_auxiliary_layer_and_tags(tmp_path):
    database = tmp_path / "candidate-filter.sqlite3"
    build_database(
        BuildConfig(
            output=database,
            additions=tmp_path / "no-additions.tsv",
            sudachi=FIXTURES / "sudachi_raw.csv",
            source_manifest=tmp_path / "none.toml",
        )
    )
    app = create_app({"TESTING": True, "WORDQUERY_DB": database})
    client = app.test_client()
    payload = {
        "version": 3,
        "mode": "reading",
        "query": "とうきょう",
        "match_type": "exact",
        "include_proper": True,
        "vocabulary_layers": ["auxiliary"],
        "tag_filters": [{"axis": "proper_type", "value": "place"}],
    }

    response = client.post("/wordquery/api/search", json=payload)
    payload["tag_filters"][0]["value"] = "person"
    excluded = client.post("/wordquery/api/search", json=payload)

    assert response.status_code == 200
    assert [item["surface"] for item in response.json["results"]] == ["東京"]
    assert response.json["request"]["vocabulary_layers"] == ["auxiliary"]
    assert response.json["request"]["tag_filters"] == [{"axis": "proper_type", "value": "place"}]
    assert excluded.status_code == 200
    assert excluded.json["total"] == 0


def test_version_4_api_marks_deprioritized_auxiliary_results(tmp_path):
    database = tmp_path / "candidate-deprioritize.sqlite3"
    build_database(
        BuildConfig(
            output=database,
            additions=tmp_path / "no-additions.tsv",
            sudachi=FIXTURES / "sudachi_raw.csv",
            source_manifest=tmp_path / "none.toml",
        )
    )
    app = create_app({"TESTING": True, "WORDQUERY_DB": database})
    response = app.test_client().post(
        "/wordquery/api/search",
        json={
            "version": 4,
            "mode": "reading",
            "query": "とうきょう",
            "match_type": "exact",
            "include_proper": True,
            "vocabulary_layers": ["core", "auxiliary"],
            "deprioritize_vocabulary_layers": ["auxiliary"],
        },
    )

    assert response.status_code == 200
    assert response.json["request"]["deprioritize_vocabulary_layers"] == ["auxiliary"]
    assert response.json["results"][0]["surface"] == "東京"
    assert response.json["results"][0]["deprioritize_reasons"] == ["補助候補"]


def test_versioned_search_api_dispatches_regex_and_anagram(app):
    client = app.test_client()

    regex = client.post(
        "/wordquery/api/search",
        json={"version": 1, "mode": "regex", "query": "^ね.*こ$"},
    )
    anagram = client.post(
        "/wordquery/api/search",
        json={"version": 1, "mode": "anagram", "query": "ネコ"},
    )

    assert regex.status_code == 200
    assert {item["surface"] for item in regex.json["results"]} == {"猫", "ネコ"}
    assert anagram.status_code == 200
    assert {item["surface"] for item in anagram.json["results"]} == {"猫", "ネコ", "こね"}


def test_version_5_pattern_api_returns_condition_description_and_error_position(app):
    client = app.test_client()

    response = client.post(
        "/wordquery/api/search",
        json={
            "version": 5,
            "mode": "pattern",
            "query": "ね?",
            "sort": "commonness",
            "vocabulary_layers": ["core"],
        },
    )
    invalid = client.post(
        "/wordquery/api/search",
        json={
            "version": 5,
            "mode": "pattern",
            "query": "ね[こ",
            "sort": "commonness",
            "vocabulary_layers": ["core"],
        },
    )

    assert response.status_code == 200
    assert {item["surface"] for item in response.json["results"]} == {"猫", "ネコ"}
    assert response.json["request"]["mode"] == "pattern"
    assert response.json["condition_description"].startswith("パターン全体:")
    assert invalid.status_code == 400
    assert invalid.json["error_position"] == 1
    assert "2文字目" in invalid.json["error"]


def test_version_6_crossword_api_returns_structured_effective_cells(app):
    client = app.test_client()
    payload = {
        "version": 6,
        "mode": "crossword",
        "grid_cells": [
            {"kind": "exact", "values": ["ネ"]},
            {"kind": "include", "values": ["コ", "ご"]},
        ],
        "must_exclude": "ご",
        "sort": "commonness",
        "vocabulary_layers": ["core"],
    }

    response = client.post("/wordquery/api/search", json=payload)
    invalid = client.post(
        "/wordquery/api/search",
        json={
            "version": 6,
            "mode": "crossword",
            "grid_cells": [{"kind": "exact", "values": ["きゃ"]}],
        },
    )

    assert response.status_code == 200
    assert {item["surface"] for item in response.json["results"]} == {"猫", "ネコ"}
    assert response.json["request"]["length"] == 2
    assert response.json["request"]["length_unit"] == "grid"
    assert response.json["request"]["grid_cells"] == [
        {"kind": "exact", "values": ["ね"]},
        {"kind": "include", "values": ["こ", "ご"]},
    ]
    assert response.json["condition_description"].startswith("クロスワード2マス:")
    assert invalid.status_code == 400
    assert "1マスになる必要" in invalid.json["error"]


def test_versioned_search_api_rejects_missing_version_and_invalid_profile(app):
    client = app.test_client()

    missing = client.post("/wordquery/api/search", json={"mode": "reading", "query": "ね"})
    invalid = client.post(
        "/wordquery/api/search",
        json={
            "version": 1,
            "mode": "reading",
            "query": "ね",
            "length_unit": "mora",
            "grid_profile": "combine_phonetic",
        },
    )

    assert missing.status_code == 400
    assert "version" in missing.json["error"]
    assert invalid.status_code == 400
    assert "文字数の数え方が「マス数」" in invalid.json["error"]


def test_reading_search_api_include_and_exclude_filters(app):
    client = app.test_client()
    response = client.post(
        "/wordquery/api/search/regex",
        json={
            "query": ".",
            "match_type": "regex",
            "must_include": "ね",
            "must_exclude": "こ",
        },
    )

    assert response.status_code == 200
    assert response.json["total"] == 0
    invalid = client.post(
        "/wordquery/api/search/regex",
        json={"query": "ね", "match_type": "contains", "must_include": "漢字"},
    )
    assert invalid.status_code == 400
    assert "絞り込み" in invalid.json["error"]
    invalid_query = client.post(
        "/wordquery/api/search/regex",
        json={"query": "漢字", "match_type": "contains"},
    )
    assert invalid_query.status_code == 400
    assert invalid_query.json["error"] == "かなと長音記号だけを使用してください。"


def test_anagram_api(app):
    response = app.test_client().post("/wordquery/api/search/anagram", json={"text": "ネコ"})
    assert response.status_code == 200
    assert {item["surface"] for item in response.json["results"]} == {"猫", "ネコ", "こね"}


def test_legacy_api_returns_canonical_request(app):
    response = app.test_client().post(
        "/wordquery/api/search/regex",
        json={"query": "ね", "match_type": "contains"},
    )

    assert response.status_code == 200
    assert response.json["request"]["version"] == 1
    assert response.json["request"]["mode"] == "reading"


def test_api_marks_on_demand_candidate_results_as_auxiliary(tmp_path):
    database = tmp_path / "candidate.sqlite3"
    build_database(
        BuildConfig(
            output=database,
            additions=tmp_path / "no-additions.tsv",
            sudachi=FIXTURES / "sudachi_raw.csv",
            source_manifest=tmp_path / "none.toml",
        )
    )
    app = create_app({"TESTING": True, "WORDQUERY_DB": database})

    response = app.test_client().post(
        "/wordquery/api/search",
        json={
            "version": 1,
            "mode": "reading",
            "query": "とうきょう",
            "match_type": "exact",
            "include_proper": True,
        },
    )

    assert response.status_code == 200
    assert response.json["results"] == [
        {
            "surface": "東京",
            "reading": "トウキョウ",
            "normalized_reading": "とうきょう",
                "category": "proper",
                "all_categories": ["proper"],
            "pos": "名詞, 固有名詞, 地名, 一般",
            "status": "candidate",
            "vocabulary_layer": "auxiliary",
                "multiple_sources": False,
                "sources": [
                    {
                        "source": "sudachidict",
                        "source_entry_id": "sudachi_raw.csv:7",
                        "surface": "東京",
                        "reading": "トウキョウ",
                        "category": "proper",
                        "pos": "名詞, 固有名詞, 地名, 一般",
                        "reason": "",
                        "reference": "",
                    }
                ],
            "lengths": {"kana": 5, "mora": 4, "surface": 2},
            "sort_score": 10,
            "sort_reasons": ["辞書優先度 10"],
            "deprioritize_reasons": [],
            "tags": [
                {
                    "axis": "proper_type",
                    "value": "place",
                    "evidence": [
                        {
                            "source": "sudachidict",
                            "source_entry_id": "sudachi_raw.csv:7",
                            "value": "地名",
                            "reason": "",
                            "reference": "",
                        }
                    ],
                }
            ],
            "match_start": 0,
            "match_end": 5,
        }
    ]


def test_result_limit_is_shared_by_ui_and_api(app):
    app.config["WORDQUERY_RESULT_LIMIT"] = 1
    client = app.test_client()
    page = client.get("/wordquery/").get_data(as_text=True)
    response = client.post("/wordquery/api/search/anagram", json={"text": "ネコ"})

    assert "最大1件まで表示" in page
    assert response.json["total"] == 3
    assert response.json["truncated"] is True
    assert len(response.json["results"]) == 1


def test_search_api_accepts_a_result_limit_up_to_the_server_maximum(app):
    client = app.test_client()
    response = client.post(
        "/wordquery/api/search/anagram", json={"text": "ネコ", "limit": 1}
    )
    too_large = client.post(
        "/wordquery/api/search/anagram", json={"text": "ネコ", "limit": 3001}
    )
    invalid_type = client.post(
        "/wordquery/api/search/anagram", json={"text": "ネコ", "limit": True}
    )

    assert response.status_code == 200
    assert response.json["request"]["limit"] == 1
    assert len(response.json["results"]) == 1
    assert too_large.status_code == 400
    assert "1から3000まで" in too_large.json["error"]
    assert invalid_type.status_code == 400


def test_mobile_styles_stack_controls_and_wrap_results(app):
    response = app.test_client().get("/static/wordquery/wordquery.css")
    css = response.get_data(as_text=True)

    assert response.status_code == 200
    assert "@media (max-width: 360px)" in css
    assert ".primary-options { display: grid; grid-template-columns: 1fr; }" in css
    assert "flex-direction: column;" in css
    assert "grid-template-columns: repeat(3, minmax(0, 1fr));" not in css
    assert ".crossword-cells" not in css
    assert ".condition-chips button::after" in css
    assert ".condition-options-content" in css
    assert ".advanced-actions" not in css
    assert "overflow-wrap: anywhere" in css


def test_workbench_visual_language_uses_unified_light_tool_palette(app):
    page = app.test_client().get("/wordquery/").get_data(as_text=True)
    css = app.test_client().get("/static/wordquery/wordquery.css").get_data(as_text=True)

    assert 'class="site-header"' in page
    assert 'class="hero"' not in page
    assert "--bg: hsl(178 17% 92%)" in css
    assert "--surface: hsl(180 12% 97%)" in css
    assert "--ink: hsl(222 10% 20%)" in css
    assert "--line: hsl(186 12% 78%)" in css
    assert "--accent: hsl(16 57% 39%)" in css
    assert "box-shadow" not in css
    assert "#f4f1e8" not in css
    assert ".site-header h1" in css
    assert "letter-spacing: 0" in css
    assert ".tabs {\n  display: flex;" in css
    assert "gap: 24px" in css
    assert ".result-group:hover" in css


def test_result_workbench_groups_readings_without_row_selection_noise(app):
    page = app.test_client().get("/wordquery/").get_data(as_text=True)
    css = app.test_client().get("/static/wordquery/wordquery.css").get_data(as_text=True)

    assert 'id="result-actions"' not in page
    assert 'id="copy-search-url"' not in page
    assert "const groupResultItems = (items)" in page
    assert 'detailSummary.textContent = "詳細"' in page
    assert "resultItems = groupResultItems(data.results)" in page
    assert "variant.append(surface, detail)" in page
    assert 'className = "result-select"' not in page
    assert 'id="copy-selected"' not in page
    assert "result-primary-meta" not in page
    assert ".result-group-heading" in css
    assert ".result-variant" in css
    assert 'font-size: 1.08rem' in css
    assert 'color: var(--ink)' in css
    assert 'background: #edf2f3' not in css
    assert "position: sticky" in css


def test_result_display_options_control_readings_highlight_and_sort(app):
    page = app.test_client().get("/wordquery/").get_data(as_text=True)
    css = app.test_client().get("/static/wordquery/wordquery.css").get_data(as_text=True)

    assert 'id="result-display-options"' in page
    assert 'id="result-header" class="result-header hidden"' in page
    assert 'class="result-display-options hidden"' in page
    assert '<details id="result-display-options"' not in page
    assert 'id="readings-only"' in page
    assert "表記を隠す" in page
    assert 'id="highlight-match" type="checkbox" checked' in page
    assert '<label id="highlight-control">\n                  <input id="highlight-match"' in page
    assert "一致強調" in page
    assert '<label for="sort-mode">並び順' in page
    assert 'resultCount.textContent = `${count}件`' in page
    assert 'readingCount.textContent = `/ ${readings}読み`' in page
    assert 'region.classList.toggle("readings-only", readingsOnly.checked)' in page
    assert 'region.classList.toggle("hide-match-highlight", !highlightMatch.checked)' in page
    assert 'highlightControl.classList.toggle("hidden", state.mode === "anagram")' in page
    assert 'primaryOptions.classList.toggle("hidden", state.mode !== "reading")' in page
    assert 'if (state.mode === "reading") {' in page
    assert "body.grid_profile" not in page
    assert "if (resultItems.length) form.requestSubmit()" in page
    assert ".readings-only .result-variants" in css
    assert 'className = "result-group-detail"' in page
    assert 'groupDetailSummary.textContent = "詳細"' in page
    assert ".readings-only .result-group-detail" in css
    assert ".hide-match-highlight .results mark" in css
    assert ".result-header" in css


def test_sources_page_uses_product_name(app):
    page = app.test_client().get("/wordquery/sources").get_data(as_text=True)

    assert "<title>データ出典 — WordQuery: JP</title>" in page
    assert "← WordQuery: JP" in page
    assert "James William Breen" in page
    assert "現在使用中のデータ版" not in page
    assert "SudachiDict-LEGAL.txt" in page
    assert "CC BY-SA 4.0" in page


def test_search_page_always_links_to_licensing(app):
    page = app.test_client().get("/wordquery/").get_data(as_text=True)

    assert "データ出典・ライセンス" in page
    assert page.count('href="/wordquery/sources"') == 1
    assert "item.all_categories" in page


def test_invalid_query_and_missing_database(tmp_path):
    app = create_app({"TESTING": True, "WORDQUERY_DB": tmp_path / "missing.sqlite3"})
    response = app.test_client().post("/wordquery/api/search/anagram", json={"text": "東京"})
    assert response.status_code == 503
    assert "error" in response.json
    page = app.test_client().get("/wordquery/").get_data(as_text=True)
    assert "現在、不具合により検索を利用できません。" in page
    assert "make lexicon-build" not in page
    assert str(tmp_path) not in page


def test_rate_limit(app):
    app.extensions["wordquery_limiter"].limit = 1
    client = app.test_client()
    assert client.post("/wordquery/api/search/regex", json={"pattern": "ね"}).status_code == 200
    assert client.post("/wordquery/api/search/regex", json={"pattern": "ね"}).status_code == 429
