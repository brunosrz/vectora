"""Testes do contrato de coleção do registry — `CollectionSettingField` e o
`SqliteTableAdapter` que envolve as tabelas SQLite ad hoc de modelos
registrados por gateway (provider_routing). Isolado do disco real: usa DB em
tmp_path.

Cobertura: contrato de coleção no registry (registra/recupera/listar por
categoria/duplicado) e o adapter de tabela de modelos (list/add/remove +
par de erro).
"""

from __future__ import annotations

import pytest

from backend.config import registry as registry_mod
from backend.config import collections as collections_mod
from backend.config.collections import (
    CollectionSettingField,
    DuplicateCollectionFieldError,
)
from backend.config.adapters import RegisteredModelsTableAdapter


@pytest.fixture  # type: ignore[misc]
def clean_registry():
    """Isola os registries globais (escalar e coleção) entre testes."""
    scalar = dict(registry_mod._REGISTRY)
    collection = dict(collections_mod._COLLECTION_REGISTRY)
    registry_mod._REGISTRY.clear()
    collections_mod._COLLECTION_REGISTRY.clear()
    yield
    registry_mod._REGISTRY.clear()
    collections_mod._COLLECTION_REGISTRY.clear()
    registry_mod._REGISTRY.update(scalar)
    collections_mod._COLLECTION_REGISTRY.update(collection)


# ---------------------------------------------------------------------------
# Contrato de coleção no registry
# ---------------------------------------------------------------------------


class TestCollectionRegistry:
    def test_registra_e_recupera(self, clean_registry):
        from backend.config.collections import collection_field

        collection_field(
            "openrouter_registered_models",
            category="provider_routing",
            description="Modelos registrados do gateway OpenRouter.",
            adapter=RegisteredModelsTableAdapter("openrouter_registered_models"),
        )
        field = collections_mod.get_collection_field("openrouter_registered_models")
        assert field is not None
        assert field.category == "provider_routing"
        assert isinstance(field, CollectionSettingField)

    def test_chave_duplicada_levanta_erro(self, clean_registry):
        from backend.config.collections import collection_field

        collection_field(
            "ollama_registered_models",
            category="provider_routing",
            description="d",
            adapter=RegisteredModelsTableAdapter("ollama_registered_models"),
        )
        with pytest.raises(DuplicateCollectionFieldError):
            collection_field(
                "ollama_registered_models",
                category="provider_routing",
                description="d2",
                adapter=RegisteredModelsTableAdapter("ollama_registered_models"),
            )

    def test_lista_por_categoria(self, clean_registry):
        from backend.config.collections import collection_field

        collection_field(
            "ollama_registered_models",
            category="provider_routing",
            description="d",
            adapter=RegisteredModelsTableAdapter("ollama_registered_models"),
        )
        collection_field(
            "openrouter_registered_models",
            category="provider_routing",
            description="d",
            adapter=RegisteredModelsTableAdapter("openrouter_registered_models"),
        )
        names = [f.key for f in collections_mod.collections_for_category("provider_routing")]
        assert sorted(names) == [
            "ollama_registered_models",
            "openrouter_registered_models",
        ]


# ---------------------------------------------------------------------------
# RegisteredModelsTableAdapter — coleção de modelos registrados
# ---------------------------------------------------------------------------


class TestRegisteredModelsTableAdapter:
    @pytest.mark.asyncio
    async def test_add_list_remove(self, tmp_path, monkeypatch):
        from backend.api.handlers.provider_routing import _get_db

        # Usa DB isolado em tmp_path via monkeypatch do resolutor de DB.
        import sqlite3
        import aiosqlite

        db_path = tmp_path / "provider.db"

        async def _fake_get_db():
            return await aiosqlite.connect(db_path)

        monkeypatch.setattr("backend.api.handlers.provider_routing._get_db", _fake_get_db)

        adapter = RegisteredModelsTableAdapter("ollama_registered_models")
        model = await adapter.add({"tag": "llama3:8b"})
        assert model["tag"] == "llama3:8b"
        assert model["id"]

        items = await adapter.list_items()
        assert len(items) == 1
        assert items[0]["tag"] == "llama3:8b"

        await adapter.remove(model["id"])
        assert await adapter.list_items() == []

    @pytest.mark.asyncio
    async def test_add_tag_duplicada_levanta_erro(self, tmp_path, monkeypatch):
        import aiosqlite

        db_path = tmp_path / "provider.db"

        async def _fake_get_db():
            return await aiosqlite.connect(db_path)

        monkeypatch.setattr(
            "backend.api.handlers.provider_routing._get_db", _fake_get_db
        )

        adapter = RegisteredModelsTableAdapter("ollama_registered_models")
        await adapter.add({"tag": "llama3:8b"})
        with pytest.raises(Exception) as exc_info:
            await adapter.add({"tag": "llama3:8b"})
        assert "409" in str(exc_info.value) or "209" in str(exc_info.value)