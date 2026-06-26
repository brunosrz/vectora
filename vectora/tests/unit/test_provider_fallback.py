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
