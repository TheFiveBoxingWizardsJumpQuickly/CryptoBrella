# WordQuery: JP data sources

## JMdict

- Purpose: foundational written forms, readings, parts of speech, priorities,
  and `field/misc/dial` vocabulary tags.
- Source: <https://www.edrdg.org/jmdict/j_jmdict.html>
- License: Creative Commons Attribution-ShareAlike 4.0.
- Attribution: James William Breen and the Electronic Dictionary Research and
  Development Group (EDRDG).

## SudachiDict small and core

- Purpose: independent corroboration, supplementary vocabulary, part-of-speech
  classification, and proper-name type tags.
- Source: <https://github.com/WorksApplications/SudachiDict>
- Adopted version: 20260428 small plus core; SHA-256 values are pinned in
  `data/sources.toml`.
- License: Apache License 2.0.
- Third-party notices: the official `LEGAL` notices for UniDic, NEologd, Hatena
  Keyword, Japan Post, station names, person names, and other sources are
  preserved in the [service copy](../../../app/static/wordquery/legal/SudachiDict-LEGAL.txt).

## Developer-maintained data

- Purpose: additions, corrections, and exclusions.
- Storage: UTF-8 TSV files under `components/wordquery/data/manual/`.
- Evidence: each non-empty record includes a reason and a supporting reference.

## Repository contents

The repository contains source configuration, evidence-backed manual records,
and small automated-test fixtures. It does not contain production dictionary
archives or generated SQLite databases.

## License boundaries

- Written forms, readings, parts of speech, and tags derived from JMdict, and
  adaptations that normalize, exclude, or merge them, remain under CC BY-SA 4.0.
- Material derived from SudachiDict remains under Apache License 2.0 and the
  official `LEGAL` third-party notices.
- Search results may combine material from both dictionaries; each part
  remains subject to the terms of its source.
- Author-owned code, for which no reuse license is granted, is presented
  separately from third-party dictionary licenses.
- The service provides a source notice from every search screen and retains
  field-level provenance in the API.

This summary does not replace the license terms published by the source
providers.
