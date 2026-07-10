"""Fixtures mínimas compartilhadas — KISS."""

from __future__ import annotations

from unittest.mock import AsyncMock

import pytest


@pytest.fixture
def _no_nats_sidecar(monkeypatch: pytest.MonkeyPatch):
    """Neutraliza o sidecar NATS: ``get_kv``/``get_mq`` caem no fallback de memória.

    Sem isso, todo teste que assume ``MemoryKV``/``MemoryMQ`` passa a subir o
    ``nats-server`` real assim que o binário existe em ``resources/`` (após
    ``scons nats``) — deixando a suíte dependente da presença do binário e
    compartilhando o store JetStream em ``~/.vectora/nats`` entre os testes.

    Testes que querem o ``NatsKV``/``NatsMQ`` de verdade ou re-mockam
    ``ensure_nats_sidecar`` no próprio corpo (o último ``setattr`` vence) ou
    vivem em ``test_nats_sidecar.py`` / ``test_nats_mq_kv_real.py`` (que não
    dependem deste fixture).
    """
    from backend.scheduling import nats_sidecar

    monkeypatch.setattr(
        nats_sidecar, "ensure_nats_sidecar", AsyncMock(return_value=None)
    )
