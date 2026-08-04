"""Handler de Webhooks — recebe e despacha eventos de provedores externos.

Infraestrutura genérica de recepção/verificação + handlers específicos por provider (GitHub, etc.).

Endpoints:
    POST /webhook/{provider}  — recebe evento, verifica assinatura, persiste e emite SSE

Provedores suportados:
    github   — X-Hub-Signature-256 (HMAC-SHA256)
    gitlab   — X-Gitlab-Token (comparação direta)
    slack    — X-Slack-Signature (v0=HMAC-SHA256)
    linear   — X-Linear-Signature (HMAC-SHA256)
    resend   — svix-signature (HMAC-SHA256)
    sendgrid — verificação ECDSA via chave pública
    mailgun  — token + timestamp + signature HMAC-SHA256

Configuração (env vars / Settings):
    GITHUB_WEBHOOK_SECRET
    GITLAB_WEBHOOK_SECRET
    SLACK_SIGNING_SECRET
    LINEAR_WEBHOOK_SECRET
    RESEND_WEBHOOK_SECRET
    SENDGRID_WEBHOOK_KEY
    MAILGUN_WEBHOOK_SIGNING_KEY
"""

from __future__ import annotations

import contextlib
import hashlib
import hmac
import json
import logging
import os
import time
import uuid
from collections.abc import Callable, Coroutine
from typing import Any

from fastapi import APIRouter, HTTPException, Request, Response
from fastapi.responses import JSONResponse

logger = logging.getLogger(__name__)

router = APIRouter(tags=["webhooks"])

# ---------------------------------------------------------------------------
# Tipos
# ---------------------------------------------------------------------------

WebhookPayload = dict[str, Any]
WebhookHandler = Callable[[str, WebhookPayload, Request], Coroutine[Any, Any, None]]

# ---------------------------------------------------------------------------
# Verificação de assinatura por provider
# ---------------------------------------------------------------------------


def _verify_github(body: bytes, headers: dict[str, str], secret: str) -> bool:
    sig = headers.get("x-hub-signature-256", "")
    if not sig.startswith("sha256="):
        return False
    expected = "sha256=" + hmac.new(secret.encode(), body, hashlib.sha256).hexdigest()
    return hmac.compare_digest(sig, expected)


def _verify_gitlab(body: bytes, headers: dict[str, str], secret: str) -> bool:
    token = headers.get("x-gitlab-token", "")
    return hmac.compare_digest(token, secret)


def _verify_slack(body: bytes, headers: dict[str, str], secret: str) -> bool:
    ts = headers.get("x-slack-request-timestamp", "")
    sig = headers.get("x-slack-signature", "")
    # Rejeita requisições com mais de 5 minutos (replay attack)
    try:
        if abs(time.time() - float(ts)) > 300:
            return False
    except (ValueError, TypeError):
        return False
    base = f"v0:{ts}:{body.decode()}"
    expected = (
        "v0=" + hmac.new(secret.encode(), base.encode(), hashlib.sha256).hexdigest()
    )
    return hmac.compare_digest(sig, expected)


def _verify_linear(body: bytes, headers: dict[str, str], secret: str) -> bool:
    sig = headers.get("x-linear-signature", "")
    expected = hmac.new(secret.encode(), body, hashlib.sha256).hexdigest()
    return hmac.compare_digest(sig, expected)


def _verify_resend(body: bytes, headers: dict[str, str], secret: str) -> bool:
    sig_header = headers.get("svix-signature", "")
    ts = headers.get("svix-timestamp", "")
    msg_id = headers.get("svix-id", "")
    signed_content = f"{msg_id}.{ts}.{body.decode()}"
    expected = hmac.new(
        secret.encode(), signed_content.encode(), hashlib.sha256
    ).hexdigest()
    import base64

    for part in sig_header.split(" "):
        if "," not in part:
            continue
        _, sig_b64 = part.split(",", 1)
        decoded = None
        with contextlib.suppress(Exception):
            decoded = base64.b64decode(sig_b64).hex()
        if decoded is not None and hmac.compare_digest(decoded, expected):
            return True
    return False


def _verify_mailgun(body: bytes, headers: dict[str, str], secret: str) -> bool:
    try:
        payload = json.loads(body)
        ts = str(payload.get("timestamp", ""))
        token = payload.get("token", "")
        signature = payload.get("signature", "")
    except Exception:
        return False
    data = (ts + token).encode()
    expected = hmac.new(secret.encode(), data, hashlib.sha256).hexdigest()
    return hmac.compare_digest(signature, expected)


# mapa provider → (env var do secret, verificador)
_VERIFIERS: dict[str, tuple[str, Callable[[bytes, dict[str, str], str], bool]]] = {
    "github": ("GITHUB_WEBHOOK_SECRET", _verify_github),
    "gitlab": ("GITLAB_WEBHOOK_SECRET", _verify_gitlab),
    "slack": ("SLACK_SIGNING_SECRET", _verify_slack),
    "linear": ("LINEAR_WEBHOOK_SECRET", _verify_linear),
    "resend": ("RESEND_WEBHOOK_SECRET", _verify_resend),
    "mailgun": ("MAILGUN_WEBHOOK_SIGNING_KEY", _verify_mailgun),
}

# ---------------------------------------------------------------------------
# Handlers específicos por provider
# ---------------------------------------------------------------------------


async def _handle_github(
    event_type: str, payload: WebhookPayload, request: Request
) -> None:
    """Processa eventos do GitHub e emite SSE para o workbench."""
    action = payload.get("action", "")
    normalized_type = f"{event_type}.{action}" if action else event_type

    # workflow_run — notifica CI status
    if event_type == "workflow_run":
        run = payload.get("workflow_run", {})
        _emit_sse_event(
            provider="github",
            event_type=normalized_type,
            data={
                "run_id": run.get("id"),
                "name": run.get("name"),
                "status": run.get("status"),
                "conclusion": run.get("conclusion"),
                "html_url": run.get("html_url"),
                "repo": payload.get("repository", {}).get("full_name"),
            },
        )

    # pull_request — atualiza aba Git
    elif event_type == "pull_request":
        pr = payload.get("pull_request", {})
        _emit_sse_event(
            provider="github",
            event_type=normalized_type,
            data={
                "pr_number": pr.get("number"),
                "title": pr.get("title"),
                "state": pr.get("state"),
                "merged": pr.get("merged"),
                "html_url": pr.get("html_url"),
                "repo": payload.get("repository", {}).get("full_name"),
            },
        )

    # push — novo commit no histórico
    elif event_type == "push":
        commits = payload.get("commits", [])
        _emit_sse_event(
            provider="github",
            event_type="push",
            data={
                "ref": payload.get("ref"),
                "commit_count": len(commits),
                "head_sha": payload.get("after"),
                "pusher": payload.get("pusher", {}).get("name"),
                "repo": payload.get("repository", {}).get("full_name"),
            },
        )

    # check_run — status de checks individuais
    elif event_type == "check_run":
        check = payload.get("check_run", {})
        _emit_sse_event(
            provider="github",
            event_type=normalized_type,
            data={
                "check_id": check.get("id"),
                "name": check.get("name"),
                "status": check.get("status"),
                "conclusion": check.get("conclusion"),
                "html_url": check.get("html_url"),
                "repo": payload.get("repository", {}).get("full_name"),
            },
        )

    # issues — atualiza Issues tab
    elif event_type == "issues":
        issue = payload.get("issue", {})
        _emit_sse_event(
            provider="github",
            event_type=normalized_type,
            data={
                "issue_number": issue.get("number"),
                "title": issue.get("title"),
                "state": issue.get("state"),
                "html_url": issue.get("html_url"),
                "repo": payload.get("repository", {}).get("full_name"),
            },
        )


async def _handle_slack(
    event_type: str, payload: WebhookPayload, request: Request
) -> None:
    """Processa eventos do Slack — inclui url_verification challenge."""
    if payload.get("type") == "url_verification":
        # Slack envia challenge na primeira configuração — resposta especial
        # (tratada antes de persistir no banco)
        pass

    event = payload.get("event", {})
    _emit_sse_event(
        provider="slack",
        event_type=event.get("type", event_type),
        data={
            "channel": event.get("channel"),
            "user": event.get("user"),
            "text": event.get("text", "")[:500],
            "ts": event.get("ts"),
        },
    )


async def _handle_linear(
    event_type: str, payload: WebhookPayload, request: Request
) -> None:
    _emit_sse_event(
        provider="linear",
        event_type=event_type,
        data={
            "action": payload.get("action"),
            "type": payload.get("type"),
            "data": payload.get("data", {}),
        },
    )


async def _handle_gitlab(
    event_type: str, payload: WebhookPayload, request: Request
) -> None:
    _emit_sse_event(
        provider="gitlab",
        event_type=event_type,
        data={
            "object_kind": payload.get("object_kind"),
            "status": payload.get("object_attributes", {}).get("status"),
            "project": payload.get("project", {}).get("path_with_namespace"),
        },
    )


async def _handle_email(
    event_type: str, payload: WebhookPayload, request: Request
) -> None:
    _emit_sse_event(
        provider="email",
        event_type=event_type,
        data={
            "from": payload.get("from", payload.get("sender", "")),
            "to": payload.get("to", payload.get("recipient", "")),
            "subject": payload.get("subject", ""),
            "event": payload.get("event", event_type),
        },
    )


_HANDLERS: dict[str, WebhookHandler] = {
    "github": _handle_github,
    "gitlab": _handle_gitlab,
    "slack": _handle_slack,
    "linear": _handle_linear,
    "resend": _handle_email,
    "sendgrid": _handle_email,
    "mailgun": _handle_email,
}

# ---------------------------------------------------------------------------
# SSE bridge — emite WebhookEvent para clientes conectados
#
# Cross-réplica: `_emit_sse_event` publica no KV (`CHANNEL_SSE` — Redis em
# modo complete, sidecar NATS por padrão, local em modo lite) em vez de
# escrever direto em `_sse_queues`. Cada réplica está inscrita nesse canal
# (registro em `backend/embedding/cache_sync.py::start_cache_sync`, que já é
# o bootstrap único de pub/sub do KV) e só ela entrega pros seus próprios
# clientes SSE via `_on_remote_sse_event` — sem isso, um evento de
# background_tasks/RAG processado na réplica A nunca chegava a um cliente
# conectado na réplica B (o `_sse_queues` sempre foi local ao processo).
# Em modo lite (MemoryKV), o publish entrega no mesmo processo — o
# comportamento observável não muda, só passa a existir a ponte pronta pra
# quando há mais de uma réplica.
# ---------------------------------------------------------------------------

CHANNEL_SSE = "vectora:sse"

# Fila global de eventos webhook SSE (asyncio.Queue por conexão aberta)
_sse_queues: list[Any] = []


def _emit_sse_event(provider: str, event_type: str, data: dict[str, Any]) -> None:
    from backend.persistence.kv import publish_soon

    event = {
        "type": "webhook_event",
        "provider": provider,
        "event_type": event_type,
        "data": data,
    }
    publish_soon(CHANNEL_SSE, json.dumps(event))


def on_remote_sse_event(payload: str) -> None:
    """Callback do KV — entrega um evento (desta réplica ou de outra) pros
    clientes SSE conectados NESTA réplica. Única gravadora de `_sse_queues`.
    """
    try:
        event = json.loads(payload)
    except json.JSONDecodeError:
        return
    for q in _sse_queues:
        with contextlib.suppress(Exception):
            q.put_nowait(event)


# ---------------------------------------------------------------------------
# Persistência no banco
# ---------------------------------------------------------------------------


async def _persist_event(
    provider: str,
    event_type: str,
    payload: WebhookPayload,
    workspace_id: str | None,
) -> None:
    try:
        from backend.rbac.auth import _get_db

        db = await _get_db()
        await db.execute(
            """
            INSERT OR IGNORE INTO webhook_events
                (id, provider, event_type, payload_json, workspace_id, received_at)
            VALUES (?, ?, ?, ?, ?, datetime('now'))
            """,
            (
                str(uuid.uuid4()),
                provider,
                event_type,
                json.dumps(payload),
                workspace_id,
            ),
        )
        await db.commit()
    except Exception:
        logger.exception(
            "webhook: falha ao persistir evento provider=%s type=%s",
            provider,
            event_type,
        )


# ---------------------------------------------------------------------------
# Endpoint principal
# ---------------------------------------------------------------------------


@router.post("/webhook/{provider}")
async def receive_webhook(provider: str, request: Request) -> Response:
    """Recebe webhook de um provider externo, verifica assinatura e despacha."""
    body = await request.body()
    headers = {k.lower(): v for k, v in request.headers.items()}

    # Slack url_verification — responde imediatamente sem verificar assinatura
    # (o challenge chega antes do secret estar configurado na primeira vez)
    if provider == "slack":
        try:
            payload_check = json.loads(body)
            if payload_check.get("type") == "url_verification":
                return JSONResponse({"challenge": payload_check.get("challenge", "")})
        except Exception:
            pass

    # Verificação de assinatura
    verifier_cfg = _VERIFIERS.get(provider)
    if verifier_cfg:
        env_var, verify_fn = verifier_cfg
        secret = os.environ.get(env_var, "")
        if secret and not verify_fn(body, headers, secret):
            logger.warning("webhook: assinatura inválida provider=%s", provider)
            raise HTTPException(status_code=401, detail="Assinatura inválida")

    # Parse do payload
    try:
        payload: WebhookPayload = json.loads(body) if body else {}
    except json.JSONDecodeError:
        raise HTTPException(status_code=400, detail="Payload JSON inválido") from None

    # Determina tipo do evento. `payload["event"]` pode ser dict (Slack) OU
    # string (ex: email providers com {"event": "delivered"}) — só extrai
    # `.type` quando for dict.
    event_field = payload.get("event")
    nested_type = event_field.get("type") if isinstance(event_field, dict) else None
    event_type = (
        headers.get("x-github-event")
        or headers.get("x-gitlab-event")
        or payload.get("type")
        or nested_type
        or "unknown"
    )

    logger.info("webhook: recebido provider=%s event=%s", provider, event_type)

    # Persiste
    await _persist_event(provider, str(event_type), payload, workspace_id=None)

    # Despacha para handler específico
    handler = _HANDLERS.get(provider)
    if handler:
        try:
            await handler(str(event_type), payload, request)
        except Exception:
            logger.exception("webhook: erro no handler provider=%s", provider)

    # Ponte webhook→IA: dispara tasks 'webhook' cujo filtro casa este evento.
    # Fire-and-forget — a execução do agente pode demorar, e o provider (GitHub
    # etc.) espera resposta rápida; não bloqueamos o 200.
    async def _dispatch_bg() -> None:
        try:
            from backend.scheduling.background_tasks import dispatch_webhook_event

            await dispatch_webhook_event(provider, str(event_type), payload)
        except Exception:
            logger.exception("webhook: erro ao despachar para background tasks")

    import asyncio

    asyncio.create_task(_dispatch_bg())  # noqa: RUF006

    return Response(status_code=200)


# ---------------------------------------------------------------------------
# SSE endpoint — frontend subscreve eventos webhook em tempo real
# ---------------------------------------------------------------------------


@router.get("/webhook/events")
async def webhook_events_stream(request: Request) -> Any:
    """SSE stream de eventos webhook recebidos em tempo real."""
    import asyncio

    from fastapi.responses import StreamingResponse

    queue: asyncio.Queue[dict[str, Any]] = asyncio.Queue(maxsize=200)
    _sse_queues.append(queue)

    async def _stream() -> Any:
        try:
            # Heartbeat inicial
            yield 'data: {"type":"connected","provider":"system"}\n\n'
            while not await request.is_disconnected():
                try:
                    event = await asyncio.wait_for(queue.get(), timeout=30.0)
                    yield f"data: {json.dumps(event)}\n\n"
                except TimeoutError:
                    yield ": ping\n\n"
        finally:
            _sse_queues.remove(queue)

    return StreamingResponse(
        _stream(),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )
