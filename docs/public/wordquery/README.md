# WordQuery: JP

WordQuery: JP finds Japanese word candidates with readable patterns, exact
anagrams, and regular expressions. A Flask layer provides the browser UI and
JSON API, while the search core and lexicon builder remain a Flask-independent
Python package under `components/wordquery`.

## Documentation

- [Architecture](architecture.md)
- [Readable pattern search](pattern_search.md)
- [Lexicon policy](lexicon_policy.md)
- [Data sources and license boundaries](data_sources.md)

Production dictionary archives and generated SQLite databases are not included
in this repository. Small dictionary excerpts are retained as automated test
fixtures.

## Purpose

WordQuery is a search tool for finding Japanese word candidates
under changing constraints in crosswords, puzzles, anagrams, shiritori, and
similar word games. Internally it uses regular expressions and character
frequency indexes, but its task-oriented UI does not require regular-expression
knowledge.

The product prioritizes reaching plausible puzzle answers over academic
completeness. Proper nouns, technical terms, archaisms, and dialect forms remain
available alongside general vocabulary. Sorting and filters manage an excess of
candidates without discarding them categorically.

## Design principles

- Keep stored-reading normalization predictable; apply ambiguous equivalence
  only through explicit search-time options.
- Treat kana characters, morae, and written characters as distinct, explicit
  length units.
- Convert the pattern, anagram, and Regex experiences into one shared search
  condition model without exposing internal implementation details.
- Separate validity, word type, commonness, and task suitability, and make
  sorting reasons explainable.
- Keep source provenance for imported entries and a justification for every
  developer-maintained entry.
- Separate external inputs from generated artifacts so the search database can
  be rebuilt reproducibly.

## Current features

- Contains, prefix, suffix, exact, and readable-pattern matching, plus Regex for
  advanced users.
- Length constraints in kana characters, morae, and written characters.
- Exact anagrams.
- Filtering by additional required or forbidden characters and selected
  classifications.
- Browser sorting by commonness or normalized reading; dictionary-priority sorting remains available through the API.
- Grouping of written forms by normalized reading, with expandable details.
- Integration of JMdict, SudachiDict small and core, and developer-maintained data.
- A three-mode browser UI and versioned JSON API.

## Current limitations

- Definitions and usage frequencies are not displayed.
- There is no browser-based lexicon administration interface.
- There are no public submissions, collaborative editing, or public user dictionaries.
- Search conditions cannot be saved in or restored from the URL.
