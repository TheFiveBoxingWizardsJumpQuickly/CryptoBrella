from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def test_public_readmes_describe_product_without_internal_operations():
    readme = (ROOT / "README.md").read_text(encoding="utf-8")
    docs_readme = (ROOT / "docs/README.md").read_text(encoding="utf-8")
    public_documents = [readme, docs_readme]
    public_documents.extend(
        path.read_text(encoding="utf-8") for path in (ROOT / "docs/public").rglob("*.md")
    )

    for expected in ("## Features", "## Requirements", "WordQuery: JP"):
        assert expected in readme

    for internal_term in (
        "docs/local",
        "PythonAnywhere",
        "virtualenv",
        "Development Environment",
        "Continuous Integration",
        ".venv",
        "pip install",
        "/absolute/path",
    ):
        assert all(internal_term not in document for document in public_documents)

    for internal_term in (
        "local-only",
        "ローカル専用",
        "Git公開対象",
        "handover",
        "dashboard",
        "backlog",
    ):
        assert all(internal_term not in document for document in public_documents)


def test_public_readme_links_resolve_within_repository():
    expected_links = (
        "docs/public/crypto_function_inventory.md",
        "docs/public/system_overview.md",
        "docs/public/wordquery/README.md",
        "docs/public/wordquery/data_sources.md",
        "docs/README.md",
    )

    for relative_path in expected_links:
        assert (ROOT / relative_path).is_file()
