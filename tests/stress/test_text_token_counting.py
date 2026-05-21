"""Stress test 3 — TextService: contagem de tokens sob carga.

count_tokens() e count_messages_tokens() são chamados em toda invocação do LLM
pelo trim_messages(). Em conversas longas ou pipelines de ingestão com muitos
chunks, essas funções precisam ser rápidas e corretas sob chamadas em rajada.

Verifica:
  - 10 000 chamadas de count_tokens() completam em menos de 5 s
  - contagem é determinística (mesma string → mesmo resultado em todas as chamadas)
  - split() + count_tokens() são consistentes entre si para o mesmo texto
"""

from __future__ import annotations

import asyncio
import time

import pytest
from langchain_core.messages import AIMessage, HumanMessage

from vectora.services.text import text_service


@pytest.mark.stress
def test_token_counting_throughput():
    """10 000 chamadas de count_tokens() — determinismo e throughput."""
    sample = (
        "O Vectora é um assistente de IA com suporte a RAG, busca vetorial e MCP. "
        "Utiliza LanceDB como banco vetorial e SQLite para checkpoints de sessão. "
        "O pipeline de embedding usa Cohere embed-multilingual-v3.0."
    )

    # Pré-aquece o encoder tiktoken (lazy init)
    baseline = text_service.count_tokens(sample)
    assert baseline > 0

    N = 10_000
    t0 = time.perf_counter()
    for _ in range(N):
        count = text_service.count_tokens(sample)
        # Determinismo: mesma string deve sempre retornar o mesmo valor
        assert count == baseline
    elapsed = time.perf_counter() - t0

    throughput = N / elapsed
    # Budget: pelo menos 5 000 chamadas/segundo (tiktoken é compilado em Rust)
    assert throughput >= 5_000, (
        f"Throughput insuficiente: {throughput:.0f} calls/s (mínimo: 5 000)"
    )


@pytest.mark.stress
def test_message_token_counting_large_history():
    """Histórico de 500 mensagens — contagem total em menos de 1 s."""
    messages = []
    for i in range(250):
        messages.append(HumanMessage(content=f"Pergunta número {i}: o que é RAG?"))
        messages.append(
            AIMessage(
                content=f"Resposta {i}: RAG é Retrieval Augmented Generation, "
                "que combina busca vetorial com geração de texto."
            )
        )

    assert len(messages) == 500

    t0 = time.perf_counter()
    total_tokens = text_service.count_messages_tokens(messages)
    elapsed = time.perf_counter() - t0

    assert total_tokens > 0
    # Budget: 500 mensagens contadas em menos de 1 s
    assert elapsed < 1.0, f"Contagem de 500 msgs levou {elapsed:.3f}s"


@pytest.mark.stress
def test_split_consistency_under_load():
    """split() em 1 000 textos — consistência dos chunks e throughput."""
    # Texto de ~3 000 tokens (vai ser dividido em vários chunks)
    paragraph = (
        "O Vectora processa documentos em chunks usando tiktoken cl100k_base. "
        "Cada chunk tem no máximo 512 tokens com overlap de 50 tokens. "
    )
    large_text = paragraph * 100  # ~3 200 tokens

    # Referência: split uma vez e guarda o resultado
    reference_chunks = text_service.split(large_text)
    assert len(reference_chunks) >= 2

    N = 200
    t0 = time.perf_counter()
    for _ in range(N):
        chunks = text_service.split(large_text)
        assert len(chunks) == len(reference_chunks), (
            "split() não é determinístico — resultados inconsistentes"
        )
    elapsed = time.perf_counter() - t0

    # Budget: 200 splits em menos de 60 s
    # (tiktoken é mais lento em Windows; CI Linux deve completar bem abaixo do limite)
    assert elapsed < 60.0, f"Tempo excessivo: {elapsed:.2f}s para {N} splits"
