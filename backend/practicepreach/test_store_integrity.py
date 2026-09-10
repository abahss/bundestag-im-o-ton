import sqlite3

import pytest

from practicepreach import rag as rag_module
from practicepreach.rag import (
    Rag,
    StoreIntegrityError,
    _assert_store_healthy,
    _download_chroma_store,
)

VECTOR_SEG = "94576fab-c54f-42cb-954b-0decc87770fe"
META_SEG = "9533cdeb-d679-48af-a8fa-b4f43e9b3131"

# Small dimension keeps the fake data_level0.bin sizes tiny while preserving the
# real "size scales with n_vectors * dimension" relationship the check relies on.
DIM = 8


def make_store(
    path,
    *,
    n_vectors=50_000,
    dimension=DIM,
    with_sqlite=True,
    corrupt_sqlite=False,
    with_segment_bin=True,
    segment_bin_size=None,
):
    """Build a Chroma-store-shaped directory at `path`. Defaults produce a store
    that passes _assert_store_healthy; flip a flag to simulate a partial download."""
    path.mkdir(parents=True, exist_ok=True)
    if corrupt_sqlite:
        (path / "chroma.sqlite3").write_bytes(b"SQLite format 3\x00" + b"\xde\xad\xbe\xef" * 64)
    elif with_sqlite:
        con = sqlite3.connect(path / "chroma.sqlite3")
        con.executescript(
            """
            CREATE TABLE collections (id TEXT PRIMARY KEY, name TEXT NOT NULL, dimension INTEGER);
            CREATE TABLE segments (
                id TEXT PRIMARY KEY, type TEXT NOT NULL, scope TEXT NOT NULL,
                collection TEXT NOT NULL
            );
            CREATE TABLE embeddings (
                id INTEGER PRIMARY KEY, segment_id TEXT NOT NULL,
                embedding_id TEXT NOT NULL, seq_id BLOB NOT NULL,
                created_at TIMESTAMP
            );
            """
        )
        con.execute("INSERT INTO collections VALUES ('col1', 'political_collection', ?)", (dimension,))
        con.execute(
            "INSERT INTO segments VALUES (?, ?, 'VECTOR', 'col1')",
            (VECTOR_SEG, "urn:chroma:segment/vector/hnsw-local-persisted"),
        )
        con.execute(
            "INSERT INTO segments VALUES (?, ?, 'METADATA', 'col1')",
            (META_SEG, "urn:chroma:segment/metadata/sqlite"),
        )
        con.executemany(
            "INSERT INTO embeddings (segment_id, embedding_id, seq_id, created_at) "
            "VALUES (?, ?, X'00', '2026-01-01')",
            [(VECTOR_SEG, f"e{i}") for i in range(n_vectors)],
        )
        con.commit()
        con.close()
    if with_segment_bin:
        if segment_bin_size is None:
            segment_bin_size = n_vectors * dimension * 4 * 4  # comfortably over the 3x floor
        seg_dir = path / VECTOR_SEG
        seg_dir.mkdir(parents=True, exist_ok=True)
        (seg_dir / "data_level0.bin").write_bytes(b"\x00" * segment_bin_size)
        (seg_dir / "header.bin").write_bytes(b"\x00" * 100)
    return str(path)


# --- _assert_store_healthy -------------------------------------------------------

def test_complete_store_returns_vector_count(tmp_path):
    store = make_store(tmp_path / "chroma_store_gemini", n_vectors=49_544)
    assert _assert_store_healthy(store) == 49_544


def test_realistic_segment_size_passes(tmp_path):
    # data_level0.bin in a real store is ~n_vectors * dimension * 4 (a hair under,
    # once some rows are tombstoned) — the floor must not reject that.
    store = make_store(
        tmp_path / "chroma_store_gemini",
        n_vectors=49_544,
        segment_bin_size=int(49_544 * DIM * 4 * 0.98),
    )
    assert _assert_store_healthy(store) == 49_544


def test_too_few_vectors_raises(tmp_path):
    store = make_store(tmp_path / "chroma_store_gemini", n_vectors=1_169)
    with pytest.raises(StoreIntegrityError):
        _assert_store_healthy(store)


def test_missing_sqlite_raises(tmp_path):
    store = make_store(tmp_path / "chroma_store_gemini", with_sqlite=False)
    with pytest.raises(StoreIntegrityError):
        _assert_store_healthy(store)


def test_corrupt_sqlite_raises(tmp_path):
    store = make_store(tmp_path / "chroma_store_gemini", corrupt_sqlite=True)
    with pytest.raises(StoreIntegrityError):
        _assert_store_healthy(store)


def test_missing_segment_binary_raises(tmp_path):
    store = make_store(tmp_path / "chroma_store_gemini", with_segment_bin=False)
    with pytest.raises(StoreIntegrityError):
        _assert_store_healthy(store)


def test_truncated_segment_binary_raises(tmp_path):
    # A quarter of n_vectors * DIM * 4 — well under the 0.5x floor.
    store = make_store(
        tmp_path / "chroma_store_gemini", n_vectors=50_000, segment_bin_size=50_000 * DIM
    )
    with pytest.raises(StoreIntegrityError):
        _assert_store_healthy(store)


# --- upload_to_gcs: partial store never reaches GCS, sidecars still do ----------

@pytest.fixture
def spy_subprocess(monkeypatch):
    import subprocess

    calls = []

    def fake_run(cmd, *args, **kwargs):
        calls.append(cmd)
        return subprocess.CompletedProcess(cmd, 0, stdout="", stderr="")

    monkeypatch.setattr("subprocess.run", fake_run)
    return calls


def test_upload_never_cps_an_unhealthy_store(tmp_path, monkeypatch, spy_subprocess):
    store = make_store(tmp_path / "chroma_store_gemini", n_vectors=1_169)
    monkeypatch.setattr(rag_module, "GCS_LOCAL_CACHE", store)
    monkeypatch.chdir(tmp_path)

    with pytest.raises(StoreIntegrityError):
        Rag.upload_to_gcs(Rag.__new__(Rag))

    assert not any("cp" in cmd and "-r" in cmd for cmd in spy_subprocess)


def test_upload_still_pushes_sidecars_when_store_is_unhealthy(tmp_path, monkeypatch, spy_subprocess):
    store = make_store(tmp_path / "chroma_store_gemini", n_vectors=1_169)
    monkeypatch.setattr(rag_module, "GCS_LOCAL_CACHE", store)
    monkeypatch.chdir(tmp_path)
    (tmp_path / "data").mkdir()
    (tmp_path / "data" / "summaries_cache.json").write_text("{}")

    with pytest.raises(StoreIntegrityError):
        Rag.upload_to_gcs(Rag.__new__(Rag))

    assert any("summaries_cache.json" in " ".join(cmd) for cmd in spy_subprocess)


def test_upload_cps_the_store_when_healthy(tmp_path, monkeypatch, spy_subprocess):
    store = make_store(tmp_path / "chroma_store_gemini", n_vectors=49_544)
    monkeypatch.setattr(rag_module, "GCS_LOCAL_CACHE", store)
    monkeypatch.chdir(tmp_path)

    Rag.upload_to_gcs(Rag.__new__(Rag))

    assert any(store in " ".join(cmd) for cmd in spy_subprocess)


# --- _download_chroma_store retries a partial download -------------------------

def _fake_gcloud_laying_down(stores, tmp_path, monkeypatch):
    """Patch subprocess.run to mimic `gcloud storage rsync -r <src> <dest>`:
    materialise the next store spec from `stores` (a list of make_store kwargs, or
    'fail' for a non-zero exit) *at the destination path in the command* — so a
    regression to `cp -r <src> <parent>` writes to the wrong place and is caught.
    Returns the call counter list."""
    import pathlib
    import shutil
    import subprocess

    calls = []

    def fake_run(cmd, *args, **kwargs):
        calls.append(cmd)
        spec = stores[min(len(calls) - 1, len(stores) - 1)]
        if spec == "fail":
            return subprocess.CompletedProcess(cmd, 1, stdout="", stderr="boom")
        dest = pathlib.Path(cmd[-1])
        if dest.exists():
            shutil.rmtree(dest)
        make_store(dest, **spec)
        return subprocess.CompletedProcess(cmd, 0, stdout="", stderr="")

    monkeypatch.setattr("subprocess.run", fake_run)
    return calls


def test_download_retries_until_store_is_complete(tmp_path, monkeypatch):
    calls = _fake_gcloud_laying_down(
        [{"with_segment_bin": False}, {"n_vectors": 49_544}], tmp_path, monkeypatch
    )
    local = str(tmp_path / "chroma_store_gemini")

    n = _download_chroma_store("gs://bucket/chroma_store_gemini", local)

    assert n == 49_544
    assert len(calls) == 2


def test_download_raises_after_exhausting_attempts(tmp_path, monkeypatch):
    calls = _fake_gcloud_laying_down([{"n_vectors": 1_169}], tmp_path, monkeypatch)
    local = str(tmp_path / "chroma_store_gemini")

    with pytest.raises(StoreIntegrityError):
        _download_chroma_store("gs://bucket/chroma_store_gemini", local, attempts=3)

    assert len(calls) == 3


def test_download_raises_on_persistent_gcloud_failure(tmp_path, monkeypatch):
    calls = _fake_gcloud_laying_down(["fail"], tmp_path, monkeypatch)
    local = str(tmp_path / "chroma_store_gemini")

    with pytest.raises(RuntimeError):
        _download_chroma_store("gs://bucket/chroma_store_gemini", local, attempts=3)

    assert len(calls) == 3
