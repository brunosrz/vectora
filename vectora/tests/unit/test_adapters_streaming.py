"""Streaming token-a-token do ``adapt_stream`` (regressão do bug #2).

O bug era o grafo envolvido em ``RunnableRetry``, que bufferiza toda a saída
(precisa poder reexecutar atômico) — o cliente só via a resposta ao final.
Aqui garantimos o invariante de streaming no nível do adaptador: **cada
``on_chat_model_stream`` vira um ``TokenEvent`` imediatamente, em ordem, um por
chunk** — sem concatenar tudo num único evento. Dirigimos o gerador passo a
passo (``__anext__``) para provar a emissão incremental (não em lote).
"""

from __future__ import annotations

import json

import pytest
from langchain_core.messages import AIMessageChunk

from backend.api.adapters import adapt_stream


def _chunk_event(text, node="model"):
    """Evento LangGraph ``on_chat_model_stream`` com um AIMessageChunk."""
    return {
        "event": "on_chat_model_stream",
        "name": node,
        "run_name": node,
        "metadata": {"langgraph_node": node},
        "data": {"chunk": AIMessageChunk(content=text)},
    }


def _parse(sse: str) -> dict:
    """Decodifica uma linha SSE ``data: {...}\\n\\n`` em dict."""
    assert sse.startswith("data: ")
    return json.loads(sse[len("data: ") :].strip())


async def _agen(events):
    for ev in events:
        yield ev


@pytest.mark.asyncio
async def test_each_chunk_emits_one_token_in_order():
    events = [_chunk_event("Hello"), _chunk_event(" "), _chunk_event("world")]
    out = [_parse(s) async for s in adapt_stream(_agen(events), "tid")]

    # 1º = thread, último = done; no meio, exatamente 3 tokens em ordem.
    assert out[0]["type"] == "thread"
    assert out[-1]["type"] == "done"
    tokens = [e for e in out if e["type"] == "token"]
    assert [t["content"] for t in tokens] == ["Hello", " ", "world"]


@pytest.mark.asyncio
async def test_tokens_are_incremental_not_buffered():
    """Dirige o gerador passo a passo: token N sai ANTES do chunk N+1 entrar.

    Se houvesse buffering (RunnableRetry), só sairia um único evento com todo o
    texto ao final — este teste falharia.
    """
    pulled: list[str] = []

    async def _source():
        for text in ["um", "dois", "tres"]:
            pulled.append(text)
            yield _chunk_event(text)

    gen = adapt_stream(_source(), "tid")

    first = _parse(await gen.__anext__())
    assert first["type"] == "thread"
    # Nenhum chunk foi puxado da fonte ainda (só o header thread).
    assert pulled == []

    tok1 = _parse(await gen.__anext__())
    assert tok1 == {"type": "token", "content": "um", "node": "model"}
    assert pulled == ["um"]  # exatamente 1 chunk consumido p/ 1 token emitido

    tok2 = _parse(await gen.__anext__())
    assert tok2["content"] == "dois"
    assert pulled == ["um", "dois"]

    tok3 = _parse(await gen.__anext__())
    assert tok3["content"] == "tres"
    assert pulled == ["um", "dois", "tres"]

    done = _parse(await gen.__anext__())
    assert done["type"] == "done"


@pytest.mark.asyncio
async def test_gemini_list_content_chunk_extracts_text():
    """Gemini emite content como lista de blocos; o adaptador extrai o texto."""
    ev = {
        "event": "on_chat_model_stream",
        "name": "model",
        "run_name": "model",
        "metadata": {"langgraph_node": "model"},
        "data": {"chunk": AIMessageChunk(content=[{"type": "text", "text": "Oi"}])},
    }
    out = [_parse(s) async for s in adapt_stream(_agen([ev]), "tid")]
    tokens = [e for e in out if e["type"] == "token"]
    assert [t["content"] for t in tokens] == ["Oi"]


@pytest.mark.asyncio
async def test_empty_chunk_emits_no_token():
    """Chunk sem conteúdo (ex.: só metadados) não vira TokenEvent."""
    ev = {
        "event": "on_chat_model_stream",
        "name": "model",
        "metadata": {"langgraph_node": "model"},
        "data": {"chunk": AIMessageChunk(content="")},
    }
    out = [_parse(s) async for s in adapt_stream(_agen([ev]), "tid")]
    assert [e for e in out if e["type"] == "token"] == []


@pytest.mark.asyncio
async def test_provider_error_midstream_becomes_clean_rate_limit():
    """429 no meio do stream vira ErrorEvent limpo (RATE_LIMIT), não JSON cru."""

    async def _boom():
        yield _chunk_event("parcial")
        raise RuntimeError(
            "Error calling model 'gemini-2.5-flash' (Too Many Requests): 429 "
            "RESOURCE_EXHAUSTED quota exceeded"
        )

    out = [_parse(s) async for s in adapt_stream(_boom(), "tid")]
    errors = [e for e in out if e["type"] == "error"]
    assert len(errors) == 1
    assert errors[0]["code"] == "RATE_LIMIT"
    assert "RESOURCE_EXHAUSTED" not in errors[0]["message"]
    assert "429" not in errors[0]["message"]


# ============================================================================
# _record_turn_checkpoint
# ============================================================================


@pytest.mark.asyncio
async def test_record_turn_checkpoint_nonexistent_directory_no_error(
    tmp_path, monkeypatch, caplog
):
    """_record_turn_checkpoint não loga ERROR quando diretório do workspace não existe.

    Regressão do NoSuchPathError — o diretório referenciado pelo workspace pode
    não existir em disco (sessão nova ainda não inicializada). Antes do fix, a
    exceção não era capturada pelo inner except (só pegava InvalidGitRepositoryError)
    e chegava ao outer except como ERROR. Após o fix deve ser silenciosa.
    """
    import logging
    from unittest.mock import MagicMock

    from backend.api.adapters import _record_turn_checkpoint

    ws = MagicMock()
    ws.cwd = str(tmp_path / "nonexistent_workspace_dir_xyz")  # não existe

    monkeypatch.setattr(
        "backend.services.workspace.workspace_registry",
        MagicMock(get=MagicMock(return_value=ws)),
    )

    with caplog.at_level(logging.ERROR, logger="backend.api.adapters"):
        await _record_turn_checkpoint("ws-1", "thread-1", {"run_id": "r1"})

    error_msgs = [r.message for r in caplog.records if r.levelno >= logging.ERROR]
    assert not error_msgs, (
        f"_record_turn_checkpoint logou ERROR para diretório inexistente: {error_msgs}"
    )


@pytest.mark.asyncio
async def test_record_turn_checkpoint_nonexistent_directory_returns_silently(
    tmp_path, monkeypatch
):
    """_record_turn_checkpoint retorna sem levantar exceção se diretório não existe."""
    from unittest.mock import MagicMock

    from backend.api.adapters import _record_turn_checkpoint

    ws = MagicMock()
    ws.cwd = str(tmp_path / "also_nonexistent_xyz")

    monkeypatch.setattr(
        "backend.services.workspace.workspace_registry",
        MagicMock(get=MagicMock(return_value=ws)),
    )

    # Deve retornar sem levantar — best-effort
    await _record_turn_checkpoint("ws-2", "thread-2", {"run_id": "r2"})
