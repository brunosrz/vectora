"""Bloco F — File Handling Completo — testes TDD.

Cobre:
- F1: schemas Pydantic (Attachment, StreamChatRequest.attachments)
- F1: _build_human_message — conversão de attachments para HumanMessage multimodal
- F1: _mime_to_lang — detecção de linguagem por extensão de arquivo
"""

from __future__ import annotations

import base64
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from langchain_core.messages import HumanMessage

from backend.api.schemas import (
    Attachment,
    AttachmentKind,
    ChatConfig,
    StreamChatRequest,
)

# ===========================================================================
# Helpers
# ===========================================================================


def _b64(text: str) -> str:
    """Encoda texto para base64 (mesmo formato que o frontend envia)."""
    return base64.b64encode(text.encode()).decode()


def _b64_bytes(data: bytes) -> str:
    return base64.b64encode(data).decode()


# ===========================================================================
# Classe 1 — Schema de Attachment
# ===========================================================================


class TestAttachmentSchema:
    def test_image_attachment_valid(self) -> None:
        att = Attachment(
            kind=AttachmentKind.IMAGE,
            name="photo.png",
            mime_type="image/png",
            base64_data="abc123",
        )
        assert att.kind == AttachmentKind.IMAGE
        assert att.name == "photo.png"

    def test_code_attachment_valid(self) -> None:
        att = Attachment(
            kind=AttachmentKind.CODE,
            name="main.py",
            mime_type="text/x-python",
            base64_data="abc",
        )
        assert att.kind == AttachmentKind.CODE

    def test_pdf_attachment_valid(self) -> None:
        att = Attachment(
            kind=AttachmentKind.PDF,
            name="doc.pdf",
            mime_type="application/pdf",
            base64_data="abc",
        )
        assert att.kind == AttachmentKind.PDF

    def test_text_attachment_valid(self) -> None:
        att = Attachment(
            kind=AttachmentKind.TEXT,
            name="readme.txt",
            mime_type="text/plain",
            base64_data="abc",
        )
        assert att.kind == AttachmentKind.TEXT

    def test_invalid_kind_raises(self) -> None:
        from pydantic import ValidationError

        with pytest.raises(ValidationError):
            Attachment(
                kind="video",  # type: ignore[arg-type]  # tipo inválido
                name="clip.mp4",
                mime_type="video/mp4",
                base64_data="abc",
            )


# ===========================================================================
# Classe 2 — StreamChatRequest com attachments
# ===========================================================================


class TestStreamChatRequestAttachments:
    def test_default_empty_attachments(self) -> None:
        req = StreamChatRequest(content="olá")
        assert req.attachments == []

    def test_request_with_single_attachment(self) -> None:
        att = Attachment(
            kind=AttachmentKind.IMAGE,
            name="img.png",
            mime_type="image/png",
            base64_data="abc",
        )
        req = StreamChatRequest(content="veja isso", attachments=[att])
        assert len(req.attachments) == 1
        assert req.attachments[0].kind == AttachmentKind.IMAGE

    def test_request_json_roundtrip(self) -> None:
        att = Attachment(
            kind=AttachmentKind.CODE,
            name="main.py",
            mime_type="text/x-python",
            base64_data=_b64("print('hi')"),
        )
        req = StreamChatRequest(content="explique", attachments=[att])
        as_dict = req.model_dump()
        req2 = StreamChatRequest.model_validate(as_dict)
        assert req2.attachments[0].name == "main.py"
        assert req2.attachments[0].kind == AttachmentKind.CODE


# ===========================================================================
# Classe 3 — _build_human_message
# ===========================================================================


class TestBuildHumanMessage:
    @pytest.mark.asyncio
    async def test_no_attachments_returns_plain_string(self) -> None:
        from backend.api.handlers.chat import _build_human_message

        msg = await _build_human_message("olá", [])
        assert isinstance(msg, HumanMessage)
        assert msg.content == "olá"

    @pytest.mark.asyncio
    async def test_empty_list_returns_plain_string(self) -> None:
        from backend.api.handlers.chat import _build_human_message

        msg = await _build_human_message("teste", [])
        assert isinstance(msg.content, str)
        assert msg.content == "teste"

    @pytest.mark.asyncio
    async def test_image_attachment_produces_multimodal(self) -> None:
        from backend.api.handlers.chat import _build_human_message

        raw = _b64_bytes(b"fake_image_bytes")
        att = Attachment(
            kind=AttachmentKind.IMAGE,
            name="img.png",
            mime_type="image/png",
            base64_data=raw,
        )
        msg = await _build_human_message("veja isso", [att])

        assert isinstance(msg.content, list)
        # Parte 0: texto original
        assert msg.content[0] == {"type": "text", "text": "veja isso"}
        # Parte 1: imagem no formato OpenAI
        assert msg.content[1]["type"] == "image_url"
        assert "data:image/png;base64," in msg.content[1]["image_url"]["url"]
        assert raw in msg.content[1]["image_url"]["url"]

    @pytest.mark.asyncio
    async def test_code_attachment_injects_code_block(self) -> None:
        from backend.api.handlers.chat import _build_human_message

        code = "def hello():\n    print('hi')"
        att = Attachment(
            kind=AttachmentKind.CODE,
            name="hello.py",
            mime_type="text/x-python",
            base64_data=_b64(code),
        )
        msg = await _build_human_message("explique", [att])

        assert isinstance(msg.content, list)
        all_text = "\n".join(p["text"] for p in msg.content if p["type"] == "text")
        assert "hello.py" in all_text
        assert "python" in all_text  # linguagem detectada pela extensão
        assert code in all_text

    @pytest.mark.asyncio
    async def test_pdf_attachment_injects_decoded_text(self) -> None:
        from backend.api.handlers.chat import _build_human_message

        content = "Este é o conteúdo do PDF"
        att = Attachment(
            kind=AttachmentKind.PDF,
            name="relatorio.pdf",
            mime_type="application/pdf",
            base64_data=_b64(content),
        )
        msg = await _build_human_message("resuma", [att])

        assert isinstance(msg.content, list)
        all_text = "\n".join(p["text"] for p in msg.content if p["type"] == "text")
        assert "relatorio.pdf" in all_text
        assert content in all_text

    @pytest.mark.asyncio
    async def test_text_attachment_decoded_utf8(self) -> None:
        from backend.api.handlers.chat import _build_human_message

        content = "Olá, Mundo! 🌍"
        att = Attachment(
            kind=AttachmentKind.TEXT,
            name="nota.txt",
            mime_type="text/plain",
            base64_data=_b64(content),
        )
        msg = await _build_human_message("leia", [att])

        all_text = "\n".join(p["text"] for p in msg.content if p["type"] == "text")
        assert content in all_text

    @pytest.mark.asyncio
    async def test_mixed_attachments_correct_parts_count(self) -> None:
        from backend.api.handlers.chat import _build_human_message

        img_att = Attachment(
            kind=AttachmentKind.IMAGE,
            name="img.png",
            mime_type="image/png",
            base64_data=_b64_bytes(b"img"),
        )
        code_att = Attachment(
            kind=AttachmentKind.CODE,
            name="script.py",
            mime_type="text/x-python",
            base64_data=_b64("x = 1"),
        )
        msg = await _build_human_message("analyze", [img_att, code_att])

        assert isinstance(msg.content, list)
        assert len(msg.content) == 3  # texto + image_url + texto-código
        types = [p["type"] for p in msg.content]
        assert types == ["text", "image_url", "text"]

    @pytest.mark.asyncio
    async def test_multiple_images(self) -> None:
        from backend.api.handlers.chat import _build_human_message

        att1 = Attachment(
            kind=AttachmentKind.IMAGE,
            name="a.png",
            mime_type="image/png",
            base64_data=_b64_bytes(b"img1"),
        )
        att2 = Attachment(
            kind=AttachmentKind.IMAGE,
            name="b.jpg",
            mime_type="image/jpeg",
            base64_data=_b64_bytes(b"img2"),
        )
        msg = await _build_human_message("compare", [att1, att2])

        assert len(msg.content) == 3  # text + 2 images
        assert msg.content[1]["type"] == "image_url"
        assert msg.content[2]["type"] == "image_url"
        assert "image/jpeg" in msg.content[2]["image_url"]["url"]

    @pytest.mark.asyncio
    async def test_audio_attachment_transcribed_and_injected(self) -> None:
        from unittest.mock import AsyncMock, patch

        from backend.api.handlers.chat import _build_human_message

        att = Attachment(
            kind=AttachmentKind.AUDIO,
            name="memo.mp3",
            mime_type="audio/mpeg",
            base64_data=_b64_bytes(b"fake_audio_bytes"),
        )
        with patch(
            "backend.llm.transcription.transcribe_audio",
            AsyncMock(return_value="fale sobre o projeto"),
        ):
            msg = await _build_human_message("ouça isso", [att])

        assert isinstance(msg.content, list)
        all_text = "\n".join(p["text"] for p in msg.content if p["type"] == "text")
        assert "memo.mp3" in all_text
        assert "fale sobre o projeto" in all_text

    @pytest.mark.asyncio
    async def test_audio_attachment_transcription_failure_injects_error_note(
        self,
    ) -> None:
        from unittest.mock import AsyncMock, patch

        from backend.api.handlers.chat import _build_human_message
        from backend.llm.transcription import TranscriptionError

        att = Attachment(
            kind=AttachmentKind.AUDIO,
            name="memo.wav",
            mime_type="audio/wav",
            base64_data=_b64_bytes(b"fake_audio_bytes"),
        )
        with patch(
            "backend.llm.transcription.transcribe_audio",
            AsyncMock(side_effect=TranscriptionError("sem chave configurada")),
        ):
            msg = await _build_human_message("ouça isso", [att])

        assert isinstance(msg.content, list)
        all_text = "\n".join(p["text"] for p in msg.content if p["type"] == "text")
        assert "memo.wav" in all_text
        assert "falha ao transcrever" in all_text


# ===========================================================================
# Classe 4 — _mime_to_lang
# ===========================================================================


class TestMimeToLang:
    def test_python_by_extension(self) -> None:
        from backend.api.handlers.chat import _mime_to_lang

        assert _mime_to_lang("script.py") == "python"

    def test_typescript_by_extension(self) -> None:
        from backend.api.handlers.chat import _mime_to_lang

        assert _mime_to_lang("app.ts") == "typescript"

    def test_tsx_by_extension(self) -> None:
        from backend.api.handlers.chat import _mime_to_lang

        assert _mime_to_lang("component.tsx") == "typescript"

    def test_json_by_extension(self) -> None:
        from backend.api.handlers.chat import _mime_to_lang

        assert _mime_to_lang("config.json") == "json"

    def test_pdf_returns_empty_string(self) -> None:
        from backend.api.handlers.chat import _mime_to_lang

        assert _mime_to_lang("doc.pdf") == ""

    def test_unknown_extension_returns_empty(self) -> None:
        from backend.api.handlers.chat import _mime_to_lang

        assert _mime_to_lang("file.xyz") == ""

    def test_shell_script(self) -> None:
        from backend.api.handlers.chat import _mime_to_lang

        assert _mime_to_lang("run.sh") == "bash"


# ===========================================================================
# Classe 5 — stream_chat recusa imagem quando o provider não suporta visão
# ===========================================================================


def _image_attachment() -> Attachment:
    return Attachment(
        kind=AttachmentKind.IMAGE,
        name="foto.png",
        mime_type="image/png",
        base64_data=_b64("fake-image-bytes"),
    )


async def _collect_sse_body(response) -> str:
    chunks = [chunk async for chunk in response.body_iterator]
    return "".join(
        chunk.decode() if isinstance(chunk, bytes) else chunk for chunk in chunks
    )


class TestStreamChatBlocksImageForNonVisionProvider:
    """Regressão: imagem + Cohere estourava BadRequestError cru da API
    ('image content is not supported for this model'). Agora recusa antes
    de chamar o provider, com um ErrorEvent(code='MODEL_NO_VISION')."""

    @pytest.mark.asyncio
    async def test_cohere_with_image_returns_model_no_vision_without_calling_provider(
        self,
    ) -> None:
        from backend.api.handlers import chat as chat_mod

        mock_get_user_agent = AsyncMock()
        with patch(
            "backend.services.agent_factory.get_user_agent", mock_get_user_agent
        ):
            request = StreamChatRequest(
                content="o que tem nessa imagem?",
                config=ChatConfig(model="cohere:command-a-03-2025"),
                attachments=[_image_attachment()],
            )
            http_request = MagicMock()
            http_request.state = MagicMock(user=None)
            response = await chat_mod.stream_chat(request, http_request)

        body = await _collect_sse_body(response)
        assert '"code": "MODEL_NO_VISION"' in body
        mock_get_user_agent.assert_not_called()

    @pytest.mark.asyncio
    async def test_gemini_with_image_is_not_blocked(self) -> None:
        """Provider com suporte a visão (google_genai) não é bloqueado —
        confirma que a checagem é por provider, não um bloqueio geral."""
        from backend.api.handlers import chat as chat_mod

        async def _empty_events(*_a: object, **_kw: object):
            for _ in ():
                yield

        mock_graph = MagicMock()
        mock_graph.astream_events = MagicMock(return_value=_empty_events())

        with (
            patch(
                "backend.services.agent_factory.get_user_agent",
                new=AsyncMock(return_value=mock_graph),
            ),
            patch(
                "backend.api.handlers.threads._upsert_session",
                new=AsyncMock(),
            ),
        ):
            request = StreamChatRequest(
                content="o que tem nessa imagem?",
                config=ChatConfig(model="google-genai:gemini-2.5-flash"),
                attachments=[_image_attachment()],
            )
            http_request = MagicMock()
            http_request.state = MagicMock(user=None)
            response = await chat_mod.stream_chat(request, http_request)

        body = await _collect_sse_body(response)
        assert "MODEL_NO_VISION" not in body
