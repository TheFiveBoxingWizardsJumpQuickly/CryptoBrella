# WordQuery: JP

WordQuery: JP finds Japanese word candidates with readable patterns, exact
anagrams, and regular expressions. A Flask layer provides the browser UI and
JSON API, while the search core and lexicon builder remain a Flask-independent
Python package under `components/wordquery`.

## Documentation

- [Overview](overview.md)
- [Architecture](architecture.md)
- [Readable pattern search](pattern_search.md)
- [Lexicon policy](lexicon_policy.md)
- [Data sources and license boundaries](data_sources.md)

Production dictionary archives and generated SQLite databases are not included
in this repository. Small dictionary excerpts are retained as automated test
fixtures.
