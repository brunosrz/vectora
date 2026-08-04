"""Reasoning Reveal & Thinking UX: eventos de stream do chat.

Cobre: SubagentOutputEvent (identidade do subagente delegado via task());
mapeamento node → label humano (node_labels); duration_ms nos NodeEvent
de início/fim; comportamentos de adapters que não podem regredir (tokens,
tool calls/results, eventos thread/done/error).
"""

from __future__ import annotations

import json

import pytest


@pytest.fixture(autouse=True)
def _isolated(_no_thread_persistence):
    pass


# ===========================================================================
# SubagentOutputEvent: identidade do subagente no card "Subagent Outputs"
# ===========================================================================


class TestSubagentOutputEventSchema:
    """SubagentOutputEvent carrega a identidade do subagente delegado via task()."""

    def test_thinking_event_foi_removido(self):
        """Erro/borda: o ThinkingEvent legado não existe mais no schema."""
        from backend.api import schemas

        assert not hasattr(schemas, "ThinkingEvent")

    def test_campos_e_defaults(self):
        from backend.api.schemas import SubagentOutputEvent

        e = SubagentOutputEvent(subagent_type="coder")
        assert e.subagent_type == "coder"
        assert e.status == "running"  # default
        assert e.content == ""
        assert e.description == ""

        full = SubagentOutputEvent(
            subagent_type="search",
            description="pesquisar X",
            status="complete",
            tool_call_id="call-1",
            content="achei X",
        )
        assert full.status == "complete"
        assert full.content == "achei X"

    def test_encode_tem_type_subagent_output(self):
        from backend.api.schemas import SubagentOutputEvent, encode_event

        line = encode_event(
            SubagentOutputEvent(subagent_type="coder", status="complete")
        )
        data = json.loads(line.removeprefix("data: ").strip())
        assert data["type"] == "subagent_output"
        assert data["subagent_type"] == "coder"

    def test_no_stream_payload_union(self):
        from backend.api.schemas import StreamChatEventPayload, SubagentOutputEvent

        e: StreamChatEventPayload = SubagentOutputEvent(subagent_type="coder")
        assert e is not None

    @pytest.mark.asyncio
    async def test_adapt_stream_emite_subagent_output_na_tool_task(self):
        """A tool `task` emite subagent_output 'running' (start) e 'complete'
        (end, com o resultado) — identidade do subagente pro card. Erro/borda:
        uma tool comum (não `task`) NÃO emite subagent_output."""
        from langchain_core.messages import ToolMessage

        from backend.api.adapters import adapt_stream

        events = [
            {
                "event": "on_tool_start",
                "name": "task",
                "data": {"input": {"subagent_type": "coder", "description": "faz X"}},
                "run_id": "r1",
                "metadata": {},
            },
            {
                "event": "on_tool_end",
                "name": "task",
                "data": {"output": ToolMessage(content="feito X", tool_call_id="r1")},
                "run_id": "r1",
                "metadata": {},
            },
            # tool comum não deve gerar subagent_output
            {
                "event": "on_tool_start",
                "name": "web_search",
                "data": {"input": {"query": "x"}},
                "run_id": "r2",
                "metadata": {},
            },
        ]

        async def _fake_events():
            for e in events:
                yield e

        payloads = [
            json.loads(line.removeprefix("data: ").strip())
            async for line in adapt_stream(_fake_events(), "t-sub")
            if line.startswith("data: ")
        ]
        subs = [p for p in payloads if p.get("type") == "subagent_output"]
        assert len(subs) == 2
        assert subs[0]["status"] == "running"
        assert subs[0]["subagent_type"] == "coder"
        assert subs[0]["tool_call_id"] == "r1"
        assert subs[1]["status"] == "complete"
        assert subs[1]["content"] == "feito X"
        # web_search não gerou subagent_output.
        assert all(s["tool_call_id"] == "r1" for s in subs)

    @pytest.mark.asyncio
    async def test_adapt_stream_emite_subagent_output_status_error(self):
        """Erro/borda: quando a delegação falha (ToolMessage com
        status='error'), o subagent_output final sai com status='error' (não
        'complete') — o card precisa distinguir falha de sucesso."""
        from langchain_core.messages import ToolMessage

        from backend.api.adapters import adapt_stream

        events = [
            {
                "event": "on_tool_start",
                "name": "task",
                "data": {
                    "input": {"subagent_type": "search", "description": "busca X"}
                },
                "run_id": "r-err",
                "metadata": {},
            },
            {
                "event": "on_tool_end",
                "name": "task",
                "data": {
                    "output": ToolMessage(
                        content="falha ao buscar",
                        tool_call_id="r-err",
                        status="error",
                    )
                },
                "run_id": "r-err",
                "metadata": {},
            },
        ]

        async def _fake_events():
            for e in events:
                yield e

        payloads = [
            json.loads(line.removeprefix("data: ").strip())
            async for line in adapt_stream(_fake_events(), "t-sub-err")
            if line.startswith("data: ")
        ]
        subs = [p for p in payloads if p.get("type") == "subagent_output"]
        assert len(subs) == 2
        assert subs[1]["status"] == "error"
        assert subs[1]["content"] == "falha ao buscar"


# ===========================================================================
# Progresso semântico: node → label
# ===========================================================================


class TestNodeLabels:
    """node_labels.py mapeia nome interno de nó para label legível."""

    def test_node_labels_module_importable(self):
        from backend.api import node_labels

    def test_get_node_label_returns_string(self):
        from backend.api.node_labels import get_node_label

        label = get_node_label("orchestrator")
        assert isinstance(label, str)
        assert len(label) > 0

    def test_get_node_label_model(self):
        from backend.api.node_labels import get_node_label

        assert get_node_label("model") == "Analisando..."

    def test_get_node_label_search(self):
        from backend.api.node_labels import get_node_label

        assert get_node_label("search") == "Pesquisando…"

    def test_get_node_label_tools(self):
        from backend.api.node_labels import get_node_label

        label = get_node_label("tools")
        assert "ferramenta" in label.lower()

    def test_get_node_label_coder(self):
        from backend.api.node_labels import get_node_label

        label = get_node_label("coder")
        assert (
            "código" in label.lower()
            or "coder" in label.lower()
            or "programa" in label.lower()
        )

    def test_get_node_label_main_agent(self):
        from backend.api.node_labels import get_node_label

        label = get_node_label("vectora")
        assert isinstance(label, str)
        assert len(label) > 0

    def test_get_node_label_unknown_returns_generic(self):
        from backend.api.node_labels import get_node_label

        label = get_node_label("nó_desconhecido_xyz")
        assert isinstance(label, str)
        assert len(label) > 0

    def test_node_labels_dict_exported(self):
        from backend.api.node_labels import NODE_LABELS

        assert isinstance(NODE_LABELS, dict)
        assert "model" in NODE_LABELS
        assert "coder" in NODE_LABELS

    def test_node_label_routing_decision(self):
        """Label especial quando o agente delega ao sub-agent de busca."""
        from backend.api.node_labels import get_routing_label

        label = get_routing_label("search")
        assert (
            "busca" in label.lower()
            or "pesquisa" in label.lower()
            or "web" in label.lower()
        )

    def test_get_routing_label_rag(self):
        from backend.api.node_labels import get_routing_label

        label = get_routing_label("rag_agent")
        assert isinstance(label, str)
        assert len(label) > 0

    def test_get_routing_label_unknown(self):
        from backend.api.node_labels import get_routing_label

        label = get_routing_label("agente_desconhecido")
        assert isinstance(label, str)
        assert len(label) > 0

    def test_node_event_with_label_in_sse(self):
        """NodeEvent com started deve emitir label semântico no campo node_label."""
        from backend.api.schemas import NodeEvent, encode_event

        e = NodeEvent(node="search_agent", status="started")
        data = json.loads(encode_event(e).removeprefix("data: ").strip())
        # Após D2, o NodeEvent deve incluir node_label
        assert "node_label" in data
        assert isinstance(data["node_label"], str)
        assert len(data["node_label"]) > 0


# ===========================================================================
# Duration badges: duration_ms no NodeEvent de fim
# ===========================================================================


class TestNodeEventDuration:
    """adapt_stream já calcula duration_ms; testes garantem comportamento correto."""

    @pytest.mark.asyncio
    async def test_node_finished_has_duration_ms(self):
        from backend.api.adapters import adapt_stream

        events = [
            {
                "event": "on_chain_start",
                "name": "search_agent",
                "data": {},
                "metadata": {},
            },
            {
                "event": "on_chain_end",
                "name": "search_agent",
                "data": {},
                "metadata": {},
            },
        ]

        async def _fake_events():
            for e in events:
                yield e

        payloads = [
            json.loads(line.removeprefix("data: ").strip())
            async for line in adapt_stream(_fake_events(), "t-test")
            if line.startswith("data: ")
        ]

        finished = [
            p
            for p in payloads
            if p.get("type") == "node" and p.get("status") == "finished"
        ]
        assert len(finished) >= 1
        # duration_ms deve ser um inteiro ≥ 0
        assert isinstance(finished[0]["duration_ms"], int)
        assert finished[0]["duration_ms"] >= 0

    @pytest.mark.asyncio
    async def test_node_started_has_zero_duration_ms(self):
        from backend.api.adapters import adapt_stream

        events = [
            {
                "event": "on_chain_start",
                "name": "invoke_llm",
                "data": {},
                "metadata": {},
            },
        ]

        async def _fake_events():
            for e in events:
                yield e

        payloads = [
            json.loads(line.removeprefix("data: ").strip())
            async for line in adapt_stream(_fake_events(), "t-test")
            if line.startswith("data: ")
        ]

        started = [
            p
            for p in payloads
            if p.get("type") == "node" and p.get("status") == "started"
        ]
        assert len(started) >= 1
        assert started[0]["duration_ms"] == 0

    def test_node_event_duration_schema(self):
        from backend.api.schemas import NodeEvent

        e = NodeEvent(node="n", status="finished", duration_ms=1337)
        assert e.duration_ms == 1337

    @pytest.mark.asyncio
    async def test_multiple_nodes_have_independent_durations(self):
        from backend.api.adapters import adapt_stream

        events = [
            {"event": "on_chain_start", "name": "node_a", "data": {}, "metadata": {}},
            {"event": "on_chain_start", "name": "node_b", "data": {}, "metadata": {}},
            {"event": "on_chain_end", "name": "node_a", "data": {}, "metadata": {}},
            {"event": "on_chain_end", "name": "node_b", "data": {}, "metadata": {}},
        ]

        async def _fake_events():
            for e in events:
                yield e

        payloads = [
            json.loads(line.removeprefix("data: ").strip())
            async for line in adapt_stream(_fake_events(), "t-test")
            if line.startswith("data: ")
        ]

        finished = {
            p["node"]: p["duration_ms"]
            for p in payloads
            if p.get("type") == "node" and p.get("status") == "finished"
        }
        assert "node_a" in finished
        assert "node_b" in finished
        assert finished["node_a"] >= 0
        assert finished["node_b"] >= 0


# ===========================================================================
# Comportamentos existentes do adapters que não devem regredir
# ===========================================================================


class TestAdaptersRegression:
    """Testes de não-regressão: comportamentos correntes dos adapters."""

    def test_token_event_from_chat_model_stream(self):
        from backend.api.adapters import langgraph_event_to_payload
        from backend.api.schemas import TokenEvent

        class FakeChunk:
            content = "hello"

        event = {
            "event": "on_chat_model_stream",
            "name": "invoke_llm",
            "run_name": "invoke_llm",
            "data": {"chunk": FakeChunk()},
            "metadata": {"langgraph_node": "invoke_llm"},
        }
        result = langgraph_event_to_payload(event)
        assert isinstance(result, TokenEvent)
        assert result.content == "hello"

    def test_orchestrator_tokens_now_emitted(self):
        """O orchestrator não usa structured output (_STRUCTURED_OUTPUT_NODES
        vazio), então seus tokens são user-facing e viram TokenEvent."""
        from backend.api.adapters import langgraph_event_to_payload
        from backend.api.schemas import TokenEvent

        class FakeChunk:
            content = "Olá, como posso ajudar?"

        event = {
            "event": "on_chat_model_stream",
            "name": "orchestrator",
            "run_name": "orchestrator",
            "data": {"chunk": FakeChunk()},
            "metadata": {"langgraph_node": "orchestrator"},
        }
        result = langgraph_event_to_payload(event)
        assert isinstance(result, TokenEvent)
        assert result.content == "Olá, como posso ajudar?"
        assert result.node == "orchestrator"

    def test_tool_call_event_emitted(self):
        from backend.api.adapters import langgraph_event_to_payload
        from backend.api.schemas import ToolCallEvent

        event = {
            "event": "on_tool_start",
            "name": "web_search",
            "run_id": "run-1",
            "data": {"input": {"query": "python asyncio"}},
            "metadata": {},
        }
        result = langgraph_event_to_payload(event)
        assert isinstance(result, ToolCallEvent)
        assert result.tool_name == "web_search"
        assert "python asyncio" in result.args_json

    def test_tool_result_event_emitted(self):
        from backend.api.adapters import langgraph_event_to_payload
        from backend.api.schemas import ToolResultEvent

        event = {
            "event": "on_tool_end",
            "name": "web_search",
            "run_id": "run-1",
            "data": {"output": "resultado da busca"},
            "metadata": {},
        }
        result = langgraph_event_to_payload(event)
        assert isinstance(result, ToolResultEvent)
        assert result.content_json == "resultado da busca"

    def test_node_started_event(self):
        from backend.api.adapters import langgraph_event_to_payload
        from backend.api.schemas import NodeEvent

        event = {
            "event": "on_chain_start",
            "name": "search_agent",
            "data": {},
            "metadata": {},
        }
        result = langgraph_event_to_payload(event)
        assert isinstance(result, NodeEvent)
        assert result.status == "started"
        assert result.node == "search_agent"

    def test_node_finished_event(self):
        from backend.api.adapters import langgraph_event_to_payload
        from backend.api.schemas import NodeEvent

        event = {
            "event": "on_chain_end",
            "name": "search_agent",
            "data": {},
            "metadata": {},
        }
        result = langgraph_event_to_payload(event)
        assert isinstance(result, NodeEvent)
        assert result.status == "finished"

    def test_langgraph_root_events_ignored(self):
        from backend.api.adapters import langgraph_event_to_payload

        for name in ("", "LangGraph"):
            event = {
                "event": "on_chain_start",
                "name": name,
                "data": {},
                "metadata": {},
            }
            result = langgraph_event_to_payload(event)
            assert result is None, f"name={name!r} deveria ser ignorado"

    @pytest.mark.asyncio
    async def test_stream_always_starts_with_thread_event(self):
        from backend.api.adapters import adapt_stream

        async def _empty():
            return
            yield  # make it an async generator

        payloads = [
            json.loads(line.removeprefix("data: ").strip())
            async for line in adapt_stream(_empty(), "t-xyz")
            if line.startswith("data: ")
        ]

        assert payloads[0]["type"] == "thread"
        assert payloads[0]["thread_id"] == "t-xyz"

    @pytest.mark.asyncio
    async def test_stream_always_ends_with_done_event(self):
        from backend.api.adapters import adapt_stream

        async def _empty():
            return
            yield

        payloads = [
            json.loads(line.removeprefix("data: ").strip())
            async for line in adapt_stream(_empty(), "t-xyz")
            if line.startswith("data: ")
        ]

        assert payloads[-1]["type"] == "done"
        assert payloads[-1]["thread_id"] == "t-xyz"

    @pytest.mark.asyncio
    async def test_stream_emits_error_event_on_exception(self):
        from backend.api.adapters import adapt_stream

        async def _failing():
            raise RuntimeError("erro simulado")
            yield

        payloads = [
            json.loads(line.removeprefix("data: ").strip())
            async for line in adapt_stream(_failing(), "t-err")
            if line.startswith("data: ")
        ]

        error_events = [p for p in payloads if p["type"] == "error"]
        assert len(error_events) >= 1
        # O adaptador classifica o erro e NÃO vaza a exceção crua ao usuário
        # (ver adapters.classify_stream_error): erro genérico → STREAM_ERROR
        # com mensagem limpa. A mensagem técnica fica só no log do servidor.
        assert error_events[0]["code"] == "STREAM_ERROR"
        assert "erro simulado" not in error_events[0]["message"]
        assert error_events[0]["message"]
