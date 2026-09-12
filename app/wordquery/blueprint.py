"""Thin Flask delivery layer."""

from __future__ import annotations

import os
import sqlite3
import threading
import time
from collections import defaultdict, deque
from pathlib import Path
from typing import Any

from flask import Blueprint, Flask, current_app, jsonify, render_template, request
from wordquery_jp.models import SearchRequest, SearchResponse
from wordquery_jp.operations import (
    public_snapshot_is_fresh,
    verify_reviewed_release,
)
from wordquery_jp.query import (
    SEARCH_REQUEST_VERSION,
    RequestValidationError,
    parse_search_request,
    serialize_search_request,
)
from wordquery_jp.repository import LexiconUnavailable, load_snapshot
from wordquery_jp.search import QueryValidationError, SearchService, SearchTimedOut
from wordquery_jp.search_budget import RegexMatchTimedOut
from wordquery_jp.units import count_normalized_reading_units, count_units

blueprint = Blueprint("wordquery", __name__)


class MemoryRateLimiter:
    def __init__(self, limit: int, window_seconds: float = 60.0) -> None:
        self.limit = limit
        self.window_seconds = window_seconds
        self.requests: dict[str, deque[float]] = defaultdict(deque)

    def allow(self, key: str) -> bool:
        now = time.monotonic()
        history = self.requests[key]
        while history and history[0] <= now - self.window_seconds:
            history.popleft()
        if len(history) >= self.limit:
            return False
        history.append(now)
        return True


def register_wordquery(app: Flask, config: dict[str, Any] | None = None) -> None:
    public = os.environ.get("WORDQUERY_PUBLIC", "0") == "1"
    app.config.from_mapping(
        WORDQUERY_DB=os.environ.get(
            "WORDQUERY_DB", "var/wordquery/current/lexicon.sqlite3"
        ),
        WORDQUERY_MAX_QUERY=200,
        WORDQUERY_TIMEOUT=float(os.environ.get("WORDQUERY_TIMEOUT", "5")),
        WORDQUERY_REGEX_TIMEOUT=float(os.environ.get("WORDQUERY_REGEX_TIMEOUT", "0.05")),
        WORDQUERY_RESULT_LIMIT=3000,
        WORDQUERY_RATE_LIMIT=30,
        WORDQUERY_URL_PREFIX=os.environ.get("WORDQUERY_URL_PREFIX", "/wordquery"),
        WORDQUERY_PUBLIC=public,
        WORDQUERY_RELEASE_MODE=os.environ.get("WORDQUERY_RELEASE_MODE", "updated"),
        WORDQUERY_STATE_DIR=os.environ.get("WORDQUERY_STATE_DIR", "var/wordquery"),
        WORDQUERY_ENFORCE_FRESHNESS=(
            os.environ.get("WORDQUERY_ENFORCE_FRESHNESS", "1" if public else "0") == "1"
        ),
        WORDQUERY_SHOW_ON_HOME=(
            os.environ.get("WORDQUERY_SHOW_ON_HOME", "1" if public else "0") == "1"
        ),
        WORDQUERY_LOAD_MODE=os.environ.get("WORDQUERY_LOAD_MODE", "eager"),
    )
    if config:
        app.config.update(config)

    app.extensions["wordquery_metadata"] = {}
    app.extensions["wordquery_service"] = None
    app.extensions["wordquery_error"] = None
    app.extensions["wordquery_load_lock"] = threading.Lock()
    load_mode = app.config["WORDQUERY_LOAD_MODE"]
    if load_mode not in {"eager", "lazy", "disabled"}:
        app.extensions["wordquery_load_state"] = "failed"
        app.extensions["wordquery_error"] = (
            "WORDQUERY_LOAD_MODE must be eager, lazy or disabled"
        )
    elif load_mode == "disabled":
        app.extensions["wordquery_load_state"] = "disabled"
        app.extensions["wordquery_error"] = "WordQuery is disabled in this environment."
    else:
        app.extensions["wordquery_load_state"] = "unloaded"
        if load_mode == "eager":
            _ensure_wordquery_loaded(app)

    app.extensions["wordquery_limiter"] = MemoryRateLimiter(
        int(app.config["WORDQUERY_RATE_LIMIT"])
    )
    app.register_blueprint(
        blueprint,
        url_prefix=str(app.config["WORDQUERY_URL_PREFIX"]).rstrip("/"),
    )


def _ensure_wordquery_loaded(app: Flask) -> None:
    if app.extensions["wordquery_load_state"] != "unloaded":
        return
    lock: threading.Lock = app.extensions["wordquery_load_lock"]
    with lock:
        if app.extensions["wordquery_load_state"] != "unloaded":
            return
        _load_wordquery(app)


def _load_wordquery(app: Flask) -> None:
    release_mode = app.config["WORDQUERY_RELEASE_MODE"]
    try:
        if release_mode not in {"updated", "reviewed"}:
            raise ValueError("WORDQUERY_RELEASE_MODE must be updated or reviewed")
        if release_mode == "reviewed":
            app.extensions["wordquery_release"] = verify_reviewed_release(
                Path(app.config["WORDQUERY_DB"])
            )
        snapshot = load_snapshot(Path(app.config["WORDQUERY_DB"]))
        app.extensions["wordquery_metadata"] = snapshot.metadata
        app.extensions["wordquery_service"] = SearchService(
            snapshot,
            max_query_length=int(app.config["WORDQUERY_MAX_QUERY"]),
            timeout_seconds=float(app.config["WORDQUERY_TIMEOUT"]),
            regex_timeout_seconds=float(app.config["WORDQUERY_REGEX_TIMEOUT"]),
        )
        app.extensions["wordquery_error"] = None
        app.extensions["wordquery_load_state"] = "loaded"
    except (LexiconUnavailable, OSError, ValueError, sqlite3.Error) as exc:
        app.extensions["wordquery_metadata"] = {}
        app.extensions["wordquery_service"] = None
        app.extensions["wordquery_error"] = str(exc)
        app.extensions["wordquery_load_state"] = "failed"


@blueprint.before_request
def enforce_public_freshness():
    _ensure_wordquery_loaded(current_app)
    if request.endpoint == "wordquery.sources":
        return None
    app = current_app
    if (app.config["WORDQUERY_ENFORCE_FRESHNESS"]
            and not public_snapshot_is_fresh(
                Path(app.config["WORDQUERY_STATE_DIR"]),
                app.extensions["wordquery_metadata"].get("input_hash"),
            )):
        message = "現在、不具合により検索を利用できません。"
        if request.path.rstrip("/").endswith("wordquery") or request.endpoint == "wordquery.index":
            return render_template(
                "wordquery/index.html", lexicon_error=message,
                max_query_length=int(app.config["WORDQUERY_MAX_QUERY"]),
                timeout_seconds=float(app.config["WORDQUERY_TIMEOUT"]),
                result_limit=int(app.config["WORDQUERY_RESULT_LIMIT"]),
            ), 503
        return jsonify(error=message), 503
    return None


@blueprint.after_request
def mark_preview_response(response):
    if not current_app.config["WORDQUERY_PUBLIC"]:
        response.headers["X-Robots-Tag"] = "noindex, nofollow"
    return response


@blueprint.get("/")
def index():
    error = current_app.extensions["wordquery_error"]
    rendered = render_template(
        "wordquery/index.html",
        lexicon_error=error,
        search_request_version=SEARCH_REQUEST_VERSION,
        max_query_length=int(current_app.config["WORDQUERY_MAX_QUERY"]),
        timeout_seconds=float(current_app.config["WORDQUERY_TIMEOUT"]),
        result_limit=int(current_app.config["WORDQUERY_RESULT_LIMIT"]),
    )
    return (rendered, 503) if error else rendered


@blueprint.get("/sources")
def sources() -> str:
    metadata = current_app.extensions["wordquery_metadata"]
    return render_template(
        "wordquery/sources.html",
        jmdict_version=metadata.get("source.jmdict.version"),
        sudachi_version=metadata.get("source.sudachidict_core.version"),
    )


@blueprint.post("/api/search")
def search_api():
    return _handle_search(current_app)


def _handle_search(app: Flask):
    limiter: MemoryRateLimiter = app.extensions["wordquery_limiter"]
    client = request.remote_addr or "unknown"
    if not limiter.allow(client):
        return jsonify(error="検索回数が上限を超えました。しばらく待ってください。"), 429
    service: SearchService | None = app.extensions["wordquery_service"]
    if service is None:
        return jsonify(error=app.extensions["wordquery_error"]), 503
    payload = request.get_json(silent=True)
    if not isinstance(payload, dict):
        return jsonify(error="JSONオブジェクトを送信してください。"), 400
    try:
        result_limit = _requested_result_limit(
            payload, maximum=int(app.config["WORDQUERY_RESULT_LIMIT"])
        )
        search_request = parse_search_request(
            payload,
            max_length=int(app.config["WORDQUERY_MAX_QUERY"]),
            limit=result_limit,
        )
        response = service.execute(search_request)
    except (QueryValidationError, RequestValidationError, ValueError) as exc:
        error: dict[str, object] = {"error": str(exc)}
        position = getattr(exc, "position", None)
        if isinstance(position, int):
            error["error_position"] = position
        return jsonify(error), 400
    except SearchTimedOut as exc:
        return jsonify(
            error=str(exc),
            error_code="regex_match_timeout" if isinstance(exc, RegexMatchTimedOut)
            else "search_timeout",
        ), 408
    return jsonify(_serialize_response(response, search_request))


def _requested_result_limit(payload: dict[str, object], *, maximum: int) -> int:
    value = payload.get("limit", maximum)
    if isinstance(value, bool) or not isinstance(value, int) or not 1 <= value <= maximum:
        raise RequestValidationError(f"表示件数は1から{maximum}までの整数で指定してください。")
    return value


def _serialize_response(
    response: SearchResponse, search_request: SearchRequest
) -> dict[str, object]:
    return {
        "request": serialize_search_request(search_request),
        "normalized_query": response.normalized_query,
        "total": response.total,
        "truncated": response.truncated,
        "duration_ms": round(response.duration_ms, 2),
        "condition_description": response.condition_description,
        "results": [
            {
                "surface": record.surface,
                "reading": record.reading,
                "normalized_reading": record.normalized_reading,
                "category": record.category,
                "all_categories": sorted(
                    {record.category, *(source.category for source in record.sources)}
                ),
                "pos": record.pos,
                "status": record.status,
                "vocabulary_layer": (
                    "auxiliary" if record.status == "candidate" else "core"
                ),
                "tags": [
                    {
                        "axis": tag.axis,
                        "value": tag.value,
                        "evidence": [
                            {
                                "source": evidence.source,
                                "source_entry_id": evidence.source_entry_id,
                                "value": evidence.evidence,
                                "reason": evidence.reason,
                                "reference": evidence.reference,
                            }
                            for evidence in tag.evidence
                        ],
                    }
                    for tag in record.tags
                ],
                "multiple_sources": record.multiple_sources,
                "sources": [
                    {
                        "source": source.source,
                        "source_entry_id": source.source_entry_id,
                        "surface": source.surface,
                        "reading": source.reading,
                        "category": source.category,
                        "pos": source.pos,
                        "reason": source.reason,
                        "reference": source.reference,
                    }
                    for source in record.sources
                ],
                "lengths": {
                    "kana": count_normalized_reading_units(
                        record.normalized_reading, "kana"
                    ),
                    "mora": count_normalized_reading_units(
                        record.normalized_reading, "mora"
                    ),
                    "surface": count_units(record.surface, "surface"),
                },
                "sort_score": sort_score,
                "sort_reasons": list(sort_reasons),
                "deprioritize_reasons": list(deprioritize_reasons),
                "match_start": span[0] if span else None,
                "match_end": span[1] if span else None,
            }
            for record, span, sort_score, sort_reasons, deprioritize_reasons in zip(
                response.results,
                response.match_spans,
                response.sort_scores,
                response.sort_reasons,
                response.deprioritize_reasons,
                strict=True,
            )
        ],
    }
