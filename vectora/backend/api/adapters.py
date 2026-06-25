"""Converte eventos do LangGraph (astream_events v2) em StreamChatEvent.

O LangGraph emite eventos do tipo:
    {"event": "on_chat_model_stream", "data": {"chunk": AIMessageChunk(...)}, ...}
    {"event": "on_tool_start", "data": {"input": {...}}, "name": "web_search", ...}
    ...

Este módulo mapeia esses eventos para os nossos tipos Pydantic e serializa
para o formato SSE (data: {...}\\n\\n) usado pelo endpoint /StreamChat.
"""

from __future__ import annotations

import json
import logging
from typing import Any

from backend.api.node_labels import get_node_label
from backend.api.schemas import (
    DoneEvent,
    ErrorEvent,
    HITLEvent,
    MessageBreakEvent,
    NodeEvent,
    RagCitation,
    RagCitationEvent,
    StreamChatEventPayload,
    TokenEvent,
    ToolActivityEvent,
    ToolCallEvent,
    ToolResultEvent,
    WorkbenchInvalidateEvent,
    encode_event,
)

logger = logging.getLogger(__name__)


def classify_stream_error(exc: BaseException) -> tuple[str, str]:
    """Classifica uma exceção do stream em ``(code, message)``.

    O ``code`` é tipado e estável para o frontend localizar a mensagem ao
    usuário (i18n no cliente). O ``message`` é um resumo limpo (sem o JSON cru
    do provedor) usado como fallback.

    Códigos: ``RATE_LIMIT`` (429 / quota esgotada), ``AUTH`` (chave inválida /
    401 / 403), ``STREAM_ERROR`` (genérico).
    """
    text = f"{type(exc).__name__}: {exc}".lower()
    if (
        "429" in text
        or "too many requests" in text
        or "resource_exhausted" in text
        or "rate limit" in text
        or "ratelimit" in text
        or "quota" in text
    ):
        return "RATE_LIMIT", "O limite de uso deste modelo foi atingido."
    if (
        "401" in text
        or "403" in text
        or "unauthorized" in text
        or "permission denied" in text
        or "api key" in text
        or "api_key" in text
        or "invalid authentication" in text
    ):
        return "AUTH", "Falha de autenticação com o provedor do modelo."
    return "STREAM_ERROR", "Ocorreu um erro ao gerar a resposta."


# Cache de metadados de tool: nome → dict com render_hint, category, destructive, icon.
# Populado lazily para evitar importar ALL_TOOLS no startup.
_tool_meta_cache: dict[str, dict] = {}

_DEFAULT_META = {
    "render_hint": "json",
    "category": "general",
    "destructive": False,
    "icon": "tool",
}


def _get_tool_meta(tool_name: str) -> dict:
    """Retorna metadados de UI da tool (render_hint, category, destructive, icon, invalidates)."""
    if not _tool_meta_cache:
        try:
            from backend.nodes.tools import ALL_TOOLS

            for t in ALL_TOOLS:
                meta = getattr(t, "extras", None) or getattr(t, "metadata", None) or {}
                _tool_meta_cache[t.name] = {
                    "render_hint": meta.get("render_hint", "json"),
                    "category": meta.get("category", "general"),
                    "destructive": bool(meta.get("destructive", False)),
                    "icon": meta.get("icon", "tool"),
                    "invalidates": meta.get("invalidates", []),
                }
        except Exception:
            pass
    return _tool_meta_cache.get(tool_name, _DEFAULT_META)


def _args_preview(tool_input: dict | str) -> str:
    """Gera preview curto (≤80 chars) dos args para exibir no AgentStatusLine."""
    if isinstance(tool_input, dict):
        # Prefere campos semânticos: path, query, command, url, name, file_path
        for key in ("path", "file_path", "query", "command", "url", "name"):
            val = tool_input.get(key)
            if val and isinstance(val, str):
                preview = val
                break
        else:
            preview = ", ".join(f"{k}={v}" for k, v in list(tool_input.items())[:2])
    else:
        preview = str(tool_input)
    return preview[:80]


# ---------------------------------------------------------------------------
# Nós cuja saída do LLM é JSON estruturado (Pydantic) — não user-facing.
# Com deepagents (E.B-1), o agente principal ("model") faz streaming natural;
# nenhum nó usa structured output no caminho do usuário.
# Mantido vazio para eventuais nós de síntese adicionados em E.B+.
_STRUCTURED_OUTPUT_NODES: set[str] = set()


def langgraph_event_to_payload(  # noqa: PLR0911
    event: dict[str, Any],
) -> StreamChatEventPayload | None:
    """Converte um evento LangGraph em nosso StreamChatEventPayload.

    Retorna None se o evento não deve ser transmitido ao cliente
    (ex.: eventos internos de infraestrutura do grafo).
    """
    kind: str = event.get("event", "")
    name: str = event.get("name", "")
    data: dict[str, Any] = event.get("data", {})

    # ── Tokens de texto do LLM ────────────────────────────────────────────
    if kind == "on_chat_model_stream":
        # Filtrar saída de nós com structured output (Pydantic) — esses tokens
        # são JSON cru da decisão estruturada, não user-facing.
        md = event.get("metadata", {}) or {}
        lg_node = md.get("langgraph_node", "")
        if lg_node in _STRUCTURED_OUTPUT_NODES:
            return None

        chunk = data.get("chunk")
        if chunk is None:
            return None
        # AIMessageChunk tem .content (str ou list[dict])
        content = getattr(chunk, "content", "")
        if isinstance(content, list):
            # Formato multimodal: pegar só os blocos de texto
            content = "".join(b.get("text", "") for b in content if isinstance(b, dict))
        if not content:
            return None
        run_name: str = event.get("run_name", "")
        return TokenEvent(content=content, node=run_name or name)

    # ── Início de tool call ───────────────────────────────────────────────
    if kind == "on_tool_start":
        tool_input = data.get("input", {})
        args_json = (
            json.dumps(tool_input) if isinstance(tool_input, dict) else str(tool_input)
        )
        # tool_call_id pode estar nos metadados ou no run_id
        call_id: str = event.get("run_id", "")
        meta = _get_tool_meta(name)
        return ToolCallEvent(
            tool_name=name,
            tool_call_id=call_id,
            args_json=args_json,
            render_hint=meta["render_hint"],
            category=meta["category"],
            destructive=meta["destructive"],
            icon=meta["icon"],
        )

    # ── Resultado de tool ─────────────────────────────────────────────────
    if kind == "on_tool_end":
        output = data.get("output", "")
        call_id = event.get("run_id", "")
        # output pode ser ToolMessage, str, dict, etc.
        if hasattr(output, "content"):
            raw = output.content
        elif isinstance(output, dict):
            raw = json.dumps(output)
        else:
            raw = str(output)

        is_error = False
        if hasattr(output, "status"):
            is_error = output.status == "error"  # type: ignore[union-attr]

        content_json = raw if isinstance(raw, str) else json.dumps(raw)
        return ToolResultEvent(
            tool_call_id=call_id,
            content_json=content_json,
            is_error=is_error,
        )

    # ── Início / fim de nó do grafo ───────────────────────────────────────
    if kind == "on_chain_start" and name not in ("", "LangGraph"):
        return NodeEvent(node=name, status="started", node_label=get_node_label(name))

    if kind == "on_chain_end" and name not in ("", "LangGraph"):
        return NodeEvent(node=name, status="finished", node_label=get_node_label(name))

    return None


async def _record_turn_checkpoint(
    workspace_id: str, thread_id: str, event: Any
) -> None:
    """Grava um artefato de checkpoint de rewind após cada turno do orchestrador.

    Chamado no ``on_chain_end`` do nó ``orchestrator`` — marca o fim de um turno
    completo do agente. Best-effort: qualquer falha (workspace sem git, I/O,
    banco indisponível) é registrada em log e descartada silenciosamente.
    """
    import uuid
    from datetime import UTC, datetime

    try:
        from backend.services.workspace import workspace_registry

        ws = workspace_registry.get(workspace_id)
        if ws is None:
            return

        import git as gitpy

        checkpoint_id = event.get("run_id") or str(uuid.uuid4())
        msg = f"turn:{thread_id}:{checkpoint_id[:8]}"

        strategy: str
        git_sha: str | None = None
        snapshot_path: str | None = None
        files_touched: str = "[]"

        try:
            repo = gitpy.Repo(ws.cwd, search_parent_directories=True)
            from backend.services.checkpoint import create_git_checkpoint

            result = create_git_checkpoint(repo, thread_id, msg)
            if result["status"] != "ok":
                logger.warning(
                    "_record_turn_checkpoint: git snapshot falhou: %s", result
                )
                return
            strategy = "git"
            git_sha = result["sha"]
        except (gitpy.InvalidGitRepositoryError, gitpy.NoSuchPathError):
            # Fallback: snapshot tarball para workspaces sem git.
            # NoSuchPathError ocorre quando o diretório do workspace não existe
            # ainda em disco (sessão nova não inicializada) — nesse caso não há
            # snapshot possível e retornamos silenciosamente.
            from pathlib import Path as _Path

            if not _Path(ws.cwd).exists():
                return

            from backend.services.checkpoint import (
                create_snapshot_checkpoint,
                gc_snapshots,
            )

            snap_dir = _Path.home() / ".vectora" / "snapshots" / workspace_id
            result = create_snapshot_checkpoint(str(ws.cwd), snap_dir, thread_id, msg)
            if result["status"] != "ok":
                logger.warning("_record_turn_checkpoint: snapshot falhou: %s", result)
                return
            strategy = "snapshot"
            snapshot_path = result["snapshot_path"]
            files_touched = __import__("json").dumps(result.get("files_touched", []))
            # GC: limpa snapshots antigos desta thread.
            gc_snapshots(snap_dir)

        now = datetime.now(UTC).isoformat()
        from backend.api.handlers.threads import _get_db

        db = await _get_db()
        await db.execute(
            "INSERT INTO vectora_checkpoint_artifacts "
            "(id, thread_id, checkpoint_id, strategy, git_sha, snapshot_path, files_touched, created_at) "
            "VALUES (?,?,?,?,?,?,?,?)",
            (
                str(uuid.uuid4()),
                thread_id,
                checkpoint_id,
                strategy,
                git_sha,
                snapshot_path,
                files_touched,
                now,
            ),
        )
        await db.commit()
        logger.debug(
            "_record_turn_checkpoint: checkpoint gravado thread=%s strategy=%s",
            thread_id,
            strategy,
        )
    except Exception:
        logger.exception("_record_turn_checkpoint: falha ao gravar checkpoint de turno")


def adapt_stream(
    events: Any,
    thread_id: str,
    workspace_id: str | None = None,
) -> Any:
    """AsyncGenerator que converte o stream de eventos LangGraph em linhas SSE.

    Yields:
        str — linhas ``data: {...}\\n\\n`` prontas para StreamingResponse.

    ``workspace_id`` — quando fornecido e o workspace for um repositório git,
    cria um checkpoint de rewind em ``refs/vectora/checkpoints/<thread_id>``
    ao final de cada turno do orchestrador (``on_chain_end`` do nó
    ``"orchestrator"``). Falhas são registradas em log e ignoradas — nunca
    interrompem o stream.
    """

    async def _gen() -> Any:
        # 1º evento: thread_id
        from backend.api.schemas import ThreadEvent

        yield encode_event(ThreadEvent(thread_id=thread_id))

        node_start_times: dict[str, float] = {}
        tool_start_times: dict[str, float] = {}
        tool_args_previews: dict[str, str] = {}
        import time

        # Multi-bubble: rastreia o nó que gera tokens para emitir message_break
        # quando o nó muda e já há tokens na bolha atual.
        current_token_node: str | None = None
        token_buffer_nonempty = False

        try:
            async for event in events:
                kind = event.get("event", "")
                name = event.get("name", "")

                # Rastreia tempo de início dos nós para calcular duration_ms
                if kind == "on_chain_start":
                    node_start_times[name] = time.monotonic()

                # Extrai data uma vez para o bloco HITL + orchestrator abaixo
                data = event.get("data", {})

                # ── HITL: interrupt() chamado em algum nó ────────────────────
                # Quando hitl_check chama interrupt(payload), o LangGraph emite
                # um on_chain_stream com "__interrupt__" no chunk. Detectamos
                # esse sentinel e traduzimos para HITLEvent antes do DoneEvent.
                if kind == "on_chain_stream":
                    chunk = data.get("chunk", {})
                    if isinstance(chunk, dict) and "__interrupt__" in chunk:
                        raw_interrupts = chunk["__interrupt__"]
                        for intr in raw_interrupts:
                            intr_val = getattr(intr, "value", None)
                            if not isinstance(intr_val, list) or not intr_val:
                                continue
                            first = intr_val[0]
                            yield encode_event(
                                HITLEvent(
                                    tool_name=first.get("name", "unknown"),
                                    args_json=json.dumps(first.get("args", {})),
                                    interrupt_id=first.get("id", ""),
                                )
                            )
                        # Stream encerra aqui — cliente exibirá o painel HITL
                        # e chamará ResumeChat para continuar.
                        return

                # Emite RagCitationEvent quando o nó rag_inject conclui —
                # extrai a lista de docs do output para expor as fontes ao frontend.
                if kind == "on_chain_end" and name == "rag_inject":
                    rag_docs = event.get("data", {}).get("input", {}) or {}
                    rag_docs = rag_docs.get("rag_docs") or []
                    if rag_docs:
                        citations = [
                            RagCitation(
                                index=i,
                                source=(
                                    doc.get("metadata", {}).get("source", "")
                                    or doc.get("metadata", {}).get("title", "")
                                ),
                                chunk=doc.get("page_content", "")[:200],
                            )
                            for i, doc in enumerate(rag_docs[:5], 1)
                        ]
                        yield encode_event(RagCitationEvent(citations=citations))

                # Com deepagents (E.B-1), o agente principal é o nó "model".
                # O orchestrator antigo (structured output) foi removido.
                # Thinking events: E.B-6 adiciona suporte via streaming v3.
                # Checkpoint de rewind: disparado no on_chain_end do grafo raiz.
                # O grafo raiz tem name="" ou "LangGraph" — usamos o nome do
                # grafo configurado em create_deep_agent("name='vectora'").
                if kind == "on_chain_end" and name == "vectora":
                    # Grava checkpoint de rewind ao final de cada turno completo.
                    # (best-effort — falha silenciosa para não cortar o stream).
                    if workspace_id:
                        await _record_turn_checkpoint(workspace_id, thread_id, event)

                # ── ToolActivityEvent: status line ao vivo ────────────────
                # Emite antes do ToolCallEvent (start) e após ToolResultEvent (end).
                if kind == "on_tool_start":
                    tool_input = data.get("input", {})
                    preview = _args_preview(tool_input)
                    run_id: str = event.get("run_id", name)
                    tool_start_times[run_id] = time.monotonic()
                    tool_args_previews[run_id] = preview
                    yield encode_event(
                        ToolActivityEvent(
                            tool_name=name,
                            tool_call_id=run_id,
                            args_preview=preview,
                            elapsed_ms=None,
                        )
                    )

                payload = langgraph_event_to_payload(event)

                if payload is None:
                    continue

                # Multi-bubble: emite message_break quando o nó emissor de tokens muda
                # e a bolha atual já tem conteúdo. Garante bolhas separadas por nó.
                if isinstance(payload, TokenEvent):
                    node_name = payload.node or ""
                    if (
                        token_buffer_nonempty
                        and node_name
                        and node_name != current_token_node
                    ):
                        yield encode_event(MessageBreakEvent())
                        token_buffer_nonempty = False
                    if node_name:
                        current_token_node = node_name
                    token_buffer_nonempty = True

                # Injeta duration_ms nos NodeEvent de fim
                if isinstance(payload, NodeEvent) and payload.status == "finished":
                    start = node_start_times.pop(name, None)
                    if start is not None:
                        payload = payload.model_copy(
                            update={
                                "duration_ms": int((time.monotonic() - start) * 1000)
                            }
                        )

                yield encode_event(payload)

                # Após tool_result (payload): emite ToolActivityEvent de fim e
                # WorkbenchInvalidateEvent. Ordem: result → activity(end) → invalidate.
                if kind == "on_tool_end":
                    run_id = event.get("run_id", name)
                    t0 = tool_start_times.pop(run_id, None)
                    elapsed = (
                        int((time.monotonic() - t0) * 1000) if t0 is not None else 0
                    )
                    preview = tool_args_previews.pop(run_id, "")
                    yield encode_event(
                        ToolActivityEvent(
                            tool_name=name,
                            tool_call_id=run_id,
                            args_preview=preview,
                            elapsed_ms=elapsed,
                        )
                    )
                    meta = _get_tool_meta(name)
                    tabs = meta.get("invalidates", [])
                    if tabs:
                        yield encode_event(
                            WorkbenchInvalidateEvent(tabs=tabs, tool_name=name)
                        )

        except Exception as exc:
            logger.exception("adapt_stream: erro no stream LangGraph")
            code, friendly = classify_stream_error(exc)
            yield encode_event(ErrorEvent(message=friendly, code=code))

        finally:
            yield encode_event(DoneEvent(thread_id=thread_id))

    return _gen()
