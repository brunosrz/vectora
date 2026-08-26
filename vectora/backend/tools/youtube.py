"""YouTube (e outras plataformas suportadas pelo yt-dlp): transcrição
primeiro, sem baixar mídia nenhuma quando possível.

Fluxo: legendas PÚBLICAS do YouTube via API própria (sem baixar áudio/
vídeo — caminho leve e defensável, mesmo padrão que Gemini/Hermes usam por
padrão). Só cai pra baixar áudio (yt-dlp, sem vídeo, sem re-encode — não
depende de ffmpeg vendorizado) + transcrição remota
(`backend/llm/transcription.py`) quando o vídeo não tem legendas.

Baixar VÍDEO do YouTube sem permissão viola os Termos de Uso (não é crime,
mas pode gerar suspensão de conta/ação civil por quebra de contrato) — por
isso o fallback baixa só o stream de ÁUDIO, nunca o vídeo, e só quando
legendas públicas não existem.
"""

from __future__ import annotations

import asyncio
import json
import logging
import re
import tempfile
from pathlib import Path
from typing import Any

from backend.tools.registry import ToolExtras, vtool

logger = logging.getLogger(__name__)

_VIDEO_ID_RE = re.compile(r"(?:v=|youtu\.be/|shorts/|embed/)([\w-]{11})")
_BARE_ID_RE = re.compile(r"^[\w-]{11}$")

#: Ordem de preferência quando o chamador não pede um idioma específico.
_DEFAULT_LANGUAGES = ["pt", "pt-BR", "en", "es"]

#: mime_type inferido da extensão real do stream audio-only que o yt-dlp
#: escolher (webm/opus e m4a/aac são os formatos mais comuns).
_MIME_BY_EXT = {
    "webm": "audio/webm",
    "m4a": "audio/mp4",
    "mp3": "audio/mpeg",
    "opus": "audio/opus",
    "ogg": "audio/ogg",
    "wav": "audio/wav",
}


def _extract_video_id(url: str) -> str | None:
    """Aceita URL completa (com `v=`, `youtu.be/`, `/shorts/`, `/embed/`)
    ou o ID de 11 caracteres cru — nunca lança, devolve `None` pra input
    que não é nenhum dos dois."""
    match = _VIDEO_ID_RE.search(url)
    if match:
        return match.group(1)
    candidate = url.strip()
    if _BARE_ID_RE.fullmatch(candidate):
        return candidate
    return None


def _format_transcript(entries: list[dict[str, Any]]) -> str:
    """`[MM:SS] texto` por linha — mesmo formato que o Gemini usa pra
    transcrição de vídeo, familiar pro modelo interpretar timestamps."""
    lines: list[str] = []
    for entry in entries:
        start = int(entry.get("start", 0) or 0)
        minutes, seconds = divmod(start, 60)
        text = str(entry.get("text", "")).strip()
        if text:
            lines.append(f"[{minutes:02d}:{seconds:02d}] {text}")
    return "\n".join(lines)


def _fetch_captions_sync(video_id: str, languages: list[str]) -> list[dict[str, Any]]:
    """Síncrono de propósito (roda em thread via `asyncio.to_thread`) — a
    lib usa `requests` por baixo, sem variante async."""
    from youtube_transcript_api import YouTubeTranscriptApi

    api = YouTubeTranscriptApi()
    fetched = api.fetch(video_id, languages=languages)
    return fetched.to_raw_data()


def _download_audio_sync(url: str) -> tuple[bytes, str]:
    """Baixa só o STREAM DE ÁUDIO (nunca o vídeo) via yt-dlp, sem
    postprocessador de re-encode — evita depender de um binário ffmpeg
    vendorizado (fora do escopo desta tool). Devolve os bytes crus e o
    mime_type inferido da extensão real do stream escolhido pelo yt-dlp
    (webm/opus e m4a/aac são os formatos audio-only mais comuns)."""
    import yt_dlp

    with tempfile.TemporaryDirectory() as tmpdir:
        outtmpl = str(Path(tmpdir) / "audio.%(ext)s")
        opts = {
            "format": "bestaudio/best",
            "outtmpl": outtmpl,
            "quiet": True,
            "no_warnings": True,
            "noplaylist": True,
        }
        with yt_dlp.YoutubeDL(opts) as ydl:
            ydl.download([url])

        files = [p for p in Path(tmpdir).iterdir() if p.is_file()]
        if not files:
            raise RuntimeError("yt-dlp não produziu nenhum arquivo de áudio")
        audio_path = files[0]
        ext = audio_path.suffix.lstrip(".").lower()
        mime_type = _MIME_BY_EXT.get(ext, "application/octet-stream")
        return audio_path.read_bytes(), mime_type


@vtool(
    extras=ToolExtras(
        render_hint="json",
        category="web",
        destructive=False,
        icon="globe",
    )
)
async def get_transcript(url: str, language: str = "") -> str:
    """Obtém a transcrição de um vídeo do YouTube (ou de qualquer
    plataforma suportada pelo yt-dlp — Vimeo, Twitter/X, TikTok, etc.),
    com timestamps `[MM:SS]`.

    Caminho leve primeiro: lê as legendas PÚBLICAS do vídeo — sem baixar
    áudio nem vídeo nenhum. Só baixa o stream de ÁUDIO (nunca vídeo) e
    transcreve via LLM quando o vídeo não tem legendas — mais lento, e usa
    a chave de LLM já configurada (`transcribe_audio`).

    Args:
        url: URL do vídeo, ou o ID de 11 caracteres do YouTube.
        language: Idioma preferido da legenda (ex: "pt", "en"). Vazio tenta
            português e inglês antes de espanhol.

    Returns:
        JSON com `transcript` (texto com timestamps), `source`
        ("captions" ou "audio_fallback") e `video_id`, ou `error`.
    """
    video_id = _extract_video_id(url)
    if not video_id:
        return json.dumps(
            {"error": f"não reconheci um ID de vídeo do YouTube em: {url}"},
            ensure_ascii=False,
        )

    languages = [language] if language else _DEFAULT_LANGUAGES
    try:
        entries = await asyncio.to_thread(_fetch_captions_sync, video_id, languages)
        transcript = _format_transcript(entries)
        if transcript:
            return json.dumps(
                {
                    "transcript": transcript,
                    "source": "captions",
                    "video_id": video_id,
                },
                ensure_ascii=False,
            )
    except Exception as exc:
        logger.info(
            "get_transcript: sem legendas públicas, tentando fallback de áudio",
            extra={"video_id": video_id, "error": str(exc)},
        )

    try:
        from backend.llm.transcription import transcribe_audio

        audio_bytes, mime_type = await asyncio.to_thread(_download_audio_sync, url)
        ext = mime_type.split("/")[-1]
        text = await transcribe_audio(audio_bytes, f"{video_id}.{ext}", mime_type)
        return json.dumps(
            {
                "transcript": text,
                "source": "audio_fallback",
                "video_id": video_id,
            },
            ensure_ascii=False,
        )
    except Exception as exc:
        logger.exception(
            "get_transcript: fallback de áudio falhou", extra={"video_id": video_id}
        )
        return json.dumps(
            {"error": f"não foi possível obter transcrição: {exc}"},
            ensure_ascii=False,
        )
