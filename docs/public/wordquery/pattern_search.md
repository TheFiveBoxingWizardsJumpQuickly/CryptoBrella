# WordQuery: JP readable pattern search

## Purpose

Readable patterns express common crossword and fill-in-the-blank reading
shapes without requiring Regex knowledge. They use `mode=pattern` in search
request version 7 and are validated with a grammar separate from `mode=regex`.

## Grammar

The pattern matches the entire normalized reading, not a substring.

| Syntax | Meaning | Example |
|---|---|---|
| Kana | Match that kana character | `ねこ` |
| `?` | Match any one character | `ね?` |
| `*` | Match zero or more characters | `*ね` |
| `[かき]` | Match one character from the set | `ね[こご]` |
| `[!かき]` | Match one character outside the set | `ね[!こ]` |

Hiragana, katakana, and full-width or half-width forms follow the standard
reading normalization rules. Consecutive `*` tokens collapse into one, as do
duplicate kana in include or exclude sets. Empty `[]` or `[!]`, an unclosed
`[`, `?` or `*` inside a set, and Regex tokens such as `.`, `(`, or `|` are
errors.

Regex `.`, `.*`, character classes, and anchors are not accepted as readable
pattern syntax. Users who need advanced Regex select the Japanese UI tab
labelled `Regex` explicitly.

## Error locations and interpreted conditions

For a syntax error, the API returns a zero-based `error_position` along with a
Japanese message. The UI focuses the input and selects the relevant character.
For a valid pattern, it displays an interpreted condition above the results;
for example, `ね?[こご]` becomes
`パターン全体: 『ね』→任意の1文字→『こ・ご』のいずれか1文字`.

## API

The JSON search endpoint accepts the following request body with
`mode=pattern`.

```json
{
  "version": 7,
  "mode": "pattern",
  "query": "ね?[こご]",
  "sort": "commonness",
  "vocabulary_layers": ["core"]
}
```

Length, counting unit, required or forbidden characters, category, vocabulary
layer, tag, sorting, and deprioritization use the shared conditions. The pattern
itself is evaluated in kana-character units over the normalized reading. A
different selected length unit is applied as an additional result filter.

Search prefilters use fixed prefixes, suffixes, and character lengths when safe.
Broad patterns can still reach the search time limit; existing time and result
limits apply.

## Small kana equivalence

In the Pattern tab, enable `小書きかなを同一視` under `その他の条件` to match
small kana and their full-size counterparts. The option is off by default.
The JSON field is `fold_small_kana` (boolean, default `false`) for `reading`
and `pattern` requests.

| Small kana | Full-size kana |
|---|---|
| ぁ ぃ ぅ ぇ ぉ | あ い う え お |
| ゃ ゅ ょ | や ゆ よ |
| っ ゎ ゕ ゖ | つ わ か け |

Matching is symmetric: `きやつと` can find `きゃっと`, and vice versa.
The same rule applies to all four reading match types, pattern literals,
include/exclude sets, and required/forbidden text. For example, `[!つ]`
excludes both `つ` and `っ` when the option is enabled.

Voicing marks, semi-voicing marks, and long-vowel marks remain distinct.
Original readings, displayed forms, result grouping, and sort order are kept.
Counting still uses the original reading: `きゃっと` has four reading
characters and three morae. This option does not change Regex or anagram
matching, and does not require a dictionary rebuild.
