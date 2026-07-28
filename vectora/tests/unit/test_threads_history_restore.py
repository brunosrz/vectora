"""Recuperação de histórico do checkpointer (regressão do bug #1).

A sessão abria vazia ao reabrir após reiniciar. O backend lê via
``aget_thread_messages`` → ``aget_state`` do **mesmo** grafo que escreve (o
``aget_state`` do LangGraph dobra os pending writes nos canais). Aqui cobrimos a
camada de transformação/filtragem que é nossa responsabilidade: dado um estado
reconstruído, devolver pares ``(role, text)`` humano/assistente limpos —
filtrando mensagens de tool e turnos de IA sem texto (só tool-call), e lidando
com conteúdo multimodal (lista de blocos) e estado vazio.
"""

from __future__ import annotations

from typing import Annotated, TypedDict

import pytest
from langchain_core.messages import AIMessage, HumanMessage, ToolMessage
from langgraph.graph.message import add_messages

from backend.services import agent_factory


class _RoundtripState(TypedDict):
    # Definido no módulo (não dentro do teste) para que `get_type_hints` do
    # LangGraph resolva ``Annotated``/``add_messages`` nas globais do módulo —
    # com ``from __future__ import annotations`` a anotação é uma string e o
    # eval falha se os nomes só existirem no escopo local da função.
    messages: Annotated[list, add_messages]


class _FakeSnapshot:
    def __init__(self, messages) -> None:
        self.values = {"messages": messages} if messages is not None else {}
        self.parent_config = None


def _patch_graph(monkeypatch, messages) -> None:
    """Patcha get_user_agent para devolver um grafo fake cujo aget_state_history
    devolve um único snapshot com ``messages`` (tudo commitado em um passo só —
    o mapeamento por-mensagem do checkpoint pai é coberto em
    test_services_agent_factory.py; aqui o foco é a filtragem/transformação)."""

    class _FakeCompiled:
        async def _history(self, _config):
            yield _FakeSnapshot(messages)

        def aget_state_history(self, config):
            return self._history(config)

    async def _fake_get_user_agent(*a, **kw):
        return _FakeCompiled()

    monkeypatch.setattr(agent_factory, "get_user_agent", _fake_get_user_agent)
    monkeypatch.setattr(agent_factory, "_checkpointer", object())

    async def _noop_ensure() -> None:
        pass

    monkeypatch.setattr(agent_factory, "_ensure_infra", _noop_ensure)


@pytest.mark.asyncio
async def test_returns_clean_human_assistant_pairs(monkeypatch):
    messages = [
        HumanMessage(content="oi"),
        AIMessage(content="Olá! Como posso ajudar?"),
        HumanMessage(content="liste arquivos"),
        # Turno de IA só com tool-call (sem texto) → filtrado.
        AIMessage(content="", tool_calls=[]),
        ToolMessage(content="a.py\nb.py", tool_call_id="t1"),  # tool → filtrado
        AIMessage(content="Encontrei 2 arquivos."),
    ]
    _patch_graph(monkeypatch, messages)

    pairs = await agent_factory.aget_thread_messages("tid")

    assert pairs == [
        ("human", "oi", "", []),
        ("assistant", "Olá! Como posso ajudar?", "", []),
        ("human", "liste arquivos", "", []),
        ("assistant", "Encontrei 2 arquivos.", "", []),
    ]


@pytest.mark.asyncio
async def test_multimodal_assistant_content_extracted(monkeypatch):
    messages = [
        HumanMessage(content="oi"),
        AIMessage(content=[{"type": "text", "text": "resposta multimodal"}]),
    ]
    _patch_graph(monkeypatch, messages)

    pairs = await agent_factory.aget_thread_messages("tid")
    assert pairs == [
        ("human", "oi", "", []),
        ("assistant", "resposta multimodal", "", []),
    ]


@pytest.mark.asyncio
async def test_empty_state_returns_empty(monkeypatch):
    _patch_graph(monkeypatch, None)
    assert await agent_factory.aget_thread_messages("tid") == []


@pytest.mark.asyncio
async def test_no_messages_channel_returns_empty(monkeypatch):
    _patch_graph(monkeypatch, [])
    assert await agent_factory.aget_thread_messages("tid") == []


@pytest.mark.asyncio
async def test_checkpointer_roundtrip_survives_reconnect(tmp_path):
    """Round-trip real: escreve numa conexão, reabre em OUTRA e recupera.

    Reproduz o cenário do bug #1 (reiniciar o app → reabrir a sessão): o estado
    do canal ``messages`` é gravado pelo checkpointer SQLite e precisa voltar
    íntegro ao abrir uma conexão nova sobre o mesmo arquivo. Sem LLM/rede — um
    grafo mínimo com reducer ``add_messages`` exercita o mesmo mecanismo de
    persistência (``aget_state`` dobrando os writes) que o grafo real usa.
    """
    from langchain_core.runnables import RunnableConfig
    from langgraph.checkpoint.sqlite.aio import AsyncSqliteSaver
    from langgraph.graph import END, START, StateGraph

    def _reply(state):
        return {"messages": [AIMessage(content="resposta")]}

    db_path = str(tmp_path / "ckpt.db")
    cfg: RunnableConfig = {"configurable": {"thread_id": "t1"}}

    def _build(saver):
        g = StateGraph(_RoundtripState)  # ty: ignore[invalid-argument-type]
        g.add_node("reply", _reply)
        g.add_edge(START, "reply")
        g.add_edge("reply", END)
        return g.compile(checkpointer=saver)

    # 1) Conexão A: escreve um turno (humano → IA).
    async with AsyncSqliteSaver.from_conn_string(db_path) as saver_a:
        await _build(saver_a).ainvoke({"messages": [HumanMessage(content="oi")]}, cfg)

    # 2) Conexão B (nova): simula o restart do backend e recupera.
    async with AsyncSqliteSaver.from_conn_string(db_path) as saver_b:
        state = await _build(saver_b).aget_state(cfg)
        contents = [m.content for m in state.values["messages"]]

    assert contents == ["oi", "resposta"]
