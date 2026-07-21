"""Memory Library — download/publish de buckets RAG compartilhados.

download_memory_bucket: valida embed_model ANTES de tocar em qualquer
arquivo (nunca mistura dimensões de vetor silenciosamente); publish_memory_bucket:
empacota a coleção local e publica via multipart.
"""

from __future__ import annotations

import io
import tarfile

import httpx
import pytest

from backend.services.memory_library import (
    MemoryLibraryError,
    download_memory_bucket,
    publish_memory_bucket,
)


def _catalog_response(entries: list[dict]) -> httpx.Response:
    return httpx.Response(
        200, json=entries, request=httpx.Request("GET", "https://x/rag-library/")
    )


def _make_tar_gz(files: dict[str, bytes]) -> bytes:
    buf = io.BytesIO()
    with tarfile.open(fileobj=buf, mode="w:gz") as tar:
        for name, content in files.items():
            info = tarfile.TarInfo(name=name)
            info.size = len(content)
            tar.addfile(info, io.BytesIO(content))
    return buf.getvalue()


@pytest.mark.asyncio
async def test_download_incompatible_embed_model_raises_before_touching_files(
    tmp_path, monkeypatch
):
    async def _fake_get(self, url, **kwargs):
        assert "download" not in url  # nunca chega a baixar o arquivo
        return _catalog_response(
            [{"id": "b1", "embed_model": "voyage-3", "name": "Bucket 1"}]
        )

    monkeypatch.setattr(httpx.AsyncClient, "get", _fake_get)
    monkeypatch.setattr(
        "backend.settings.settings.embedding_model", "embed-multilingual-v3.0"
    )

    with pytest.raises(MemoryLibraryError, match="embedder"):
        await download_memory_bucket("b1", lancedb_dir=tmp_path)

    assert list(tmp_path.iterdir()) == []


@pytest.mark.asyncio
async def test_download_bucket_not_found_raises_clear_error(monkeypatch, tmp_path):
    async def _fake_get(self, url, **kwargs):
        return _catalog_response([])

    monkeypatch.setattr(httpx.AsyncClient, "get", _fake_get)

    with pytest.raises(MemoryLibraryError, match="não encontrado"):
        await download_memory_bucket("missing", lancedb_dir=tmp_path)


@pytest.mark.asyncio
async def test_download_compatible_bucket_extracts_into_isolated_collection(
    tmp_path, monkeypatch
):
    archive = _make_tar_gz({"data.lance": b"fake lance content"})
    call_log: list[str] = []

    async def _fake_get(self, url, **kwargs):
        call_log.append(url)
        if url.endswith("/rag-library/"):
            return _catalog_response(
                [{"id": "b1", "embed_model": "embed-multilingual-v3.0", "name": "b1"}]
            )
        return httpx.Response(200, content=archive, request=httpx.Request("GET", url))

    monkeypatch.setattr(httpx.AsyncClient, "get", _fake_get)
    monkeypatch.setattr(
        "backend.settings.settings.embedding_model", "embed-multilingual-v3.0"
    )
    monkeypatch.setattr("backend.settings.settings.lancedb_dir", None)

    # Erro/borda: coleção do usuário já existente com outro nome não pode
    # ser tocada — só a nova pasta isolada `shared_b1` é criada.
    (tmp_path / "meu_workspace_local").mkdir()

    collection = await download_memory_bucket("b1", lancedb_dir=tmp_path)

    assert collection == "shared_b1"
    assert (tmp_path / "shared_b1" / "data.lance").is_file()
    assert (tmp_path / "meu_workspace_local").is_dir()
    assert list((tmp_path / "meu_workspace_local").iterdir()) == []


@pytest.mark.asyncio
async def test_publish_missing_local_workspace_raises_clear_error(tmp_path):
    with pytest.raises(MemoryLibraryError, match="não tem coleção"):
        await publish_memory_bucket(
            "nonexistent-ws",
            "Nome",
            "Descrição",
            "MIT",
            session_token="tok",
            lancedb_dir=tmp_path,
        )


@pytest.mark.asyncio
async def test_publish_success_returns_bucket_id(tmp_path, monkeypatch):
    ws_dir = tmp_path / "ws1"
    ws_dir.mkdir()
    (ws_dir / "table.lance").write_bytes(b"data")

    captured: dict = {}

    async def _fake_post(self, url, **kwargs):
        captured["headers"] = kwargs.get("headers")
        captured["data"] = kwargs.get("data")
        return httpx.Response(
            200,
            json={"ok": True, "id": "new-bucket-id", "verified": False},
            request=httpx.Request("POST", url),
        )

    monkeypatch.setattr(httpx.AsyncClient, "post", _fake_post)
    monkeypatch.setattr(
        "backend.settings.settings.embedding_model", "embed-multilingual-v3.0"
    )

    bucket_id = await publish_memory_bucket(
        "ws1",
        "Meu bucket",
        "descrição",
        "MIT",
        session_token="tok123",
        lancedb_dir=tmp_path,
    )

    assert bucket_id == "new-bucket-id"
    assert captured["headers"]["Authorization"] == "Bearer tok123"
    assert captured["data"]["embed_model"] == "embed-multilingual-v3.0"


@pytest.mark.asyncio
async def test_publish_network_failure_raises_memory_library_error(
    tmp_path, monkeypatch
):
    ws_dir = tmp_path / "ws1"
    ws_dir.mkdir()
    (ws_dir / "table.lance").write_bytes(b"data")

    async def _fake_post(self, url, **kwargs):
        raise httpx.ConnectError("offline")

    monkeypatch.setattr(httpx.AsyncClient, "post", _fake_post)

    with pytest.raises(MemoryLibraryError, match="Falha ao publicar"):
        await publish_memory_bucket(
            "ws1", "n", "d", "MIT", session_token="tok", lancedb_dir=tmp_path
        )
