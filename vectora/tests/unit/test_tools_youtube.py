"""``backend/tools/youtube.py`` — transcrição de vídeo (YouTube e outras
plataformas via yt-dlp), transcript-first sem baixar mídia.

Guardado em duas camadas, mesmo padrão de ``test_llm_live.py``:
- Parsers/formatadores puros (``_extract_video_id``/``_format_transcript``)
  e ``get_transcript`` com as chamadas de rede mockadas — sempre rodam,
  fazem parte de ``scons tests``.
- Um teste ``live`` contra um vídeo público real e permanente (o primeiro
  vídeo do YouTube, "Me at the zoo") — só roda via ``scons tests-live``.
"""

from __future__ import annotations

import json
from unittest.mock import AsyncMock, patch

import pytest

from backend.tools.youtube import (
    _extract_video_id,
    _format_transcript,
    get_transcript,
)

# ---------------------------------------------------------------------------
# _extract_video_id — parsing puro
# ---------------------------------------------------------------------------


class TestExtractVideoId:
    def test_reconhece_as_formas_comuns_de_url_e_rejeita_o_que_nao_e_video(self):
        casos = {
            "https://www.youtube.com/watch?v=jNQXAC9IVRw": "jNQXAC9IVRw",
            "https://youtu.be/jNQXAC9IVRw": "jNQXAC9IVRw",
            "https://www.youtube.com/shorts/jNQXAC9IVRw": "jNQXAC9IVRw",
            "https://www.youtube.com/embed/jNQXAC9IVRw": "jNQXAC9IVRw",
            "https://www.youtube.com/watch?v=jNQXAC9IVRw&t=10s": "jNQXAC9IVRw",
            "jNQXAC9IVRw": "jNQXAC9IVRw",  # ID cru
        }
        for url, expected in casos.items():
            assert _extract_video_id(url) == expected, url

        # Erro/borda no mesmo teste: não é vídeo nenhum — não pode inventar
        # um ID nem lançar, só devolver None.
        assert _extract_video_id("https://example.com/nao-e-youtube") is None
        assert _extract_video_id("") is None
        assert _extract_video_id("curto") is None


# ---------------------------------------------------------------------------
# _format_transcript — formatação pura
# ---------------------------------------------------------------------------


class TestFormatTranscript:
    def test_formata_com_timestamps_mmss_e_ignora_entradas_vazias(self):
        entries = [
            {"text": "primeiro", "start": 1.2, "duration": 2.0},
            {"text": "  ", "start": 5.0, "duration": 1.0},  # só espaço — some
            {"text": "depois de um minuto", "start": 61.0, "duration": 3.0},
        ]

        result = _format_transcript(entries)

        assert result == "[00:01] primeiro\n[01:01] depois de um minuto"

        # Erro/borda: lista vazia não pode quebrar, só devolver string vazia.
        assert _format_transcript([]) == ""


# ---------------------------------------------------------------------------
# get_transcript — orquestração (rede mockada)
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
class TestGetTranscript:
    async def test_url_invalida_devolve_erro_sem_tocar_em_rede(self):
        result = json.loads(await get_transcript(url="https://example.com/x"))
        assert "error" in result

    async def test_com_captions_publicas_usa_o_caminho_leve(self, monkeypatch):
        """Caminho feliz: legendas existem — nunca baixa áudio nenhum."""
        import backend.tools.youtube as mod

        monkeypatch.setattr(
            mod,
            "_fetch_captions_sync",
            lambda video_id, languages: [
                {"text": "ola mundo", "start": 0, "duration": 1}
            ],
        )
        chamou_audio = {"sim": False}

        def _fake_download(_url):
            chamou_audio["sim"] = True
            return b"", "audio/webm"

        monkeypatch.setattr(mod, "_download_audio_sync", _fake_download)

        result = json.loads(
            await get_transcript(url="https://www.youtube.com/watch?v=jNQXAC9IVRw")
        )

        assert result["source"] == "captions"
        assert result["video_id"] == "jNQXAC9IVRw"
        assert "[00:00] ola mundo" in result["transcript"]
        assert chamou_audio["sim"] is False

    async def test_sem_captions_cai_pro_fallback_de_audio_sem_baixar_video(
        self, monkeypatch
    ):
        """Erro/borda: vídeo sem legendas (exceção da lib) — cai pro
        fallback de áudio, chamando transcribe_audio (LLM), não algum
        download de vídeo."""
        import backend.tools.youtube as mod

        def _sem_captions(video_id, languages):
            raise RuntimeError("TranscriptsDisabled")

        monkeypatch.setattr(mod, "_fetch_captions_sync", _sem_captions)
        monkeypatch.setattr(
            mod, "_download_audio_sync", lambda _url: (b"audio-bytes", "audio/webm")
        )

        with patch(
            "backend.llm.transcription.transcribe_audio",
            AsyncMock(return_value="transcrito via LLM"),
        ) as mock_transcribe:
            result = json.loads(
                await get_transcript(url="https://www.youtube.com/watch?v=jNQXAC9IVRw")
            )

        assert result["source"] == "audio_fallback"
        assert result["transcript"] == "transcrito via LLM"
        mock_transcribe.assert_called_once()
        # Confirma que o mime_type/nome batem com o que o download real devolveu.
        args = mock_transcribe.call_args
        assert args[0][0] == b"audio-bytes"
        assert args[0][2] == "audio/webm"

    async def test_falha_nos_dois_caminhos_vira_erro_tipado(self, monkeypatch):
        """Erro/borda: sem legendas E sem conseguir baixar áudio (ex.: vídeo
        indisponível/geobloqueado) — erro legível, nunca traceback cru."""
        import backend.tools.youtube as mod

        monkeypatch.setattr(
            mod,
            "_fetch_captions_sync",
            lambda *_a: (_ for _ in ()).throw(RuntimeError("sem legendas")),
        )
        monkeypatch.setattr(
            mod,
            "_download_audio_sync",
            lambda _url: (_ for _ in ()).throw(RuntimeError("vídeo indisponível")),
        )

        result = json.loads(
            await get_transcript(url="https://www.youtube.com/watch?v=jNQXAC9IVRw")
        )

        assert "error" in result


# ---------------------------------------------------------------------------
# Live — vídeo público real, sem mock (rede de verdade)
# ---------------------------------------------------------------------------


@pytest.mark.live
@pytest.mark.asyncio
async def test_get_transcript_video_publico_real_via_captions():
    """ "Me at the zoo" (jNQXAC9IVRw) — primeiro vídeo do YouTube, público,
    permanente, com legendas em inglês. Prova o caminho leve fim a fim
    contra a API real, sem baixar áudio/vídeo nenhum."""
    result = json.loads(
        await get_transcript(
            url="https://www.youtube.com/watch?v=jNQXAC9IVRw", language="en"
        )
    )

    assert result["source"] == "captions"
    assert result["video_id"] == "jNQXAC9IVRw"
    assert "elephant" in result["transcript"].lower()
    assert result["transcript"].startswith("[00:")
