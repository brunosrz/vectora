"""Transcrição de áudio (STT).

Usado pro ditado de voz no desktop (`TranscribeAudio` endpoint) e pra anexos
de áudio pré-gravados no chat — o ditado de voz do browser
(`use-voice-input.ts`) é 100% client-side via Web Speech API, sem chamada
nenhuma ao backend.

Tenta OpenAI Whisper primeiro (mais preciso pra transcrição pura); sem
``openai_api_key``, cai pro Gemini (audio understanding) usando a mesma
``google_api_key`` já configurada pro chat.
"""

from __future__ import annotations

import logging

import httpx

from backend.settings import settings

logger = logging.getLogger(__name__)

_OPENAI_TRANSCRIPTION_URL = "https://api.openai.com/v1/audio/transcriptions"
_OPENAI_TRANSCRIPTION_MODEL = "whisper-1"
_GEMINI_TRANSCRIPTION_MODEL = "gemini-2.5-flash"
_GEMINI_TRANSCRIPTION_PROMPT = (
    "Transcreva o áudio a seguir literalmente, sem comentários nem "
    "formatação — devolva só o texto falado."
)
_TIMEOUT_S = 60.0


class TranscriptionError(Exception):
    """Falha ao transcrever um áudio — sem chave configurada ou erro da API."""


async def transcribe_audio(data: bytes, filename: str, mime_type: str) -> str:
    """Transcreve `data` (bytes de áudio) via OpenAI Whisper ou Gemini.

    Args:
        data: Conteúdo binário do arquivo de áudio.
        filename: Nome original do arquivo (usado no multipart do Whisper).
        mime_type: Content-Type do arquivo.

    Returns:
        Texto transcrito.

    Raises:
        TranscriptionError: Sem chave configurada (nem OpenAI nem Google) ou
            erro da API.
    """
    if settings.openai_api_key:
        return await _transcribe_openai(data, filename, mime_type)
    if settings.google_api_key:
        return await _transcribe_gemini(data, mime_type)
    raise TranscriptionError(
        "nenhuma chave de transcrição configurada (openai_api_key ou google_api_key)"
    )


async def _transcribe_openai(data: bytes, filename: str, mime_type: str) -> str:
    try:
        async with httpx.AsyncClient(timeout=_TIMEOUT_S) as client:
            response = await client.post(
                _OPENAI_TRANSCRIPTION_URL,
                headers={"Authorization": f"Bearer {settings.openai_api_key}"},
                files={"file": (filename, data, mime_type)},
                data={"model": _OPENAI_TRANSCRIPTION_MODEL},
            )
        response.raise_for_status()
    except httpx.HTTPError as exc:
        logger.exception("transcribe_audio: falha na chamada à API Whisper")
        raise TranscriptionError(str(exc)) from exc

    return str(response.json().get("text", "")).strip()


async def _transcribe_gemini(data: bytes, mime_type: str) -> str:
    try:
        from google import genai
        from google.genai import types

        client = genai.Client(api_key=settings.google_api_key)
        response = await client.aio.models.generate_content(
            model=_GEMINI_TRANSCRIPTION_MODEL,
            contents=[
                _GEMINI_TRANSCRIPTION_PROMPT,
                types.Part.from_bytes(data=data, mime_type=mime_type),
            ],
        )
    except Exception as exc:
        logger.exception("transcribe_audio: falha na chamada à API Gemini")
        raise TranscriptionError(str(exc)) from exc

    return (response.text or "").strip()
