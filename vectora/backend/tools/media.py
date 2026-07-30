"""Geração de mídia (imagem, voz) pelo provider que o usuário já escolheu.

Regra central: **nunca trocar de provider por conta própria**. Se o modelo
selecionado não gera imagem, a tool devolve um erro legível e o agente
avisa — gerar em outro provider chamaria uma API que o usuário não pediu
(e cobraria por ela). Mesmo princípio que `chat.py` já aplica pra visão
(`VISION_CAPABLE_PROVIDERS`).

O binário sai como arquivo em ``~/.vectora/artifacts/{session_id}/media/``
— mesma raiz de `create_artifact`, mas em subpasta própria: artifact é
markdown versionado, mídia é binário imutável (regerar produz um arquivo
novo, não uma versão do anterior).
"""

from __future__ import annotations

import base64
import json
import logging
from datetime import UTC, datetime
from pathlib import Path
from typing import Annotated, Any
from uuid import uuid4

from langchain_core.runnables import RunnableConfig
from langchain_core.tools import InjectedToolArg, tool

logger = logging.getLogger(__name__)


def _session_id(config: RunnableConfig | None) -> str:
    """thread_id do config — nunca do texto do prompt (mesma razão de
    `fs.py::_session_id_from_config`: o system prompt é cacheado por
    workspace, o thread real não aparece nele)."""
    return (
        str((config.get("configurable") or {}).get("thread_id", "")) if config else ""
    )


def _active_provider(config: RunnableConfig | None) -> str:
    """Provider do modelo ativo da sessão.

    Lê do config primeiro (a sessão pode ter trocado de modelo em runtime)
    e só cai no runtime_settings quando o config não traz — assim a tool
    respeita a escolha feita naquela conversa, não a global.
    """
    if config:
        configurable = config.get("configurable") or {}
        model = str(configurable.get("model", ""))
        if ":" in model:
            return model.split(":", 1)[0]
    try:
        from backend.workspace.runtime_settings import runtime_settings

        return runtime_settings.active_provider
    except Exception:
        return ""


def _media_dir(session_id: str) -> Path:
    return (
        Path.home() / ".vectora" / "artifacts" / (session_id or "sem-sessao") / "media"
    )


def _unsupported(provider: str, capability: str, hint: str) -> str:
    """Erro legível pro LLM relaiar — nunca uma exceção crua."""
    return json.dumps(
        {
            "error": (
                f"o provider ativo ({provider or 'nenhum'}) não suporta "
                f"{capability}. {hint} Não troque de provider por conta "
                "própria — avise o usuário e deixe ele escolher."
            )
        },
        ensure_ascii=False,
    )


def _persist(session_id: str, data: bytes, suffix: str) -> Path:
    directory = _media_dir(session_id)
    directory.mkdir(parents=True, exist_ok=True)
    path = directory / f"{datetime.now(UTC):%Y%m%d-%H%M%S}-{uuid4().hex[:8]}{suffix}"
    path.write_bytes(data)
    return path


def _generate_image_bytes(provider: str, prompt: str) -> bytes:
    """Chama o SDK do provider ativo. Cada provider expõe geração de imagem
    de um jeito diferente — o mapeamento fica aqui, isolado da tool."""
    from backend.settings import settings

    if provider == "openai":
        from openai import OpenAI

        client = OpenAI(api_key=settings.openai_api_key)
        result = client.images.generate(model="gpt-image-1", prompt=prompt, n=1)
        # O SDK tipa `data` como opcional: resposta sem imagem é possível
        # (filtro de conteúdo, por exemplo) e vira erro claro no caller.
        entries = result.data or []
        b64 = entries[0].b64_json if entries else None
        return base64.b64decode(b64) if b64 else b""

    if provider == "google-genai":
        from google import genai

        client = genai.Client(api_key=settings.google_api_key)
        result = client.models.generate_images(
            model="imagen-4.0-generate-001", prompt=prompt
        )
        images = result.generated_images or []
        if not images:
            return b""
        image = images[0].image
        raw = getattr(image, "image_bytes", None) if image else None
        return bytes(raw) if raw else b""

    # Ollama/OpenRouter: modelo escolhido pelo usuário (ver settings).
    model = getattr(settings, f"{provider}_image_model", None)
    raise NotImplementedError(
        f"geração de imagem via {provider} (modelo {model}) ainda não tem "
        "cliente implementado"
    )


def _synthesize_speech_bytes(provider: str, text: str, voice: str) -> bytes:
    from backend.settings import settings

    if provider == "openai":
        from openai import OpenAI

        client = OpenAI(api_key=settings.openai_api_key)
        response = client.audio.speech.create(
            model="gpt-4o-mini-tts", voice=voice or "alloy", input=text
        )
        return response.read()

    if provider == "google-genai":
        from google import genai

        client = genai.Client(api_key=settings.google_api_key)
        result = client.models.generate_content(
            model="gemini-2.5-flash-preview-tts", contents=text
        )
        # Toda a cadeia é opcional no SDK — resposta bloqueada/vazia é um
        # caminho real, não um "não deveria acontecer".
        candidates = result.candidates or []
        content = candidates[0].content if candidates else None
        parts = (content.parts if content else None) or []
        inline = parts[0].inline_data if parts else None
        raw = inline.data if inline else None
        return bytes(raw) if raw else b""

    model = getattr(settings, f"{provider}_tts_model", None)
    raise NotImplementedError(
        f"síntese de voz via {provider} (modelo {model}) ainda não tem "
        "cliente implementado"
    )


@tool(
    extras={
        "render_hint": "image",
        "category": "media",
        "destructive": False,
        "icon": "image",
    }
)
def generate_image(
    prompt: str,
    config: Annotated[RunnableConfig, InjectedToolArg] = None,  # ty: ignore[invalid-parameter-default]
) -> str:
    """Gera uma imagem a partir de uma descrição, usando o modelo ativo.

    Só funciona se o provider selecionado gera imagem (Gemini e OpenAI
    geram; Anthropic e Cohere não). Com Ollama/OpenRouter, depende de o
    usuário ter configurado um modelo de imagem nas Settings.

    Se o provider ativo não suporta, esta tool devolve um erro explicando —
    relaie a mensagem ao usuário e NÃO tente gerar com outro provider.

    Args:
        prompt: Descrição do que desenhar, em linguagem natural.

    Returns:
        JSON com o path do arquivo gerado, ou com `error` se o provider
        ativo não gera imagem.
    """
    provider = _active_provider(config)
    try:
        from backend.settings import provider_supports

        if not provider_supports(provider, "image"):
            return _unsupported(
                provider,
                "geração de imagem",
                "Troque para um modelo Gemini/OpenAI, ou configure um "
                "modelo de imagem em Settings (Ollama/OpenRouter).",
            )
        if not prompt.strip():
            return json.dumps({"error": "prompt vazio — descreva a imagem"})

        data = _generate_image_bytes(provider, prompt)
        if not data:
            return json.dumps({"error": "provider devolveu imagem vazia"})
        path = _persist(_session_id(config), data, ".png")
        logger.info("generate_image: %s bytes → %s", len(data), path)
        return json.dumps(
            {"path": str(path), "provider": provider, "bytes": len(data)},
            ensure_ascii=False,
        )
    except Exception as exc:
        logger.exception("generate_image: falha", extra={"provider": provider})
        return json.dumps(
            {"error": f"falha ao gerar imagem: {exc}"}, ensure_ascii=False
        )


@tool(
    extras={
        "render_hint": "audio",
        "category": "media",
        "destructive": False,
        "icon": "volume-2",
    }
)
def text_to_speech(
    text: str,
    voice: str = "",
    config: Annotated[RunnableConfig, InjectedToolArg] = None,  # ty: ignore[invalid-parameter-default]
) -> str:
    """Converte texto em áudio falado, usando o modelo ativo.

    Mesma regra de `generate_image`: se o provider ativo não faz síntese de
    voz, devolve erro explicando — não troque de provider sozinho.

    Args:
        text: Texto a ser falado.
        voice: Nome da voz (opcional; cada provider tem as suas).

    Returns:
        JSON com o path do áudio gerado, ou com `error`.
    """
    provider = _active_provider(config)
    try:
        from backend.settings import provider_supports

        if not provider_supports(provider, "tts"):
            return _unsupported(
                provider,
                "síntese de voz",
                "Troque para um modelo Gemini/OpenAI, ou configure um "
                "modelo de voz em Settings (Ollama/OpenRouter).",
            )
        if not text.strip():
            return json.dumps({"error": "texto vazio — nada a falar"})

        data = _synthesize_speech_bytes(provider, text, voice)
        if not data:
            return json.dumps({"error": "provider devolveu áudio vazio"})
        path = _persist(_session_id(config), data, ".mp3")
        logger.info("text_to_speech: %s bytes → %s", len(data), path)
        return json.dumps(
            {"path": str(path), "provider": provider, "bytes": len(data)},
            ensure_ascii=False,
        )
    except Exception as exc:
        logger.exception("text_to_speech: falha", extra={"provider": provider})
        return json.dumps({"error": f"falha ao gerar áudio: {exc}"}, ensure_ascii=False)


MEDIA_TOOLS: list[Any] = [generate_image, text_to_speech]

__all__ = ["MEDIA_TOOLS", "generate_image", "text_to_speech"]
