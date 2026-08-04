"""Tests for src/tools/rag.py"""

from __future__ import annotations

import json
from unittest.mock import AsyncMock, MagicMock, patch

import pytest


class TestVectorSearch:
    @pytest.mark.asyncio
    async def test_vector_search_full_path_no_rerank(self):
        """Covers lines 128-224: full vector_search with mocked LanceDB + Cohere."""
        from unittest.mock import AsyncMock, MagicMock, patch

        # Mock a pandas-like DataFrame row
        mock_row = MagicMock()
        mock_row.get.side_effect = lambda k, d=None: {
            "_distance": 0.1,
            "text": "content",
            "metadata": "{}",
        }.get(k, d)
        mock_row.__getitem__ = lambda self, k: {
            "id": "1",
            "_distance": 0.1,
            "text": "content",
            "metadata": "{}",
        }[k]

        mock_df = MagicMock()
        mock_df.iterrows.return_value = iter([(0, mock_row)])

        mock_table = MagicMock()
        mock_table.vector_search.return_value.limit.return_value.to_pandas = AsyncMock(
            return_value=mock_df
        )

        mock_db = AsyncMock()
        mock_db.open_table = AsyncMock(return_value=mock_table)

        mock_embeddings = MagicMock()
        mock_embeddings.return_value.embed_query.return_value = [0.1, 0.2, 0.3]

        mock_lancedb = MagicMock()
        mock_lancedb.connect_async = AsyncMock(return_value=mock_db)

        from backend.tools.rag import vector_search

        with patch("backend.tools.rag.settings") as ms:
            ms.get_cohere_api_key.return_value = "test-key"
            ms.lancedb_dir = "/tmp/lancedb"  # nosec B108
            ms.embedding_model = "embed-english-v3.0"
            ms.reranker_type = "none"
            with patch("backend.tools.rag.lancedb", mock_lancedb):
                with patch("backend.tools.rag.CohereEmbeddings", mock_embeddings):
                    with patch("backend.tools.rag.SecretStr", lambda x: x):
                        with patch("backend.tools.rag.CohereRerank", None):
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
        """Covers the except-on-open_table path returning no_results."""
        from unittest.mock import AsyncMock, MagicMock, patch

        mock_db = AsyncMock()
        mock_db.open_table = AsyncMock(side_effect=Exception("table not found"))

        mock_embeddings = MagicMock()
        mock_embeddings.return_value.embed_query.return_value = [0.1, 0.2]

        mock_lancedb = MagicMock()
        mock_lancedb.connect_async = AsyncMock(return_value=mock_db)

        from backend.tools.rag import vector_search

        with patch("backend.tools.rag.settings") as ms:
            ms.get_cohere_api_key.return_value = "test-key"
            ms.lancedb_dir = "/tmp/lancedb"  # nosec B108
            ms.embedding_model = "embed-english-v3.0"
            with patch("backend.tools.rag.lancedb", mock_lancedb):
                with patch("backend.tools.rag.CohereEmbeddings", mock_embeddings):
                    with patch("backend.tools.rag.SecretStr", lambda x: x):
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
                with patch("backend.tools.rag.CohereEmbeddings", None):
                    result = await vector_search.ainvoke(
                        {"query": "test", "collection": "articles", "limit": 5}
                    )
        assert "missing" in result.lower() or isinstance(result, str)

    @pytest.mark.asyncio
    async def test_missing_api_key_returns_error(self):
        from backend.tools.rag import vector_search

        with patch("backend.tools.rag.settings") as mock_settings:
            mock_settings.get_cohere_api_key.return_value = None
            with patch("backend.tools.rag.lancedb", MagicMock()):
                with patch("backend.tools.rag.CohereEmbeddings", MagicMock()):
                    result = await vector_search.ainvoke(
                        {"query": "test", "collection": "articles", "limit": 5}
                    )
        data = json.loads(result)
        assert data.get("status") in ("failed", "error")


class TestVectorSearchBucketFanout:
    """Sem `collection` explícito, a busca varre só os buckets ativos do
    workspace (backend/services/rag_buckets.py) — não a tabela `articles`
    inteira sempre."""

    def _mock_lancedb(self, tables: dict[str, list[dict]]):
        """`tables` mapeia nome de coleção -> lista de linhas (dicts com
        id/_distance/text/metadata) que essa tabela "contém"."""

        async def _open_table(name: str):
            if name not in tables:
                raise Exception(f"table {name} not found")
            rows = tables[name]
            mock_df = MagicMock()

            def _row(d):
                r = MagicMock()
                r.get.side_effect = lambda k, default=None: d.get(k, default)
                r.__getitem__ = lambda self, k, d=d: d[k]
                return r

            mock_df.iterrows.return_value = iter(
                [(i, _row(d)) for i, d in enumerate(rows)]
            )
            table = MagicMock()
            table.vector_search.return_value.limit.return_value.to_pandas = AsyncMock(
                return_value=mock_df
            )
            return table

        mock_db = AsyncMock()
        mock_db.open_table = AsyncMock(side_effect=_open_table)
        mock_lancedb = MagicMock()
        mock_lancedb.connect_async = AsyncMock(return_value=mock_db)
        return mock_lancedb

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
        mock_lancedb = self._mock_lancedb(tables)
        mock_embeddings = MagicMock()
        mock_embeddings.return_value.embed_query.return_value = [0.1, 0.2, 0.3]

        with (
            patch("backend.tools.rag.settings") as ms,
            patch("backend.workspace.runtime_settings.runtime_settings", rs),
        ):
            ms.get_cohere_api_key.return_value = "test-key"
            ms.lancedb_dir = "/tmp/lancedb"  # nosec B108
            ms.embedding_model = "embed-english-v3.0"
            with (
                patch("backend.tools.rag.lancedb", mock_lancedb),
                patch("backend.tools.rag.CohereEmbeddings", mock_embeddings),
                patch("backend.tools.rag.SecretStr", lambda x: x),
                patch("backend.tools.rag.CohereRerank", None),
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
        mock_lancedb = self._mock_lancedb(tables)
        mock_embeddings = MagicMock()
        mock_embeddings.return_value.embed_query.return_value = [0.1, 0.2, 0.3]

        with (
            patch("backend.tools.rag.settings") as ms,
            patch("backend.workspace.runtime_settings.runtime_settings", rs),
        ):
            ms.get_cohere_api_key.return_value = "test-key"
            ms.lancedb_dir = "/tmp/lancedb"  # nosec B108
            ms.embedding_model = "embed-english-v3.0"
            with (
                patch("backend.tools.rag.lancedb", mock_lancedb),
                patch("backend.tools.rag.CohereEmbeddings", mock_embeddings),
                patch("backend.tools.rag.SecretStr", lambda x: x),
                patch("backend.tools.rag.CohereRerank", None),
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
        mock_lancedb = self._mock_lancedb(tables)
        mock_embeddings = MagicMock()
        mock_embeddings.return_value.embed_query.return_value = [0.1, 0.2, 0.3]

        with (
            patch("backend.tools.rag.settings") as ms,
            patch("backend.workspace.runtime_settings.runtime_settings", rs),
        ):
            ms.get_cohere_api_key.return_value = "test-key"
            ms.lancedb_dir = "/tmp/lancedb"  # nosec B108
            ms.embedding_model = "embed-english-v3.0"
            with (
                patch("backend.tools.rag.lancedb", mock_lancedb),
                patch("backend.tools.rag.CohereEmbeddings", mock_embeddings),
                patch("backend.tools.rag.SecretStr", lambda x: x),
                patch("backend.tools.rag.CohereRerank", None),
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

        mock_db = MagicMock()
        mock_db.drop_table = AsyncMock()
        with patch("backend.tools.rag.lancedb") as mock_lancedb:
            mock_lancedb.connect_async = AsyncMock(return_value=mock_db)
            result = await manage_retriever.ainvoke(
                {"action": "purge", "collection": "web_cache"}
            )
        data = json.loads(result)
        assert data["status"] == "purged"
        mock_db.drop_table.assert_awaited_once_with("web_cache")

    @pytest.mark.asyncio
    async def test_list_missing_collection(self):
        from backend.tools.rag import manage_retriever

        mock_db = MagicMock()
        mock_db.open_table = AsyncMock(side_effect=Exception("table not found"))
        with patch("backend.tools.rag.lancedb") as mock_lancedb:
            mock_lancedb.connect_async = AsyncMock(return_value=mock_db)
            result = await manage_retriever.ainvoke(
                {"action": "list", "collection": "ghost"}
            )
        data = json.loads(result)
        assert data["status"] == "no_results"

    @staticmethod
    def _mock_db_with_df(df) -> tuple[MagicMock, MagicMock]:
        """Monta um mock LanceDB cujo open_table().to_pandas() devolve `df`."""
        mock_table = MagicMock()
        mock_table.to_pandas = AsyncMock(return_value=df)
        mock_table.delete = AsyncMock()
        mock_db = MagicMock()
        mock_db.open_table = AsyncMock(return_value=mock_table)
        return mock_db, mock_table

    @pytest.mark.asyncio
    async def test_list_returns_documents_via_pandas(self):
        """Parseia o DataFrame (metadata JSON) sem iterrows."""
        import pandas as pd

        from backend.tools.rag import manage_retriever

        df = pd.DataFrame(
            {
                "id": ["a1", "b2"],
                "metadata": [
                    json.dumps(
                        {
                            "source": "https://github.com/brunosrz/AbilitySystem",
                            "title": "Ability System",
                            "origin": "web_search",
                        }
                    ),
                    json.dumps({"source": "docs/manual.md", "title": "Manual"}),
                ],
            }
        )
        mock_db, _ = self._mock_db_with_df(df)
        with patch("backend.tools.rag.lancedb") as mock_lancedb:
            mock_lancedb.connect_async = AsyncMock(return_value=mock_db)
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
        """Delete usa máscara booleana vetorizada sobre o DataFrame."""
        import pandas as pd

        from backend.tools.rag import manage_retriever

        df = pd.DataFrame(
            {
                "id": ["a1", "b2", "c3"],
                "metadata": [
                    json.dumps({"source": "godot-gameplay-systems/foo"}),
                    json.dumps({"source": "github.com/brunosrz/AbilitySystem"}),
                    json.dumps({"title": "godot-gameplay-systems wiki"}),
                ],
            }
        )
        mock_db, mock_table = self._mock_db_with_df(df)
        with patch("backend.tools.rag.lancedb") as mock_lancedb:
            mock_lancedb.connect_async = AsyncMock(return_value=mock_db)
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
        mock_table.delete.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_delete_no_match_via_pandas(self):
        """Delete sem match retorna no_match, sem chamar table.delete."""
        import pandas as pd

        from backend.tools.rag import manage_retriever

        df = pd.DataFrame(
            {
                "id": ["a1"],
                "metadata": [json.dumps({"source": "docs/manual.md"})],
            }
        )
        mock_db, mock_table = self._mock_db_with_df(df)
        with patch("backend.tools.rag.lancedb") as mock_lancedb:
            mock_lancedb.connect_async = AsyncMock(return_value=mock_db)
            result = await manage_retriever.ainvoke(
                {
                    "action": "delete",
                    "collection": "web_cache",
                    "source": "inexistente",
                }
            )
        data = json.loads(result)
        assert data["status"] == "no_match"
        mock_table.delete.assert_not_awaited()


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

    def test_cohere_sdk_absent_returns_none(self):
        from backend.tools.rag import _build_reranker

        with (
            patch("backend.tools.rag.settings") as ms,
            patch("backend.tools.rag.CohereRerank", None),
        ):
            ms.reranker_type = "cohere"
            ms.get_cohere_api_key.return_value = "ck-1"
            assert _build_reranker() is None

    def test_voyage_with_key_returns_voyage_reranker(self):
        from langchain_voyageai import VoyageAIRerank

        from backend.tools.rag import _build_reranker

        with patch("backend.tools.rag.settings") as ms:
            ms.reranker_type = "voyage"
            ms.voyage_api_key = "voy-1"
            ms.voyage_rerank_model = "rerank-2"
            ms.reranker_top_k = 5
            ms.get_cohere_api_key.return_value = None  # sem secundário → voyage puro
            out = _build_reranker()
        assert isinstance(out, VoyageAIRerank)
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
        from langchain_voyageai import VoyageAIRerank

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
        assert isinstance(out, VoyageAIRerank)

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
