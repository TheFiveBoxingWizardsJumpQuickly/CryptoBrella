from pathlib import Path
import re


TEXT_EXTENSIONS = {".html", ".css", ".js"}

FORBIDDEN_PATTERNS = [
    re.compile(r'(?P<path>(?:href|src|action|content|poster)=["\'])/(?!niantic_wiki/|/)'),
    re.compile(r'(?P<path>url\(["\']?)/(?!niantic_wiki/|/)'),
    re.compile(r'(?P<path>(?:fetch|location\.assign|location\.replace)\(["\'])/(?!niantic_wiki/|/)'),
    re.compile(r'(?P<path>[("\'\s=])/(favicon\.ico\b|search-index\.json|page/|search\b|about\b|media-manager\b|styles\.css\b|script\.js\b|media/|lib/)')
]


def iter_text_files(site_root: Path):
    for path in sorted(site_root.rglob("*")):
        if path.is_file() and path.suffix.lower() in TEXT_EXTENSIONS:
            yield path


def find_unrewritten_paths(site_root: Path):
    findings = []
    for path in iter_text_files(site_root):
        relative_path = path.relative_to(site_root).as_posix()
        text = path.read_text(encoding="utf-8")
        for pattern in FORBIDDEN_PATTERNS:
            for match in pattern.finditer(text):
                findings.append(
                    {
                        "file": relative_path,
                        "snippet": text[max(0, match.start() - 40): min(len(text), match.end() + 80)],
                    }
                )
    return findings
