import json
from pathlib import Path

import pytest

from app.cipher.fn import (
    auto_split_number_string,
    bigram_frequency,
    bifid_d,
    bifid_e,
    braille_d,
    braille_ja_d,
    letter_frequency,
    morse_d,
    morse_e,
    morse_wabun_d,
    morse_wabun_e,
    phonetic_alphabet_d,
    phonetic_alphabet_e,
    playfair_d,
    playfair_e,
    polybius_d,
    polybius_e,
    return_japan_traditional_month_names_list,
    return_japanese_zodiac_list,
    return_phonetic_alphabet_values,
    return_zodiac_list,
    spelling_alphabet_icao_1947_1,
    spelling_alphabet_icao_1947_2,
    spelling_alphabet_icao_1949,
    spelling_alphabet_icao_1951,
    spelling_alphabet_icao_2008,
    text_split,
    vanity_d,
    vanity_e,
)


FUNCTIONS = {
    "playfair_e": playfair_e,
    "playfair_d": playfair_d,
    "polybius_e": polybius_e,
    "polybius_d": polybius_d,
    "bifid_e": bifid_e,
    "bifid_d": bifid_d,
    "morse_e": morse_e,
    "morse_d": morse_d,
    "morse_wabun_e": morse_wabun_e,
    "morse_wabun_d": morse_wabun_d,
    "phonetic_alphabet_e": phonetic_alphabet_e,
    "phonetic_alphabet_d": phonetic_alphabet_d,
    "return_phonetic_alphabet_values": return_phonetic_alphabet_values,
    "letter_frequency": letter_frequency,
    "bigram_frequency": bigram_frequency,
    "text_split": text_split,
    "braille_d": braille_d,
    "braille_ja_d": braille_ja_d,
    "auto_split_number_string": auto_split_number_string,
    "vanity_e": vanity_e,
    "vanity_d": vanity_d,
    "return_japan_traditional_month_names_list": return_japan_traditional_month_names_list,
    "return_zodiac_list": return_zodiac_list,
    "return_japanese_zodiac_list": return_japanese_zodiac_list,
}

TABLES = {
    "icao_2008": spelling_alphabet_icao_2008,
    "icao_1951": spelling_alphabet_icao_1951,
    "icao_1949": spelling_alphabet_icao_1949,
    "icao_1947_1": spelling_alphabet_icao_1947_1,
    "icao_1947_2": spelling_alphabet_icao_1947_2,
}


def _load_cases():
    path = Path(__file__).parent / "fixtures" / "gear_called_vectors.json"
    with path.open(encoding="utf-8") as f:
        return json.load(f)["cases"]


@pytest.mark.parametrize("case", _load_cases(), ids=lambda c: c["id"])
def test_gear_called_vectors(case):
    fn = FUNCTIONS[case["function"]]
    args = dict(case["args"])
    if "table" in args:
        args["dic"] = TABLES[args.pop("table")]

    try:
        actual = fn(**args)
    except Exception as exc:
        assert case.get("expected_exception") == exc.__class__.__name__
        return

    assert "expected_exception" not in case
    assert actual == case["expected"]
