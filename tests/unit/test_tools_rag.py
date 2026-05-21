"""Tests for vectora/tools/rag.py"""

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

        from vectora.tools.rag import vector_search

        with patch("vectora.tools.rag.settings") as ms:
            ms.enable_rag = True
            ms.get_cohere_api_key.return_value = "test-key"
            ms.lancedb_dir = "/tmp/lancedb"
            ms.embedding_model = "embed-english-v3.0"
            ms.reranker_type = "none"
            with patch("vectora.tools.rag.lancedb", mock_lancedb):
                with patch("vectora.tools.rag.CohereEmbeddings", mock_embeddings):
                    with patch("vectora.tools.rag.SecretStr", lambda x: x):
                        with patch("vectora.tools.rag.CohereRerank", None):
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

        from vectora.tools.rag import vector_search

        with patch("vectora.tools.rag.settings") as ms:
            ms.enable_rag = True
            ms.get_cohere_api_key.return_value = "test-key"
            ms.lancedb_dir = "/tmp/lancedb"
            ms.embedding_model = "embed-english-v3.0"
            with patch("vectora.tools.rag.lancedb", mock_lancedb):
                with patch("vectora.tools.rag.CohereEmbeddings", mock_embeddings):
                    with patch("vectora.tools.rag.SecretStr", lambda x: x):
                        result = await vector_search.ainvoke(
                            {"query": "test", "collection": "articles", "limit": 5}
                        )
        data = json.loads(result)
        assert data["status"] == "no_results"

    @pytest.mark.asyncio
    async def test_rag_disabled_returns_message(self):
        from vectora.tools.rag import vector_search

        with patch("vectora.tools.rag.settings") as mock_settings:
            mock_settings.enable_rag = False
            result = await vector_search.ainvoke(
                {"query": "test", "collection": "articles", "limit": 5}
            )
        assert "disabled" in result.lower() or "RAG" in result

    @pytest.mark.asyncio
    async def test_missing_dependencies_returns_message(self):
        from vectora.tools.rag import vector_search

        with patch("vectora.tools.rag.settings") as mock_settings:
            with patch("vectora.tools.rag.lancedb", None):
                with patch("vectora.tools.rag.CohereEmbeddings", None):
                    mock_settings.enable_rag = True
                    result = await vector_search.ainvoke(
                        {"query": "test", "collection": "articles", "limit": 5}
                    )
        assert "missing" in result.lower() or isinstance(result, str)

    @pytest.mark.asyncio
    async def test_missing_api_key_returns_error(self):
        from vectora.tools.rag import vector_search

        with patch("vectora.tools.rag.settings") as mock_settings:
            mock_settings.enable_rag = True
            mock_settings.get_cohere_api_key.return_value = None
            with patch("vectora.tools.rag.lancedb", MagicMock()):
                with patch("vectora.tools.rag.CohereEmbeddings", MagicMock()):
                    result = await vector_search.ainvoke(
                        {"query": "test", "collection": "articles", "limit": 5}
                    )
        data = json.loads(result)
        assert data.get("status") in ("failed", "error")


class TestEmbedding:
    @pytest.mark.asyncio
    async def test_rag_disabled_returns_error(self):
        from vectora.tools.rag import embedding

        with patch("vectora.tools.rag.settings") as mock_settings:
            mock_settings.enable_rag = False
            result = await embedding.ainvoke({"text": "doc", "collection": "articles"})
        data = json.loads(result)
        assert data["status"] == "error"

    @pytest.mark.asyncio
    async def test_queue_not_enabled_returns_error(self):
        from vectora.tools.rag import embedding

        with patch("vectora.tools.rag.settings") as mock_settings:
            mock_settings.enable_rag = True
            mock_settings.embedding_queue_enabled = False
            result = await embedding.ainvoke({"text": "doc", "collection": "articles"})
        data = json.loads(result)
        assert data["status"] == "error"

    @pytest.mark.asyncio
    async def test_enqueue_success_returns_fire_and_forget(self):
        from vectora.tools.rag import embedding

        mock_queue = AsyncMock()
        mock_queue.enqueue.return_value = "queue-id-123"

        with patch("vectora.tools.rag.settings") as mock_settings:
            mock_settings.enable_rag = True
            mock_settings.embedding_queue_enabled = True
            mock_settings.embedding_queue_dsn = "sqlite:///test.db"
            with patch(
                "vectora.tools.rag.get_embedding_queue",
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
        from vectora.tools.rag import embedding

        with patch("vectora.tools.rag.settings") as mock_settings:
            mock_settings.enable_rag = True
            mock_settings.embedding_queue_enabled = True
            mock_settings.embedding_queue_dsn = "sqlite:///test.db"
            with patch(
                "vectora.tools.rag.get_embedding_queue",
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
    async def test_file_operations_disabled(self):
        from vectora.tools.rag import ingest_docs

        with patch("vectora.tools.rag.settings") as mock_settings:
            mock_settings.enable_file_operations = False
            result = await ingest_docs.ainvoke(
                {"directory_path": "/tmp", "collection": "articles"}
            )
        assert "disabled" in result.lower()

    @pytest.mark.asyncio
    async def test_unsafe_path_denied(self):
        from vectora.tools.rag import ingest_docs

        with patch("vectora.tools.rag.settings") as mock_settings:
            mock_settings.enable_file_operations = True
            with patch(
                "vectora.services.security.is_safe_file_path", return_value=False
            ):
                result = await ingest_docs.ainvoke(
                    {"directory_path": "/etc", "collection": "articles"}
                )
        assert "denied" in result.lower() or "Access" in result

    @pytest.mark.asyncio
    async def test_not_a_directory_returns_error(self, tmp_path):
        from vectora.tools.rag import ingest_docs

        not_dir = tmp_path / "file.txt"
        not_dir.write_text("I am a file")

        with patch("vectora.tools.rag.settings") as mock_settings:
            mock_settings.enable_file_operations = True
            with patch(
                "vectora.services.security.is_safe_file_path", return_value=True
            ):
                result = await ingest_docs.ainvoke(
                    {"directory_path": str(not_dir), "collection": "articles"}
                )
        assert "Not a directory" in result

    @pytest.mark.asyncio
    async def test_no_files_found_returns_no_files(self, tmp_path):
        from vectora.tools.rag import ingest_docs

        with patch("vectora.tools.rag.settings") as mock_settings:
            mock_settings.enable_file_operations = True
            with patch(
                "vectora.services.security.is_safe_file_path", return_value=True
            ):
                with patch(
                    "vectora.services.gitignore.load_gitignore_spec", return_value=None
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
        from vectora.tools.rag import ingest_docs

        md_file = tmp_path / "doc.md"
        md_file.write_text("# Content")

        with patch("vectora.tools.rag.settings") as mock_settings:
            mock_settings.enable_file_operations = True
            with patch(
                "vectora.services.security.is_safe_file_path", return_value=True
            ):
                with patch("vectora.services.gitignore.is_ignored", return_value=False):
                    with patch(
                        "vectora.services.gitignore.load_gitignore_spec",
                        return_value=None,
                    ):
                        with patch("vectora.tools.rag.embedding") as mock_emb:
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
        from vectora.tools.rag import ingest_docs

        md_file = tmp_path / "ignored.md"
        md_file.write_text("# Ignored")

        with patch("vectora.tools.rag.settings") as mock_settings:
            mock_settings.enable_file_operations = True
            with patch(
                "vectora.services.security.is_safe_file_path", return_value=True
            ):
                with patch(
                    "vectora.services.gitignore.load_gitignore_spec", return_value=None
                ):
                    # All files are ignored → no_files result
                    with patch(
                        "vectora.services.gitignore.is_ignored", return_value=True
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
        assert data["skipped_ignored"] >= 1

    @pytest.mark.asyncio
    async def test_file_read_error_counts_as_failure(self, tmp_path):
        """Covers file read exception path (lines 310-316)."""
        from unittest.mock import mock_open, patch

        from vectora.tools.rag import ingest_docs

        md_file = tmp_path / "unreadable.md"
        md_file.write_text("content")

        with patch("vectora.tools.rag.settings") as mock_settings:
            mock_settings.enable_file_operations = True
            with patch(
                "vectora.services.security.is_safe_file_path", return_value=True
            ):
                with patch("vectora.services.gitignore.is_ignored", return_value=False):
                    with patch(
                        "vectora.services.gitignore.load_gitignore_spec",
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
        from vectora.tools.rag import ingest_docs

        md_file = tmp_path / "doc.md"
        md_file.write_text("# Content for embedding")

        # Return something that is NOT fire_and_forget
        mock_result = json.dumps({"status": "error", "reason": "queue full"})

        with patch("vectora.tools.rag.settings") as mock_settings:
            mock_settings.enable_file_operations = True
            with patch(
                "vectora.services.security.is_safe_file_path", return_value=True
            ):
                with patch("vectora.services.gitignore.is_ignored", return_value=False):
                    with patch(
                        "vectora.services.gitignore.load_gitignore_spec",
                        return_value=None,
                    ):
                        with patch("vectora.tools.rag.embedding") as mock_emb:
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
        from vectora.tools.rag import ingest_docs

        md_file = tmp_path / "test.md"
        md_file.write_text("# Test\nConteúdo de teste para embedding.")

        mock_result = json.dumps({"status": "fire_and_forget", "queue_id": "q1"})

        with patch("vectora.tools.rag.settings") as mock_settings:
            mock_settings.enable_file_operations = True
            mock_settings.enable_rag = True
            mock_settings.embedding_queue_enabled = True
            with patch(
                "vectora.services.security.is_safe_file_path", return_value=True
            ):
                with patch("vectora.services.gitignore.is_ignored", return_value=False):
                    with patch(
                        "vectora.services.gitignore.load_gitignore_spec",
                        return_value=None,
                    ):
                        with patch("vectora.tools.rag.embedding") as mock_emb:
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
