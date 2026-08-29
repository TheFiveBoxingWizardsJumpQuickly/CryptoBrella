import csv
import hashlib
import sqlite3

import pytest

from wordquery_jp.lexicon.formal_review import (
    FORMAL_SAMPLE_FIELDS,
    clopper_pearson_lower_bound,
    evaluate_formal_human_gate,
    write_formal_review_sample,
)
from wordquery_jp.lexicon.quality import evaluate_database
from wordquery_jp.lexicon.review import JUDGMENT_FIELDS, SAMPLE_FIELDS, write_judgment_template
from wordquery_jp.lexicon.schema import SCHEMA
from wordquery_jp.normalization import anagram_signature


def write_rows(path, fieldnames, rows):
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames, delimiter="\t")
        writer.writeheader()
        writer.writerows(rows)


def read_rows(path):
    with path.open(encoding="utf-8", newline="") as handle:
        return list(csv.DictReader(handle, delimiter="\t"))


def reading_for(index):
    alphabet = "あいうえおかきくけこさしすせそたちつてとなにぬねの"
    return f"てすと{alphabet[index // len(alphabet)]}{alphabet[index % len(alphabet)]}"


def build_general_database(path, count):
    with sqlite3.connect(path) as connection:
        connection.executescript(SCHEMA)
        connection.execute("INSERT INTO metadata VALUES ('input_hash', 'formal-test-hash')")
        for index in range(count):
            reading = reading_for(index)
            word_id = index + 1
            connection.execute(
                """
                INSERT INTO words(
                    id, surface, reading, normalized_reading, signature,
                    category, pos, priority, status
                ) VALUES (?, ?, ?, ?, ?, 'general', 'fixture', 10, 'accepted')
                """,
                (
                    word_id,
                    f"試験語{index}",
                    reading,
                    reading,
                    anagram_signature(reading),
                ),
            )
            connection.execute(
                """
                INSERT INTO provenance(
                    word_id, source, source_entry_id, surface, reading, category, pos,
                    reason, reference
                ) VALUES (?, 'manual', ?, ?, ?, 'general', 'fixture', 'fixture', 'fixture')
                """,
                (word_id, f"fixture:{word_id}", f"試験語{index}", reading),
            )


def sample_id(surface, normalized_reading):
    value = "\0".join((surface, normalized_reading, "general"))
    return hashlib.sha256(value.encode()).hexdigest()[:24]


def write_exploration_sample(path, *, index=0):
    reading = reading_for(index)
    surface = f"試験語{index}"
    write_rows(
        path,
        SAMPLE_FIELDS,
        [
            {
                "sample_schema_version": "1.0",
                "sample_id": sample_id(surface, reading),
                "database_input_hash": "exploration-hash",
                "sampling_seed": "7",
                "stratum": "sudachi_only",
                "population_size": "1",
                "sample_size": "1",
                "sample_weight": "1",
                "surface": surface,
                "reading": reading,
                "normalized_reading": reading,
                "claimed_category": "general",
                "status": "accepted",
                "pos": "fixture",
                "priority": "10",
                "sources": "manual",
            }
        ],
    )


def complete_human_judgment(row, *, valid=True):
    row.update(
        {
            "reviewer": "human-a",
            "reviewer_kind": "human",
            "model_version": "not-applicable",
            "prompt_version": "1.0",
            "lexicality": "pass" if valid else "fail",
            "reading_match": "pass",
            "headword_form": "pass",
            "form_integrity": "pass",
            "expected_category": "general",
            "category_match": "pass",
            "overall_label": "valid" if valid else "invalid",
            "confidence": "1.0",
            "reason_codes": "VALID_COMMON_KNOWLEDGE" if valid else "NON_LEXEME",
            "review_note": "formal fixture judgment",
        }
    )


@pytest.mark.parametrize(
    ("valid_count", "sample_size", "passes"),
    [
        (300, 300, True),
        (299, 300, False),
        (472, 473, True),
        (471, 473, False),
    ],
)
def test_formal_gate_uses_one_sided_exact_lower_bound(
    tmp_path, valid_count, sample_size, passes
):
    database = tmp_path / "lexicon.sqlite3"
    build_general_database(database, sample_size + 10)
    exploration = tmp_path / "exploration.tsv"
    write_exploration_sample(exploration)
    sample = tmp_path / "formal.tsv"
    summary = write_formal_review_sample(
        database,
        sample,
        exploration_samples=[exploration],
        size=sample_size,
        seed=11,
    )
    assert summary["selected"] == sample_size
    assert summary["overlap_with_exploration"] == 0
    assert all(
        row["sample_id"] != sample_id("試験語0", reading_for(0))
        for row in read_rows(sample)
    )

    judgment = tmp_path / "human.tsv"
    write_judgment_template(
        sample,
        judgment,
        reviewer="human-a",
        reviewer_kind="human",
        model_version="not-applicable",
        prompt_version="1.0",
    )
    rows = read_rows(judgment)
    for index, row in enumerate(rows):
        complete_human_judgment(row, valid=index < valid_count)
    write_rows(judgment, JUDGMENT_FIELDS, rows)

    report = evaluate_formal_human_gate(
        database,
        sample,
        judgment,
        exploration_samples=[exploration],
    )

    assert report["active"] is True
    assert report["passed"] is passes
    assert report["review"]["valid"] == valid_count
    assert (report["one_sided_95_lower_bound"] >= 0.99) is passes


def test_formal_gate_rejects_changed_exploration_evidence_and_llm_judge(tmp_path):
    database = tmp_path / "lexicon.sqlite3"
    build_general_database(database, 310)
    exploration = tmp_path / "exploration.tsv"
    write_exploration_sample(exploration)
    sample = tmp_path / "formal.tsv"
    write_formal_review_sample(
        database,
        sample,
        exploration_samples=[exploration],
        size=300,
    )
    incomplete_judgment = tmp_path / "incomplete-human.tsv"
    write_judgment_template(
        sample,
        incomplete_judgment,
        reviewer="human-a",
        reviewer_kind="human",
        model_version="not-applicable",
        prompt_version="1.0",
    )
    incomplete = evaluate_formal_human_gate(
        database,
        sample,
        incomplete_judgment,
        exploration_samples=[exploration],
    )
    assert incomplete["active"] is False
    assert incomplete["passed"] is False
    assert incomplete["failures"] == ["incomplete:0/300"]

    judgment = tmp_path / "judge.tsv"
    write_judgment_template(
        sample,
        judgment,
        reviewer="judge-a",
        reviewer_kind="llm",
        model_version="test-model",
        prompt_version="1.0",
    )

    with pytest.raises(ValueError, match="human"):
        evaluate_formal_human_gate(
            database,
            sample,
            judgment,
            exploration_samples=[exploration],
        )

    changed_exploration = tmp_path / "changed.tsv"
    write_exploration_sample(changed_exploration, index=1)
    with pytest.raises(ValueError, match="探索標本"):
        evaluate_formal_human_gate(
            database,
            sample,
            judgment,
            exploration_samples=[changed_exploration],
        )


def test_formal_gate_rejects_dictionary_version_change_and_duplicate_sample_id(
    tmp_path,
):
    database = tmp_path / "lexicon.sqlite3"
    build_general_database(database, 310)
    exploration = tmp_path / "exploration.tsv"
    write_exploration_sample(exploration)
    sample = tmp_path / "formal.tsv"
    write_formal_review_sample(
        database,
        sample,
        exploration_samples=[exploration],
        size=300,
    )
    judgment = tmp_path / "human.tsv"
    write_judgment_template(
        sample,
        judgment,
        reviewer="human-a",
        reviewer_kind="human",
        model_version="not-applicable",
        prompt_version="1.0",
    )

    with sqlite3.connect(database) as connection:
        connection.execute(
            "UPDATE metadata SET value = 'changed-hash' WHERE key = 'input_hash'"
        )
    with pytest.raises(ValueError, match="辞書入力ハッシュ"):
        evaluate_formal_human_gate(
            database,
            sample,
            judgment,
            exploration_samples=[exploration],
        )

    with sqlite3.connect(database) as connection:
        connection.execute(
            "UPDATE metadata SET value = 'formal-test-hash' WHERE key = 'input_hash'"
        )
    rows = read_rows(sample)
    rows[-1] = rows[0]
    write_rows(sample, FORMAL_SAMPLE_FIELDS, rows)
    with pytest.raises(ValueError, match="重複ID"):
        evaluate_formal_human_gate(
            database,
            sample,
            judgment,
            exploration_samples=[exploration],
        )


def test_quality_report_only_blocks_an_active_failed_formal_gate(tmp_path):
    database = tmp_path / "lexicon.sqlite3"
    build_general_database(database, 310)
    missing = tmp_path / "missing.tsv"

    without_evidence = evaluate_database(
        database,
        accepted_gold=missing,
        rejected_gold=missing,
    )
    assert without_evidence.passed is True
    assert without_evidence.report["formal_human_review"]["active"] is False

    exploration = tmp_path / "exploration.tsv"
    write_exploration_sample(exploration)
    sample = tmp_path / "formal.tsv"
    write_formal_review_sample(
        database,
        sample,
        exploration_samples=[exploration],
        size=300,
    )
    judgment = tmp_path / "human.tsv"
    write_judgment_template(
        sample,
        judgment,
        reviewer="human-a",
        reviewer_kind="human",
        model_version="not-applicable",
        prompt_version="1.0",
    )
    rows = read_rows(judgment)
    for index, row in enumerate(rows):
        complete_human_judgment(row, valid=index < 299)
    write_rows(judgment, JUDGMENT_FIELDS, rows)

    failed_gate = evaluate_database(
        database,
        accepted_gold=missing,
        rejected_gold=missing,
        formal_sample=sample,
        formal_judgment=judgment,
        exploration_samples=[exploration],
    )
    assert failed_gate.passed is False
    assert failed_gate.report["formal_human_review"]["active"] is True
    assert failed_gate.report["formal_human_review"]["passed"] is False
    assert failed_gate.report["failures"][0].startswith("formal_human_precision:")


def test_exact_lower_bound_threshold_examples():
    assert clopper_pearson_lower_bound(300, 300) == pytest.approx(
        0.05 ** (1 / 300)
    )
    assert clopper_pearson_lower_bound(300, 300) >= 0.99
    assert clopper_pearson_lower_bound(299, 300) < 0.99
    assert clopper_pearson_lower_bound(472, 473) >= 0.99
    assert clopper_pearson_lower_bound(471, 473) < 0.99
    with pytest.raises(ValueError):
        clopper_pearson_lower_bound(2, 1)
