import csv
from pathlib import Path

import pytest

from wordquery_jp.lexicon.builder import BuildConfig, build_database
from wordquery_jp.lexicon.review import (
    JUDGMENT_FIELDS,
    compare_judgments,
    write_judgment_template,
    write_stratified_review_sample,
)

FIXTURES = Path(__file__).parent / "fixtures"


def write_rows(path, fieldnames, rows):
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames, delimiter="\t")
        writer.writeheader()
        writer.writerows(rows)


def read_rows(path):
    with path.open(encoding="utf-8", newline="") as handle:
        return list(csv.DictReader(handle, delimiter="\t"))


def build_three_strata_database(tmp_path):
    sudachi = tmp_path / "sudachi.csv"
    sudachi.write_text(
        "surface,reading,dictionary_form,pos_1,pos_2\n"
        "犬,イヌ,犬,名詞,普通名詞\n"
        "苺,イチゴ,苺,名詞,普通名詞\n",
        encoding="utf-8",
    )
    database = tmp_path / "lexicon.sqlite3"
    build_database(
        BuildConfig(
            output=database,
            additions=tmp_path / "missing.tsv",
            jmdict=FIXTURES / "jmdict.xml",
            sudachi=sudachi,
            source_manifest=tmp_path / "missing.toml",
        )
    )
    return database


def complete_judgment(row, *, label="valid"):
    axis = "pass" if label == "valid" else "fail"
    row.update(
        {
            "lexicality": axis,
            "reading_match": "pass",
            "headword_form": "pass",
            "form_integrity": "pass",
            "expected_category": "general",
            "category_match": "pass",
            "overall_label": label,
            "confidence": "0.95",
            "reason_codes": "VALID_COMMON_KNOWLEDGE" if label == "valid" else "NON_LEXEME",
            "review_note": "test judgment",
        }
    )


def test_stratified_sample_is_stable_and_template_is_blind(tmp_path):
    database = build_three_strata_database(tmp_path)
    first = tmp_path / "sample-a.tsv"
    second = tmp_path / "sample-b.tsv"
    sizes = {"sudachi_only": 1, "jmdict_only": 1, "multi_source": 1}

    summary = write_stratified_review_sample(database, first, sizes=sizes, seed=7)
    write_stratified_review_sample(database, second, sizes=sizes, seed=7)

    assert first.read_text(encoding="utf-8") == second.read_text(encoding="utf-8")
    assert summary["total"] == 3
    rows = read_rows(first)
    assert {row["stratum"] for row in rows} == set(sizes)
    assert len({row["sample_id"] for row in rows}) == 3
    assert all(row["database_input_hash"] != "unknown" for row in rows)

    template = tmp_path / "judge.tsv"
    assert (
        write_judgment_template(
            first,
            template,
            reviewer="judge-a",
            reviewer_kind="llm",
            model_version="test-model",
            prompt_version="1.0",
        )
        == 3
    )
    header = read_rows(template)[0]
    assert "sources" not in header
    assert "stratum" not in header
    assert header["reviewer"] == "judge-a"

    with pytest.raises(FileExistsError, match="上書き"):
        write_judgment_template(
            first,
            template,
            reviewer="judge-a",
            reviewer_kind="llm",
            model_version="test-model",
            prompt_version="1.0",
        )


def test_comparison_reports_agreement_and_rejects_tampering(tmp_path):
    database = build_three_strata_database(tmp_path)
    sample = tmp_path / "sample.tsv"
    sizes = {"sudachi_only": 1, "jmdict_only": 1, "multi_source": 1}
    write_stratified_review_sample(database, sample, sizes=sizes)
    first = tmp_path / "judge-a.tsv"
    second = tmp_path / "judge-b.tsv"
    for path, reviewer in ((first, "judge-a"), (second, "judge-b")):
        write_judgment_template(
            sample,
            path,
            reviewer=reviewer,
            reviewer_kind="llm",
            model_version="test-model",
            prompt_version="1.0",
        )
        rows = read_rows(path)
        for row in rows:
            complete_judgment(row)
        if reviewer == "judge-b":
            complete_judgment(rows[0], label="invalid")
        write_rows(path, JUDGMENT_FIELDS, rows)

    report = compare_judgments(sample, [first, second])
    assert report["diagnostic_only"] is True
    assert report["common_complete"] == 3
    assert report["agreement"]["overall_label"] == {
        "agreed": 2,
        "compared": 3,
        "rate": 2 / 3,
    }
    assert report["consensus"] == {"disagreement": 1, "valid": 2}
    assert report["diagnostic"]["record_precision"] == 1.0

    tampered = read_rows(second)
    tampered[0]["surface"] = "改変"
    write_rows(second, JUDGMENT_FIELDS, tampered)
    with pytest.raises(ValueError, match="surfaceがサンプルと一致しません"):
        compare_judgments(sample, [first, second])


def test_comparison_rejects_partial_or_inconsistent_judgment(tmp_path):
    database = build_three_strata_database(tmp_path)
    sample = tmp_path / "sample.tsv"
    write_stratified_review_sample(
        database,
        sample,
        sizes={"sudachi_only": 1, "jmdict_only": 1, "multi_source": 1},
    )
    first = tmp_path / "judge-a.tsv"
    second = tmp_path / "judge-b.tsv"
    for path, reviewer in ((first, "judge-a"), (second, "judge-b")):
        write_judgment_template(
            sample,
            path,
            reviewer=reviewer,
            reviewer_kind="human",
            model_version="not-applicable",
            prompt_version="1.0",
        )

    rows = read_rows(first)
    rows[0]["lexicality"] = "pass"
    write_rows(first, JUDGMENT_FIELDS, rows)
    with pytest.raises(ValueError, match="判定が途中"):
        compare_judgments(sample, [first, second])

    for row in rows:
        complete_judgment(row)
    rows[0]["overall_label"] = "invalid"
    write_rows(first, JUDGMENT_FIELDS, rows)
    with pytest.raises(ValueError, match="overall_labelはvalid"):
        compare_judgments(sample, [first, second])
