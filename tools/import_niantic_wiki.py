#!/usr/bin/env python3

import argparse
import json
import os
import re
import shutil
import subprocess
from datetime import datetime, timezone
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
TARGET_ROOT = ROOT / "app" / "niantic_wiki"
TARGET_SITE = TARGET_ROOT / "site"
MANIFEST_PATH = TARGET_ROOT / "import_manifest.json"
BASE_PATH = "/niantic_wiki"
TEXT_EXTENSIONS = {".html", ".css", ".js"}
ENV_SOURCE = "NIANTIC_WIKI_SITE_DIR"


def parse_args():
    parser = argparse.ArgumentParser(
        description="Import Niantic Wiki static artifacts into CryptoBrella."
    )
    parser.add_argument(
        "--source",
        type=Path,
        help=f"Path to the built Niantic Wiki site/ directory. Can also be set via {ENV_SOURCE}.",
    )
    return parser.parse_args()


def resolve_source_site(args) -> Path:
    source = args.source
    if source is None:
        env_value = os.environ.get(ENV_SOURCE)
        if env_value:
            source = Path(env_value)
    if source is None:
        raise SystemExit(
            f"Source site directory is required. Pass --source or set {ENV_SOURCE}."
        )
    return source.resolve()


def rewrite_text(text: str) -> str:
    # HTML attributes such as href="/page/..." or src="/media/..."
    text = re.sub(
        r'((?:href|src|action|content|poster)=["\'])/(?!/)',
        rf"\1{BASE_PATH}/",
        text,
    )
    # CSS url(/...)
    text = re.sub(r"(url\(['\"]?)/(?!/)", rf"\1{BASE_PATH}/", text)
    # JS fetch('/...') and similar string literals used in the generated site.
    text = re.sub(r"((?:fetch|location\.assign|location\.replace)\(['\"])/(?!/)", rf"\1{BASE_PATH}/", text)
    text = re.sub(r'([("\'\s=])/(favicon\.ico\b|search-index\.json|page/|search\b|about\b|media-manager\b|styles\.css\b|script\.js\b|media/|lib/)', rf"\1{BASE_PATH}/\2", text)
    return text


def rewrite_tree(target_site: Path):
    for path in target_site.rglob("*"):
        if not path.is_file() or path.suffix.lower() not in TEXT_EXTENSIONS:
            continue
        original = path.read_text(encoding="utf-8")
        rewritten = rewrite_text(original)
        if rewritten != original:
            path.write_text(rewritten, encoding="utf-8")


def ensure_favicon_link(target_site: Path):
    favicon_tag = f'  <link rel="shortcut icon" href="{BASE_PATH}/favicon.ico">\n'
    for path in target_site.rglob("*.html"):
        original = path.read_text(encoding="utf-8")
        if 'rel="shortcut icon"' in original:
            continue
        updated = original.replace(
            f'  <link rel="stylesheet" href="{BASE_PATH}/styles.css">\n',
            f'  <link rel="stylesheet" href="{BASE_PATH}/styles.css">\n{favicon_tag}',
            1,
        )
        if updated != original:
            path.write_text(updated, encoding="utf-8")


def get_source_commit(source_site: Path) -> str | None:
    source_root = source_site.parent
    git_dir = source_root / ".git"
    if not git_dir.exists():
        return None
    result = subprocess.run(
        ["git", "-C", str(source_root), "rev-parse", "HEAD"],
        check=False,
        capture_output=True,
        text=True,
    )
    if result.returncode != 0:
        return None
    return result.stdout.strip() or None


def build_manifest(source_site: Path, target_site: Path):
    files = []
    for path in sorted(target_site.rglob("*")):
        if path.is_file():
            files.append(path.relative_to(target_site).as_posix())

    manifest = {
        "archive": "Niantic Wiki",
        "imported_at_utc": datetime.now(timezone.utc).isoformat(),
        "source_type": "external_static_site",
        "source_dir_name": source_site.name,
        "source_commit": get_source_commit(source_site),
        "host_base_path": BASE_PATH,
        "file_count": len(files),
        "files": files,
        "notes": [
            "Imported artifacts are generated from the external Niantic Wiki project.",
            "Hosting-specific path rewriting to /niantic_wiki/ is applied during import.",
            "Upstream-preserved broken links remain intentionally preserved.",
        ],
    }
    MANIFEST_PATH.write_text(json.dumps(manifest, indent=2, ensure_ascii=True) + "\n", encoding="utf-8")


if __name__ == "__main__":
    args = parse_args()
    source_site = resolve_source_site(args)
    if not source_site.exists() or not source_site.is_dir():
        raise SystemExit(f"Source site directory not found: {source_site}")

    if TARGET_SITE.exists():
        shutil.rmtree(TARGET_SITE)
    shutil.copytree(source_site, TARGET_SITE)
    target_site = TARGET_SITE
    rewrite_tree(target_site)
    ensure_favicon_link(target_site)
    build_manifest(source_site, target_site)
