"""Repository entry point for WordQuery operations without a package install."""

from __future__ import annotations

from component_paths import activate_wordquery


def main(argv: list[str] | None = None) -> int:
    activate_wordquery()
    from wordquery_jp.cli import main as wordquery_main

    return wordquery_main(argv)


if __name__ == "__main__":
    raise SystemExit(main())
