"""Request-local cooperative deadlines, shared with SQLite and nested searches."""

from __future__ import annotations

import sqlite3
import time
from contextvars import ContextVar
from functools import wraps


class SearchTimedOut(TimeoutError):
    pass


class RegexMatchTimedOut(SearchTimedOut):
    pass


_budget: ContextVar[tuple[float, float] | None] = ContextVar("search_budget", default=None)


def expired() -> bool:
    budget = _budget.get()
    return budget is not None and time.monotonic() >= budget[0]


def check_budget() -> None:
    if expired():
        seconds = _budget.get()[1]
        raise SearchTimedOut(f"検索処理が制限時間（{seconds:g}秒）を超えたため、中断しました。")


def remaining_seconds(fallback: float) -> float:
    budget = _budget.get()
    remaining = fallback if budget is None else budget[0] - time.monotonic()
    if remaining <= 0:
        check_budget()
    return remaining


def search_budget(method):
    @wraps(method)
    def wrapped(self, *args, **kwargs):
        existing = _budget.get()
        token = _budget.set(existing or (time.monotonic() + self.timeout_seconds,
                                       self.timeout_seconds))
        try:
            check_budget()
            result = method(self, *args, **kwargs)
            check_budget()
            return result
        except sqlite3.OperationalError:
            check_budget()
            raise
        finally:
            _budget.reset(token)
    return wrapped
