"""Transcrição de áudio (STT) via OpenAI Whisper API.

Usado só para anexos de áudio pré-gravados no chat — o ditado de voz do
input (`use-voice-input.ts`) é 100% client-side via Web Speech API do
browser, sem chamada nenhuma ao backend.
"""

from __future__ import annotations

import logging

import httpx

from backend.settings import settings

logger = logging.getLogger(__name__)

_TRANSCRIPTION_URL = "https://api.openai.com/v1/audio/transcriptions"
_TRANSCRIPTION_MODEL = "whisper-1"
_TIMEOUT_S = 60.0


class TranscriptionError(Exception):
    """Falha ao transcrever um áudio — sem chave configurada ou erro da API."""


async def transcribe_audio(data: bytes, filename: str, mime_type: str) -> str:
    """Transcreve `data` (bytes de áudio) via OpenAI Whisper.

    Args:
        data: Conteúdo binário do arquivo de áudio.
        filename: Nome original do arquivo (usado no multipart e por Whisper
            para inferir o formato).
        mime_type: Content-Type do arquivo.

    Returns:
        Texto transcrito.

    Raises:
        TranscriptionError: Sem `openai_api_key` configurada ou erro da API.
    """
    api_key = settings.openai_api_key
    if not api_key:
        raise TranscriptionError("openai_api_key não configurada")

    try:
        async with httpx.AsyncClient(timeout=_TIMEOUT_S) as client:
            response = await client.post(
                _TRANSCRIPTION_URL,
                headers={"Authorization": f"Bearer {api_key}"},
                files={"file": (filename, data, mime_type)},
                data={"model": _TRANSCRIPTION_MODEL},
            )
        response.raise_for_status()
    except httpx.HTTPError as exc:
        logger.exception("transcribe_audio: falha na chamada à API Whisper")
        raise TranscriptionError(str(exc)) from exc

    return str(response.json().get("text", "")).strip()
