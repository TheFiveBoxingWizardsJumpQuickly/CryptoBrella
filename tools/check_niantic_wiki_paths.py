#!/usr/bin/env python3

import json
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from app.niantic_wiki.validation import find_unrewritten_paths


SITE_ROOT = ROOT / "app" / "niantic_wiki" / "site"


def main():
    findings = find_unrewritten_paths(SITE_ROOT)
    if findings:
        print(json.dumps({"ok": False, "findings": findings[:50]}, indent=2, ensure_ascii=True))
        raise SystemExit(1)
    print(json.dumps({"ok": True, "checked_root": str(SITE_ROOT), "findings": 0}, indent=2, ensure_ascii=True))


if __name__ == "__main__":
    main()
