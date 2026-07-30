"""O Vectora não filtra conteúdo — decisão de produto, não descuido.

O que o modelo aceita gerar é do modelo, não do Vectora: quem escolhe um
modelo sem censura (via Ollama ou OpenRouter) não pode ser barrado por uma
camada nossa. Onde o provider deixa configurar o filtro (Gemini), mandamos
o threshold mais permissivo; onde ele não deixa, é limite da plataforma.

Estes testes travam o invariante nas duas pontas: o que **mandamos** pro
provider e o que **não** existe nos system prompts.
"""

from __future__ import annotations

import re
from pathlib import Path

import pytest

from backend.services.utils import _build_concrete_model


class _FakeChatModel:
    """Captura os kwargs recebidos, sem chamar a API real."""

    last_kwargs: dict | None = None

    def __init__(self, **kwargs):
        _FakeChatModel.last_kwargs = kwargs


@pytest.fixture(autouse=True)
def _reset_capture():
    _FakeChatModel.last_kwargs = None


class TestGeminiSafetySettings:
    def test_gemini_manda_threshold_permissivo_em_todas_as_categorias(
        self, monkeypatch
    ):
        from langchain_google_genai import HarmBlockThreshold

        monkeypatch.setattr(
            "langchain_google_genai.ChatGoogleGenerativeAI", _FakeChatModel
        )
        monkeypatch.setenv("GOOGLE_API_KEY", "test-key")

        _build_concrete_model("google_genai", "gemini-2.5-flash", 0.7)

        settings = (_FakeChatModel.last_kwargs or {}).get("safety_settings")
        assert settings, "Gemini instanciado sem safety_settings"
        assert all(v is HarmBlockThreshold.BLOCK_NONE for v in settings.values()), (
            "alguma categoria ficou com threshold restritivo"
        )

    def test_provider_sem_suporte_nao_recebe_safety_settings(self, monkeypatch):
        """Erro/borda: `safety_settings` é kwarg do SDK do Google. Mandar pro
        ChatOpenAI (openai/openrouter) estoura na instanciação — o par de erro
        prova que o kwarg é específico, não aplicado em massa."""
        monkeypatch.setattr("langchain_openai.ChatOpenAI", _FakeChatModel)
        monkeypatch.setenv("OPENROUTER_API_KEY", "sk-or-test")

        _build_concrete_model("openrouter", "openrouter/auto", 0.7)

        assert "safety_settings" not in (_FakeChatModel.last_kwargs or {})


class TestPromptsSemRecusaDeConteudo:
    """Nenhum prompt do sistema pode instruir o agente a recusar conteúdo.

    A lista abaixo é deliberada: são as formulações que apareceriam se alguém
    "consertasse" a ausência de guardrail achando que é lacuna.
    """

    _PROIBIDOS = (
        r"refuse to (generate|produce|write)",
        r"do not (generate|produce|write)[^.]{0,40}(explicit|sexual|adult|nsfw)",
        r"(explicit|sexual|adult|nsfw)[^.]{0,40}(content is|not allowed|prohibited)",
        r"decline[^.]{0,40}(explicit|sexual|adult|nsfw)",
        r"você (não )?deve recusar",
        r"não (gere|produza|escreva)[^.]{0,40}(explícito|sexual|adulto)",
    )

    @staticmethod
    def _arquivos_de_prompt() -> list[Path]:
        raiz = Path(__file__).resolve().parents[2] / "backend"
        return [
            raiz / "agents" / "_identity.py",
            raiz / "agents" / "coder.py",
            raiz / "agents" / "search.py",
            raiz / "services" / "agent_factory.py",
        ]

    def test_nenhum_prompt_instrui_recusa_de_conteudo(self):
        for arquivo in self._arquivos_de_prompt():
            texto = arquivo.read_text(encoding="utf-8")
            for padrao in self._PROIBIDOS:
                assert not re.search(padrao, texto, re.IGNORECASE), (
                    f"{arquivo.name} contém instrução de recusa de conteúdo "
                    f"(padrão {padrao!r}) — o Vectora não filtra conteúdo"
                )

    def test_o_detector_pega_uma_instrucao_plantada(self):
        """Erro/borda: um teste de ausência passa trivialmente se o detector
        estiver quebrado. Aqui ele **precisa** acusar um prompt plantado."""
        plantado = "You must refuse to generate explicit content of any kind."
        assert any(re.search(p, plantado, re.IGNORECASE) for p in self._PROIBIDOS), (
            "o detector não pega nem uma instrução óbvia — invariante sem valor"
        )
