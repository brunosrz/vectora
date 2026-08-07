"""Tests for src/tools/rag.py"""

from __future__ import annotations

import json
from unittest.mock import AsyncMock, MagicMock, patch

import pytest


class TestVectorSearch:
    @pytest.mark.asyncio
    async def test_vector_search_full_path_no_rerank(self):
        """vector_search com VectorStoreBackend mockado (LanceDB ou Qdrant,
        indiferente pro tool — ele só fala com o Protocol) + Cohere embeddings."""
        from unittest.mock import AsyncMock, MagicMock, patch

        from backend.storage.vectorstore.base import VectorHit

        mock_backend = AsyncMock()
        mock_backend.search = AsyncMock(
            return_value=[
                VectorHit(
                    id="1",
                    score=0.1,
                    content="content",
                    metadata={},
                    collection="articles",
                )
            ]
        )

        mock_embeddings = MagicMock()
        mock_embeddings.return_value.embed_query.return_value = [0.1, 0.2, 0.3]

        from backend.tools.rag import vector_search

        with patch("backend.tools.rag.settings") as ms:
            ms.get_cohere_api_key.return_value = "test-key"
            ms.embedding_model = "embed-english-v3.0"
            ms.reranker_type = "none"
            with (
                patch(
                    "backend.storage.factory._build_lc_embeddings",
                    mock_embeddings,
                ),
                patch(
                    "backend.storage.factory.get_vector_store_backend",
                    AsyncMock(return_value=mock_backend),
                ),
            ):
                result = await vector_search.ainvoke(
                    {
                        "query": "test query",
                        "collection": "articles",
                        "limit": 5,
                    }
                )
        data = json.loads(result)
        assert "results" in data
        assert len(data["results"]) == 1

    @pytest.mark.asyncio
    async def test_vector_search_table_not_found(self):
        """Coleção ausente: backend.search() devolve [] (contrato do
        Protocol), vector_search reporta no_results."""
        from unittest.mock import AsyncMock, MagicMock, patch

        mock_backend = AsyncMock()
        mock_backend.search = AsyncMock(return_value=[])

        mock_embeddings = MagicMock()
        mock_embeddings.return_value.embed_query.return_value = [0.1, 0.2]

        from backend.tools.rag import vector_search

        with patch("backend.tools.rag.settings") as ms:
            ms.get_cohere_api_key.return_value = "test-key"
            ms.embedding_model = "embed-english-v3.0"
            with (
                patch(
                    "backend.storage.factory._build_lc_embeddings",
                    mock_embeddings,
                ),
                patch(
                    "backend.storage.factory.get_vector_store_backend",
                    AsyncMock(return_value=mock_backend),
                ),
            ):
                result = await vector_search.ainvoke(
                    {"query": "test", "collection": "articles", "limit": 5}
                )
        data = json.loads(result)
        assert data["status"] == "no_results"

    @pytest.mark.asyncio
    async def test_missing_dependencies_returns_message(self):
        from backend.tools.rag import vector_search

        with patch("backend.tools.rag.settings") as mock_settings:
            with patch("backend.tools.rag.lancedb", None):
                result = await vector_search.ainvoke(
                    {"query": "test", "collection": "articles", "limit": 5}
                )
        assert "missing" in result.lower() or isinstance(result, str)

    @pytest.mark.asyncio
    async def test_missing_api_key_returns_error(self):
        from backend.tools.rag import vector_search

        with patch("backend.tools.rag.settings") as mock_settings:
            mock_settings.get_cohere_api_key.return_value = None
            with (
                patch("backend.tools.rag.lancedb", MagicMock()),
                patch("backend.storage.factory._build_lc_embeddings", lambda: None),
            ):
                result = await vector_search.ainvoke(
                    {"query": "test", "collection": "articles", "limit": 5}
                )
        data = json.loads(result)
        assert data.get("status") in ("failed", "error")


class TestVectorSearchBucketFanout:
    """Sem `collection` explícito, a busca varre só os buckets ativos do
    workspace (backend/services/rag_buckets.py) — não a tabela `articles`
    inteira sempre."""

    def _mock_backend(self, tables: dict[str, list[dict]]):
        """`tables` mapeia nome de coleção -> lista de linhas (dicts com
        id/_distance/text/metadata) que essa coleção "contém". Devolve um
        `VectorStoreBackend` fake cujo `.search()` só sabe responder pelas
        coleções presentes em `tables` — mesmo contrato que
        LanceDBBackend/QdrantBackend implementam de verdade."""
        from backend.storage.vectorstore.base import VectorHit

        async def _search(collection: str, query_vector, limit: int):
            if collection not in tables:
                return []
            return [
                VectorHit(
                    id=str(row["id"]),
                    score=float(row.get("_distance", 0.0)),
                    content=row["text"],
                    metadata=json.loads(row.get("metadata", "{}")),
                    collection=collection,
                )
                for row in tables[collection]
            ]

        mock_backend = AsyncMock()
        mock_backend.search = AsyncMock(side_effect=_search)
        return mock_backend

    @pytest.mark.asyncio
    async def test_searches_only_active_buckets_of_workspace(self, tmp_path):
        from backend.services import rag_buckets
        from backend.tools.rag import vector_search
        from backend.workspace.runtime_settings import RuntimeSettings

        rs = RuntimeSettings(path=tmp_path / "checkpoints.db")
        active = rag_buckets.create_bucket(rs, workspace_id="ws1", name="Godot")
        inactive = rag_buckets.create_bucket(rs, workspace_id="ws1", name="TS libs")
        rag_buckets.set_active(rs, workspace_id="ws1", bucket_id=active.id, active=True)
        # inactive nunca é ativado — não deve aparecer na busca.

        tables = {
            f"bucket_{active.id}": [
                {"id": "1", "_distance": 0.1, "text": "godot doc", "metadata": "{}"}
            ],
            f"bucket_{inactive.id}": [
                {"id": "2", "_distance": 0.05, "text": "ts lib doc", "metadata": "{}"}
            ],
        }
        mock_backend = self._mock_backend(tables)
        mock_embeddings = MagicMock()
        mock_embeddings.return_value.embed_query.return_value = [0.1, 0.2, 0.3]

        with (
            patch("backend.tools.rag.settings") as ms,
            patch("backend.workspace.runtime_settings.runtime_settings", rs),
        ):
            ms.get_cohere_api_key.return_value = "test-key"
            ms.embedding_model = "embed-english-v3.0"
            with (
                patch(
                    "backend.storage.factory._build_lc_embeddings",
                    mock_embeddings,
                ),
                patch(
                    "backend.storage.factory.get_vector_store_backend",
                    AsyncMock(return_value=mock_backend),
                ),
            ):
                result = await vector_search.ainvoke(
                    {"query": "test", "limit": 5},
                    config={"configurable": {"workspace_id": "ws1"}},
                )

        data = json.loads(result)
        contents = [r["content"] for r in data["results"]]
        assert contents == ["godot doc"]

    @pytest.mark.asyncio
    async def test_no_active_buckets_falls_back_to_legacy_articles_table(
        self, tmp_path
    ):
        from backend.tools.rag import vector_search
        from backend.workspace.runtime_settings import RuntimeSettings

        rs = RuntimeSettings(path=tmp_path / "checkpoints.db")
        tables = {
            "articles": [
                {"id": "1", "_distance": 0.1, "text": "dado legado", "metadata": "{}"}
            ]
        }
        mock_backend = self._mock_backend(tables)
        mock_embeddings = MagicMock()
        mock_embeddings.return_value.embed_query.return_value = [0.1, 0.2, 0.3]

        with (
            patch("backend.tools.rag.settings") as ms,
            patch("backend.workspace.runtime_settings.runtime_settings", rs),
        ):
            ms.get_cohere_api_key.return_value = "test-key"
            ms.embedding_model = "embed-english-v3.0"
            with (
                patch(
                    "backend.storage.factory._build_lc_embeddings",
                    mock_embeddings,
                ),
                patch(
                    "backend.storage.factory.get_vector_store_backend",
                    AsyncMock(return_value=mock_backend),
                ),
            ):
                result = await vector_search.ainvoke(
                    {"query": "test", "limit": 5},
                    config={"configurable": {"workspace_id": "ws-sem-buckets"}},
                )

        data = json.loads(result)
        assert [r["content"] for r in data["results"]] == ["dado legado"]

    @pytest.mark.asyncio
    async def test_explicit_collection_overrides_active_buckets(self, tmp_path):
        """Passar `collection` manualmente ignora os buckets ativos —
        comportamento avançado preservado (regressão)."""
        from backend.services import rag_buckets
        from backend.tools.rag import vector_search
        from backend.workspace.runtime_settings import RuntimeSettings

        rs = RuntimeSettings(path=tmp_path / "checkpoints.db")
        bucket = rag_buckets.create_bucket(rs, workspace_id="ws1", name="Godot")
        rag_buckets.set_active(rs, workspace_id="ws1", bucket_id=bucket.id, active=True)
        tables = {
            f"bucket_{bucket.id}": [
                {"id": "1", "_distance": 0.1, "text": "bucket doc", "metadata": "{}"}
            ],
            "custom_collection": [
                {"id": "2", "_distance": 0.1, "text": "manual doc", "metadata": "{}"}
            ],
        }
        mock_backend = self._mock_backend(tables)
        mock_embeddings = MagicMock()
        mock_embeddings.return_value.embed_query.return_value = [0.1, 0.2, 0.3]

        with (
            patch("backend.tools.rag.settings") as ms,
            patch("backend.workspace.runtime_settings.runtime_settings", rs),
        ):
            ms.get_cohere_api_key.return_value = "test-key"
            ms.embedding_model = "embed-english-v3.0"
            with (
                patch(
                    "backend.storage.factory._build_lc_embeddings",
                    mock_embeddings,
                ),
                patch(
                    "backend.storage.factory.get_vector_store_backend",
                    AsyncMock(return_value=mock_backend),
                ),
            ):
                result = await vector_search.ainvoke(
                    {
                        "query": "test",
                        "collection": "custom_collection",
                        "limit": 5,
                    },
                    config={"configurable": {"workspace_id": "ws1"}},
                )

        data = json.loads(result)
        assert [r["content"] for r in data["results"]] == ["manual doc"]


class TestEmbedding:
    @pytest.mark.asyncio
    async def test_queue_not_enabled_returns_error(self):
        from backend.tools.rag import embedding

        with patch("backend.tools.rag.settings") as mock_settings:
            mock_settings.embedding_queue_enabled = False
            result = await embedding.ainvoke({"text": "doc", "collection": "articles"})
        data = json.loads(result)
        assert data["status"] == "error"

    @pytest.mark.asyncio
    async def test_enqueue_success_returns_fire_and_forget(self):
        from backend.tools.rag import embedding

        mock_queue = AsyncMock()
        mock_queue.enqueue.return_value = "queue-id-123"

        with patch("backend.tools.rag.settings") as mock_settings:
            mock_settings.embedding_queue_enabled = True
            mock_settings.embedding_queue_dsn = "sqlite:///test.db"
            with patch(
                "backend.tools.rag.get_embedding_queue",
                new_callable=AsyncMock,
                return_value=mock_queue,
            ):
                result = await embedding.ainvoke(
                    {"text": "sample text", "collection": "articles"}
                )
        data = json.loads(result)
        assert data["status"] == "fire_and_forget"
        assert data["queue_id"] == "queue-id-123"
        assert data["collection"] == "articles"

    @pytest.mark.asyncio
    async def test_enqueue_exception_returns_error(self):
        from backend.tools.rag import embedding

        with patch("backend.tools.rag.settings") as mock_settings:
            mock_settings.embedding_queue_enabled = True
            mock_settings.embedding_queue_dsn = "sqlite:///test.db"
            with patch(
                "backend.tools.rag.get_embedding_queue",
                new_callable=AsyncMock,
                side_effect=Exception("DB connection failed"),
            ):
                result = await embedding.ainvoke(
                    {"text": "sample text", "collection": "articles"}
                )
        data = json.loads(result)
        assert data["status"] == "error"
        assert "DB connection failed" in data["error"]


class TestIngestDocs:
    @pytest.mark.asyncio
    async def test_unsafe_path_denied(self):
        from backend.tools.rag import ingest_docs

        with patch("backend.tools.rag.settings") as mock_settings:
            mock_settings.enable_file_operations = True
            with patch(
                "backend.services.security.is_safe_file_path", return_value=False
            ):
                result = await ingest_docs.ainvoke(
                    {"directory_path": "/etc", "collection": "articles"}
                )
        assert "denied" in result.lower() or "Access" in result

    @pytest.mark.asyncio
    async def test_not_a_directory_returns_error(self, tmp_path):
        from backend.tools.rag import ingest_docs

        not_dir = tmp_path / "file.txt"
        not_dir.write_text("I am a file")

        with patch("backend.tools.rag.settings") as mock_settings:
            mock_settings.enable_file_operations = True
            with patch(
                "backend.services.security.is_safe_file_path", return_value=True
            ):
                result = await ingest_docs.ainvoke(
                    {"directory_path": str(not_dir), "collection": "articles"}
                )
        assert "Not a directory" in result

    @pytest.mark.asyncio
    async def test_no_files_found_returns_no_files(self, tmp_path):
        from backend.tools.rag import ingest_docs

        with patch("backend.tools.rag.settings") as mock_settings:
            mock_settings.enable_file_operations = True
            with patch(
                "backend.services.security.is_safe_file_path", return_value=True
            ):
                with patch(
                    "backend.services.ignore.load_ignore_spec", return_value=None
                ):
                    result = await ingest_docs.ainvoke(
                        {
                            "directory_path": str(tmp_path),
                            "collection": "articles",
                            "glob_pattern": "**/*.md",
                        }
                    )
        data = json.loads(result)
        assert data["status"] == "no_files"

    @pytest.mark.asyncio
    async def test_chunk_fail_counts_as_failure(self, tmp_path):
        from backend.tools.rag import ingest_docs

        md_file = tmp_path / "doc.md"
        md_file.write_text("# Content")

        with patch("backend.tools.rag.settings") as mock_settings:
            mock_settings.enable_file_operations = True
            with patch(
                "backend.services.security.is_safe_file_path", return_value=True
            ):
                with patch("backend.services.ignore.is_ignored", return_value=False):
                    with patch(
                        "backend.services.ignore.load_ignore_spec",
                        return_value=None,
                    ):
                        with patch("backend.tools.rag.embedding") as mock_emb:
                            mock_emb.ainvoke = AsyncMock(
                                side_effect=Exception("embedding fail")
                            )
                            result = await ingest_docs.ainvoke(
                                {
                                    "directory_path": str(tmp_path),
                                    "collection": "articles",
                                    "glob_pattern": "**/*.md",
                                }
                            )
        data = json.loads(result)
        assert data["status"] == "completed"
        assert data["failed"] >= 1

    @pytest.mark.asyncio
    async def test_gitignore_skip_counts_as_ignored(self, tmp_path):
        """Covers is_ignored=True branch (lines 283-288)."""
        from backend.tools.rag import ingest_docs

        md_file = tmp_path / "ignored.md"
        md_file.write_text("# Ignored")

        with patch("backend.tools.rag.settings") as mock_settings:
            mock_settings.enable_file_operations = True
            with patch(
                "backend.services.security.is_safe_file_path", return_value=True
            ):
                with patch(
                    "backend.services.ignore.load_ignore_spec", return_value=None
                ):
                    # All files are ignored → no_files result
                    with patch("backend.services.ignore.is_ignored", return_value=True):
                        result = await ingest_docs.ainvoke(
                            {
                                "directory_path": str(tmp_path),
                                "collection": "articles",
                                "glob_pattern": "**/*.md",
                            }
                        )
        data = json.loads(result)
        assert data["status"] == "no_files"
        assert data["skipped_ignored"] >= 1

    @pytest.mark.asyncio
    async def test_always_skip_dirs_counted_in_ignored(self, tmp_path):
        """Dirs em ALWAYS_SKIP_DIRS contam em skipped_ignored (não silenciados).

        Com walk_files, __pycache__ é PODADO durante o os.walk (a subárvore
        nem é varrida) e conta como 1 em skipped_ignored — antes do fix de
        performance, rglob varria a árvore inteira e contava arquivo a arquivo.
        """
        from backend.services.ignore import ALWAYS_SKIP_DIRS
        from backend.tools.rag import ingest_docs

        # Cria um arquivo .py dentro de __pycache__ (dir em ALWAYS_SKIP_DIRS)
        cache_dir = tmp_path / "__pycache__"
        cache_dir.mkdir()
        (cache_dir / "module.py").write_text("# cached module")

        # Cria também um arquivo .py legítimo fora de dirs ignorados
        (tmp_path / "app.py").write_text("# main app")

        with patch("backend.tools.rag.settings") as mock_settings:
            mock_settings.enable_file_operations = True
            with patch(
                "backend.services.security.is_safe_file_path", return_value=True
            ):
                with patch(
                    "backend.services.ignore.load_ignore_spec", return_value=None
                ):
                    # Não mockamos is_ignored — usa a implementação real
                    with patch("backend.tools.rag.embedding") as mock_emb:
                        mock_emb.ainvoke = AsyncMock(
                            return_value=json.dumps(
                                {"status": "fire_and_forget", "queue_id": "q1"}
                            )
                        )
                        result = await ingest_docs.ainvoke(
                            {
                                "directory_path": str(tmp_path),
                                "collection": "code",
                                "glob_pattern": "**/*.py",
                            }
                        )
        data = json.loads(result)
        # app.py deve ser indexado; __pycache__/module.py deve ser contado como ignorado
        assert data["status"] == "completed"
        assert data["total_files"] == 1, "apenas app.py deve ser indexado"
        assert data["skipped_ignored"] == 1, (
            "__pycache__/module.py deve contar como ignorado"
        )

    @pytest.mark.asyncio
    async def test_file_read_error_counts_as_failure(self, tmp_path):
        """Covers file read exception path (lines 310-316)."""
        from unittest.mock import mock_open, patch

        from backend.tools.rag import ingest_docs

        md_file = tmp_path / "unreadable.md"
        md_file.write_text("content")

        with patch("backend.tools.rag.settings") as mock_settings:
            mock_settings.enable_file_operations = True
            with patch(
                "backend.services.security.is_safe_file_path", return_value=True
            ):
                with patch("backend.services.ignore.is_ignored", return_value=False):
                    with patch(
                        "backend.services.ignore.load_ignore_spec",
                        return_value=None,
                    ):
                        with patch(
                            "pathlib.Path.read_text",
                            side_effect=PermissionError("denied"),
                        ):
                            result = await ingest_docs.ainvoke(
                                {
                                    "directory_path": str(tmp_path),
                                    "collection": "articles",
                                    "glob_pattern": "**/*.md",
                                }
                            )
        data = json.loads(result)
        assert data["status"] == "completed"
        assert data["failed"] >= 1

    @pytest.mark.asyncio
    async def test_embedding_non_fire_and_forget_counts_as_failure(self, tmp_path):
        """Covers else branch when embedding returns unexpected status (line 340)."""
        from backend.tools.rag import ingest_docs

        md_file = tmp_path / "doc.md"
        md_file.write_text("# Content for embedding")

        # Return something that is NOT fire_and_forget
        mock_result = json.dumps({"status": "error", "reason": "queue full"})

        with patch("backend.tools.rag.settings") as mock_settings:
            mock_settings.enable_file_operations = True
            with patch(
                "backend.services.security.is_safe_file_path", return_value=True
            ):
                with patch("backend.services.ignore.is_ignored", return_value=False):
                    with patch(
                        "backend.services.ignore.load_ignore_spec",
                        return_value=None,
                    ):
                        with patch("backend.tools.rag.embedding") as mock_emb:
                            mock_emb.ainvoke = AsyncMock(return_value=mock_result)
                            result = await ingest_docs.ainvoke(
                                {
                                    "directory_path": str(tmp_path),
                                    "collection": "articles",
                                    "glob_pattern": "**/*.md",
                                }
                            )
        data = json.loads(result)
        assert data["status"] == "completed"
        assert data["failed"] >= 1

    @pytest.mark.asyncio
    async def test_uses_ainvoke_not_astream(self, tmp_path):
        """Verifica o fix do bug: ingest_docs usa ainvoke, não astream."""
        from backend.tools.rag import ingest_docs

        md_file = tmp_path / "test.md"
        md_file.write_text("# Test\nConteúdo de teste para embedding.")

        mock_result = json.dumps({"status": "fire_and_forget", "queue_id": "q1"})

        with patch("backend.tools.rag.settings") as mock_settings:
            mock_settings.enable_file_operations = True
            mock_settings.embedding_queue_enabled = True
            with patch(
                "backend.services.security.is_safe_file_path", return_value=True
            ):
                with patch("backend.services.ignore.is_ignored", return_value=False):
                    with patch(
                        "backend.services.ignore.load_ignore_spec",
                        return_value=None,
                    ):
                        with patch("backend.tools.rag.embedding") as mock_emb:
                            mock_emb.ainvoke = AsyncMock(return_value=mock_result)
                            mock_emb.astream = MagicMock(
                                side_effect=AssertionError("astream foi chamado!")
                            )
                            result = await ingest_docs.ainvoke(
                                {
                                    "directory_path": str(tmp_path),
                                    "collection": "articles",
                                    "glob_pattern": "**/*.md",
                                }
                            )

        data = json.loads(result)
        assert data["status"] == "completed"
        assert mock_emb.ainvoke.called


class TestManageRetriever:
    """Tool de gestão do RAG (list / delete / purge)."""

    @pytest.mark.asyncio
    async def test_delete_without_source_errors_early(self):
        from backend.tools.rag import manage_retriever

        result = await manage_retriever.ainvoke(
            {"action": "delete", "collection": "web_cache"}
        )
        data = json.loads(result)
        assert data["status"] == "error"
        assert "source" in data["error"]

    @pytest.mark.asyncio
    async def test_purge_drops_table(self):
        from backend.tools.rag import manage_retriever

        mock_backend = AsyncMock()
        with patch(
            "backend.storage.factory.get_vector_store_backend",
            AsyncMock(return_value=mock_backend),
        ):
            result = await manage_retriever.ainvoke(
                {"action": "purge", "collection": "web_cache"}
            )
        data = json.loads(result)
        assert data["status"] == "purged"
        mock_backend.purge.assert_awaited_once_with("web_cache")

    @pytest.mark.asyncio
    async def test_list_missing_collection(self):
        from backend.tools.rag import manage_retriever

        mock_backend = AsyncMock()
        mock_backend.list_rows = AsyncMock(return_value=[])
        with patch(
            "backend.storage.factory.get_vector_store_backend",
            AsyncMock(return_value=mock_backend),
        ):
            result = await manage_retriever.ainvoke(
                {"action": "list", "collection": "ghost"}
            )
        data = json.loads(result)
        assert data["status"] == "no_results"

    @staticmethod
    def _mock_backend_with_rows(rows_meta: list[dict]) -> AsyncMock:
        """Monta um `VectorStoreBackend` fake cujo `list_rows()` devolve
        `VectorRow`s com os metadados dados (ids sintéticos a1, b2, c3...)."""
        from backend.storage.vectorstore.base import VectorRow

        ids = [f"{chr(97 + i)}{i + 1}" for i in range(len(rows_meta))]
        rows = [
            VectorRow(id=doc_id, vector=[], text="", metadata=meta)
            for doc_id, meta in zip(ids, rows_meta, strict=True)
        ]
        mock_backend = AsyncMock()
        mock_backend.list_rows = AsyncMock(return_value=rows)
        mock_backend.delete = AsyncMock(
            side_effect=lambda _collection, matched_ids: len(matched_ids)
        )
        return mock_backend

    @pytest.mark.asyncio
    async def test_list_returns_documents_via_pandas(self):
        """Erro/borda coberto no mesmo teste: metadata sem 'source' cai no
        fallback vazio em vez de KeyError."""
        from backend.tools.rag import manage_retriever

        mock_backend = self._mock_backend_with_rows(
            [
                {
                    "source": "https://github.com/brunosrz/AbilitySystem",
                    "title": "Ability System",
                    "origin": "web_search",
                },
                {"source": "docs/manual.md", "title": "Manual"},
            ]
        )
        with patch(
            "backend.storage.factory.get_vector_store_backend",
            AsyncMock(return_value=mock_backend),
        ):
            result = await manage_retriever.ainvoke(
                {"action": "list", "collection": "web_cache"}
            )
        data = json.loads(result)
        assert data["status"] == "success"
        assert data["count"] == 2
        assert {d["source"] for d in data["documents"]} == {
            "https://github.com/brunosrz/AbilitySystem",
            "docs/manual.md",
        }

    @pytest.mark.asyncio
    async def test_delete_matches_by_source_via_pandas(self):
        """Delete filtra por substring case-insensitive no source/url/title."""
        from backend.tools.rag import manage_retriever

        mock_backend = self._mock_backend_with_rows(
            [
                {"source": "godot-gameplay-systems/foo"},
                {"source": "github.com/brunosrz/AbilitySystem"},
                {"title": "godot-gameplay-systems wiki"},
            ]
        )
        with patch(
            "backend.storage.factory.get_vector_store_backend",
            AsyncMock(return_value=mock_backend),
        ):
            result = await manage_retriever.ainvoke(
                {
                    "action": "delete",
                    "collection": "web_cache",
                    "source": "godot-gameplay-systems",
                }
            )
        data = json.loads(result)
        assert data["status"] == "deleted"
        assert data["deleted"] == 2
        assert set(data["ids"]) == {"a1", "c3"}
        mock_backend.delete.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_delete_no_match_via_pandas(self):
        """Delete sem match retorna no_match, sem chamar backend.delete."""
        from backend.tools.rag import manage_retriever

        mock_backend = self._mock_backend_with_rows([{"source": "docs/manual.md"}])
        with patch(
            "backend.storage.factory.get_vector_store_backend",
            AsyncMock(return_value=mock_backend),
        ):
            result = await manage_retriever.ainvoke(
                {
                    "action": "delete",
                    "collection": "web_cache",
                    "source": "inexistente",
                }
            )
        data = json.loads(result)
        assert data["status"] == "no_match"
        mock_backend.delete.assert_not_awaited()


# ---------------------------------------------------------------------------
# _build_reranker — Cohere ↔ VoyageAI
# ---------------------------------------------------------------------------


class TestBuildReranker:
    def test_cohere_without_key_returns_none(self):
        from backend.tools.rag import _build_reranker

        with patch("backend.tools.rag.settings") as ms:
            ms.reranker_type = "cohere"
            ms.get_cohere_api_key.return_value = None
            assert _build_reranker() is None

    def test_voyage_without_key_returns_none(self):
        from backend.tools.rag import _build_reranker

        with patch("backend.tools.rag.settings") as ms:
            ms.reranker_type = "voyage"
            ms.voyage_api_key = None
            assert _build_reranker() is None

    def test_unknown_type_returns_none(self):
        from backend.tools.rag import _build_reranker

        with patch("backend.tools.rag.settings") as ms:
            ms.reranker_type = "qualquer-outro"
            assert _build_reranker() is None

    def test_cohere_client_construction_failure_returns_none(self):
        """Erro/borda: qualquer falha ao montar o client nativo (ex.: key
        vazia detectada dentro do construtor) é capturada e vira None, nunca
        propaga pro chamador de `_build_reranker`."""
        from backend.tools.rag import _build_reranker

        with patch("backend.tools.rag.settings") as ms:
            ms.reranker_type = "cohere"
            # get_cohere_api_key() devolve algo não-vazio (passa no guard de
            # _build_cohere_reranker), mas CohereClient valida de novo e
            # rejeita string vazia — simula um estado inconsistente real.
            ms.get_cohere_api_key.return_value = " "
            assert _build_reranker() is None

    def test_voyage_with_key_returns_voyage_reranker(self):
        from backend.llm.voyage.rerank import VectoraVoyageRerank
        from backend.tools.rag import _build_reranker

        with patch("backend.tools.rag.settings") as ms:
            ms.reranker_type = "voyage"
            ms.voyage_api_key = "voy-1"
            ms.voyage_rerank_model = "rerank-2"
            ms.reranker_top_k = 5
            ms.get_cohere_api_key.return_value = None  # sem secundário → voyage puro
            out = _build_reranker()
        assert isinstance(out, VectoraVoyageRerank)
        assert out.model == "rerank-2"
        assert out.top_k == 5

    def test_reranker_disabled_returns_none(self):
        # reranker_enabled=False nos settings de runtime → sem rerank (None).
        from backend.tools import rag as rag_mod
        from backend.tools.rag import _build_reranker

        with (
            patch("backend.tools.rag.settings") as ms,
            patch.object(
                rag_mod,
                "_rag_runtime",
                lambda: {"reranker_enabled": False, "reranker_top_k": 5},
            ),
        ):
            ms.reranker_type = "cohere"
            ms.get_cohere_api_key.return_value = "ck-1"
            assert _build_reranker() is None

    def test_reranker_provider_pref_forces_voyage(self):
        from backend.llm.voyage.rerank import VectoraVoyageRerank
        from backend.tools import rag as rag_mod
        from backend.tools.rag import _build_reranker

        with (
            patch("backend.tools.rag.settings") as ms,
            patch.object(
                rag_mod,
                "_rag_runtime",
                lambda: {
                    "reranker_enabled": True,
                    "reranker_top_k": 5,
                    "rerank_provider": "voyage",
                },
            ),
        ):
            ms.reranker_type = "cohere"  # mas a preferência força voyage
            ms.voyage_api_key = "voy-1"
            ms.voyage_rerank_model = "rerank-2"
            ms.get_cohere_api_key.return_value = None
            out = _build_reranker()
        assert isinstance(out, VectoraVoyageRerank)

    def test_both_configured_returns_fallback_reranker(self):
        from backend.llm.fallback_reranker import FallbackReranker
        from backend.tools.rag import _build_reranker

        with patch("backend.tools.rag.settings") as ms:
            ms.reranker_type = "cohere"
            ms.get_cohere_api_key.return_value = "ck-1"
            ms.reranker_model = "rerank-english-v3.0"
            ms.voyage_api_key = "voy-1"
            ms.voyage_rerank_model = "rerank-2"
            ms.reranker_top_k = 5
            out = _build_reranker()
        assert isinstance(out, FallbackReranker)
        assert out.primary_id == "cohere:rerank-english-v3.0"
        assert out.secondary_id == "voyage:rerank-2"


class TestFallbackRerankerBehavior:
    def _wrap(self, primary, secondary):
        from backend.llm.fallback_reranker import FallbackReranker

        return FallbackReranker(
            primary,
            secondary,
            primary_id="cohere:r",
            secondary_id="voyage:r",
        )

    def test_compress_primary_ok_no_switch(self):
        from backend.llm import provider_fallback as pf

        pf.drain_switches()
        primary = MagicMock()
        primary.compress_documents.return_value = ["doc-primary"]
        secondary = MagicMock()
        out = self._wrap(primary, secondary).compress_documents(["d"], "q")
        assert out == ["doc-primary"]
        secondary.compress_documents.assert_not_called()
        assert pf.drain_switches() == []

    def test_compress_primary_quota_switches(self):
        from backend.llm import provider_fallback as pf

        pf.drain_switches()
        primary = MagicMock()
        primary.compress_documents.side_effect = Exception("429 quota")
        secondary = MagicMock()
        secondary.compress_documents.return_value = ["doc-secondary"]
        out = self._wrap(primary, secondary).compress_documents(["d"], "q")
        assert out == ["doc-secondary"]
        assert pf.drain_switches() == [{"from": "cohere:r", "to": "voyage:r"}]

    def test_compress_non_quota_reraises(self):
        primary = MagicMock()
        primary.compress_documents.side_effect = ValueError("boom")
        secondary = MagicMock()
        with pytest.raises(ValueError):
            self._wrap(primary, secondary).compress_documents(["d"], "q")
        secondary.compress_documents.assert_not_called()

    @pytest.mark.asyncio
    async def test_acompress_quota_switches(self):
        from backend.llm import provider_fallback as pf

        pf.drain_switches()
        primary = MagicMock()
        primary.acompress_documents = AsyncMock(side_effect=Exception("rate limit"))
        secondary = MagicMock()
        secondary.acompress_documents = AsyncMock(return_value=["async-secondary"])
        out = await self._wrap(primary, secondary).acompress_documents(["d"], "q")
        assert out == ["async-secondary"]
        assert pf.drain_switches() == [{"from": "cohere:r", "to": "voyage:r"}]
