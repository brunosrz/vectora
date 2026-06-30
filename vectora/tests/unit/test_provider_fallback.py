"""Fallback multi-provider de LLM (Parte A).

Contrato:
- is_quota_error: reconhece 429/quota/rate-limit; ignora outros erros.
- get_fallback_chain: lê llm_fallback_order, remove o provider atual e os sem key.
- try_with_fallback: tenta o modelo; em quota error percorre a cadeia; em troca
  registra record_switch + on_switch; esgotou tudo → QuotaExhaustedError.
- record_switch/drain_switches: fila por ContextVar, drena e limpa.
"""

from __future__ import annotations

from unittest.mock import patch

import pytest

from backend.services import provider_fallback as pf

# ---------------------------------------------------------------------------
# is_quota_error
# ---------------------------------------------------------------------------


class TestIsQuotaError:
    def test_429(self):
        assert pf.is_quota_error(Exception("429 RESOURCE_EXHAUSTED")) is True

    def test_resource_exhausted(self):
        assert pf.is_quota_error(Exception("RESOURCE_EXHAUSTED")) is True

    def test_quota_word(self):
        assert pf.is_quota_error(Exception("You exceeded your current quota")) is True

    def test_rate_limit_space(self):
        assert pf.is_quota_error(Exception("Rate limit reached")) is True

    def test_rate_limit_underscore(self):
        assert pf.is_quota_error(Exception("rate_limit_exceeded")) is True

    def test_case_insensitive(self):
        assert pf.is_quota_error(Exception("Quota Exceeded")) is True

    def test_non_quota_connection(self):
        assert pf.is_quota_error(Exception("connection refused")) is False

    def test_non_quota_value_error(self):
        assert pf.is_quota_error(ValueError("bad input")) is False

    def test_empty(self):
        assert pf.is_quota_error(Exception("")) is False

    def test_quota_exhausted_error_is_quota(self):
        assert pf.is_quota_error(pf.QuotaExhaustedError("gemini esgotou")) is True


# ---------------------------------------------------------------------------
# is_transient_error
# ---------------------------------------------------------------------------


class TestIsTransientError:
    def test_timeout_word(self):
        assert pf.is_transient_error(Exception("ReadTimeout: timed out")) is True

    def test_timed_out(self):
        assert pf.is_transient_error(Exception("request timed out after 30s")) is True

    def test_connecttimeout(self):
        assert (
            pf.is_transient_error(Exception("ConnectTimeout connecting to API")) is True
        )

    def test_readtimeout(self):
        assert pf.is_transient_error(Exception("ReadTimeout reading response")) is True

    def test_connection_error(self):
        assert (
            pf.is_transient_error(Exception("connection error: reset by peer")) is True
        )

    def test_connection_refused(self):
        assert pf.is_transient_error(Exception("connection refused")) is True

    def test_case_insensitive(self):
        assert pf.is_transient_error(Exception("TIMEOUT waiting for model")) is True

    # erros que NÃO são transientes
    def test_quota_not_transient(self):
        assert pf.is_transient_error(Exception("429 quota exceeded")) is False

    def test_auth_not_transient(self):
        assert pf.is_transient_error(Exception("401 Unauthorized")) is False

    def test_value_error_not_transient(self):
        assert pf.is_transient_error(ValueError("bad input")) is False

    def test_empty_not_transient(self):
        assert pf.is_transient_error(Exception("")) is False


# ---------------------------------------------------------------------------
# get_fallback_chain
# ---------------------------------------------------------------------------


def _patch_env(order, keyed_providers):
    """Patcha runtime_settings.get(llm_fallback_order) e _provider_has_key."""
    rt = patch.object(pf, "_fallback_order", return_value=list(order))
    keys = patch.object(
        pf, "_provider_has_key", side_effect=lambda p: p in keyed_providers
    )
    return rt, keys


class TestGetFallbackChain:
    def test_removes_current_provider(self):
        order = ["openai:gpt-4o", "google-genai:gemini-2.5-flash", "cohere:command-a"]
        rt, keys = _patch_env(order, {"openai", "google-genai", "cohere"})
        with rt, keys:
            chain = pf.get_fallback_chain("openai:gpt-4o")
        assert chain == ["google-genai:gemini-2.5-flash", "cohere:command-a"]

    def test_removes_providers_without_key(self):
        order = ["openai:gpt-4o", "google-genai:gemini-2.5-flash", "cohere:command-a"]
        rt, keys = _patch_env(order, {"openai", "google-genai"})  # sem cohere
        with rt, keys:
            chain = pf.get_fallback_chain("openai:gpt-4o")
        assert chain == ["google-genai:gemini-2.5-flash"]

    def test_empty_order(self):
        rt, keys = _patch_env([], {"openai", "google-genai"})
        with rt, keys:
            assert pf.get_fallback_chain("openai:gpt-4o") == []

    def test_current_provider_appears_multiple_times_all_removed(self):
        order = ["openai:gpt-4o", "openai:gpt-4o-mini", "cohere:command-a"]
        rt, keys = _patch_env(order, {"openai", "cohere"})
        with rt, keys:
            chain = pf.get_fallback_chain("openai:gpt-4o")
        assert chain == ["cohere:command-a"]

    def test_preserves_order(self):
        order = ["cohere:command-a", "google-genai:gemini-2.5-flash"]
        rt, keys = _patch_env(order, {"cohere", "google-genai"})
        with rt, keys:
            chain = pf.get_fallback_chain("openai:gpt-4o")
        assert chain == ["cohere:command-a", "google-genai:gemini-2.5-flash"]

    def test_no_keyed_providers(self):
        order = ["cohere:command-a", "google-genai:gemini-2.5-flash"]
        rt, keys = _patch_env(order, set())
        with rt, keys:
            assert pf.get_fallback_chain("openai:gpt-4o") == []


# ---------------------------------------------------------------------------
# record_switch / drain_switches
# ---------------------------------------------------------------------------


class TestSwitchQueue:
    def test_drain_empty(self):
        pf.drain_switches()  # limpa estado anterior
        assert pf.drain_switches() == []

    def test_record_then_drain(self):
        pf.drain_switches()
        pf.record_switch("openai:gpt-4o", "google-genai:gemini-2.5-flash")
        drained = pf.drain_switches()
        assert drained == [
            {"from": "openai:gpt-4o", "to": "google-genai:gemini-2.5-flash"}
        ]

    def test_drain_clears(self):
        pf.drain_switches()
        pf.record_switch("a:1", "b:2")
        pf.drain_switches()
        assert pf.drain_switches() == []

    def test_multiple_switches_in_order(self):
        pf.drain_switches()
        pf.record_switch("a:1", "b:2")
        pf.record_switch("b:2", "c:3")
        drained = pf.drain_switches()
        assert [d["from"] for d in drained] == ["a:1", "b:2"]
        assert [d["to"] for d in drained] == ["b:2", "c:3"]


# ---------------------------------------------------------------------------
# try_with_fallback
# ---------------------------------------------------------------------------


class TestTryWithFallback:
    async def test_success_first_no_switch(self):
        pf.drain_switches()
        calls = []

        async def fn(mid):
            calls.append(mid)
            return f"ok:{mid}"

        out = await pf.try_with_fallback(fn, "openai:gpt-4o")
        assert out == "ok:openai:gpt-4o"
        assert calls == ["openai:gpt-4o"]
        assert pf.drain_switches() == []

    async def test_switch_once(self):
        pf.drain_switches()
        switches = []

        async def fn(mid):
            if mid == "openai:gpt-4o":
                raise Exception("429 RESOURCE_EXHAUSTED")
            return f"ok:{mid}"

        with patch.object(
            pf, "get_fallback_chain", return_value=["google-genai:gemini-2.5-flash"]
        ):
            out = await pf.try_with_fallback(
                fn, "openai:gpt-4o", on_switch=lambda a, b: switches.append((a, b))
            )
        assert out == "ok:google-genai:gemini-2.5-flash"
        assert switches == [("openai:gpt-4o", "google-genai:gemini-2.5-flash")]
        assert pf.drain_switches() == [
            {"from": "openai:gpt-4o", "to": "google-genai:gemini-2.5-flash"}
        ]

    async def test_switch_twice(self):
        async def fn(mid):
            if mid != "cohere:command-a":
                raise Exception("quota exceeded")
            return "ok"

        with patch.object(
            pf,
            "get_fallback_chain",
            return_value=["google-genai:gemini-2.5-flash", "cohere:command-a"],
        ):
            out = await pf.try_with_fallback(fn, "openai:gpt-4o")
        assert out == "ok"

    async def test_exhausts_raises_quota(self):
        async def fn(mid):
            raise Exception("429 quota")

        with patch.object(
            pf, "get_fallback_chain", return_value=["google-genai:gemini-2.5-flash"]
        ):
            with pytest.raises(pf.QuotaExhaustedError):
                await pf.try_with_fallback(fn, "openai:gpt-4o")

    async def test_empty_chain_raises_quota(self):
        async def fn(mid):
            raise Exception("rate limit")

        with patch.object(pf, "get_fallback_chain", return_value=[]):
            with pytest.raises(pf.QuotaExhaustedError):
                await pf.try_with_fallback(fn, "openai:gpt-4o")

    async def test_non_quota_propagates_immediately(self):
        calls = []

        async def fn(mid):
            calls.append(mid)
            raise ValueError("boom")

        with patch.object(
            pf, "get_fallback_chain", return_value=["google-genai:gemini-2.5-flash"]
        ):
            with pytest.raises(ValueError):
                await pf.try_with_fallback(fn, "openai:gpt-4o")
        assert calls == ["openai:gpt-4o"]  # não tentou fallback


# ---------------------------------------------------------------------------
# FallbackChatModel — LLM do chat com fallback de provider (A2)
# ---------------------------------------------------------------------------


class _FakeLLM:
    """LLM fake: astream/ainvoke configuráveis para simular quota/sucesso."""

    def __init__(
        self,
        *,
        chunks: list[str] | None = None,
        stream_error: Exception | None = None,
        error_after: int = 0,
        invoke_result: object = None,
        invoke_error: Exception | None = None,
    ) -> None:
        self._chunks = chunks or []
        self._stream_error = stream_error
        self._error_after = error_after
        self._invoke_result = invoke_result
        self._invoke_error = invoke_error
        self.bound_with: object = None

    async def astream(self, messages, stop=None, **kwargs):
        from langchain_core.messages import AIMessageChunk

        for i, c in enumerate(self._chunks):
            if self._stream_error is not None and i >= self._error_after:
                raise self._stream_error
            yield AIMessageChunk(content=c)
        if self._stream_error is not None and self._error_after >= len(self._chunks):
            raise self._stream_error

    async def ainvoke(self, messages, stop=None, **kwargs):
        if self._invoke_error is not None:
            raise self._invoke_error
        return self._invoke_result

    def bind_tools(self, tools, **kwargs):
        self.bound_with = tools
        return self


def _loader(mapping: dict[str, _FakeLLM]):
    def _load(mid: str) -> _FakeLLM:
        return mapping[mid]

    return _load


class TestFallbackChatModel:
    def test_llm_type(self):
        from backend.services.fallback_chat_model import FallbackChatModel

        assert FallbackChatModel(primary_model_id="p")._llm_type == "vectora-fallback"

    async def test_no_chain_delegates_to_primary(self):
        from langchain_core.messages import HumanMessage

        from backend.services.fallback_chat_model import FallbackChatModel

        primary = _FakeLLM(chunks=["he", "llo"])
        fcm = FallbackChatModel(primary_model_id="openai:gpt-4o")
        with (
            patch(
                "backend.services.utils.load_llm", _loader({"openai:gpt-4o": primary})
            ),
            patch.object(pf, "get_fallback_chain", return_value=[]),
        ):
            out = [c async for c in fcm._astream([HumanMessage(content="hi")])]
        assert "".join(str(c.message.content) for c in out) == "hello"

    async def test_quota_before_first_chunk_switches(self):
        from langchain_core.messages import HumanMessage

        from backend.services.fallback_chat_model import FallbackChatModel

        pf.drain_switches()
        primary = _FakeLLM(chunks=[], stream_error=Exception("429 quota"))
        fb = _FakeLLM(chunks=["ok"])
        fcm = FallbackChatModel(primary_model_id="openai:gpt-4o")
        with (
            patch(
                "backend.services.utils.load_llm",
                _loader({"openai:gpt-4o": primary, "cohere:command-a": fb}),
            ),
            patch.object(pf, "get_fallback_chain", return_value=["cohere:command-a"]),
        ):
            out = [c async for c in fcm._astream([HumanMessage(content="hi")])]
        assert "".join(str(c.message.content) for c in out) == "ok"
        assert pf.drain_switches() == [
            {"from": "openai:gpt-4o", "to": "cohere:command-a"}
        ]

    async def test_quota_after_chunk_reraises(self):
        from langchain_core.messages import HumanMessage

        from backend.services.fallback_chat_model import FallbackChatModel

        primary = _FakeLLM(chunks=["a"], stream_error=Exception("429"), error_after=1)
        fcm = FallbackChatModel(primary_model_id="openai:gpt-4o")
        with (
            patch(
                "backend.services.utils.load_llm", _loader({"openai:gpt-4o": primary})
            ),
            patch.object(pf, "get_fallback_chain", return_value=["cohere:command-a"]),
        ):
            with pytest.raises(Exception, match="429"):
                _ = [c async for c in fcm._astream([HumanMessage(content="hi")])]

    async def test_non_quota_reraises_immediately(self):
        from langchain_core.messages import HumanMessage

        from backend.services.fallback_chat_model import FallbackChatModel

        primary = _FakeLLM(chunks=[], stream_error=ValueError("boom"))
        fcm = FallbackChatModel(primary_model_id="openai:gpt-4o")
        with (
            patch(
                "backend.services.utils.load_llm", _loader({"openai:gpt-4o": primary})
            ),
            patch.object(pf, "get_fallback_chain", return_value=["cohere:command-a"]),
        ):
            with pytest.raises(ValueError):
                _ = [c async for c in fcm._astream([HumanMessage(content="hi")])]

    async def test_all_exhausted_raises_quota(self):
        from langchain_core.messages import HumanMessage

        from backend.services.fallback_chat_model import FallbackChatModel

        a = _FakeLLM(chunks=[], stream_error=Exception("quota"))
        b = _FakeLLM(chunks=[], stream_error=Exception("rate limit"))
        fcm = FallbackChatModel(primary_model_id="openai:gpt-4o")
        with (
            patch(
                "backend.services.utils.load_llm",
                _loader({"openai:gpt-4o": a, "cohere:command-a": b}),
            ),
            patch.object(pf, "get_fallback_chain", return_value=["cohere:command-a"]),
        ):
            with pytest.raises(pf.QuotaExhaustedError):
                _ = [c async for c in fcm._astream([HumanMessage(content="hi")])]

    async def test_agenerate_switches_on_quota(self):
        from langchain_core.messages import AIMessage, HumanMessage

        from backend.services.fallback_chat_model import FallbackChatModel

        pf.drain_switches()
        primary = _FakeLLM(invoke_error=Exception("429 RESOURCE_EXHAUSTED"))
        fb = _FakeLLM(invoke_result=AIMessage(content="resposta"))
        fcm = FallbackChatModel(primary_model_id="openai:gpt-4o")
        with (
            patch(
                "backend.services.utils.load_llm",
                _loader({"openai:gpt-4o": primary, "cohere:command-a": fb}),
            ),
            patch.object(pf, "get_fallback_chain", return_value=["cohere:command-a"]),
        ):
            res = await fcm._agenerate([HumanMessage(content="hi")])
        assert res.generations[0].message.content == "resposta"
        assert pf.drain_switches() == [
            {"from": "openai:gpt-4o", "to": "cohere:command-a"}
        ]

    async def test_agenerate_non_quota_reraises(self):
        from langchain_core.messages import HumanMessage

        from backend.services.fallback_chat_model import FallbackChatModel

        primary = _FakeLLM(invoke_error=ValueError("boom"))
        fcm = FallbackChatModel(primary_model_id="openai:gpt-4o")
        with (
            patch(
                "backend.services.utils.load_llm", _loader({"openai:gpt-4o": primary})
            ),
            patch.object(pf, "get_fallback_chain", return_value=[]),
        ):
            with pytest.raises(ValueError):
                await fcm._agenerate([HumanMessage(content="hi")])

    def test_bind_tools_returns_new_with_tools(self):
        from backend.services.fallback_chat_model import FallbackChatModel

        fcm = FallbackChatModel(primary_model_id="openai:gpt-4o")
        tools = [{"name": "t1"}]
        bound = fcm.bind_tools(tools)
        assert bound is not fcm
        assert bound.primary_model_id == "openai:gpt-4o"
        assert bound.bound_tools == tools

    async def test_transient_before_first_chunk_switches(self):
        """Timeout/conexão antes de qualquer chunk deve acionar o próximo provider."""
        from langchain_core.messages import HumanMessage

        from backend.services.fallback_chat_model import FallbackChatModel

        pf.drain_switches()
        primary = _FakeLLM(chunks=[], stream_error=Exception("ReadTimeout connecting"))
        fb = _FakeLLM(chunks=["ok"])
        fcm = FallbackChatModel(primary_model_id="openai:gpt-4o")
        with (
            patch(
                "backend.services.utils.load_llm",
                _loader({"openai:gpt-4o": primary, "cohere:command-a": fb}),
            ),
            patch.object(pf, "get_fallback_chain", return_value=["cohere:command-a"]),
        ):
            out = [c async for c in fcm._astream([HumanMessage(content="hi")])]
        assert "".join(str(c.message.content) for c in out) == "ok"
        assert pf.drain_switches() == [
            {"from": "openai:gpt-4o", "to": "cohere:command-a"}
        ]

    async def test_transient_after_chunk_reraises(self):
        """Timeout após o primeiro chunk ser streamado não faz fallback — resposta parcial."""
        from langchain_core.messages import HumanMessage

        from backend.services.fallback_chat_model import FallbackChatModel

        primary = _FakeLLM(
            chunks=["a"], stream_error=Exception("timeout"), error_after=1
        )
        fcm = FallbackChatModel(primary_model_id="openai:gpt-4o")
        with (
            patch(
                "backend.services.utils.load_llm", _loader({"openai:gpt-4o": primary})
            ),
            patch.object(pf, "get_fallback_chain", return_value=["cohere:command-a"]),
        ):
            with pytest.raises(Exception, match="timeout"):
                _ = [c async for c in fcm._astream([HumanMessage(content="hi")])]

    async def test_agenerate_transient_switches(self):
        """Timeout em _agenerate aciona o próximo provider."""
        from langchain_core.messages import AIMessage, HumanMessage

        from backend.services.fallback_chat_model import FallbackChatModel

        pf.drain_switches()
        primary = _FakeLLM(invoke_error=Exception("ConnectTimeout"))
        fb = _FakeLLM(invoke_result=AIMessage(content="fallback ok"))
        fcm = FallbackChatModel(primary_model_id="openai:gpt-4o")
        with (
            patch(
                "backend.services.utils.load_llm",
                _loader({"openai:gpt-4o": primary, "cohere:command-a": fb}),
            ),
            patch.object(pf, "get_fallback_chain", return_value=["cohere:command-a"]),
        ):
            res = await fcm._agenerate([HumanMessage(content="hi")])
        assert res.generations[0].message.content == "fallback ok"

    def test_bind_tools_propagates_to_inner(self):
        from backend.services.fallback_chat_model import FallbackChatModel

        primary = _FakeLLM(chunks=["x"])
        bound = FallbackChatModel(primary_model_id="openai:gpt-4o").bind_tools(
            [{"name": "t1"}]
        )
        with patch(
            "backend.services.utils.load_llm",
            _loader({"openai:gpt-4o": primary}),
        ):
            inner = bound._inner("openai:gpt-4o")
        assert inner is primary
        assert primary.bound_with == [{"name": "t1"}]
