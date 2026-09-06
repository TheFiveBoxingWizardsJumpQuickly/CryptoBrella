"""Disposable, DB-bound covering index for auxiliary vocabulary.

The published lexicon is never modified. Build in a temporary file and publish
only after validation; existing search indexes are immutable and never overwritten.
"""

import hashlib
import json
import logging
import os
import sqlite3
import tempfile
from contextlib import closing
from pathlib import Path

from .sqlite_paths import absolute_read_only_uri


def index_path(database: Path) -> Path:
    return database.with_name(database.name + ".search.sqlite3")


def file_hash(path: Path) -> str:
    with path.open("rb") as handle:
        return hashlib.file_digest(handle, "sha256").hexdigest()


def validate_search_index(database: Path, *, path: Path | None = None) -> Path | None:
    declaration = None
    manifest = database.parent / "manifest.json"
    if path is None and manifest.exists():
        release = json.loads(manifest.read_text(encoding="utf-8"))
        if not isinstance(release, dict):
            raise ValueError("Invalid release manifest")
        declaration = release.get("search_index")
    path = path or index_path(database)
    if not path.exists():
        if declaration is not None:
            raise ValueError("Published search index is missing")
        return None
    if declaration is not None and (
        not isinstance(declaration, dict) or declaration.get("filename") != path.name
        or declaration.get("sha256") != file_hash(path)
    ):
        raise ValueError("Search index does not match its release manifest")
    with closing(sqlite3.connect(absolute_read_only_uri(path), uri=True)) as connection:
        metadata = dict(connection.execute("SELECT key,value FROM metadata"))
        if metadata.get("schema") != "1" or metadata.get("database_sha256") != file_hash(database):
            raise ValueError("Search index does not match the dictionary; rebuild the index")
        if connection.execute("PRAGMA quick_check").fetchone()[0] != "ok":
            raise ValueError("Search index integrity check failed")
        count = connection.execute("SELECT count(*) FROM words").fetchone()[0]
        if str(count) != metadata.get("count"):
            raise ValueError("Search index row count mismatch")
    return path


def build_search_index(database: Path) -> dict:
    database = database.resolve(strict=True)
    target = index_path(database)
    if target.exists():
        validate_search_index(database)
        return {"path": str(target), "status": "already_exists"}
    logging.getLogger(__name__).info("Building auxiliary search index; original DB is unchanged")
    digest = file_hash(database)
    descriptor, name = tempfile.mkstemp(prefix=".search-index-", dir=database.parent)
    os.close(descriptor)
    temporary = Path(name)
    try:
        with closing(sqlite3.connect(absolute_read_only_uri(database), uri=True)) as source:  # noqa: SIM117
            with closing(sqlite3.connect(temporary)) as output, output:
                output.executescript("""
                    CREATE TABLE metadata(key TEXT PRIMARY KEY,value TEXT NOT NULL);
                    CREATE TABLE words(
                        id INTEGER PRIMARY KEY, surface TEXT, reading TEXT,
                        normalized_reading TEXT, signature TEXT, category TEXT,
                        pos TEXT, priority INTEGER, status TEXT, multiple_sources INTEGER,
                        reversed_reading TEXT, reading_length INTEGER);
                """)
                rows = source.execute("""
                    SELECT id,surface,reading,normalized_reading,signature,category,pos,
                           priority,status,
                           (SELECT count(DISTINCT p.source)>=2
                            FROM provenance p WHERE p.word_id=w.id)
                    FROM words w WHERE status='candidate' ORDER BY id
                """)
                output.executemany("INSERT INTO words VALUES (?,?,?,?,?,?,?,?,?,?,?,?)",
                                   (tuple(row) + (row[3][::-1], len(row[3])) for row in rows))
                logging.getLogger(__name__).info("Creating prefix, suffix and length indexes")
                output.executescript("""
                    CREATE INDEX auxiliary_prefix ON words(normalized_reading);
                    CREATE INDEX auxiliary_suffix ON words(reversed_reading);
                    CREATE INDEX auxiliary_length ON words(reading_length);
                    CREATE INDEX auxiliary_signature ON words(signature);
                """)
                count = output.execute("SELECT count(*) FROM words").fetchone()[0]
                output.executemany("INSERT INTO metadata VALUES (?,?)", [
                    ("schema", "1"), ("database_sha256", digest), ("count", str(count)),
                ])
        logging.getLogger(__name__).info("Validating search index before publication")
        validate_search_index(database, path=temporary)
        with temporary.open("rb") as handle:
            os.fsync(handle.fileno())
        # Hard-link publication is atomic and refuses to overwrite a concurrent build.
        os.link(temporary, target)
        return {"path": str(target), "status": "built", "count": count,
                "bytes": target.stat().st_size, "database_sha256": digest}
    finally:
        temporary.unlink(missing_ok=True)
