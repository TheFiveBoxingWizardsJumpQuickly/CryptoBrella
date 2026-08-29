# WordQuery: JP lexicon policy

## Entry unit

The lexicon centers on dictionary headwords and generally excludes predictable
inflected surface forms. An entry with a reading and traceable evidence is not
excluded solely for its length, rarity, or specialization. General vocabulary,
proper nouns, and function words are classified separately. Source-supported
attributes such as domain, proper-name type, period, region, abbreviation, and
orthographic type are stored as tags.

A tag retains its source, source item ID, and original source value as well as
its normalized search/display value. Developer-assigned tags require a reason
and reference. A classification inferred from spelling or meaning is not saved
as a durable tag without evidence.

## Automatic inclusion

1. Include JMdict headwords that pass structural validation.
2. Merge provenance when an entry matches across JMdict and SudachiDict.
3. Include a SudachiDict-only general or function word at a lower initial
   priority than JMdict when it has a dictionary form, reading, known part of
   speech, and no prohibited condition.
4. Include a SudachiDict-only proper noun in the candidate SQLite auxiliary
   layer as a merged written-form plus normalized-reading record. Do not promote
   records in bulk without entry-specific semantic evidence. Proper-noun status
   alone is not a permanent exclusion reason.
5. Count external readings outside kana-search scope, such as alphanumeric
   readings, as warnings and exclude them from kana search. An invalid
   developer-added reading is a validation issue.
6. Require evidence for every developer-added entry.

## Corrections and exclusions

External dictionaries are never edited directly. Reasons and evidence are
recorded in `components/wordquery/data/manual/additions.tsv`,
`corrections.tsv`, and `exclusions.tsv`. Developer tags identify entries by
written form and reading in `components/wordquery/data/manual/tags.tsv` and
record the axis, value, reason, and reference.
Manual corrections, exclusions, and tags are reapplied after source updates.

## Reading requirements

After NFKC and katakana-to-hiragana conversion, a reading normally contains
only hiragana, the prolonged sound mark, and required iteration marks. Middle
dots, commas, and periods from external dictionaries are removed from search
keys, and wave dashes are normalized to prolonged sound marks, while the
original display reading is preserved. Symbols are not silently removed from
developer additions or search input. A reading containing kanji, whitespace,
or control characters is a validation issue.

When the same written form and normalized reading belong to multiple
categories, the representative search category is general if present, then
proper, and function only when all categories are function-word categories. A
matching developer entry overrides external dictionaries with its explicit
category and priority. All parts of speech and sources are retained.

## Search utility

Data validity, commonness, and suitability as an answer for a particular word
game are distinct concepts.

- `accepted/candidate` expresses validation state.
- General vocabulary, proper nouns, function words, and domains express word type.
- Commonness, rarity, and task suitability are ranking signals.
- Display-safety concerns such as offensive or adult vocabulary use independent tags.

Rare words, archaisms, dialect forms, technical terms, and proper nouns remain
candidates when their source and reading are valid. Users may explicitly
deprioritize or exclude them, but an entry is not deleted merely for being
uncommon. Ranking and suitability values retain a source, calculation basis,
or human judgment whenever possible.
