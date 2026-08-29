"""Generated SQLite schema."""

SCHEMA = """
PRAGMA foreign_keys = ON;

CREATE TABLE metadata (
    key TEXT PRIMARY KEY,
    value TEXT NOT NULL
);

CREATE TABLE words (
    id INTEGER PRIMARY KEY,
    surface TEXT NOT NULL,
    reading TEXT NOT NULL,
    normalized_reading TEXT NOT NULL,
    signature TEXT NOT NULL,
    category TEXT NOT NULL CHECK (category IN ('general', 'proper', 'function')),
    pos TEXT NOT NULL DEFAULT '',
    priority INTEGER NOT NULL DEFAULT 0,
    status TEXT NOT NULL CHECK (status IN ('accepted', 'candidate')),
    UNIQUE(surface, normalized_reading)
);

CREATE INDEX words_reading_idx ON words(normalized_reading);
CREATE INDEX words_signature_idx ON words(signature, category, priority DESC);

CREATE TABLE provenance (
    word_id INTEGER NOT NULL REFERENCES words(id) ON DELETE CASCADE,
    source TEXT NOT NULL,
    source_entry_id TEXT NOT NULL,
    surface TEXT NOT NULL DEFAULT '',
    reading TEXT NOT NULL DEFAULT '',
    category TEXT NOT NULL DEFAULT 'general'
        CHECK (category IN ('general', 'proper', 'function')),
    pos TEXT NOT NULL DEFAULT '',
    reason TEXT NOT NULL DEFAULT '',
    reference TEXT NOT NULL DEFAULT '',
    PRIMARY KEY(word_id, source, source_entry_id)
);

CREATE TABLE word_tags (
    word_id INTEGER NOT NULL REFERENCES words(id) ON DELETE CASCADE,
    axis TEXT NOT NULL,
    value TEXT NOT NULL,
    source TEXT NOT NULL,
    source_entry_id TEXT NOT NULL,
    evidence TEXT NOT NULL,
    reason TEXT NOT NULL DEFAULT '',
    reference TEXT NOT NULL DEFAULT '',
    PRIMARY KEY(word_id, axis, value, source, source_entry_id, evidence)
);

CREATE INDEX word_tags_lookup_idx ON word_tags(axis, value, word_id);

CREATE TABLE build_issues (
    kind TEXT NOT NULL,
    source TEXT NOT NULL,
    source_entry_id TEXT NOT NULL,
    detail TEXT NOT NULL
);
"""
