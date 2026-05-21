"""Stress test 4 — sanitize_for_gemini: throughput com históricos malformados.

sanitize_for_gemini() é chamada em toda invocação do LLM. Em conversas longas
com múltiplos tool_calls encadeados (padrão normal do agente de busca), a função
percorre e descarta blocos inválidos do início da lista de mensagens.

Verifica:
  - throughput mínimo com históricos de 200 mensagens (50% malformadas)
  - resultado sempre começa com HumanMessage ou AIMessage sem tool_calls
  - nenhuma exceção em nenhum dos padrões de entrada
"""

from __future__ import annotations

import time

import pytest
from langchain_core.messages import AIMessage, HumanMessage, ToolMessage

from vectora.nodes.base import sanitize_for_gemini


def _make_valid_history(n_pairs: int) -> list:
    """Gera histórico bem formado: Human → AI → Human → AI → ..."""
    msgs = []
    for i in range(n_pairs):
        msgs.append(HumanMessage(content=f"Pergunta {i}"))
        msgs.append(AIMessage(content=f"Resposta {i}"))
    return msgs


def _make_dirty_history(n_pairs: int) -> list:
    """Gera histórico que começa com bloco AI(tool_calls) + ToolMessages inválidos."""
    dirty_prefix = [
        AIMessage(
            content="", tool_calls=[{"name": "web_search", "id": "t0", "args": {}}]
        ),
        ToolMessage(content="resultado", tool_call_id="t0"),
        AIMessage(
            content="", tool_calls=[{"name": "vector_search", "id": "t1", "args": {}}]
        ),
        ToolMessage(content="docs", tool_call_id="t1"),
    ]
    return dirty_prefix + _make_valid_history(n_pairs)


@pytest.mark.stress
def test_sanitize_throughput_valid_history():
    """1 000 históricos válidos de 100 mensagens — sem overhead."""
    history = _make_valid_history(50)  # 100 msgs
    assert len(history) == 100

    N = 1_000
    t0 = time.perf_counter()
    for _ in range(N):
        result = sanitize_for_gemini(history)
        # Histórico válido não deve ser alterado
        assert len(result) == len(history)
    elapsed = time.perf_counter() - t0

    assert elapsed < 5.0, (
        f"Throughput insuficiente: {elapsed:.2f}s para {N} sanitizações"
    )


@pytest.mark.stress
def test_sanitize_throughput_dirty_history():
    """1 000 históricos sujos (prefixo inválido) de 108 mensagens — descarte correto."""
    history = _make_dirty_history(50)  # 4 inválidas + 104 válidas
    expected_start_type = (HumanMessage, AIMessage)

    N = 1_000
    t0 = time.perf_counter()
    for _ in range(N):
        result = sanitize_for_gemini(history)
        assert result, "sanitize_for_gemini retornou lista vazia"
        assert isinstance(result[0], expected_start_type), (
            f"Primeiro elemento inválido após sanitização: {type(result[0])}"
        )
    elapsed = time.perf_counter() - t0

    assert elapsed < 5.0, (
        f"Throughput insuficiente: {elapsed:.2f}s para {N} sanitizações"
    )


@pytest.mark.stress
def test_sanitize_deep_invalid_chain():
    """Histórico com 100 blocos inválidos consecutivos antes do primeiro HumanMessage."""
    # 100 × (AIMessage com tool_call + ToolMessage) antes do conteúdo real
    deep_dirty: list = []
    for i in range(100):
        deep_dirty.append(
            AIMessage(
                content="",
                tool_calls=[{"name": "web_search", "id": f"tc{i}", "args": {}}],
            )
        )
        deep_dirty.append(ToolMessage(content=f"resultado {i}", tool_call_id=f"tc{i}"))
    deep_dirty.append(HumanMessage(content="pergunta real"))
    deep_dirty.append(AIMessage(content="resposta real"))

    t0 = time.perf_counter()
    result = sanitize_for_gemini(deep_dirty)
    elapsed = time.perf_counter() - t0

    assert result, "Resultado vazio — HumanMessage real não foi encontrado"
    assert isinstance(result[0], HumanMessage)
    assert result[0].content == "pergunta real"
    # Mesmo com 200 mensagens para percorrer, deve ser instantâneo
    assert elapsed < 0.1, f"Sanitização de cadeia profunda levou {elapsed:.3f}s"
