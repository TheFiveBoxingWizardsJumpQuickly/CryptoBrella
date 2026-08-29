"""Cheap invariants for the public WordQuery documentation."""

from __future__ import annotations

import re
from pathlib import Path

REPOSITORY_ROOT = Path(__file__).resolve().parents[3]
PUBLIC_DOCS = REPOSITORY_ROOT / "docs" / "public" / "wordquery"
REQUIRED = {
    "README.md": ("Documentation", "generated SQLite"),
    "overview.md": ("Current features", "Current limitations"),
    "architecture.md": ("Data flow", "Error boundaries"),
    "pattern_search.md": ("Grammar", "Error locations"),
    "lexicon_policy.md": ("Automatic inclusion", "Search utility"),
    "data_sources.md": ("License boundaries", "Repository contents"),
}
JAPANESE_PROSE = re.compile(r"[ぁ-んァ-ヶ一-龠]")


def prose_without_examples(text: str) -> str:
    """Remove fenced and inline code, where Japanese UI labels and examples belong."""
    without_fences = re.sub(r"```.*?```", "", text, flags=re.DOTALL)
    return re.sub(r"`[^`]*`", "", without_fences)


def main() -> int:
    failures: list[str] = []
    for relative, headings in REQUIRED.items():
        path = PUBLIC_DOCS / relative
        if not path.is_file():
            failures.append(f"missing: {relative}")
            continue
        text = path.read_text(encoding="utf-8")
        for heading in headings:
            if heading not in text:
                failures.append(f"{relative}: required text not found: {heading}")
        if JAPANESE_PROSE.search(prose_without_examples(text)):
            failures.append(
                f"{relative}: Japanese prose found outside a code example or UI label"
            )

    if failures:
        print("Documentation check failed:")
        for failure in failures:
            print(f"- {failure}")
        return 1
    print("Documentation check passed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
