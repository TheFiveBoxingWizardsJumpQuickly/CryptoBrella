from pathlib import Path

from flask import Blueprint, abort, render_template, send_from_directory


SITE_DIR = Path(__file__).resolve().parent / "site"
PAGES_DIR = SITE_DIR / "page"

niantic_wiki = Blueprint("niantic_wiki", __name__, url_prefix="/niantic_wiki")


def _send_site_file(relative_path: str):
    target = SITE_DIR / relative_path
    if not target.exists() or not target.is_file():
        abort(404)
    return send_from_directory(SITE_DIR, relative_path)


@niantic_wiki.errorhandler(404)
def not_found(error):
    return (
        render_template(
            "niantic_wiki_404.html",
            start_url="/niantic_wiki/page/start.html",
        ),
        404,
    )


@niantic_wiki.get("/")
def root():
    return _send_site_file("index.html")


@niantic_wiki.get("/about")
def about():
    return _send_site_file("about.html")


@niantic_wiki.get("/search")
def search():
    return _send_site_file("search.html")


@niantic_wiki.get("/media-manager")
def media_manager():
    return _send_site_file("media-manager.html")


@niantic_wiki.get("/page/<path:slug>")
def page(slug: str):
    file_name = slug if slug.endswith(".html") else f"{slug}.html"
    target = PAGES_DIR / file_name
    if not target.exists() or not target.is_file():
        abort(404)
    return send_from_directory(PAGES_DIR, file_name)


@niantic_wiki.get("/<path:asset_path>")
def asset(asset_path: str):
    return _send_site_file(asset_path)
