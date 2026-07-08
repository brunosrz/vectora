"""Testes para backend/api/handlers/webhooks.py — INT-1 (infra) + INT-2 (GitHub).

Cobre:
- Verificação de assinatura por provider (válida → 200, inválida → 401)
- Payload malformado → 400
- Slack url_verification challenge → responde imediatamente
- Dispatcher chama handler correto por provider
- SSE bridge emite evento para clientes conectados
- Persistência no banco (mock do get_db)
"""

from __future__ import annotations

import hashlib
import hmac
import json
import time
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi.testclient import TestClient

from backend.api.handlers.webhooks import (
    CHANNEL_SSE,
    _emit_sse_event,
    _sse_queues,
    _verify_github,
    _verify_gitlab,
    _verify_linear,
    _verify_mailgun,
    _verify_slack,
    on_remote_sse_event,
    router,
)

# ---------------------------------------------------------------------------
# Fixture de app mínimo com o router de webhooks
# ---------------------------------------------------------------------------


@pytest.fixture
def client() -> TestClient:
    from fastapi import FastAPI

    app = FastAPI()
    app.include_router(router)
    return TestClient(app, raise_server_exceptions=False)


# ---------------------------------------------------------------------------
# Verificadores de assinatura — testes unitários puros
# ---------------------------------------------------------------------------


class TestVerifyGitHub:
    def _sig(self, body: bytes, secret: str) -> str:
        return "sha256=" + hmac.new(secret.encode(), body, hashlib.sha256).hexdigest()

    def test_assinatura_valida(self) -> None:
        body = b'{"action":"opened"}'
        secret = "meu-secret"
        headers = {"x-hub-signature-256": self._sig(body, secret)}
        assert _verify_github(body, headers, secret) is True

    def test_assinatura_invalida(self) -> None:
        body = b'{"action":"opened"}'
        headers = {"x-hub-signature-256": "sha256=invalido"}
        assert _verify_github(body, headers, "secret") is False

    def test_sem_header(self) -> None:
        assert _verify_github(b"body", {}, "secret") is False

    def test_prefixo_errado(self) -> None:
        body = b"body"
        headers = {"x-hub-signature-256": "md5=abc"}
        assert _verify_github(body, headers, "secret") is False


class TestVerifyGitLab:
    def test_token_correto(self) -> None:
        assert (
            _verify_gitlab(b"body", {"x-gitlab-token": "meu-token"}, "meu-token")
            is True
        )

    def test_token_errado(self) -> None:
        assert _verify_gitlab(b"body", {"x-gitlab-token": "errado"}, "correto") is False

    def test_sem_header(self) -> None:
        assert _verify_gitlab(b"body", {}, "correto") is False


class TestVerifySlack:
    def _make_headers(
        self, body: bytes, secret: str, ts: str | None = None
    ) -> dict[str, str]:
        ts = ts or str(int(time.time()))
        base = f"v0:{ts}:{body.decode()}"
        sig = (
            "v0=" + hmac.new(secret.encode(), base.encode(), hashlib.sha256).hexdigest()
        )
        return {"x-slack-request-timestamp": ts, "x-slack-signature": sig}

    def test_assinatura_valida(self) -> None:
        body = b'{"type":"event_callback"}'
        secret = "slack-secret"
        headers = self._make_headers(body, secret)
        assert _verify_slack(body, headers, secret) is True

    def test_assinatura_invalida(self) -> None:
        body = b'{"type":"event_callback"}'
        headers = self._make_headers(body, "certo")
        assert _verify_slack(body, headers, "errado") is False

    def test_timestamp_expirado(self) -> None:
        body = b"body"
        ts = str(int(time.time()) - 400)  # mais de 5 min atrás
        headers = self._make_headers(body, "secret", ts=ts)
        assert _verify_slack(body, headers, "secret") is False

    def test_timestamp_invalido(self) -> None:
        body = b"body"
        headers = {
            "x-slack-request-timestamp": "nao-e-numero",
            "x-slack-signature": "v0=abc",
        }
        assert _verify_slack(body, headers, "secret") is False


class TestVerifyLinear:
    def _sig(self, body: bytes, secret: str) -> str:
        return hmac.new(secret.encode(), body, hashlib.sha256).hexdigest()

    def test_assinatura_valida(self) -> None:
        body = b'{"type":"Issue","action":"create"}'
        secret = "linear-secret"
        headers = {"x-linear-signature": self._sig(body, secret)}
        assert _verify_linear(body, headers, secret) is True

    def test_assinatura_invalida(self) -> None:
        headers = {"x-linear-signature": "invalido"}
        assert _verify_linear(b"body", headers, "secret") is False


class TestVerifyMailgun:
    def _sig(self, ts: str, token: str, key: str) -> str:
        data = (ts + token).encode()
        return hmac.new(key.encode(), data, hashlib.sha256).hexdigest()

    def test_assinatura_valida(self) -> None:
        ts = str(int(time.time()))
        token = "abc123"
        key = "mailgun-key"
        sig = self._sig(ts, token, key)
        body = json.dumps({"timestamp": ts, "token": token, "signature": sig}).encode()
        assert _verify_mailgun(body, {}, key) is True

    def test_assinatura_invalida(self) -> None:
        body = json.dumps(
            {"timestamp": "1", "token": "t", "signature": "errado"}
        ).encode()
        assert _verify_mailgun(body, {}, "chave") is False

    def test_payload_invalido(self) -> None:
        assert _verify_mailgun(b"nao-e-json", {}, "chave") is False


# ---------------------------------------------------------------------------
# Endpoint /webhook/{provider}
# ---------------------------------------------------------------------------


class TestWebhookEndpoint:
    def _github_body_and_sig(self, payload: dict, secret: str) -> tuple[bytes, str]:
        body = json.dumps(payload).encode()
        sig = "sha256=" + hmac.new(secret.encode(), body, hashlib.sha256).hexdigest()
        return body, sig

    @patch("backend.api.handlers.webhooks._persist_event", new_callable=AsyncMock)
    def test_github_assinatura_valida(
        self, mock_persist: AsyncMock, client: TestClient
    ) -> None:
        payload = {"action": "opened", "pull_request": {"number": 1, "title": "PR"}}
        secret = "meu-secret"
        body, sig = self._github_body_and_sig(payload, secret)
        with patch.dict("os.environ", {"GITHUB_WEBHOOK_SECRET": secret}):
            resp = client.post(
                "/webhook/github",
                content=body,
                headers={
                    "x-github-event": "pull_request",
                    "x-hub-signature-256": sig,
                    "content-type": "application/json",
                },
            )
        assert resp.status_code == 200
        mock_persist.assert_awaited_once()

    @patch("backend.api.handlers.webhooks._persist_event", new_callable=AsyncMock)
    def test_github_assinatura_invalida(
        self, mock_persist: AsyncMock, client: TestClient
    ) -> None:
        with patch.dict("os.environ", {"GITHUB_WEBHOOK_SECRET": "correto"}):
            resp = client.post(
                "/webhook/github",
                content=b'{"action":"opened"}',
                headers={
                    "x-github-event": "push",
                    "x-hub-signature-256": "sha256=errado",
                    "content-type": "application/json",
                },
            )
        assert resp.status_code == 401
        mock_persist.assert_not_awaited()

    @patch("backend.api.handlers.webhooks._persist_event", new_callable=AsyncMock)
    def test_sem_secret_configurado_aceita(
        self, mock_persist: AsyncMock, client: TestClient
    ) -> None:
        with patch.dict("os.environ", {}, clear=True):
            resp = client.post(
                "/webhook/github",
                json={"action": "opened"},
                headers={"x-github-event": "push"},
            )
        assert resp.status_code == 200

    @patch("backend.api.handlers.webhooks._persist_event", new_callable=AsyncMock)
    def test_payload_malformado(
        self, mock_persist: AsyncMock, client: TestClient
    ) -> None:
        with patch.dict("os.environ", {}, clear=True):
            resp = client.post(
                "/webhook/github",
                content=b"isto nao e json{",
                headers={
                    "x-github-event": "push",
                    "content-type": "application/json",
                },
            )
        assert resp.status_code == 400

    @patch("backend.api.handlers.webhooks._persist_event", new_callable=AsyncMock)
    def test_slack_url_verification_sem_secret(
        self, mock_persist: AsyncMock, client: TestClient
    ) -> None:
        resp = client.post(
            "/webhook/slack",
            json={"type": "url_verification", "challenge": "abc123"},
        )
        assert resp.status_code == 200
        assert resp.json()["challenge"] == "abc123"
        # url_verification não persiste
        mock_persist.assert_not_awaited()

    @patch("backend.api.handlers.webhooks._persist_event", new_callable=AsyncMock)
    def test_provider_sem_verificador_aceita(
        self, mock_persist: AsyncMock, client: TestClient
    ) -> None:
        resp = client.post("/webhook/sendgrid", json={"event": "delivered"})
        assert resp.status_code == 200


# ---------------------------------------------------------------------------
# SSE bridge
# ---------------------------------------------------------------------------


class TestSSEBridge:
    """`_emit_sse_event` publica no KV (cross-réplica); `on_remote_sse_event`
    (o subscriber, registrado em cache_sync.start_cache_sync) é quem de fato
    escreve em `_sse_queues`. As duas pontas são testadas separadamente e
    depois juntas de ponta a ponta via um MemoryKV real."""

    def test_emit_sse_event_publica_no_canal_kv(self) -> None:
        with patch("backend.persistence.kv.publish_soon") as mock_publish:
            _emit_sse_event("github", "push", {"ref": "main"})

        assert mock_publish.call_count == 1
        channel, payload = mock_publish.call_args[0]
        assert channel == CHANNEL_SSE
        event = json.loads(payload)
        assert event["provider"] == "github"
        assert event["event_type"] == "push"
        assert event["data"]["ref"] == "main"

    def test_on_remote_sse_event_entrega_para_filas(self) -> None:
        import asyncio

        q: asyncio.Queue = asyncio.Queue()
        _sse_queues.append(q)
        try:
            payload = json.dumps(
                {
                    "type": "webhook_event",
                    "provider": "github",
                    "event_type": "push",
                    "data": {"ref": "main"},
                }
            )
            on_remote_sse_event(payload)
            assert not q.empty()
            event = q.get_nowait()
            assert event["provider"] == "github"
            assert event["data"]["ref"] == "main"
        finally:
            _sse_queues.remove(q)

    def test_on_remote_sse_event_fila_cheia_nao_levanta(self) -> None:
        import asyncio

        q: asyncio.Queue = asyncio.Queue(maxsize=1)
        q.put_nowait({"dummy": True})
        _sse_queues.append(q)
        try:
            on_remote_sse_event(json.dumps({"provider": "github"}))
        finally:
            _sse_queues.remove(q)

    def test_on_remote_sse_event_payload_invalido_nao_levanta(self) -> None:
        # Erro: payload que não é JSON válido — não deve propagar exceção
        # (viria de outra réplica via KV, fora do nosso controle de forma).
        on_remote_sse_event("isso não é json")

    @pytest.mark.asyncio
    async def test_emit_sse_event_ponta_a_ponta_via_kv_real(self) -> None:
        """Publica via `_emit_sse_event` e confirma que chega em
        `_sse_queues` passando pelo roundtrip real do KV (MemoryKV em modo
        lite) — prova que a ponte publish→subscribe funciona de fato, não
        só que cada metade foi chamada com os argumentos certos."""
        import asyncio

        from backend.persistence import kv as kv_module

        kv_module.reset_kv()
        try:
            kv = await kv_module.get_kv()
            kv.subscribe(CHANNEL_SSE, on_remote_sse_event)
            await kv.start()

            q: asyncio.Queue = asyncio.Queue()
            _sse_queues.append(q)
            try:
                _emit_sse_event("linear", "issue.created", {"id": "ISS-1"})
                # publish_soon agenda uma task no loop corrente — cede o
                # controle uma vez pra ela rodar antes de checar a fila.
                await asyncio.sleep(0)
                event = await asyncio.wait_for(q.get(), timeout=1.0)
                assert event["provider"] == "linear"
                assert event["data"]["id"] == "ISS-1"
            finally:
                _sse_queues.remove(q)
        finally:
            kv_module.reset_kv()


# ---------------------------------------------------------------------------
# Handlers específicos — GitHub (INT-2)
# ---------------------------------------------------------------------------


class TestGitHubHandlers:
    @pytest.mark.asyncio
    async def test_handle_github_workflow_run(self) -> None:
        from unittest.mock import patch as p

        from backend.api.handlers.webhooks import _handle_github

        payload = {
            "action": "completed",
            "workflow_run": {
                "id": 1,
                "name": "CI",
                "status": "completed",
                "conclusion": "success",
                "html_url": "https://github.com/r/actions/runs/1",
            },
            "repository": {"full_name": "user/repo"},
        }
        emitted: list[dict] = []

        def fake_emit(provider: str, event_type: str, data: dict) -> None:
            emitted.append(
                {"provider": provider, "event_type": event_type, "data": data}
            )

        with p("backend.api.handlers.webhooks._emit_sse_event", fake_emit):
            await _handle_github("workflow_run", payload, MagicMock())

        assert len(emitted) == 1
        assert emitted[0]["event_type"] == "workflow_run.completed"
        assert emitted[0]["data"]["conclusion"] == "success"

    @pytest.mark.asyncio
    async def test_handle_github_pull_request(self) -> None:
        from unittest.mock import patch as p

        from backend.api.handlers.webhooks import _handle_github

        payload = {
            "action": "opened",
            "pull_request": {
                "number": 42,
                "title": "feat: nova feature",
                "state": "open",
                "merged": False,
                "html_url": "https://github.com/r/pull/42",
            },
            "repository": {"full_name": "user/repo"},
        }
        emitted: list[dict] = []

        with p(
            "backend.api.handlers.webhooks._emit_sse_event",
            lambda *a, **kw: emitted.append(
                kw or {"provider": a[0], "event_type": a[1], "data": a[2]}
            ),
        ):
            await _handle_github("pull_request", payload, MagicMock())

        assert len(emitted) == 1

    @pytest.mark.asyncio
    async def test_handle_github_push(self) -> None:
        from unittest.mock import patch as p

        from backend.api.handlers.webhooks import _handle_github

        payload = {
            "ref": "refs/heads/main",
            "after": "abc123",
            "commits": [{}, {}],
            "pusher": {"name": "dev"},
            "repository": {"full_name": "user/repo"},
        }
        emitted: list[dict] = []

        def fake_emit(provider: str, event_type: str, data: dict) -> None:
            emitted.append({"event_type": event_type, "data": data})

        with p("backend.api.handlers.webhooks._emit_sse_event", fake_emit):
            await _handle_github("push", payload, MagicMock())

        assert emitted[0]["event_type"] == "push"
        assert emitted[0]["data"]["commit_count"] == 2

    @pytest.mark.asyncio
    async def test_handle_github_issues(self) -> None:
        from unittest.mock import patch as p

        from backend.api.handlers.webhooks import _handle_github

        payload = {
            "action": "opened",
            "issue": {
                "number": 10,
                "title": "Bug no login",
                "state": "open",
                "html_url": "https://github.com/r/issues/10",
            },
            "repository": {"full_name": "user/repo"},
        }
        emitted: list[dict] = []

        def fake_emit(provider: str, event_type: str, data: dict) -> None:
            emitted.append({"event_type": event_type, "data": data})

        with p("backend.api.handlers.webhooks._emit_sse_event", fake_emit):
            await _handle_github("issues", payload, MagicMock())

        assert emitted[0]["data"]["issue_number"] == 10
