#!/usr/bin/env python3
import argparse
import ast
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
TESTS_DIR = ROOT / "tests"


def _find_fixture_cases(function_name):
    results = []
    for path in TESTS_DIR.glob("**/fixtures/*.json"):
        try:
            payload = json.loads(path.read_text(encoding="utf-8"))
        except Exception:
            continue
        cases = payload.get("cases")
        if not isinstance(cases, list):
            continue
        for case in cases:
            if case.get("function") != function_name:
                continue
            args = case.get("args", case.get("json", {}))
            results.append(
                {
                    "path": path,
                    "id": case.get("id", "<no-id>"),
                    "args": args,
                }
            )
    return results


def _find_source_calls(function_name):
    hits = []
    for path in TESTS_DIR.glob("**/*.py"):
        try:
            src = path.read_text(encoding="utf-8")
            tree = ast.parse(src)
        except Exception:
            continue

        parent_test_fn = {}
        for node in ast.walk(tree):
            if isinstance(node, ast.FunctionDef):
                for child in ast.walk(node):
                    parent_test_fn[id(child)] = node.name

        for node in ast.walk(tree):
            if not isinstance(node, ast.Call):
                continue
            fn_name = None
            if isinstance(node.func, ast.Name):
                fn_name = node.func.id
            elif isinstance(node.func, ast.Attribute):
                fn_name = node.func.attr
            if fn_name != function_name:
                continue
            hits.append(
                {
                    "path": path,
                    "line": node.lineno,
                    "test_fn": parent_test_fn.get(id(node), "<module-scope>"),
                }
            )
    return sorted(hits, key=lambda x: (str(x["path"]), x["line"]))


def main():
    parser = argparse.ArgumentParser(
        description="List test cases for a function name from fixture JSON and pytest source."
    )
    parser.add_argument("function_name", help="Function name (e.g. purple_decode, vigenere_gen)")
    parser.add_argument(
        "--show-args",
        action="store_true",
        help="Print full args/json payload for each fixture case.",
    )
    parser.add_argument(
        "--limit",
        type=int,
        default=None,
        help="Max number of fixture cases to print.",
    )
    args = parser.parse_args()

    fixture_cases = _find_fixture_cases(args.function_name)
    source_hits = _find_source_calls(args.function_name)

    print(f"Function: {args.function_name}")
    print(f"Fixture cases: {len(fixture_cases)}")
    print(f"Source call sites: {len(source_hits)}")
    print("")

    if fixture_cases:
        print("[Fixture Cases]")
        ordered = sorted(fixture_cases, key=lambda x: (str(x["path"]), x["id"]))
        if args.limit is not None:
            ordered = ordered[: args.limit]
        for c in ordered:
            rel = c["path"].resolve().relative_to(ROOT)
            print(f"- {rel} :: {c['id']}")
            if args.show_args:
                print(json.dumps(c["args"], ensure_ascii=False, indent=2))
        if args.limit is not None and len(fixture_cases) > args.limit:
            print(f"... truncated: {len(fixture_cases) - args.limit} more fixture cases")
        print("")

    if source_hits:
        print("[Source Call Sites]")
        for h in source_hits:
            rel = h["path"].resolve().relative_to(ROOT)
            print(f"- {rel}:{h['line']} (test: {h['test_fn']})")

    if not fixture_cases and not source_hits:
        print("No matches found.")


if __name__ == "__main__":
    main()
