from pathlib import Path

from app.niantic_wiki.validation import find_unrewritten_paths


SITE_ROOT = Path(__file__).resolve().parents[2] / "app" / "niantic_wiki" / "site"


def test_niantic_wiki_about_page_renders(client):
    resp = client.get("/niantic_wiki/about")
    assert resp.status_code == 200
    body = resp.get_data(as_text=True)
    assert "About this archive" in body
    assert 'action="/niantic_wiki/search"' in body
    assert 'href="/niantic_wiki/page/start.html"' in body
    assert "This archive is hosted as part of Cryptobrella" in body
    assert 'href="https://www.cryptobrella.app/"' in body


def test_niantic_wiki_representative_assets_render(client):
    for path in [
        "/niantic_wiki/favicon.ico",
        "/niantic_wiki/styles.css",
        "/niantic_wiki/search-index.json",
        "/niantic_wiki/lib/tpl/dokuwiki2/images/logo.png",
        "/niantic_wiki/media/logo.png",
    ]:
        resp = client.get(path)
        assert resp.status_code == 200, path


def test_niantic_wiki_representative_nested_page_renders(client):
    resp = client.get("/niantic_wiki/page/investigation/characters.html")
    assert resp.status_code == 200
    body = resp.get_data(as_text=True)
    assert "Niantic Project Wiki" in body
    assert 'href="/niantic_wiki/page/investigation/characters/organizations.html"' in body
    assert 'href="/niantic_wiki/page/investigation/characters/acolyte.html"' in body


def test_niantic_wiki_known_missing_asset_stays_404(client):
    resp = client.get("/niantic_wiki/media/investigation/apps/ingress/us1.png")
    assert resp.status_code == 404
    body = resp.get_data(as_text=True)
    assert "Page not found" in body


def test_niantic_wiki_import_has_no_unrewritten_internal_paths():
    findings = find_unrewritten_paths(SITE_ROOT)
    assert findings == []
