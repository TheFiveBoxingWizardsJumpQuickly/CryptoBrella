import importlib
import json
import sys
import types
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

EXCLUDED_FUNCTIONS = set()


class DummyRequest:
    def __init__(self, payload):
        self.json = payload


def _ensure_secret_stub():
    if "app.secret" not in sys.modules:
        sys.modules["app.secret"] = types.ModuleType("app.secret")


def _apply_stubs(gear):
    def stub_password_generate(length, table):
        if length <= 0:
            return ""
        if not table:
            return ""
        out = []
        for i in range(length):
            out.append(table[i % len(table)])
        return "".join(out)

    def stub_passcode_get_random_id():
        return 42

    def stub_passcode_get_today_id():
        return 77

    def stub_passcode_get_list():
        return [
            {"id": 1, "date": "2026-03-01", "code": "ABCDEF123456", "tag": "Difficulty: Easy"},
            {"id": 2, "date": "2026-03-02", "code": "QWERTY987654", "tag": "Difficulty: Hard"},
        ]

    def stub_passcode_validate_answer(pid, input_answer):
        if input_answer == "ok":
            return ["Confirmed", "Invalid.", "Invalid."]
        if input_answer == "near":
            return ["Number part might be wrong.", "Invalid.", "Invalid."]
        return ["Invalid.", "Invalid.", "Invalid."]

    def stub_passcode_get_reward(pid, index):
        return ["100 AP", "100 XM", "L1 Resonator", "L1 Xmp Burster", "L4 Power Cube"]

    def stub_passcode_get_filtered_keywords(pattern):
        base = ["agent", "alpha", "abaddon", "delta"]
        return [w for w in base if pattern in w]

    gear.password_generate = stub_password_generate
    gear.passcode_get_random_id = stub_passcode_get_random_id
    gear.passcode_get_today_id = stub_passcode_get_today_id
    gear.passcode_get_list = stub_passcode_get_list
    gear.passcode_validate_answer = stub_passcode_validate_answer
    gear.passcode_get_reward = stub_passcode_get_reward
    gear.passcode_get_filtered_keywords = stub_passcode_get_filtered_keywords


def _normalize(value):
    if isinstance(value, dict):
        return {str(k): _normalize(v) for k, v in value.items()}
    if isinstance(value, list):
        return [_normalize(v) for v in value]
    return value


def _build_cases():
    cases = [
        {"function": "rot_gen", "json": {"input_text": "Abc-123"}},
        {"function": "playfair_gen", "json": {"input_text": "hidethegold"}},
        {"function": "vigenere_gen", "json": {"input_text": "AttackAtDawn", "key": "White Rabbit 42!"}},
        {
            "function": "enigma_gen",
            "json": {
                "input_text": "zuulpguxlkvjwmyrjbclxfoa",
                "left_rotor": "1",
                "mid_rotor": "2",
                "right_rotor": "3",
                "reflector": "B",
                "rotor_key": "AMT",
                "ring_key": "AAA",
                "plug_board": "",
            },
        },
        {
            "function": "purple_gen",
            "json": {
                "input_text": "FOV TATAKIDASI",
                "sixes_switch_position": "9",
                "twenties_switch_1_position": "1",
                "twenties_switch_2_position": "24",
                "twenties_switch_3_position": "6",
                "plugboard_full": "NOKTYUXEQLHBRMPDICJASVWGZF",
                "rotor_motion_key": "231",
            },
        },
        {"function": "prime_gen", "json": {"input_text": "84"}},
        {"function": "pwgen_gen", "json": {"char_type": "0", "length": "12"}},
        {"function": "charcode_gen", "json": {"input_text": "Ab!", "base": "16", "mode": "Char to Codepoint"}},
        {"function": "charcode_gen", "json": {"input_text": "41 62 21", "base": "16", "mode": "Codepoint to Char"}},
        {"function": "base64_gen", "json": {"input_text": "hello", "mode": "Encode"}},
        {"function": "base64_gen", "json": {"input_text": "aGVsbG8=", "mode": "Decode"}},
        {"function": "rectangle_gen", "json": {"input_text": "ABCDEFGH", "mode": "Divisors only"}},
        {"function": "rectangle_gen", "json": {"input_text": "ABCDE", "mode": "All pattern"}},
        {"function": "simplesub_gen", "json": {"input_text": "Hello-World_123"}},
        {"function": "frequency_gen", "json": {"input_text": "HELLO WORLD\nHELLO"}},
        {"function": "subs_handsolve_gen", "json": {"input_text": "ABCD-ABCD", "subs_from": "ABCD", "subs_to": "WXYZ"}},
        {"function": "railfence_gen", "json": {"input_text": "WEAREDISCOVEREDFLEEATONCE", "mode": "Encode", "offset": "0"}},
        {"function": "railfence_gen", "json": {"input_text": "WECRLTEERDSOEEFEAOCAIVDEN", "mode": "Decode", "offset": "0"}},
        {"function": "railfence_gen", "json": {"input_text": "WEAREDISCOVEREDFLEEATONCE", "mode": "Encode", "offset": ""}},
        {"function": "railfence_gen", "json": {"input_text": "WECRLTEERDSOEEFEAOCAIVDEN", "mode": "Decode", "offset": ""}},
        {"function": "morse_gen", "json": {"input_text": "... --- ...", "mode": "Decode"}},
        {"function": "morse_gen", "json": {"input_text": "sos", "mode": "Encode"}},
        {"function": "charreplace_gen", "json": {"input_text": "AABBCC", "replace_from": "ABC", "replace_to": "XYZ"}},
        {"function": "reverse_gen", "json": {"input_text": "stressed"}},
        {"function": "columnar_gen", "json": {"input_text": "WEAREDISCOVERED", "key": "ZEBRA"}},
        {"function": "hash_gen", "json": {"input_text": "hash-target"}},
        {"function": "braille_gen", "json": {"b1": True, "b2": False, "b3": False, "b4": False, "b5": False, "b6": False}},
        {
            "function": "braille_ja_gen",
            "json": {
                "bl1": True, "bl2": False, "bl3": False, "bl4": False, "bl5": False, "bl6": False,
                "br1": True, "br2": False, "br3": False, "br4": False, "br5": False, "br6": False,
            },
        },
        {"function": "rsa_gen", "json": {"m": "65", "e": "17", "n": "3233", "p": "61", "q": "53"}},
        {"function": "rsa_gen", "json": {"m": "65", "e": "17", "n": "3233", "p": "", "q": ""}},
        {"function": "affine_gen", "json": {"input_text": "AFFINECIPHER", "mode": "Encode"}},
        {"function": "affine_gen", "json": {"input_text": "IHHWVCSWFRCP", "mode": "Decode"}},
        {"function": "split_text_gen", "json": {"input_text": "ABCDEFGHIJ", "length": "3", "mode": "space"}},
        {"function": "split_text_gen", "json": {"input_text": "ABCDEFGHIJ", "length": "3", "mode": "comma"}},
        {"function": "split_text_gen", "json": {"input_text": "ABCDEFGHIJ", "length": "3", "mode": "newline"}},
        {"function": "number_conv_gen", "json": {"input_text": "10,255", "base": "10"}},
        {"function": "number_conv_gen", "json": {"input_text": "10,255", "base": ""}},
        {"function": "phonetic_gen", "json": {"input_text": "alpha bravo", "mode": "Decode"}},
        {"function": "phonetic_gen", "json": {"input_text": "attack", "mode": "Encode"}},
        {"function": "polybius_gen", "json": {"input_text": "2315313134", "mode": "Decode"}},
        {"function": "polybius_gen", "json": {"input_text": "HELLO", "mode": "Encode"}},
        {"function": "riddle_tables_gen", "json": {"mode": "jp_trad_month_name"}},
        {"function": "riddle_tables_gen", "json": {"mode": "zodiac"}},
        {"function": "riddle_tables_gen", "json": {"mode": "japanese_zodiac"}},
        {"function": "riddle_tables_gen", "json": {"mode": "keyboard_layout"}},
        {"function": "swap_xy_gen", "json": {"input_text": "A1B2C3"}},
        {"function": "rot_ex_gen", "json": {"input_text": "Abc123", "mode": "rotplus_atbash"}},
        {"function": "rot_ex_gen", "json": {"input_text": "Abc123", "mode": "rotminus_atbash"}},
        {"function": "rot_ex_gen", "json": {"input_text": "Abc123", "mode": "atbash_rotplus"}},
        {"function": "rot_ex_gen", "json": {"input_text": "Abc123", "mode": "atbash_rotminus"}},
        {"function": "rectangle_ex_gen", "json": {"input_text": "ABCDEFGH", "mode": "All pattern", "mode_ex": "normal"}},
        {"function": "rectangle_ex_gen", "json": {"input_text": "ABCDEFGH", "mode": "All pattern", "mode_ex": "reverse_even"}},
        {"function": "vigenere_ex_gen", "json": {"input_text": "AttackAtDawn123", "key": "KEY42"}},
        {"function": "charcode_ex_gen", "json": {"input_text": "656667 414243"}},
        {"function": "passcode_random_id", "json": {}},
        {"function": "passcode_today_id", "json": {}},
        {"function": "passcode_list", "json": {}},
        {"function": "passcode_validate", "json": {"id": "1", "input_answer": "ok"}},
        {"function": "passcode_validate", "json": {"id": "1", "input_answer": "near"}},
        {"function": "passcode_validate", "json": {"id": "1", "input_answer": "nope"}},
        {"function": "ingress_keywords_gen", "json": {"pattern": "a"}},
        {"function": "skip_gen", "json": {"input_text": "WEAREDISCOVERED", "mode": "Encode"}},
        {"function": "skip_gen", "json": {"input_text": "WEAREDISCOVERED", "mode": "Decode"}},
        {"function": "bifid_gen", "json": {"input_text": "FLEEATONCE", "key": "KEYWORD"}},
        {"function": "vanity_gen", "json": {"input_text": "HELLO", "mode": "Encode"}},
        {"function": "vanity_gen", "json": {"input_text": "4433555", "mode": "Decode"}},
        {"function": "kakushi_gen", "json": {"input_text": "HELLO", "key": "KEY", "mode": "Encode", "debug_mode": "OFF"}},
        {"function": "kakushi_gen", "json": {"input_text": "HELLO", "key": "KEY", "mode": "Encode", "debug_mode": "ON"}},
        {"function": "kakushi_gen", "json": {"input_text": "HELLO", "key": "KEY", "mode": "Decode", "debug_mode": "OFF"}},
        {"function": "kakushi_gen", "json": {"input_text": "HELLO", "key": "KEY", "mode": "Decode", "debug_mode": "ON"}},
    ]
    for char_type in range(1, 9):
        cases.append(
            {
                "function": "pwgen_gen",
                "json": {"char_type": str(char_type), "length": "12"},
            }
        )
    return cases


def main():
    _ensure_secret_stub()
    gear = importlib.import_module("app.gear")
    _apply_stubs(gear)

    out_cases = []
    for i, case in enumerate(_build_cases(), start=1):
        fn_name = case["function"]
        if fn_name in EXCLUDED_FUNCTIONS:
            continue
        payload = case["json"]
        result = getattr(gear, fn_name)(DummyRequest(payload))
        out_cases.append(
            {
                "id": f"{fn_name}_{i:03d}",
                "function": fn_name,
                "json": payload,
                "expected": _normalize(result),
            }
        )

    output = {
        "version": 1,
        "case_count": len(out_cases),
        "cases": out_cases,
        "note": "Generated from current implementation with deterministic test stubs.",
    }
    fixture_path = Path(__file__).parent / "fixtures" / "gear_regression_vectors.json"
    fixture_path.parent.mkdir(parents=True, exist_ok=True)
    fixture_path.write_text(json.dumps(output, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"wrote {len(out_cases)} cases to {fixture_path}")


if __name__ == "__main__":
    main()
