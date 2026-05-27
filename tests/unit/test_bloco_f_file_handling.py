"""Bloco F — File Handling Completo — testes TDD.

Cobre:
- F1: schemas Pydantic (Attachment, StreamChatRequest.attachments)
- F1: _build_human_message — conversão de attachments para HumanMessage multimodal
- F1: _mime_to_lang — detecção de linguagem por extensão/mime_type
"""

from __future__ import annotations

import base64

import pytest
from langchain_core.messages import HumanMessage

from vectora.api.schemas import Attachment, AttachmentKind, StreamChatRequest

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
            kind="image",
            name="photo.png",
            mime_type="image/png",
            base64_data="abc123",
        )
        assert att.kind == AttachmentKind.IMAGE
        assert att.name == "photo.png"

    def test_code_attachment_valid(self) -> None:
        att = Attachment(
            kind="code",
            name="main.py",
            mime_type="text/x-python",
            base64_data="abc",
        )
        assert att.kind == AttachmentKind.CODE

    def test_pdf_attachment_valid(self) -> None:
        att = Attachment(
            kind="pdf",
            name="doc.pdf",
            mime_type="application/pdf",
            base64_data="abc",
        )
        assert att.kind == AttachmentKind.PDF

    def test_text_attachment_valid(self) -> None:
        att = Attachment(
            kind="text",
            name="readme.txt",
            mime_type="text/plain",
            base64_data="abc",
        )
        assert att.kind == AttachmentKind.TEXT

    def test_invalid_kind_raises(self) -> None:
        with pytest.raises(Exception):
            Attachment(
                kind="video",  # tipo inválido
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
            kind="image",
            name="img.png",
            mime_type="image/png",
            base64_data="abc",
        )
        req = StreamChatRequest(content="veja isso", attachments=[att])
        assert len(req.attachments) == 1
        assert req.attachments[0].kind == AttachmentKind.IMAGE

    def test_request_json_roundtrip(self) -> None:
        att = Attachment(
            kind="code",
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
    def test_no_attachments_returns_plain_string(self) -> None:
        from vectora.api.handlers.chat import _build_human_message

        msg = _build_human_message("olá", [])
        assert isinstance(msg, HumanMessage)
        assert msg.content == "olá"

    def test_empty_list_returns_plain_string(self) -> None:
        from vectora.api.handlers.chat import _build_human_message

        msg = _build_human_message("teste", [])
        assert isinstance(msg.content, str)
        assert msg.content == "teste"

    def test_image_attachment_produces_multimodal(self) -> None:
        from vectora.api.handlers.chat import _build_human_message

        raw = _b64_bytes(b"fake_image_bytes")
        att = Attachment(
            kind="image",
            name="img.png",
            mime_type="image/png",
            base64_data=raw,
        )
        msg = _build_human_message("veja isso", [att])

        assert isinstance(msg.content, list)
        # Parte 0: texto original
        assert msg.content[0] == {"type": "text", "text": "veja isso"}
        # Parte 1: imagem no formato OpenAI
        assert msg.content[1]["type"] == "image_url"
        assert "data:image/png;base64," in msg.content[1]["image_url"]["url"]
        assert raw in msg.content[1]["image_url"]["url"]

    def test_code_attachment_injects_code_block(self) -> None:
        from vectora.api.handlers.chat import _build_human_message

        code = "def hello():\n    print('hi')"
        att = Attachment(
            kind="code",
            name="hello.py",
            mime_type="text/x-python",
            base64_data=_b64(code),
        )
        msg = _build_human_message("explique", [att])

        assert isinstance(msg.content, list)
        all_text = "\n".join(p["text"] for p in msg.content if p["type"] == "text")
        assert "hello.py" in all_text
        assert "python" in all_text  # linguagem detectada pela extensão
        assert code in all_text

    def test_pdf_attachment_injects_decoded_text(self) -> None:
        from vectora.api.handlers.chat import _build_human_message

        content = "Este é o conteúdo do PDF"
        att = Attachment(
            kind="pdf",
            name="relatorio.pdf",
            mime_type="application/pdf",
            base64_data=_b64(content),
        )
        msg = _build_human_message("resuma", [att])

        assert isinstance(msg.content, list)
        all_text = "\n".join(p["text"] for p in msg.content if p["type"] == "text")
        assert "relatorio.pdf" in all_text
        assert content in all_text

    def test_text_attachment_decoded_utf8(self) -> None:
        from vectora.api.handlers.chat import _build_human_message

        content = "Olá, Mundo! 🌍"
        att = Attachment(
            kind="text",
            name="nota.txt",
            mime_type="text/plain",
            base64_data=_b64(content),
        )
        msg = _build_human_message("leia", [att])

        all_text = "\n".join(p["text"] for p in msg.content if p["type"] == "text")
        assert content in all_text

    def test_mixed_attachments_correct_parts_count(self) -> None:
        from vectora.api.handlers.chat import _build_human_message

        img_att = Attachment(
            kind="image",
            name="img.png",
            mime_type="image/png",
            base64_data=_b64_bytes(b"img"),
        )
        code_att = Attachment(
            kind="code",
            name="script.py",
            mime_type="text/x-python",
            base64_data=_b64("x = 1"),
        )
        msg = _build_human_message("analyze", [img_att, code_att])

        assert isinstance(msg.content, list)
        assert len(msg.content) == 3  # texto + image_url + texto-código
        types = [p["type"] for p in msg.content]
        assert types == ["text", "image_url", "text"]

    def test_multiple_images(self) -> None:
        from vectora.api.handlers.chat import _build_human_message

        att1 = Attachment(
            kind="image",
            name="a.png",
            mime_type="image/png",
            base64_data=_b64_bytes(b"img1"),
        )
        att2 = Attachment(
            kind="image",
            name="b.jpg",
            mime_type="image/jpeg",
            base64_data=_b64_bytes(b"img2"),
        )
        msg = _build_human_message("compare", [att1, att2])

        assert len(msg.content) == 3  # text + 2 images
        assert msg.content[1]["type"] == "image_url"
        assert msg.content[2]["type"] == "image_url"
        assert "image/jpeg" in msg.content[2]["image_url"]["url"]


# ===========================================================================
# Classe 4 — _mime_to_lang
# ===========================================================================


class TestMimeToLang:
    def test_python_by_extension(self) -> None:
        from vectora.api.handlers.chat import _mime_to_lang

        assert _mime_to_lang("text/x-python", "script.py") == "python"

    def test_typescript_by_extension(self) -> None:
        from vectora.api.handlers.chat import _mime_to_lang

        assert _mime_to_lang("text/typescript", "app.ts") == "typescript"

    def test_tsx_by_extension(self) -> None:
        from vectora.api.handlers.chat import _mime_to_lang

        assert _mime_to_lang("text/typescript", "component.tsx") == "typescript"

    def test_json_by_extension(self) -> None:
        from vectora.api.handlers.chat import _mime_to_lang

        assert _mime_to_lang("application/json", "config.json") == "json"

    def test_pdf_returns_empty_string(self) -> None:
        from vectora.api.handlers.chat import _mime_to_lang

        assert _mime_to_lang("application/pdf", "doc.pdf") == ""

    def test_unknown_extension_returns_empty(self) -> None:
        from vectora.api.handlers.chat import _mime_to_lang

        assert _mime_to_lang("application/octet-stream", "file.xyz") == ""

    def test_shell_script(self) -> None:
        from vectora.api.handlers.chat import _mime_to_lang

        assert _mime_to_lang("text/x-sh", "run.sh") == "bash"
