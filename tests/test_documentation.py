from tools.check_documentation import anchors, check_file, document_paths


def test_relative_links_and_unicode_duplicate_anchors(tmp_path):
    page = tmp_path / 'index.md'
    (tmp_path / 'guide.md').write_text('# 検証\n# 検証\n', encoding='utf-8')
    page.write_text('[one](guide.md#検証) [two](guide.md#検証-1)', encoding='utf-8')
    assert check_file(page, tmp_path) == []
    page.write_text('[missing](guide.md#unknown)', encoding='utf-8')
    assert 'missing heading' in check_file(page, tmp_path)[0]


def test_code_path_detects_stale_document_even_without_markdown_link(tmp_path):
    page = tmp_path / 'index.md'
    page.write_text('Read `docs/old-plan.md`.', encoding='utf-8')
    assert 'missing path' in check_file(page, tmp_path)[0]


def test_public_private_link_is_rejected_even_when_target_exists(tmp_path):
    public = tmp_path / 'docs/public'
    private = tmp_path / 'docs/local'
    public.mkdir(parents=True)
    private.mkdir()
    (private / 'state.md').write_text('# Private\n', encoding='utf-8')
    page = public / 'index.md'
    page.write_text('[state](../local/state.md)', encoding='utf-8')
    assert 'public reference to private' in check_file(page, tmp_path)[0]


def test_current_scan_excludes_archived_stale_instructions(tmp_path):
    archive = tmp_path / 'docs/local/archive'
    archive.mkdir(parents=True)
    stale = archive / 'old.md'
    stale.write_text('[old](missing.md)', encoding='utf-8')
    current = archive.parent / 'README.md'
    current.write_text('# Current\n', encoding='utf-8')
    paths = document_paths(tmp_path, local=True)
    assert current in paths
    assert stale not in paths
    assert current not in document_paths(tmp_path, local=False)


def test_code_block_headings_are_not_link_targets():
    assert anchors('# Real\n```md\n# Example\n```\n') == {'real'}
