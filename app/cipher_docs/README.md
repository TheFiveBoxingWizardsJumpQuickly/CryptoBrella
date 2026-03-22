# Cipher Docs Format

Each page lives in its own text file under this directory.

## File Name

- `<pageid>.txt`
- Example: `rot-ja.txt`

## Metadata

The file begins with simple metadata lines:

```txt
title: ROT
lang: Ja
```

Then add one blank line before the first section.

## Sections

Supported sections are:

- `[about]`
- `[how_to_use_tool]`
- `[test_cases]`
- `[challenge]`
- `[related_links]`

## Paragraphs

- Separate paragraphs with one blank line.
- Keep one paragraph as one logical line when possible.

## Preformatted Blocks

Use `::pre` / `::endpre` for text that must preserve line breaks.

```txt
[test_cases]
::pre
Case 1
INPUT = ABC
OUTPUT = DEF
::endpre
```

## Related Links

Use one line per link:

```txt
[related_links]
- Cipher Tool: Rot | ../rot
```
