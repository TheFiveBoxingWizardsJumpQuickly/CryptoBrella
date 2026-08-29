"""Make repository-owned Python components importable without installing them."""

from __future__ import annotations

import sys
from pathlib import Path

REPOSITORY_ROOT = Path(__file__).resolve().parent
WORDQUERY_SOURCE = REPOSITORY_ROOT / "components" / "wordquery" / "src"


def activate_wordquery() -> Path:
    """Put the checked-out WordQuery source first on the import path."""

    if not WORDQUERY_SOURCE.is_dir():
        raise RuntimeError(f"WordQuery source directory is missing: {WORDQUERY_SOURCE}")

    source = str(WORDQUERY_SOURCE)
    while source in sys.path:
        sys.path.remove(source)
    sys.path.insert(0, source)
    return WORDQUERY_SOURCE
