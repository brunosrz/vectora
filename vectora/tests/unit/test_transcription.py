"""transcribe_audio — STT de anexos de áudio via OpenAI Whisper API."""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import httpx
import pytest

from backend.llm.transcription import TranscriptionError, transcribe_audio


class TestTranscribeAudio:
    @pytest.mark.asyncio
    async def test_returns_stripped_text_on_success(self) -> None:
        response = MagicMock()
        response.json.return_value = {"text": "  olá mundo  "}
        response.raise_for_status = MagicMock()

        mock_client = AsyncMock()
        mock_client.post = AsyncMock(return_value=response)
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=False)

        with (
            patch("backend.llm.transcription.settings.openai_api_key", "sk-test"),
            patch(
                "backend.llm.transcription.httpx.AsyncClient", return_value=mock_client
            ),
        ):
            text = await transcribe_audio(b"audio-bytes", "memo.mp3", "audio/mpeg")

        assert text == "olá mundo"
        mock_client.post.assert_awaited_once()
        _, kwargs = mock_client.post.call_args
        assert kwargs["files"]["file"][0] == "memo.mp3"

    @pytest.mark.asyncio
    async def test_raises_when_api_key_missing(self) -> None:
        with patch("backend.llm.transcription.settings.openai_api_key", None):
            with pytest.raises(TranscriptionError, match="openai_api_key"):
                await transcribe_audio(b"audio-bytes", "memo.mp3", "audio/mpeg")

    @pytest.mark.asyncio
    async def test_raises_transcription_error_on_http_failure(self) -> None:
        mock_client = AsyncMock()
        mock_client.post = AsyncMock(side_effect=httpx.ConnectError("falha de rede"))
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=False)

        with (
            patch("backend.llm.transcription.settings.openai_api_key", "sk-test"),
            patch(
                "backend.llm.transcription.httpx.AsyncClient", return_value=mock_client
            ),
        ):
            with pytest.raises(TranscriptionError):
                await transcribe_audio(b"audio-bytes", "memo.mp3", "audio/mpeg")
