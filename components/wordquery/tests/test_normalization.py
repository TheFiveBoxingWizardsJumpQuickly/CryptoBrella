import pytest

from wordquery_jp.normalization import (
    InvalidReading,
    anagram_signature,
    normalize_dictionary_reading,
    normalize_pattern,
    normalize_reading,
)


@pytest.mark.parametrize(
    ("source", "expected"),
    [
        ("ネコ", "ねこ"),
        ("ﾈｺ", "ねこ"),
        ("スーパー", "すーぱー"),
        (" ヴァイオリン ", "ゔぁいおりん"),
    ],
)
def test_normalize_reading(source, expected):
    assert normalize_reading(source) == expected


@pytest.mark.parametrize("value", ["", "東京", "ねこ です", "ねこ・いぬ"])
def test_invalid_readings_are_not_silently_cleaned(value):
    with pytest.raises(InvalidReading):
        normalize_reading(value)


def test_strict_distinctions_are_preserved():
    assert normalize_reading("がっこう") != normalize_reading("かつこう")
    assert normalize_reading("すーぱー") != normalize_reading("すうぱあ")


def test_regex_metacharacters_survive_kana_normalization():
    assert normalize_pattern("^ネ[コゴ]$") == "^ね[こご]$"


def test_dictionary_only_normalization_removes_orthographic_separators():
    assert normalize_dictionary_reading("アーガイル・チェック") == "あーがいるちぇっく"
    assert normalize_dictionary_reading("いざ、かまくら。") == "いざかまくら"
    assert normalize_dictionary_reading("ウ〜ン") == "うーん"
    with pytest.raises(InvalidReading):
        normalize_reading("アーガイル・チェック")


def test_anagram_signature_preserves_duplicate_count():
    assert anagram_signature("こころ") == "こころ"
    assert anagram_signature("こころ") != anagram_signature("ころ")
