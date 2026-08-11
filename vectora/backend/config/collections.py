"""Contrato de recurso em formato de **coleção** no schema declarativo.

Complementa `backend.config.registry` (pares chave→valor escalares). Recursos
que são listas/coleções — modelos registrados por gateway, memórias, perfil de
conta — não cabem no molde `get(key)/set(key)` de um campo escalar: precisam
de listagem, inclusão e remoção de itens. Este módulo declara esse contrato
com o mesmo espírito do registry escalar (um recurso, uma categoria, um
adapter que sabe ler/escrever no mecanismo real).

O `CollectionSettingAdapter` é um Protocol com chamadas síncronas de leitura
(`list`) e assíncronas de escrita (`add`/`remove`) — `list` é síncrono para
coberturas de adequa a catálogos já materializados em memória, enquanto a
escrita toca storage e segue o padrão async-first do projeto.
"""

from __future__ import annotations

import dataclasses
import typing
from typing import Protocol

if typing.TYPE_CHECKING:
    from collections.abc import Iterable


class CollectionSettingAdapter(Protocol):
    """Lê/escreve um recurso de coleção num mecanismo de persistência real.

    Todas as operações são async — o adapter toca storage (banco, rede), e o
    projeto é async-first (CLAUDE.md regra 10). Não há `list` síncrono aqui:
    um `list` síncrono num loop async já rodando quebraria com
    `run_until_complete` num loop ativo.
    """

    async def list_items(self) -> list[dict[str, typing.Any]]: ...

    async def add(self, item: dict[str, typing.Any]) -> dict[str, typing.Any]: ...

    async def remove(self, item_id: str) -> None: ...


@dataclasses.dataclass(frozen=True)
class CollectionSettingField:
    """Um recurso de coleção declarado — metadados + adapter de acesso."""

    key: str
    category: str
    description: str
    adapter: CollectionSettingAdapter

    async def list_items(self) -> list[dict[str, typing.Any]]:
        return await self.adapter.list_items()

    async def add(self, item: dict[str, typing.Any]) -> dict[str, typing.Any]:
        return await self.adapter.add(item)

    async def remove(self, item_id: str) -> None:
        await self.adapter.remove(item_id)


_COLLECTION_REGISTRY: dict[str, CollectionSettingField] = {}


class DuplicateCollectionFieldError(ValueError):
    """Duas definições tentaram registrar o mesmo recurso de coleção."""


def collection_field(
    key: str,
    *,
    category: str,
    description: str,
    adapter: CollectionSettingAdapter,
) -> CollectionSettingField:
    """Registra um recurso de coleção no schema declarativo."""
    if key in _COLLECTION_REGISTRY:
        raise DuplicateCollectionFieldError(f"collection_field duplicado: {key!r}")
    field = CollectionSettingField(
        key=key,
        category=category,
        description=description,
        adapter=adapter,
    )
    _COLLECTION_REGISTRY[key] = field
    return field


def get_collection_field(key: str) -> CollectionSettingField | None:
    return _COLLECTION_REGISTRY.get(key)


def collections_for_category(category: str) -> list[CollectionSettingField]:
    return [f for f in _COLLECTION_REGISTRY.values() if f.category == category]


def all_collections() -> Iterable[CollectionSettingField]:
    return _COLLECTION_REGISTRY.values()
