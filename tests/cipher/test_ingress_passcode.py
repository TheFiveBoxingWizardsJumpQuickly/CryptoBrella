from app.cipher import ingress_passcode


class FakeConnection:
    def __init__(self, rows):
        self.rows = rows
        self.row_factory = None
        self.closed = False
        self.calls = []

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, tb):
        self.close()
        return False

    def execute(self, query, params=()):
        self.calls.append((query, params))
        return self

    def fetchall(self):
        return self.rows

    def close(self):
        self.closed = True


def test_connect_db_uses_read_only_immutable_uri(monkeypatch):
    calls = []
    fake = FakeConnection([])

    def fake_connect(*args, **kwargs):
        calls.append((args, kwargs))
        return fake

    monkeypatch.setattr(ingress_passcode.sqlite3, "connect", fake_connect)

    conn = ingress_passcode._connect_db()

    assert conn is fake
    assert len(calls) == 1
    args, kwargs = calls[0]
    assert args == (
        f"file:{ingress_passcode.PASSCODE_DB_PATH}?mode=ro&immutable=1",
    )
    assert kwargs == {"uri": True}
    assert fake.row_factory is ingress_passcode.dict_factory


def test_passcode_get_record_by_id_uses_parameterized_query_and_closes_connection(monkeypatch):
    fake = FakeConnection([{"id": 7, "answer1": "ABC"}])
    monkeypatch.setattr(ingress_passcode.sqlite3, "connect", lambda *args, **kwargs: fake)

    record = ingress_passcode.passcode_get_record_by_id(7)

    assert record == {"id": 7, "answer1": "ABC"}
    assert fake.calls == [('SELECT * FROM daily WHERE id=?', (7,))]
    assert fake.closed is True


def test_get_max_id_reads_named_alias(monkeypatch):
    fake = FakeConnection([{"max_id": 301}])
    monkeypatch.setattr(ingress_passcode.sqlite3, "connect", lambda *args, **kwargs: fake)

    max_id = ingress_passcode.get_max_id()

    assert max_id == 301
    assert fake.calls == [('SELECT MAX(id) AS max_id FROM daily', ())]
    assert fake.closed is True


def test_passcode_get_list_closes_connection(monkeypatch):
    rows = [{"id": 1, "date": "2026-03-01", "code": "ABC", "tag": "easy"}]
    fake = FakeConnection(rows)
    monkeypatch.setattr(ingress_passcode.sqlite3, "connect", lambda *args, **kwargs: fake)

    result = ingress_passcode.passcode_get_list()

    assert result == rows
    assert fake.calls == [('SELECT id, date, code, tag FROM daily', ())]
    assert fake.closed is True
