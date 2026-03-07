import json
import sys
from datetime import date
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from app.cipher.enigma import enigma, plugboard_gen
from app.cipher.purple import purple_decode, purple_encode


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

    # Enigma vectors
    texts = [
        "",
        "A",
        "HELLOWORLD",
        "ENIGMA TEST MESSAGE",
        "THE QUICK BROWN FOX JUMPS OVER THE LAZY DOG",
        "NINEOSNFIVEMTHREEPSEVENX",
        "zuulpguxlkvjwmyrjbclxfoa",
        "123-ABC-xyz",
    ]
    rotor_sets = [
        (1, 2, 3),
        (2, 4, 5),
        (3, 1, 2),
        (4, 5, 1),
        (5, 3, 4),
        (1, 1, 1),
    ]
    reflector_ids = ["A", "B", "C"]
    rotor_keys = ["AAA", "BLA", "RAB", "VIA", "XYZ"]
    ring_keys = ["AAA", "BUL", "BIT", "XQO", "FVN"]
    plug_strings = ["", "AVBSCGDLFUHZINKMOWRX", "N O I R", "POMLIUKJNHYTGBVFREDC"]

    for text in texts:
        for (l, m, r) in rotor_sets:
            for refl in reflector_ids:
                for rk in rotor_keys:
                    for sk in ring_keys:
                        for p in plug_strings:
                            if len(cases) > 700:
                                break
                            pb = plugboard_gen(p)
                            args = {
                                "text": text,
                                "rotor_left_id": l,
                                "rotor_mid_id": m,
                                "rotor_right_id": r,
                                "reflector_id": refl,
                                "rotor_key": rk,
                                "ringsetting_key": sk,
                                "plugboard": pb,
                            }
                            add_eval("enigma", args, lambda args=args: enigma(**args))
                    if len(cases) > 700:
                        break
                if len(cases) > 700:
                    break
            if len(cases) > 700:
                break
        if len(cases) > 700:
            break

    # Keep known public vectors, too.
    add_case(
        "enigma",
        {
            "text": "zuulpguxlkvjwmyrjbclxfoa",
            "rotor_left_id": 1,
            "rotor_mid_id": 2,
            "rotor_right_id": 3,
            "reflector_id": "B",
            "rotor_key": "AMT",
            "ringsetting_key": "AAA",
            "plugboard": [],
        },
        expected="NINEOSNFIVEMTHREEPSEVENX",
    )

    # Purple vectors
    purple_texts = [
        "",
        "A",
        "FOV TATAKIDASI NI MUIMI NO MOXI WO IRU BESI",
        "ZTX ODNWKCCMAV NZ XYWEE TU QTCI MN VEU",
        "THE QUICK BROWN FOX JUMPS OVER THE LAZY DOG",
        "NINEOSNFIVEMTHREEPSEVENX",
        "ALICE IN WONDERLAND",
    ]
    plugboards = [
        "NOKTYUXEQLHBRMPDICJASVWGZF",
        "ABCDEFGHIJKLMNOPQRSTUVWXYZ",
        "QWERTYUIOPASDFGHJKLZXCVBNM",
    ]
    rotor_motion_keys = [123, 132, 213, 231, 312, 321]
    pos_seeds = [
        (1, 1, 1, 1),
        (9, 1, 24, 6),
        (25, 25, 25, 25),
        (13, 7, 19, 3),
    ]

    for text in purple_texts:
        for plug in plugboards:
            for motion in rotor_motion_keys:
                for p in pos_seeds:
                    kwargs = {
                        "text": text,
                        "sixes_switch_position": p[0],
                        "twenties_switch_1_position": p[1],
                        "twenties_switch_2_position": p[2],
                        "twenties_switch_3_position": p[3],
                        "plugboard_full": plug,
                        "rotor_motion_key": motion,
                    }
                    add_eval("purple_encode", kwargs, lambda kwargs=kwargs: purple_encode(**kwargs))
                    add_eval("purple_decode", kwargs, lambda kwargs=kwargs: purple_decode(**kwargs))

    # Known canonical vector snapshots.
    canonical_kwargs = {
        "sixes_switch_position": 9,
        "twenties_switch_1_position": 1,
        "twenties_switch_2_position": 24,
        "twenties_switch_3_position": 6,
        "plugboard_full": "NOKTYUXEQLHBRMPDICJASVWGZF",
        "rotor_motion_key": 231,
    }
    add_case(
        "purple_decode",
        {
            "text": "ZTX ODNWKCCMAV NZ XYWEE TU QTCI MN VEU VIWB LUA XRR TL VA RG NTP CNO IUP JLC IVRTPJKAUH VMU DTH KTXYZE LQTVWG BUH FAW SHU LBF BH EXM YHF LOWDQKWHKK NX EBVPY HHG HEKXIOHQ HU H WIKYJYH PPFEAL NN AKIB OO ZN FRLQCFLJ TTSSDDOIOCVTW ZCKQ TSH XTIJCNWXOK UF NQR TTAOIH WTATWV",
            **canonical_kwargs,
        },
        expected=purple_decode(
            text="ZTX ODNWKCCMAV NZ XYWEE TU QTCI MN VEU VIWB LUA XRR TL VA RG NTP CNO IUP JLC IVRTPJKAUH VMU DTH KTXYZE LQTVWG BUH FAW SHU LBF BH EXM YHF LOWDQKWHKK NX EBVPY HHG HEKXIOHQ HU H WIKYJYH PPFEAL NN AKIB OO ZN FRLQCFLJ TTSSDDOIOCVTW ZCKQ TSH XTIJCNWXOK UF NQR TTAOIH WTATWV",
            **canonical_kwargs,
        ),
    )

    return cases


def main():
    cases = build_cases()
    payload = {
        "version": 1,
        "generated_on": str(date.today()),
        "case_count": len(cases),
        "note": "Regression vectors for enigma and purple based on current implementation.",
        "cases": cases,
    }
    out = Path(__file__).parent / "fixtures" / "enigma_purple_vectors.json"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"wrote {len(cases)} cases to {out}")


if __name__ == "__main__":
    main()
