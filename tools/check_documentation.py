"""Check current documentation paths and anchors without reading private runtime data."""
from __future__ import annotations

import argparse
import re
import unicodedata
from pathlib import Path
from urllib.parse import unquote, urlsplit

ROOT = Path(__file__).resolve().parents[1]
LINK = re.compile(r'\[[^\]]*\]\(([^\s)]+)(?:\s+"[^"]*")?\)')
CODE_DOC = re.compile(r'`([^`\n\s]+\.md(?:#[^`\n\s]+)?)`')


def anchors(text: str) -> set[str]:
    """GitHub-style slugs for ATX headings, ignoring fenced code blocks."""
    result: set[str] = set()
    counts: dict[str, int] = {}
    fence = False
    for line in text.splitlines():
        if line.lstrip().startswith(('```', '~~~')):
            fence = not fence
            continue
        match = re.match(r'^#{1,6}\s+(.+?)\s*#*$', line)
        if fence or not match:
            continue
        title = re.sub(r'\[([^\]]+)\]\([^)]*\)', r'\1', match[1])
        title = re.sub(r'<[^>]*>', '', title).lower()
        slug = ''.join(c for c in title if c in '-_ ' or unicodedata.category(c)[0] in 'LN').replace(' ', '-')
        count = counts.get(slug, 0)
        counts[slug] = count + 1
        result.add(slug if not count else f'{slug}-{count}')
    return result


def check_file(path: Path, root: Path) -> list[str]:
    text = path.read_text(encoding='utf-8')
    problems: list[str] = []
    refs = [(m[1], m.start(), False) for m in LINK.finditer(text)]
    refs += [(m[1], m.start(), True) for m in CODE_DOC.finditer(text)]
    for raw, offset, code in refs:
        parsed = urlsplit(raw.strip('<>'))
        if parsed.scheme or parsed.netloc:
            continue
        target_text = unquote(parsed.path)
        if any(c in target_text for c in '*<>'):
            continue  # Documented templates/globs, not literal file references.
        target = (path.parent / target_text).resolve() if target_text else path.resolve()
        if code and not target.exists():
            target = (root / target_text).resolve()
        location = f'{path.relative_to(root)}:{text.count(chr(10), 0, offset) + 1}'
        if not target.exists():
            problems.append(f'{location}: missing path: {raw}')
            continue
        if path.is_relative_to(root / 'docs/public') and target.is_relative_to(root / 'docs/local'):
            problems.append(f'{location}: public reference to private document: {raw}')
        if (parsed.fragment and target.suffix == '.md' and target.is_file()
                and unquote(parsed.fragment) not in anchors(target.read_text(encoding='utf-8'))):
            problems.append(f'{location}: missing heading: {raw}')
    return problems


def document_paths(root: Path, local: bool) -> list[Path]:
    paths = [root / 'README.md', root / 'docs/README.md']
    paths.extend((root / 'docs/public').rglob('*.md'))
    paths.extend([root / 'app/cipher_docs/README.md', root / 'app/niantic_wiki/README.md', root / 'tests/cipher/README.md'])
    if local:
        paths.append(root / 'AGENTS.md')
        paths.extend(p for p in (root / 'docs/local').rglob('*.md') if 'archive' not in p.relative_to(root / 'docs/local').parts)
    return sorted(set(paths))


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--local', action='store_true', help='Also check local instructions and current operational documents')
    args = parser.parse_args()
    paths = document_paths(ROOT, args.local)
    problems = []
    for path in paths:
        if not path.is_file():
            problems.append(f'{path.relative_to(ROOT)}: required entry missing')
        else:
            problems.extend(check_file(path, ROOT))
    for problem in problems:
        print(problem)
    print(f'{len(paths)} documents checked; {len(problems)} problems. Historical archives, external URLs and runtime data are excluded.')
    return bool(problems)


if __name__ == '__main__':
    raise SystemExit(main())
