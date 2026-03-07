import json
from datetime import date
from pathlib import Path

from app.cipher.fn import (
    affine_d,
    affine_e,
    atbash,
    beaufort,
    hexbash,
    rot,
    table_subtitution,
    uu_decode,
    uu_encode,
    vig_d,
    vig_d_auto,
    vig_e,
    vig_e_auto,
)


def build_cases():
    texts = [
        "",
        "A",
        "z",
        "0123456789",
        "Hello, World!",
        "The quick brown fox jumps over the lazy dog.",
        "Sphinx of black quartz, judge my vow.",
        "Pack my box with five dozen liquor jugs.",
        "Cryptography 101: ROT, VIG, AFFINE!",
        "AAAAABBBBBCCCCCDDDDDEEEEE",
        "abcXYZ123-_=+[]{};:'\",.<>/?\\|`~",
        "line1\\nline2\\tend",
        "   leading and trailing   ",
        "日本語テキストとEnglishMix123",
        "προσπάθεια-and-テスト",
        "LongText-" + "abcXYZ012" * 20,
    ]

    rot_ks = [-104, -53, -27, -13, -1, 0, 1, 5, 13, 25, 26, 27, 52, 104]
    keys = ["A", "B", "KEY", "whiterabbit", "Cipher42", "AbC123"]
    affine_a = [1, 3, 5, 7, 9, 11, 15, 17, 19, 21, 23, 25]
    affine_b = [-53, -1, 0, 1, 8, 13, 26, 53]
    methods = [
        "A-a swap",
        "Morse .- swap",
        "Morse reverse",
        "Morse .- swap and reverse",
        "US keyboard left shift",
        "US keyboard right shift",
        "US keyboard right <-> left",
        "US keyboard up <-> down",
        "US keyboard to Dvorak keyboard",
        "Dvorak keyboard to US keyboard",
        "US keyboard to MALTRON keyboard",
        "MALTRON keyboard to US keyboard",
        "Atbash",
        "!@#_to_123",
        "ABC to 123",
        "ABC to 012",
    ]
    uu_payloads = [
        b"",
        b"A",
        b"hello",
        bytes(range(0, 32)),
        bytes(range(32, 127)),
        (b"CryptoBrella-uu-encode" * 8)[:180],
    ]

    cases = []
    idx = 1

    def add_case(function, args, expected=None, expected_hex=None, expected_exception=None):
        nonlocal idx
        case = {"id": f"{function}_{idx:04d}", "function": function, "args": args}
        if expected is not None:
            case["expected"] = expected
        if expected_hex is not None:
            case["expected_hex"] = expected_hex
        if expected_exception is not None:
            case["expected_exception"] = expected_exception
        cases.append(case)
        idx += 1

    for t in texts:
        for k in rot_ks:
            add_case("rot", {"c": t, "k": k, "nc": False}, expected=rot(t, k, nc=False))
            add_case("rot", {"c": t, "k": k, "nc": True}, expected=rot(t, k, nc=True))

    for t in texts:
        for k in keys:
            e = vig_e(t, k, nc=False)
            add_case("vig_e", {"c": t, "k": k, "nc": False}, expected=e)
            add_case("vig_d", {"c": e, "k": k, "nc": False}, expected=vig_d(e, k, nc=False))

            e_nc = vig_e(t, k, nc=True)
            add_case("vig_e", {"c": t, "k": k, "nc": True}, expected=e_nc)
            add_case("vig_d", {"c": e_nc, "k": k, "nc": True}, expected=vig_d(e_nc, k, nc=True))

            add_case("beaufort", {"c": t, "k": k, "nc": False}, expected=beaufort(t, k, nc=False))
            add_case("beaufort", {"c": t, "k": k, "nc": True}, expected=beaufort(t, k, nc=True))

            ea = vig_e_auto(t, k, nc=False)
            add_case("vig_e_auto", {"c": t, "k": k, "nc": False}, expected=ea)
            add_case(
                "vig_d_auto",
                {"c": ea, "k": k, "nc": False},
                expected=vig_d_auto(ea, k, nc=False),
            )

    add_case("vig_e", {"c": "ABC", "k": "", "nc": False}, expected_exception="IndexError")
    add_case("vig_d", {"c": "ABC", "k": "", "nc": False}, expected_exception="IndexError")
    add_case("vig_e_auto", {"c": "ABC", "k": "", "nc": False}, expected_exception="IndexError")
    add_case("vig_d_auto", {"c": "ABC", "k": "", "nc": False}, expected_exception="IndexError")

    for t in texts:
        add_case("atbash", {"c": t, "nc": False}, expected=atbash(t, nc=False))
        add_case("atbash", {"c": t, "nc": True}, expected=atbash(t, nc=True))

    for t in ["0123456789abcdef", "FEDCBA9876543210", "deadbeef", "abcxyz123", ""]:
        add_case("hexbash", {"c": t}, expected=hexbash(t))

    for t in texts:
        for a in affine_a:
            for b in affine_b:
                e = affine_e(t, a, b)
                add_case("affine_e", {"text": t, "a": a, "b": b}, expected=e)
                add_case("affine_d", {"text": e, "a": a, "b": b}, expected=affine_d(e, a, b))

    sub_texts = [
        "ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789-=[]\\;,./`~!@#$%^&*()_+",
        "Hello-World_123",
        "morse TEST 987",
        "",
    ]
    for method in methods:
        for t in sub_texts:
            add_case(
                "table_subtitution",
                {"text": t, "method": method},
                expected=table_subtitution(t, method),
            )

    for payload in uu_payloads:
        enc = uu_encode(payload)
        add_case("uu_encode", {"byte_hex": payload.hex()}, expected_hex=enc.hex())
        text = enc.decode("ascii")
        try:
            dec = uu_decode(text)
            add_case("uu_decode", {"text": text}, expected_hex=dec.hex())
        except Exception as exc:
            add_case("uu_decode", {"text": text}, expected_exception=exc.__class__.__name__)

    return cases


def main():
    cases = build_cases()
    payload = {
        "version": 1,
        "generated_on": str(date.today()),
        "generator_note": "Values are fixed from current implementation and treated as regression baseline.",
        "case_count": len(cases),
        "cases": cases,
    }
    out_path = Path(__file__).parent / "fixtures" / "regression_vectors.json"
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"wrote {payload['case_count']} cases to {out_path}")


if __name__ == "__main__":
    main()
