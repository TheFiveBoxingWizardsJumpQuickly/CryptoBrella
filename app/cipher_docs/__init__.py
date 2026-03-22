from pathlib import Path


DOCS_DIR = Path(__file__).resolve().parent
SECTION_ORDER = [
    "about",
    "how_to_use_tool",
    "test_cases",
    "challenge",
    "related_links",
]


def _parse_metadata(lines):
    metadata = {}
    index = 0

    while index < len(lines):
        line = lines[index].strip()
        if not line:
            index += 1
            break
        if line.startswith("["):
            break
        key, sep, value = line.partition(":")
        if not sep:
            raise ValueError(f"Invalid metadata line: {lines[index]}")
        metadata[key.strip()] = value.strip()
        index += 1

    return metadata, index


def _parse_sections(lines, start_index):
    sections = {section_id: [] for section_id in SECTION_ORDER}
    current_section = None
    buffer = []

    def flush():
        nonlocal buffer
        if current_section is not None:
            sections[current_section] = buffer[:]
        buffer = []

    for raw_line in lines[start_index:]:
        line = raw_line.rstrip("\n")
        stripped = line.strip()
        if stripped.startswith("[") and stripped.endswith("]"):
            flush()
            current_section = stripped[1:-1]
            if current_section not in sections:
                raise ValueError(f"Unknown section: {current_section}")
            continue

        if current_section is None:
            if stripped:
                raise ValueError(f"Content found before first section: {line}")
            continue

        buffer.append(line)

    flush()
    return sections


def _make_paragraph_blocks(lines):
    blocks = []
    paragraph_lines = []
    index = 0

    while index < len(lines):
        stripped = lines[index].strip()

        if not stripped:
            if paragraph_lines:
                blocks.append(
                    {"type": "paragraph", "text": " ".join(line.strip() for line in paragraph_lines)}
                )
                paragraph_lines = []
            index += 1
            continue

        if stripped == "::pre":
            if paragraph_lines:
                blocks.append(
                    {"type": "paragraph", "text": " ".join(line.strip() for line in paragraph_lines)}
                )
                paragraph_lines = []
            index += 1
            pre_lines = []
            while index < len(lines) and lines[index].strip() != "::endpre":
                pre_lines.append(lines[index])
                index += 1
            blocks.append({"type": "pre", "text": "\n".join(pre_lines).rstrip()})
            if index < len(lines) and lines[index].strip() == "::endpre":
                index += 1
            continue

        paragraph_lines.append(lines[index])
        index += 1

    if paragraph_lines:
        blocks.append({"type": "paragraph", "text": " ".join(line.strip() for line in paragraph_lines)})

    return blocks


def _make_related_links(lines):
    links = []
    for line in lines:
        stripped = line.strip()
        if not stripped:
            continue
        if not stripped.startswith("- "):
            raise ValueError(f"Invalid related link line: {line}")
        body = stripped[2:]
        label, sep, url = body.partition(" | ")
        if not sep:
            raise ValueError(f"Related link must use 'label | url': {line}")
        links.append({"label": label.strip(), "url": url.strip()})
    return links


def _load_page(pageid):
    page_path = DOCS_DIR / f"{pageid}.txt"
    if not page_path.exists():
        raise KeyError(pageid)

    lines = page_path.read_text(encoding="utf-8").splitlines()
    metadata, start_index = _parse_metadata(lines)
    sections = _parse_sections(lines, start_index)

    return {
        "title": metadata.get("title", pageid),
        "lang": metadata.get("lang", ""),
        "about": _make_paragraph_blocks(sections["about"]),
        "how_to_use_tool": _make_paragraph_blocks(sections["how_to_use_tool"]),
        "test_cases": _make_paragraph_blocks(sections["test_cases"]),
        "challenge": _make_paragraph_blocks(sections["challenge"]),
        "related_links": _make_related_links(sections["related_links"]),
    }


def get_cipher_doc_page(mode, pageid):
    if mode == "keys":
        return sorted(path.stem for path in DOCS_DIR.glob("*.txt") if path.is_file())
    return _load_page(pageid)
