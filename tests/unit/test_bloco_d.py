"""Testes TDD para o Bloco D — Reasoning Reveal & Thinking UX.

Todos estes testes são escritos ANTES da implementação (TDD: red → green).

Cobre:
  D1 — ThinkingEvent: schema, extração do orchestrator, emissão no stream
  D2 — Progresso semântico: mapeamento node → label humano
  D3 — Duration badges: duration_ms nos NodeEvent de fim
  D4 — Dev mode: campos extras acessíveis via flag

Subseção por sub-bloco para facilitar implementação incremental.
"""

from __future__ import annotations

import json

import pytest

# ===========================================================================
# D1 — ThinkingEvent: schema + extração + emissão
# ===========================================================================


class TestThinkingEventSchema:
    """ThinkingEvent deve existir em schemas.py com os campos corretos."""

    def test_thinking_event_importable(self):
        from src.api.schemas import ThinkingEvent

    def test_thinking_event_has_reason(self):
        from src.api.schemas import ThinkingEvent

        e = ThinkingEvent(reason="usuário perguntou sobre código")
        assert e.reason == "usuário perguntou sobre código"

    def test_thinking_event_has_action(self):
        from src.api.schemas import ThinkingEvent

        e = ThinkingEvent(reason="delegando", action="delegate")
        assert e.action == "delegate"

    def test_thinking_event_action_defaults_to_respond(self):
        from src.api.schemas import ThinkingEvent

        e = ThinkingEvent(reason="r")
        assert e.action == "respond"

    def test_thinking_event_has_delegate_to(self):
        from src.api.schemas import ThinkingEvent

        e = ThinkingEvent(reason="r", delegate_to="search_agent")
        assert e.delegate_to == "search_agent"

    def test_thinking_event_delegate_to_defaults_none(self):
        from src.api.schemas import ThinkingEvent

        e = ThinkingEvent(reason="r")
        assert e.delegate_to is None

    def test_thinking_event_encode_has_correct_type(self):
        from src.api.schemas import ThinkingEvent, encode_event

        line = encode_event(ThinkingEvent(reason="r"))
        data = json.loads(line.removeprefix("data: ").strip())
        assert data["type"] == "thinking"
        assert data["reason"] == "r"

    def test_thinking_event_in_stream_payload_union(self):
        """ThinkingEvent deve fazer parte de StreamChatEventPayload."""
        from src.api.schemas import StreamChatEventPayload, ThinkingEvent

        e: StreamChatEventPayload = ThinkingEvent(reason="ok")
        assert e is not None


class TestExtractOrchestratorThinking:
    """_extract_orchestrator_thinking extrai reason/action/delegate_to do on_chain_end."""

    def test_extract_thinking_from_dict_output_with_reason(self):
        from src.api.adapters import _extract_orchestrator_thinking

        event = {
            "event": "on_chain_end",
            "name": "orchestrator",
            "data": {
                "output": {
                    "routing_decision": "search",
                    "orchestrator_task": "buscar sobre python",
                    "thinking": {
                        "reason": "usuário quer pesquisa web",
                        "action": "delegate",
                        "delegate_to": "search_agent",
                    },
                }
            },
        }
        result = _extract_orchestrator_thinking(event)
        assert result is not None
        assert result["reason"] == "usuário quer pesquisa web"
        assert result["action"] == "delegate"
        assert result["delegate_to"] == "search_agent"

    def test_extract_thinking_from_command_update(self):
        """Deve extrair thinking de Command.update (caso real do orchestrator)."""
        from src.api.adapters import _extract_orchestrator_thinking

        class FakeCommand:
            update = {
                "routing_decision": "respond",
                "messages": [],
                "thinking": {
                    "reason": "resposta direta",
                    "action": "respond",
                    "delegate_to": None,
                    "task_query": None,
                },
            }

        event = {
            "event": "on_chain_end",
            "name": "orchestrator",
            "data": {"output": FakeCommand()},
        }
        result = _extract_orchestrator_thinking(event)
        assert result is not None
        assert result["reason"] == "resposta direta"
        assert result["action"] == "respond"

    def test_extract_thinking_returns_none_when_no_thinking_key(self):
        from src.api.adapters import _extract_orchestrator_thinking

        event = {
            "event": "on_chain_end",
            "name": "orchestrator",
            "data": {"output": {"messages": []}},
        }
        result = _extract_orchestrator_thinking(event)
        assert result is None

    def test_extract_thinking_returns_none_for_non_orchestrator(self):
        from src.api.adapters import _extract_orchestrator_thinking

        event = {
            "event": "on_chain_end",
            "name": "search_agent",
            "data": {"output": {"thinking": {"reason": "x"}}},
        }
        result = _extract_orchestrator_thinking(event)
        assert result is None

    def test_extract_thinking_handles_missing_data(self):
        from src.api.adapters import _extract_orchestrator_thinking

        event = {"event": "on_chain_end", "name": "orchestrator", "data": {}}
        result = _extract_orchestrator_thinking(event)
        assert result is None


class TestAdaptStreamThinkingEvent:
    """adapt_stream deve emitir ThinkingEvent quando o orchestrator inclui thinking."""

    @pytest.mark.asyncio
    async def test_thinking_event_emitted_in_stream(self):
        from src.api.adapters import adapt_stream
        from src.api.schemas import ThinkingEvent

        thinking_data = {
            "reason": "usuário precisa de busca",
            "action": "delegate",
            "delegate_to": "search_agent",
        }
        events = [
            {
                "event": "on_chain_start",
                "name": "orchestrator",
                "data": {},
                "metadata": {},
            },
            {
                "event": "on_chain_end",
                "name": "orchestrator",
                "data": {
                    "output": {
                        "thinking": thinking_data,
                        "messages": [],
                    }
                },
                "metadata": {},
            },
        ]

        async def _fake_events():
            for e in events:
                yield e

        lines = [line async for line in adapt_stream(_fake_events(), "t-1")]

        payloads = [
            json.loads(ln.removeprefix("data: ").strip())
            for ln in lines
            if ln.startswith("data: ")
        ]
        thinking_events = [p for p in payloads if p["type"] == "thinking"]
        assert len(thinking_events) >= 1
        assert thinking_events[0]["reason"] == "usuário precisa de busca"
        assert thinking_events[0]["action"] == "delegate"
        assert thinking_events[0]["delegate_to"] == "search_agent"

    @pytest.mark.asyncio
    async def test_no_thinking_event_when_orchestrator_responds_directly(self):
        from langchain_core.messages import AIMessage

        from src.api.adapters import adapt_stream

        events = [
            {
                "event": "on_chain_start",
                "name": "orchestrator",
                "data": {},
                "metadata": {},
            },
            {
                "event": "on_chain_end",
                "name": "orchestrator",
                "data": {
                    "output": {
                        "messages": [AIMessage(content="resposta direta")],
                    }
                },
                "metadata": {},
            },
        ]

        async def _fake_events():
            for e in events:
                yield e

        lines = [line async for line in adapt_stream(_fake_events(), "t-1")]

        payloads = [
            json.loads(ln.removeprefix("data: ").strip())
            for ln in lines
            if ln.startswith("data: ")
        ]
        thinking_events = [p for p in payloads if p["type"] == "thinking"]
        assert len(thinking_events) == 0


# ===========================================================================
# D2 — Progresso semântico: node → label
# ===========================================================================


class TestNodeLabels:
    """node_labels.py mapeia nome interno de nó para label legível."""

    def test_node_labels_module_importable(self):
        from src.api import node_labels

    def test_get_node_label_returns_string(self):
        from src.api.node_labels import get_node_label

        label = get_node_label("orchestrator")
        assert isinstance(label, str)
        assert len(label) > 0

    def test_get_node_label_orchestrator(self):
        from src.api.node_labels import get_node_label

        assert get_node_label("orchestrator") == "Analisando..."

    def test_get_node_label_search_agent(self):
        from src.api.node_labels import get_node_label

        assert get_node_label("search_agent") == "Pesquisando na web…"

    def test_get_node_label_rag_agent(self):
        from src.api.node_labels import get_node_label

        label = get_node_label("rag_agent")
        assert (
            "documento" in label.lower()
            or "rag" in label.lower()
            or "base" in label.lower()
        )

    def test_get_node_label_coder_agent(self):
        from src.api.node_labels import get_node_label

        label = get_node_label("coder_agent")
        assert (
            "código" in label.lower()
            or "coder" in label.lower()
            or "programa" in label.lower()
        )

    def test_get_node_label_invoke_llm(self):
        from src.api.node_labels import get_node_label

        label = get_node_label("invoke_llm")
        assert isinstance(label, str)
        assert len(label) > 0

    def test_get_node_label_unknown_returns_generic(self):
        from src.api.node_labels import get_node_label

        label = get_node_label("nó_desconhecido_xyz")
        assert isinstance(label, str)
        assert len(label) > 0

    def test_node_labels_dict_exported(self):
        from src.api.node_labels import NODE_LABELS

        assert isinstance(NODE_LABELS, dict)
        assert "orchestrator" in NODE_LABELS
        assert "search_agent" in NODE_LABELS

    def test_node_label_routing_decision(self):
        """Label especial quando orchestrator decide delegar para search_agent."""
        from src.api.node_labels import get_routing_label

        label = get_routing_label("search_agent")
        assert (
            "busca" in label.lower()
            or "pesquisa" in label.lower()
            or "web" in label.lower()
        )

    def test_get_routing_label_rag(self):
        from src.api.node_labels import get_routing_label

        label = get_routing_label("rag_agent")
        assert isinstance(label, str)
        assert len(label) > 0

    def test_get_routing_label_unknown(self):
        from src.api.node_labels import get_routing_label

        label = get_routing_label("agente_desconhecido")
        assert isinstance(label, str)
        assert len(label) > 0

    def test_node_event_with_label_in_sse(self):
        """NodeEvent com started deve emitir label semântico no campo node_label."""
        from src.api.schemas import NodeEvent, encode_event

        e = NodeEvent(node="search_agent", status="started")
        data = json.loads(encode_event(e).removeprefix("data: ").strip())
        # Após D2, o NodeEvent deve incluir node_label
        assert "node_label" in data
        assert isinstance(data["node_label"], str)
        assert len(data["node_label"]) > 0


# ===========================================================================
# D3 — Duration badges: duration_ms no NodeEvent de fim
# ===========================================================================


class TestNodeEventDuration:
    """adapt_stream já calcula duration_ms; testes garantem comportamento correto."""

    @pytest.mark.asyncio
    async def test_node_finished_has_duration_ms(self):
        from src.api.adapters import adapt_stream

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
        from src.api.adapters import adapt_stream

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
        from src.api.schemas import NodeEvent

        e = NodeEvent(node="n", status="finished", duration_ms=1337)
        assert e.duration_ms == 1337

    @pytest.mark.asyncio
    async def test_multiple_nodes_have_independent_durations(self):
        from src.api.adapters import adapt_stream

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
# D4 — Dev mode: campos extras acessíveis via flag
# ===========================================================================


class TestDevModeFields:
    """Com dev=True, o ThinkingEvent expõe campos extras de debug."""

    def test_thinking_event_has_task_query_field(self):
        from src.api.schemas import ThinkingEvent

        e = ThinkingEvent(
            reason="r",
            action="delegate",
            delegate_to="coder_agent",
            task_query="escreva um script python",
        )
        assert e.task_query == "escreva um script python"

    def test_thinking_event_task_query_defaults_none(self):
        from src.api.schemas import ThinkingEvent

        e = ThinkingEvent(reason="r")
        assert e.task_query is None

    def test_thinking_event_full_fields_in_encoded_event(self):
        from src.api.schemas import ThinkingEvent, encode_event

        e = ThinkingEvent(
            reason="precisa de código",
            action="delegate",
            delegate_to="coder_agent",
            task_query="crie função hello world",
        )
        data = json.loads(encode_event(e).removeprefix("data: ").strip())
        assert data["reason"] == "precisa de código"
        assert data["action"] == "delegate"
        assert data["delegate_to"] == "coder_agent"
        assert data["task_query"] == "crie função hello world"

    def test_extract_thinking_includes_task_query(self):
        from src.api.adapters import _extract_orchestrator_thinking

        event = {
            "event": "on_chain_end",
            "name": "orchestrator",
            "data": {
                "output": {
                    "thinking": {
                        "reason": "precisa de código",
                        "action": "delegate",
                        "delegate_to": "coder_agent",
                        "task_query": "crie hello world",
                    }
                }
            },
        }
        result = _extract_orchestrator_thinking(event)
        assert result is not None
        assert result.get("task_query") == "crie hello world"

    @pytest.mark.asyncio
    async def test_thinking_event_in_stream_has_task_query(self):
        from src.api.adapters import adapt_stream

        events = [
            {
                "event": "on_chain_end",
                "name": "orchestrator",
                "data": {
                    "output": {
                        "thinking": {
                            "reason": "precisa de coder",
                            "action": "delegate",
                            "delegate_to": "coder_agent",
                            "task_query": "escreva teste unitário",
                        },
                        "messages": [],
                    }
                },
                "metadata": {},
            },
        ]

        async def _fake_events():
            for e in events:
                yield e

        payloads = [
            json.loads(line.removeprefix("data: ").strip())
            async for line in adapt_stream(_fake_events(), "t-1")
            if line.startswith("data: ")
        ]

        thinking_events = [p for p in payloads if p["type"] == "thinking"]
        assert len(thinking_events) >= 1
        assert thinking_events[0].get("task_query") == "escreva teste unitário"


# ===========================================================================
# D1 — Comportamentos existentes do adapters que não devem regredir
# ===========================================================================


class TestAdaptersRegression:
    """Testes de não-regressão: comportamentos do adapters antes do Bloco D."""

    def test_token_event_from_chat_model_stream(self):
        from src.api.adapters import langgraph_event_to_payload
        from src.api.schemas import TokenEvent

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

    def test_orchestrator_tokens_filtered(self):
        from src.api.adapters import langgraph_event_to_payload

        class FakeChunk:
            content = '{"action": "respond"}'

        event = {
            "event": "on_chat_model_stream",
            "name": "orchestrator",
            "run_name": "orchestrator",
            "data": {"chunk": FakeChunk()},
            "metadata": {"langgraph_node": "orchestrator"},
        }
        result = langgraph_event_to_payload(event)
        assert result is None

    def test_tool_call_event_emitted(self):
        from src.api.adapters import langgraph_event_to_payload
        from src.api.schemas import ToolCallEvent

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
        from src.api.adapters import langgraph_event_to_payload
        from src.api.schemas import ToolResultEvent

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
        from src.api.adapters import langgraph_event_to_payload
        from src.api.schemas import NodeEvent

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
        from src.api.adapters import langgraph_event_to_payload
        from src.api.schemas import NodeEvent

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
        from src.api.adapters import langgraph_event_to_payload

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
        from src.api.adapters import adapt_stream

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
        from src.api.adapters import adapt_stream

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
        from src.api.adapters import adapt_stream

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
        assert "erro simulado" in error_events[0]["message"]
