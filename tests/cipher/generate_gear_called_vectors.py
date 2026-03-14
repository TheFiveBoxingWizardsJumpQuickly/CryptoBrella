import json
from datetime import date
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

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


def build_cases():
    cases = []
    idx = 1

    def add_case(function, args, expected=None, expected_exception=None):
        nonlocal idx
        case = {"id": f"{function}_{idx:04d}", "function": function, "args": args}
        if expected is not None:
            case["expected"] = expected
        if expected_exception is not None:
            case["expected_exception"] = expected_exception
        cases.append(case)
        idx += 1

    def add_eval(function, args, fn):
        try:
            add_case(function, args, expected=fn())
        except Exception as exc:
            add_case(function, args, expected_exception=exc.__class__.__name__)

    # playfair
    playfair_texts = [
        "",
        "A",
        "AB",
        "HELLO",
        "JIGGLE",
        "THEQUICKBROWNFOX",
        "attackatdawn",
        "A" * 31,
    ]
    for t in playfair_texts:
        add_eval("playfair_e", {"c": t}, lambda t=t: playfair_e(t))
        add_eval("playfair_d", {"c": t}, lambda t=t: playfair_d(t))

    # polybius / bifid
    poly_texts = ["A", "HELLO", "JIG", "CRYPTOGRAPHY", "ZZZZ", "ATTACKATDAWN", "CODEX"]
    for t in poly_texts:
        add_eval("polybius_e", {"text": t, "table_keyword": ""}, lambda t=t: polybius_e(t, ""))
        add_eval("polybius_e", {"text": t, "table_keyword": "KEY"}, lambda t=t: polybius_e(t, "KEY"))
        add_eval("bifid_e", {"text": t, "table_keyword": ""}, lambda t=t: bifid_e(t, ""))
        add_eval("bifid_e", {"text": t, "table_keyword": "KEY"}, lambda t=t: bifid_e(t, "KEY"))

    poly_d_texts = ["11", "2315313134", "5555", "12345", "1112131415"]
    for t in poly_d_texts:
        for key in ["", "KEY"]:
            add_eval("polybius_d", {"text": t, "table_keyword": key}, lambda t=t, key=key: polybius_d(t, key))

    bifid_d_texts = ["FNNVD", "ABCDE", "QWERTY", "A", ""]
    for t in bifid_d_texts:
        for key in ["", "KEY"]:
            add_eval("bifid_d", {"text": t, "table_keyword": key}, lambda t=t, key=key: bifid_d(t, key))

    # morse
    morse_texts = ["SOS", "HELLO WORLD", "CODEX 123", "A-B.C", "", "NINJA"]
    for t in morse_texts:
        for bin_code in [False, True]:
            for delimiter in [" ", "/", "|"]:
                add_case(
                    "morse_e",
                    {"text": t, "bin_code": bin_code, "delimiter": delimiter},
                    expected=None,
                )
                cases.pop()
                add_eval(
                    "morse_e",
                    {"text": t, "bin_code": bin_code, "delimiter": delimiter},
                    lambda t=t, bin_code=bin_code, delimiter=delimiter: morse_e(
                        t, bin_code=bin_code, delimiter=delimiter
                    ),
                )

    morse_encoded = [
        "... --- ...",
        ".-/-.../-.-.",
        "101 0 111",
        "",
        ".-|-...|.-.",
    ]
    for t in morse_encoded:
        for bin_code in [False, True]:
            for delimiter in [" ", "/", "|"]:
                add_case(
                    "morse_d",
                    {"text": t, "bin_code": bin_code, "delimiter": delimiter},
                    expected=None,
                )
                cases.pop()
                add_eval(
                    "morse_d",
                    {"text": t, "bin_code": bin_code, "delimiter": delimiter},
                    lambda t=t, bin_code=bin_code, delimiter=delimiter: morse_d(
                        t, bin_code=bin_code, delimiter=delimiter
                    ),
                )

    wabun_texts = ["アイウエオ", "ガギグ", "テスト", "かなカナ", ""]
    for t in wabun_texts:
        for bin_code in [False, True]:
            for delimiter in [" ", "/"]:
                add_case(
                    "morse_wabun_e",
                    {"text": t, "bin_code": bin_code, "delimiter": delimiter},
                    expected=None,
                )
                cases.pop()
                add_eval(
                    "morse_wabun_e",
                    {"text": t, "bin_code": bin_code, "delimiter": delimiter},
                    lambda t=t, bin_code=bin_code, delimiter=delimiter: morse_wabun_e(
                        t, bin_code=bin_code, delimiter=delimiter
                    ),
                )

    wabun_encoded = ["・－", ".- / -...", "101/010", "", ".- .- .-"]
    for t in wabun_encoded:
        for bin_code in [False, True]:
            for delimiter in [" ", "/"]:
                add_case(
                    "morse_wabun_d",
                    {"text": t, "bin_code": bin_code, "delimiter": delimiter},
                    expected=None,
                )
                cases.pop()
                add_eval(
                    "morse_wabun_d",
                    {"text": t, "bin_code": bin_code, "delimiter": delimiter},
                    lambda t=t, bin_code=bin_code, delimiter=delimiter: morse_wabun_d(
                        t, bin_code=bin_code, delimiter=delimiter
                    ),
                )

    # phonetic
    phonetic_tables = {
        "icao_2008": spelling_alphabet_icao_2008,
        "icao_1951": spelling_alphabet_icao_1951,
        "icao_1949": spelling_alphabet_icao_1949,
        "icao_1947_1": spelling_alphabet_icao_1947_1,
        "icao_1947_2": spelling_alphabet_icao_1947_2,
    }
    phonetic_inputs = ["attack", "alpha bravo", "xyz", "", "code42"]
    for name, table in phonetic_tables.items():
        add_eval(
            "return_phonetic_alphabet_values",
            {"table": name},
            lambda table=table: return_phonetic_alphabet_values(table),
        )
        for t in phonetic_inputs:
            add_eval(
                "phonetic_alphabet_e",
                {"text": t, "table": name},
                lambda t=t, table=table: phonetic_alphabet_e(t, table),
            )
            add_eval(
                "phonetic_alphabet_d",
                {"text": t, "table": name},
                lambda t=t, table=table: phonetic_alphabet_d(t, table),
            )

    # frequency / split
    freq_texts = ["HELLO", "HELLO HELLO", "AaBbCc", "", "AAAABBBCCXYZ", "one two three"]
    for t in freq_texts:
        for sortkey in [0, 1]:
            for reverse in [False, True]:
                add_case(
                    "letter_frequency",
                    {"text": t, "sortkey": sortkey, "reverse_flag": reverse},
                    expected=None,
                )
                cases.pop()
                add_eval(
                    "letter_frequency",
                    {"text": t, "sortkey": sortkey, "reverse_flag": reverse},
                    lambda t=t, sortkey=sortkey, reverse=reverse: letter_frequency(
                        t, sortkey=sortkey, reverse_flag=reverse
                    ),
                )
        add_eval("bigram_frequency", {"text": t}, lambda t=t: bigram_frequency(t))

    split_texts = ["ABCDEFGHIJ", "A", "", "1234567890", "日本語abc"]
    for t in split_texts:
        for step in [1, 2, 3, 5]:
            for sep in [" ", ",", "\n", "|"]:
                add_case("text_split", {"text": t, "step": step, "sep": sep}, expected=text_split(t, step, sep))
                cases.pop()
                add_eval(
                    "text_split",
                    {"text": t, "step": step, "sep": sep},
                    lambda t=t, step=step, sep=sep: text_split(t, step, sep),
                )
    # current behavior snapshot: step=0 raises ValueError
    try:
        text_split("ABCDE", 0, " ")
    except Exception as exc:
        add_case("text_split", {"text": "ABCDE", "step": 0, "sep": " "}, expected_exception=exc.__class__.__name__)

    # braille
    for i in range(64):
        dots = format(i, "06b")
        try:
            add_case("braille_d", {"braille_dots": dots}, expected=braille_d(dots))
        except Exception as exc:
            add_case("braille_d", {"braille_dots": dots}, expected_exception=exc.__class__.__name__)

    for i in range(0, 4096, 17):
        dots = format(i, "012b")
        add_eval("braille_ja_d", {"braille_dots": dots}, lambda dots=dots: braille_ja_d(dots))

    # auto split number string
    auto_inputs = [
        "656667 414243",
        "001000000110000101100010",
        "223334447777",
        "12 22 32 49 94",
        "abc123xyz456",
        "",
    ]
    patterns = ["DEC", "HEX", "OCT", "BIN", "vanity_toggle", "vanity_rept_number", "vanity_number_rept"]
    for t in auto_inputs:
        for p in patterns:
            add_case("auto_split_number_string", {"text": t, "pattern": p}, expected=auto_split_number_string(t, p))
            cases.pop()
            add_eval(
                "auto_split_number_string",
                {"text": t, "pattern": p},
                lambda t=t, p=p: auto_split_number_string(t, p),
            )

    # vanity
    vanity_texts = ["HELLO", "WORLD", "CRYPTO", "A", "", "INGRESS"]
    styles = ["toggle", "rept_number", "number_rept"]
    for t in vanity_texts:
        for s in styles:
            encoded = vanity_e(t, s)
            add_eval("vanity_e", {"text": t, "style": s}, lambda t=t, s=s: vanity_e(t, s))
            add_eval("vanity_d", {"text": encoded, "style": s}, lambda encoded=encoded, s=s: vanity_d(encoded, s))

    # snapshot invalid decode behavior
    for s in styles:
        bad = "999999999"
        add_eval("vanity_d", {"text": bad, "style": s}, lambda bad=bad, s=s: vanity_d(bad, s))

    # tables
    add_eval(
        "return_japan_traditional_month_names_list",
        {},
        lambda: return_japan_traditional_month_names_list(),
    )
    add_eval("return_zodiac_list", {}, lambda: return_zodiac_list())
    add_eval("return_japanese_zodiac_list", {}, lambda: return_japanese_zodiac_list())

    return cases


def main():
    cases = build_cases()
    payload = {
        "version": 1,
        "generated_on": str(date.today()),
        "case_count": len(cases),
        "note": "Additional baseline vectors for functions used by gear.py.",
        "cases": cases,
    }
    out = Path(__file__).parent / "fixtures" / "gear_called_vectors.json"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"wrote {len(cases)} cases to {out}")


if __name__ == "__main__":
    main()
