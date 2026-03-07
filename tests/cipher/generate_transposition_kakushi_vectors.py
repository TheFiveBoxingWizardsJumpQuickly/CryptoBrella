import json
import sys
from dataclasses import asdict, is_dataclass
from datetime import date
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from app.cipher.kakushi import kakushi_decode, kakushi_encode
from app.cipher.transposition import (
    columnar_d,
    columnar_e,
    railfence_d,
    railfence_e,
    skip_d,
    skip_e,
    swap_xy_axes,
)
from app.cipher.fn import braille_ja_d


def _norm(v):
    if is_dataclass(v):
        return _norm(asdict(v))
    if isinstance(v, dict):
        return {str(k): _norm(x) for k, x in v.items()}
    if isinstance(v, list):
        return [_norm(x) for x in v]
    if isinstance(v, tuple):
        return [_norm(x) for x in v]
    if isinstance(v, bytes):
        return {"__bytes_hex__": v.hex()}
    return v


def build_cases():
    cases = []
    idx = 1

    def add_case(function, args, expected=None, expected_exception=None):
        nonlocal idx
        c = {"id": f"{function}_{idx:04d}", "function": function, "args": args}
        if expected is not None:
            c["expected"] = _norm(expected)
        if expected_exception is not None:
            c["expected_exception"] = expected_exception
        cases.append(c)
        idx += 1

    def add_eval(function, args, fn):
        try:
            add_case(function, args, expected=fn())
        except Exception as exc:
            add_case(function, args, expected_exception=exc.__class__.__name__)

    # columnar_e / columnar_d
    texts = [
        "",
        "A",
        "AB",
        "ABCDE",
        "WEAREDISCOVERED",
        "THEQUICKBROWNFOXJUMPSOVERTHELAZYDOG",
        "12345-ABCDE-xyz",
        "日本語Mixed123",
    ]
    cols = [
        [1, 2],
        [2, 1],
        [1, 2, 3],
        [2, 1, 3],
        [3, 1, 4, 2],
        [2, 5, 1, 4, 3],
    ]
    for t in texts:
        for col in cols:
            add_eval("columnar_e", {"c": t, "col": col}, lambda t=t, col=col: "".join(columnar_e(t, col)))
            add_eval("columnar_d", {"c": t, "col": col}, lambda t=t, col=col: "".join(columnar_d(t, col)))
            enc = "".join(columnar_e(t, col))
            add_eval(
                "columnar_roundtrip",
                {"c": t, "col": col},
                lambda enc=enc, col=col: "".join(columnar_d(enc, col)),
            )

    # railfence
    rail_texts = [
        "",
        "A",
        "HELLOWORLD",
        "WEAREDISCOVEREDFLEEATONCE",
        "123-abc-XYZ",
        "THE QUICK BROWN FOX",
    ]
    for t in rail_texts:
        for rails in [2, 3, 4, 5, 8]:
            for offset in [0, 1, 2, 5]:
                add_eval(
                    "railfence_e",
                    {"text": t, "rails": rails, "offset": offset},
                    lambda t=t, rails=rails, offset=offset: railfence_e(t, rails, offset),
                )
                add_eval(
                    "railfence_d",
                    {"text": t, "rails": rails, "offset": offset},
                    lambda t=t, rails=rails, offset=offset: railfence_d(t, rails, offset),
                )
                enc = railfence_e(t, rails, offset)
                add_eval(
                    "railfence_roundtrip",
                    {"text": t, "rails": rails, "offset": offset},
                    lambda enc=enc, rails=rails, offset=offset: railfence_d(enc, rails, offset),
                )

    # skip
    skip_texts = [
        "",
        "A",
        "ABCD",
        "WEAREDISCOVERED",
        "1234567890",
        "THEQUICKBROWNFOX",
    ]
    for t in skip_texts:
        for step in [0, 1, 2, 3, 4, 5, 7, 10]:
            add_eval("skip_e", {"text": t, "step": step}, lambda t=t, step=step: skip_e(t, step))
            add_eval("skip_d", {"text": t, "step": step}, lambda t=t, step=step: skip_d(t, step))
            enc = skip_e(t, step)
            add_eval(
                "skip_roundtrip",
                {"text": t, "step": step},
                lambda enc=enc, step=step: skip_d(enc, step),
            )

    # swap_xy_axes
    swap_inputs = [
        "",
        "A",
        "AB\nCD",
        "ABC\nD\nEFGH",
        "line1\nline2\nline3",
        "日本語\nabc\n12345",
        "\n\n",
    ]
    for t in swap_inputs:
        add_eval("swap_xy_axes", {"text": t}, lambda t=t: swap_xy_axes(t))

    # braille_ja_d (explicitly included as requested)
    for i in range(0, 4096, 11):
        dots = format(i, "012b")
        add_eval("braille_ja_d", {"braille_dots": dots}, lambda dots=dots: braille_ja_d(dots))

    # kakushi
    kakushi_texts = [
        "",
        "HELLO",
        "隠し文章テスト",
        "CryptoBrella-123",
        "日本語MixedEnglish123",
    ]
    keywords = ["", "KEY", "ひみつ", "longer_keyword_42"]
    for t in kakushi_texts:
        for k in keywords:
            for debug in [False, True]:
                add_eval(
                    "kakushi_encode",
                    {"text": t, "keyword": k, "debug": debug},
                    lambda t=t, k=k, debug=debug: kakushi_encode(t, k, debug),
                )

                encoded = kakushi_encode(t, k, False).encoded
                add_eval(
                    "kakushi_decode",
                    {"encoded": encoded, "keyword": k, "debug": debug},
                    lambda encoded=encoded, k=k, debug=debug: kakushi_decode(encoded, k, debug),
                )

    # kakushi decode with invalid chars snapshot
    invalid_samples = ["***", "abc", "😀", "あAいBう"]
    for s in invalid_samples:
        for debug in [False, True]:
            add_eval(
                "kakushi_decode",
                {"encoded": s, "keyword": "KEY", "debug": debug},
                lambda s=s, debug=debug: kakushi_decode(s, "KEY", debug),
            )

    return cases


def main():
    cases = build_cases()
    payload = {
        "version": 1,
        "generated_on": str(date.today()),
        "case_count": len(cases),
        "note": "Additional vectors for requested transposition and kakushi functions.",
        "cases": cases,
    }
    out = Path(__file__).parent / "fixtures" / "transposition_kakushi_vectors.json"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"wrote {len(cases)} cases to {out}")


if __name__ == "__main__":
    main()
