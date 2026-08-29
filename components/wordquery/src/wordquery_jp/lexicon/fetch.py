"""Checksum-aware external source downloader."""

from __future__ import annotations

import hashlib
import shutil
import tomllib
import urllib.parse
import urllib.request
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True, slots=True)
class FetchResult:
    source: str
    path: Path
    sha256: str
    verified: bool


def fetch_source(
    name: str,
    *,
    manifest: str | Path = "data/sources.toml",
    destination: str | Path = "data/raw",
) -> FetchResult:
    manifest_path = Path(manifest)
    with manifest_path.open("rb") as handle:
        sources = tomllib.load(handle)
    if name not in sources:
        raise ValueError(f"不明なデータソースです: {name}")
    config = sources[name]
    url = config.get("url", "").strip()
    if not url:
        raise ValueError(f"{name} のURLがマニフェストに設定されていません。")
    filename = Path(urllib.parse.urlparse(url).path).name
    if not filename:
        raise ValueError(f"取得ファイル名をURLから決定できません: {url}")
    destination_path = Path(destination)
    destination_path.mkdir(parents=True, exist_ok=True)
    target = destination_path / f"{name}-{filename}"
    temporary = target.with_suffix(target.suffix + ".part")
    digest = hashlib.sha256()
    request = urllib.request.Request(url, headers={"User-Agent": "wordquery_jp/0.1"})
    try:
        with (
            urllib.request.urlopen(request, timeout=30) as response,
            temporary.open("wb") as output,
        ):
            while block := response.read(1024 * 1024):
                digest.update(block)
                output.write(block)
        actual = digest.hexdigest()
        expected = config.get("sha256", "").lower().strip()
        if expected and actual != expected:
            raise ValueError(f"SHA-256が一致しません: expected={expected}, actual={actual}")
        shutil.move(temporary, target)
    finally:
        temporary.unlink(missing_ok=True)
    return FetchResult(source=name, path=target, sha256=actual, verified=bool(expected))
