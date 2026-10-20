"""/all_topics and /topics derive `active_keys` and the session PDF URLs from the
metadata of every speech in Chroma. That scan used to run on every request and loaded
all ~67k metadatas at once (+~500 MB RSS), which got the 4 GiB Cloud Run instance
OOM-killed. These tests pin the fix: scan once per process, in small pages, safely under
concurrency, and invalidate after an update."""

import json
import threading
import time
from types import SimpleNamespace

import pytest
from fastapi.testclient import TestClient

from practicepreach import fast

TOPS = {
    "90_Tagesordnungspunkt 1": {"top_key": "90_Tagesordnungspunkt 1", "session": "90", "date": "2026-01-01", "top_id": "TOP 1"},
    "91_Tagesordnungspunkt 2": {"top_key": "91_Tagesordnungspunkt 2", "session": "91", "date": "2026-01-02", "top_id": "TOP 2"},
    "92_Tagesordnungspunkt 3": {"top_key": "92_Tagesordnungspunkt 3", "session": "92", "date": "2026-01-03", "top_id": "TOP 3"},
}


def _speech(top_key: str, n: int) -> dict:
    session = top_key.split("_", 1)[0]
    return {"type": "speech", "top_key": top_key, "id": f"ID21{session}{n:05d}", "party": "SPD"}


def _metadatas(top_keys, per_key=4):
    return [_speech(k, i) for k in top_keys for i in range(per_key)]


class FakeCollection:
    """Mimics chromadb's Collection.get, including limit/offset, and records every call."""

    def __init__(self, metadatas, delay=0.0):
        self.metadatas = metadatas
        self.delay = delay
        self.calls = []
        self.fail_next = False

    def get(self, where=None, include=None, limit=None, offset=0):
        self.calls.append({"limit": limit, "offset": offset})
        if self.fail_next:
            self.fail_next = False
            raise RuntimeError("chroma exploded")
        time.sleep(self.delay)
        end = None if limit is None else offset + limit
        return {"metadatas": self.metadatas[offset:end]}

    @property
    def scans(self):
        # every full scan starts at offset 0 (old code: single un-paged get, also offset 0)
        return sum(1 for c in self.calls if c["offset"] == 0)


def _rag(col):
    return SimpleNamespace(vector_store=SimpleNamespace(_collection=col))


@pytest.fixture(autouse=True)
def tops_file(tmp_path, monkeypatch):
    path = tmp_path / "tops.json"
    path.write_text(json.dumps(TOPS))
    monkeypatch.setattr(fast, "TOPS_JSON", path)
    fast._invalidate_store_scan()
    yield
    fast._invalidate_store_scan()


def test_result_is_unchanged():
    # characterisation: green on the old code too — the refactor must not change output
    col = FakeCollection(_metadatas(["90_Tagesordnungspunkt 1", "91_Tagesordnungspunkt 2"]))
    tops, active_keys, pdf_urls = fast._load_tops_with_active_keys(_rag(col))
    assert tops == TOPS
    assert active_keys == {"90_Tagesordnungspunkt 1", "91_Tagesordnungspunkt 2"}
    assert pdf_urls == {
        "90": "https://dserver.bundestag.de/btp/21/21090.pdf",
        "91": "https://dserver.bundestag.de/btp/21/21091.pdf",
    }


def test_repeated_calls_scan_the_store_once():
    col = FakeCollection(_metadatas(["90_Tagesordnungspunkt 1"]))
    rag = _rag(col)
    for _ in range(3):
        fast._load_tops_with_active_keys(rag)
    assert col.scans == 1


def test_scan_is_paged(monkeypatch):
    monkeypatch.setattr(fast, "STORE_SCAN_BATCH", 5)
    keys = ["90_Tagesordnungspunkt 1", "91_Tagesordnungspunkt 2", "92_Tagesordnungspunkt 3"]
    col = FakeCollection(_metadatas(keys))  # 12 rows -> pages of 5
    _, active_keys, pdf_urls = fast._load_tops_with_active_keys(_rag(col))
    assert col.calls, "store was never read"
    assert all(c["limit"] == 5 for c in col.calls), col.calls
    assert [c["offset"] for c in col.calls][:3] == [0, 5, 10]
    # paging must not lose rows at page boundaries
    assert active_keys == set(keys)
    assert set(pdf_urls) == {"90", "91", "92"}


def test_concurrent_first_requests_share_one_scan():
    col = FakeCollection(_metadatas(["90_Tagesordnungspunkt 1"]), delay=0.05)
    rag = _rag(col)
    barrier = threading.Barrier(8)

    def hit():
        barrier.wait()
        fast._load_tops_with_active_keys(rag)

    threads = [threading.Thread(target=hit) for _ in range(8)]
    [t.start() for t in threads]
    [t.join() for t in threads]
    assert col.scans == 1


def test_invalidate_forces_a_fresh_scan():
    col = FakeCollection(_metadatas(["90_Tagesordnungspunkt 1"]))
    rag = _rag(col)
    _, before, _ = fast._load_tops_with_active_keys(rag)
    assert before == {"90_Tagesordnungspunkt 1"}

    col.metadatas = _metadatas(["90_Tagesordnungspunkt 1", "92_Tagesordnungspunkt 3"])
    _, cached, _ = fast._load_tops_with_active_keys(rag)
    assert cached == before, "served a fresh scan although nothing invalidated the cache"

    fast._invalidate_store_scan()
    _, after, _ = fast._load_tops_with_active_keys(rag)
    assert after == {"90_Tagesordnungspunkt 1", "92_Tagesordnungspunkt 3"}


def test_failed_scan_is_not_cached():
    # characterisation: green on the old code too — a transient Chroma error must not
    # poison the cache for the life of the process
    col = FakeCollection(_metadatas(["90_Tagesordnungspunkt 1"]))
    rag = _rag(col)
    col.fail_next = True
    with pytest.raises(RuntimeError):
        fast._load_tops_with_active_keys(rag)
    _, active_keys, _ = fast._load_tops_with_active_keys(rag)
    assert active_keys == {"90_Tagesordnungspunkt 1"}


@pytest.mark.parametrize("update_fails", [False, True])
def test_admin_update_invalidates_the_cache(monkeypatch, update_fails):
    col = FakeCollection(_metadatas(["90_Tagesordnungspunkt 1"]))
    rag = _rag(col)
    fast.app.state.rag = rag
    monkeypatch.setattr(fast, "UPDATE_SECRET_TOKEN", "secret")

    fast._load_tops_with_active_keys(rag)  # warm the cache
    fast._load_tops_with_active_keys(rag)
    # control: without this the test would also pass when there is no cache at all
    assert col.scans == 1

    done = threading.Event()

    def fake_run_update(r, since_date=None):
        col.metadatas = _metadatas(["90_Tagesordnungspunkt 1", "92_Tagesordnungspunkt 3"])
        try:
            if update_fails:
                raise RuntimeError("update broke half-way")  # partial writes are possible
            return {"embedded": 1}
        finally:
            done.set()

    monkeypatch.setattr(fast, "run_update", fake_run_update)

    client = TestClient(fast.app)  # no `with`: lifespan (and Rag()) is not started
    resp = client.post("/admin/update", headers={"Authorization": "Bearer secret"})
    assert resp.json() == {"status": "started"}
    assert done.wait(5)
    deadline = time.time() + 5
    while fast._update_running and time.time() < deadline:
        time.sleep(0.01)

    _, active_keys, _ = fast._load_tops_with_active_keys(rag)
    assert "92_Tagesordnungspunkt 3" in active_keys


def _fake_rag_class(col):
    class FakeRag:
        def __init__(self):
            self.vector_store = SimpleNamespace(_collection=col)

        def shutdown(self):
            pass

    return FakeRag


def test_startup_warms_the_scan_before_any_request(monkeypatch):
    col = FakeCollection(_metadatas(["90_Tagesordnungspunkt 1"]))
    monkeypatch.setattr(fast, "Rag", _fake_rag_class(col))
    with TestClient(fast.app):  # `with` runs the lifespan
        assert col.scans == 1
        fast._load_tops_with_active_keys(fast.app.state.rag)
        assert col.scans == 1


def test_startup_survives_a_failing_warmup(monkeypatch):
    col = FakeCollection(_metadatas(["90_Tagesordnungspunkt 1"]))
    col.fail_next = True
    monkeypatch.setattr(fast, "Rag", _fake_rag_class(col))
    with TestClient(fast.app):  # must not raise: the first request just scans lazily
        _, active_keys, _ = fast._load_tops_with_active_keys(fast.app.state.rag)
        assert active_keys == {"90_Tagesordnungspunkt 1"}
