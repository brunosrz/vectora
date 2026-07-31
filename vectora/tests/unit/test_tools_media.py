"""Tools de mídia — geração de imagem e voz pelo provider ativo.

Invariante central coberto aqui: a tool **nunca** troca de provider por
conta própria. Se o modelo escolhido não gera imagem, o certo é avisar —
gerar em outro lugar chamaria (e cobraria) uma API que o usuário não pediu.
Cada caminho feliz tem o par de erro/borda no mesmo teste (CLAUDE.md §18).
"""

from __future__ import annotations

import json

import pytest
from langchain_core.runnables import RunnableConfig

from backend.settings import provider_supports
from backend.tools import media


def _cfg(model: str) -> RunnableConfig:
    return {"configurable": {"model": model, "thread_id": "t-media"}}


# ---------------------------------------------------------------------------
# provider_supports — matriz de capacidades
# ---------------------------------------------------------------------------


def test_provider_supports_resolve_capacidade_por_provider_fixo():
    # Happy: providers que fazem imagem/voz de verdade.
    assert provider_supports("openai", "image") is True
    assert provider_supports("google-genai", "tts") is True
    assert provider_supports("cohere", "reranker") is True

    # Erro/borda: provider que NÃO faz — precisa dar False, senão a tool
    # tentaria chamar um SDK que não tem esse endpoint.
    assert provider_supports("anthropic", "image") is False
    assert provider_supports("cohere", "image") is False
    assert provider_supports("provider-que-nao-existe", "image") is False


def test_provider_supports_gateway_depende_do_modelo_configurado(monkeypatch):
    from backend.settings import settings

    # Erro/borda primeiro: sem modelo configurado a capacidade não existe.
    monkeypatch.setattr(settings, "ollama_image_model", None, raising=False)
    assert provider_supports("ollama", "image") is False

    # Happy: com modelo escolhido pelo usuário, passa a existir.
    monkeypatch.setattr(settings, "ollama_image_model", "algum-modelo", raising=False)
    assert provider_supports("ollama", "image") is True

    # Borda: string vazia conta como não configurado (não como "existe").
    monkeypatch.setattr(settings, "openrouter_tts_model", "", raising=False)
    assert provider_supports("openrouter", "tts") is False


# ---------------------------------------------------------------------------
# generate_image
# ---------------------------------------------------------------------------


def test_generate_image_provider_sem_suporte_avisa_e_nao_chama_sdk(monkeypatch):
    chamou = {"sdk": False}

    def _nunca(*_a, **_k):
        chamou["sdk"] = True
        raise AssertionError("SDK não deveria ser chamado")

    monkeypatch.setattr(media, "_generate_image_bytes", _nunca)

    out = json.loads(
        media.generate_image.invoke({"prompt": "um gato"}, _cfg("cohere:command-r"))
    )

    assert "error" in out
    assert "não suporta" in out["error"]
    # O ponto do teste: falhou ANTES de tocar em qualquer SDK — nunca
    # tentou gerar em outro provider pra "resolver" sozinho.
    assert chamou["sdk"] is False


def test_generate_image_happy_path_persiste_arquivo(monkeypatch, tmp_path):
    monkeypatch.setattr(media, "_media_dir", lambda _s: tmp_path / "media")
    monkeypatch.setattr(media, "_generate_image_bytes", lambda *_a: b"\x89PNG-fake")

    out = json.loads(
        media.generate_image.invoke({"prompt": "um gato"}, _cfg("openai:gpt-5"))
    )

    assert "error" not in out
    assert out["provider"] == "openai"
    assert out["bytes"] == len(b"\x89PNG-fake")
    from pathlib import Path

    assert Path(out["path"]).read_bytes() == b"\x89PNG-fake"


def test_generate_image_prompt_vazio_e_sdk_quebrado_viram_erro_tipado(
    monkeypatch, tmp_path
):
    monkeypatch.setattr(media, "_media_dir", lambda _s: tmp_path / "media")

    # Erro/borda 1: prompt vazio nunca chega no SDK.
    vazio = json.loads(
        media.generate_image.invoke({"prompt": "   "}, _cfg("openai:gpt-5"))
    )
    assert "error" in vazio

    # Erro/borda 2: SDK explodindo vira string de erro, não exceção
    # propagada (CLAUDE.md regra 11 — falha de tool não derruba o grafo).
    def _explode(*_a):
        raise RuntimeError("cota estourada")

    monkeypatch.setattr(media, "_generate_image_bytes", _explode)
    quebrado = json.loads(
        media.generate_image.invoke({"prompt": "um gato"}, _cfg("openai:gpt-5"))
    )
    assert "error" in quebrado
    assert "cota estourada" in quebrado["error"]

    # Erro/borda 3: provider devolvendo vazio não grava arquivo de 0 byte.
    monkeypatch.setattr(media, "_generate_image_bytes", lambda *_a: b"")
    vazio_sdk = json.loads(
        media.generate_image.invoke({"prompt": "um gato"}, _cfg("openai:gpt-5"))
    )
    assert "error" in vazio_sdk


# ---------------------------------------------------------------------------
# text_to_speech
# ---------------------------------------------------------------------------


def test_text_to_speech_sem_suporte_avisa_com_suporte_persiste(monkeypatch, tmp_path):
    monkeypatch.setattr(media, "_media_dir", lambda _s: tmp_path / "media")

    # Erro/borda: Anthropic não sintetiza voz.
    negado = json.loads(
        media.text_to_speech.invoke({"text": "olá"}, _cfg("anthropic:claude"))
    )
    assert "error" in negado

    # Happy: OpenAI sintetiza.
    monkeypatch.setattr(media, "_synthesize_speech_bytes", lambda *_a: b"ID3-fake")
    ok = json.loads(media.text_to_speech.invoke({"text": "olá"}, _cfg("openai:gpt-5")))
    assert "error" not in ok
    assert ok["bytes"] == len(b"ID3-fake")


def test_text_to_speech_texto_vazio_e_audio_vazio_sao_rejeitados(monkeypatch, tmp_path):
    monkeypatch.setattr(media, "_media_dir", lambda _s: tmp_path / "media")

    vazio = json.loads(
        media.text_to_speech.invoke({"text": "  "}, _cfg("openai:gpt-5"))
    )
    assert "error" in vazio

    monkeypatch.setattr(media, "_synthesize_speech_bytes", lambda *_a: b"")
    sem_audio = json.loads(
        media.text_to_speech.invoke({"text": "olá"}, _cfg("openai:gpt-5"))
    )
    assert "error" in sem_audio


# ---------------------------------------------------------------------------
# Resolução de provider
# ---------------------------------------------------------------------------


def test_provider_vem_do_config_da_sessao_nao_do_global(monkeypatch):
    """A sessão pode ter trocado de modelo em runtime — vale o que está no
    config daquela conversa, não a preferência global."""

    class _Global:
        active_provider = "cohere"

    monkeypatch.setattr(
        "backend.workspace.runtime_settings.runtime_settings", _Global()
    )

    # Happy: config manda.
    assert media._active_provider(_cfg("openai:gpt-5")) == "openai"

    # Erro/borda: sem config (ou sem modelo no config) cai no global —
    # nunca retorna vazio silenciosamente quando há um provider ativo.
    assert media._active_provider(None) == "cohere"
    assert media._active_provider({"configurable": {}}) == "cohere"


@pytest.mark.parametrize("capability", ["image", "tts"])
def test_nenhuma_tool_de_midia_troca_de_provider_sozinha(capability, monkeypatch):
    """Regressão explícita do invariante do sprint: mesmo com outro provider
    perfeitamente capaz configurado, a tool recusa em vez de desviar."""
    from backend.settings import settings

    monkeypatch.setattr(settings, "ollama_image_model", "modelo-capaz", raising=False)
    monkeypatch.setattr(settings, "ollama_tts_model", "modelo-capaz", raising=False)

    tool = media.generate_image if capability == "image" else media.text_to_speech
    payload = {"prompt": "x"} if capability == "image" else {"text": "x"}

    out = json.loads(tool.invoke({**payload}, _cfg("anthropic:claude")))

    assert "error" in out
    # Recusou em vez de desviar: nenhum arquivo foi gerado e nenhum outro
    # provider aparece como tendo atendido a chamada. (A mensagem *cita*
    # Ollama como sugestão de configuração — isso é orientação pro usuário,
    # não sinal de que a tool gerou lá por conta própria.)
    assert "path" not in out
    assert out.get("provider") is None


# ---------------------------------------------------------------------------
# Modelo escolhido na UI vs. env var
# ---------------------------------------------------------------------------


def test_escolha_da_ui_vence_a_env_var(monkeypatch):
    """Sem essa precedência, quem configurou por env nunca conseguiria trocar
    de modelo pela interface: a env sempre ganharia e a UI pareceria não
    salvar."""
    from backend.settings import configured_gateway_model, settings
    from backend.workspace.runtime_settings import runtime_settings

    monkeypatch.setattr(settings, "ollama_image_model", "modelo-da-env", raising=False)

    # Só env configurada: é ela que vale.
    monkeypatch.setattr(
        type(runtime_settings), "media_settings", property(lambda _s: {})
    )
    assert configured_gateway_model("ollama", "image") == "modelo-da-env"

    # Happy: usuário escolheu na UI -> a escolha vence.
    monkeypatch.setattr(
        type(runtime_settings),
        "media_settings",
        property(lambda _s: {"ollama_image_model": "modelo-da-ui"}),
    )
    assert configured_gateway_model("ollama", "image") == "modelo-da-ui"

    # Erro/borda: escolha vazia na UI **não** mascara a env — limpar o campo
    # devolve o controle pra env var em vez de desligar a capacidade.
    monkeypatch.setattr(
        type(runtime_settings),
        "media_settings",
        property(lambda _s: {"ollama_image_model": "   "}),
    )
    assert configured_gateway_model("ollama", "image") == "modelo-da-env"

    # Erro/borda: sem nenhum dos dois, a capacidade não existe.
    monkeypatch.setattr(settings, "ollama_image_model", None, raising=False)
    monkeypatch.setattr(
        type(runtime_settings), "media_settings", property(lambda _s: {})
    )
    assert configured_gateway_model("ollama", "image") == ""
    from backend.settings import provider_supports

    assert provider_supports("ollama", "image") is False


def test_runtime_settings_indisponivel_cai_na_env_sem_estourar(monkeypatch):
    """Erro/borda: uma checagem de capacidade não pode explodir só porque o
    runtime_settings ainda não subiu (boot muito cedo, teste isolado)."""
    import backend.settings as settings_mod
    from backend.settings import settings

    monkeypatch.setattr(settings, "openrouter_tts_model", "voz-da-env", raising=False)

    class _Boom:
        @property
        def media_settings(self):
            raise RuntimeError("runtime_settings não inicializado")

    monkeypatch.setattr("backend.workspace.runtime_settings.runtime_settings", _Boom())
    assert settings_mod.configured_gateway_model("openrouter", "tts") == "voz-da-env"


def test_reranker_type_recusa_provider_sem_api_de_rerank():
    """Só entra provider com endpoint de rerank de verdade.

    O OpenRouter tem: ``POST /api/v1/rerank`` (`model`, `query`, `documents`,
    `top_n`). Este teste já excluiu o OpenRouter por uma afirmação errada de
    que ele seria só proxy de chat. O Ollama segue fora — esse realmente não
    tem o endpoint.
    """
    import pydantic

    from backend.settings import Settings

    # Happy: os providers que de fato têm API de rerank.
    assert Settings(reranker_type="cohere").reranker_type == "cohere"
    assert Settings(reranker_type="voyage").reranker_type == "voyage"
    assert Settings(reranker_type="openrouter").reranker_type == "openrouter"

    # Erro/borda: provider sem rerank é rejeitado na validação, não ignorado
    # silenciosamente lá na frente em `_build_reranker`.
    for invalido in ("ollama", "qualquer-coisa"):
        with pytest.raises(pydantic.ValidationError):
            Settings(reranker_type=invalido)


class TestOpenRouterLigadoNasTools:
    """`generate_image`/`text_to_speech` com OpenRouter ativo deixavam de
    levantar `NotImplementedError` — a UI oferecia o modelo e a geração
    falhava depois, que é pior que não oferecer."""

    @staticmethod
    def _sem_key(monkeypatch):
        from backend.settings import settings as _s

        monkeypatch.setattr(_s, "openrouter_api_key", "", raising=False)

    def test_imagem_via_openrouter_chama_o_cliente_nativo(self, monkeypatch):
        from backend.settings import settings as _s
        from backend.tools import media

        monkeypatch.setattr(_s, "openrouter_api_key", "sk-or-test", raising=False)
        monkeypatch.setattr(
            "backend.settings.configured_gateway_model",
            lambda _p, _c: "openai/gpt-image-1",
        )

        async def _fake(_client, *, model, prompt, **_kw):
            assert model == "openai/gpt-image-1"
            assert prompt == "um gato"
            return b"\x89PNG-fake"

        monkeypatch.setattr("backend.llm.openrouter.media.generate_image_bytes", _fake)

        assert media._generate_image_bytes("openrouter", "um gato") == b"\x89PNG-fake"

    def test_tts_via_openrouter_chama_o_cliente_nativo(self, monkeypatch):
        from backend.settings import settings as _s
        from backend.tools import media

        monkeypatch.setattr(_s, "openrouter_api_key", "sk-or-test", raising=False)
        monkeypatch.setattr(
            "backend.settings.configured_gateway_model",
            lambda _p, _c: "openai/gpt-4o-mini-tts",
        )

        async def _fake(_client, *, model, text, voice, **_kw):
            assert voice == "alloy"
            return b"audio-cru"

        monkeypatch.setattr(
            "backend.llm.openrouter.media.synthesize_speech_bytes", _fake
        )

        assert (
            media._synthesize_speech_bytes("openrouter", "oi", "alloy") == b"audio-cru"
        )

    def test_provider_ainda_sem_cliente_segue_levantando(self, monkeypatch):
        """Erro/borda: o Ollama continua sem cliente de imagem. Ligar o
        OpenRouter não pode ter transformado o erro claro num silêncio."""
        from backend.tools import media

        monkeypatch.setattr(
            "backend.settings.configured_gateway_model", lambda _p, _c: "algum-modelo"
        )

        with pytest.raises(NotImplementedError, match="ollama"):
            media._generate_image_bytes("ollama", "x")
