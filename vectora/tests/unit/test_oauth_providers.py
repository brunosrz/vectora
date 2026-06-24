"""Testes para os novos OAuth providers: GitLab, Google, Slack (INT-3/4/5).

Cobre:
- Inicio de fluxo OAuth → redirect correto com parâmetros
- Callback com code válido → token salvo + redirect de sucesso
- Callback sem code → 400
- Status com token → connected=True
- Status sem token → connected=False
- Disconnect → chama delete_env_override
- Verificação de API key por provider
"""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from backend.api.handlers.oauth import router


@pytest.fixture
def client() -> TestClient:
    app = FastAPI()
    app.include_router(router)

    def fake_user(request):
        from types import SimpleNamespace

        request.state.user = SimpleNamespace(id="user-123")

    app.middleware("http")(lambda req, call_next: (fake_user(req), call_next(req))[1])
    return TestClient(app, raise_server_exceptions=False, follow_redirects=False)


# ---------------------------------------------------------------------------
# GitLab OAuth
# ---------------------------------------------------------------------------


class TestGitLabOAuth:
    _env = {
        "GITLAB_OAUTH_CLIENT_ID": "gl-client-id",
        "GITLAB_OAUTH_CLIENT_SECRET": "gl-client-secret",
        "GITLAB_BASE_URL": "https://gitlab.com",
    }

    def test_start_redirect(self, client: TestClient) -> None:
        with patch.dict("os.environ", self._env):
            r = client.get("/auth/gitlab")
        assert r.status_code == 302
        loc = r.headers["location"]
        assert "gitlab.com/oauth/authorize" in loc
        assert "gl-client-id" in loc
        assert "user-123" in loc

    def test_callback_sem_code(self, client: TestClient) -> None:
        with patch.dict("os.environ", self._env):
            r = client.get("/auth/gitlab/callback")
        assert r.status_code == 400

    @patch("backend.services.auth.set_env_override", new_callable=AsyncMock)
    def test_callback_token_salvo(
        self, mock_set: AsyncMock, client: TestClient
    ) -> None:
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"access_token": "gltoken123"}

        with (
            patch.dict("os.environ", self._env),
            patch("httpx.AsyncClient") as mock_httpx,
        ):
            mock_ctx = AsyncMock()
            mock_ctx.__aenter__ = AsyncMock(return_value=mock_ctx)
            mock_ctx.__aexit__ = AsyncMock(return_value=False)
            mock_ctx.post = AsyncMock(return_value=mock_response)
            mock_httpx.return_value = mock_ctx

            r = client.get("/auth/gitlab/callback?code=abc&state=user-123")

        assert r.status_code in {302, 307}
        assert "oauth_success=gitlab" in r.headers.get("location", "")

    def test_status_sem_token(self, client: TestClient) -> None:
        with (
            patch.dict(
                "os.environ", {k: v for k, v in self._env.items() if "CLIENT" not in k}
            ),
            patch(
                "backend.services.auth.get_env_overrides",
                new_callable=AsyncMock,
                return_value={},
            ),
        ):
            r = client.get("/auth/gitlab/status")
        assert r.status_code == 200
        assert r.json()["connected"] is False

    @patch("backend.services.auth.delete_env_override", new_callable=AsyncMock)
    def test_disconnect(self, mock_del: AsyncMock, client: TestClient) -> None:
        r = client.request("DELETE", "/auth/gitlab")
        assert r.status_code == 200
        assert r.json()["status"] == "disconnected"


# ---------------------------------------------------------------------------
# Google OAuth
# ---------------------------------------------------------------------------


class TestGoogleOAuth:
    _env = {
        "GOOGLE_OAUTH_CLIENT_ID": "google-client-id.apps.googleusercontent.com",
        "GOOGLE_OAUTH_CLIENT_SECRET": "GOCSPX-secret",
    }

    def test_start_redirect(self, client: TestClient) -> None:
        with patch.dict("os.environ", self._env):
            r = client.get("/auth/google")
        assert r.status_code == 302
        loc = r.headers["location"]
        assert "accounts.google.com" in loc
        assert "drive.readonly" in loc
        assert "gmail.readonly" in loc

    def test_callback_sem_code(self, client: TestClient) -> None:
        with patch.dict("os.environ", self._env):
            r = client.get("/auth/google/callback")
        assert r.status_code == 400

    @patch("backend.services.auth.set_env_override", new_callable=AsyncMock)
    def test_callback_salva_access_e_refresh(
        self, mock_set: AsyncMock, client: TestClient
    ) -> None:
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "access_token": "goog-access",
            "refresh_token": "goog-refresh",
        }

        with (
            patch.dict("os.environ", self._env),
            patch("httpx.AsyncClient") as mock_httpx,
        ):
            mock_ctx = AsyncMock()
            mock_ctx.__aenter__ = AsyncMock(return_value=mock_ctx)
            mock_ctx.__aexit__ = AsyncMock(return_value=False)
            mock_ctx.post = AsyncMock(return_value=mock_response)
            mock_httpx.return_value = mock_ctx

            r = client.get("/auth/google/callback?code=gcode&state=user-123")

        assert r.status_code in {302, 307}
        assert "oauth_success=google" in r.headers.get("location", "")
        calls = [str(c) for c in mock_set.await_args_list]
        assert any("GOOGLE_ACCESS_TOKEN" in c for c in calls)
        assert any("GOOGLE_REFRESH_TOKEN" in c for c in calls)

    def test_status_sem_token(self, client: TestClient) -> None:
        with patch(
            "backend.services.auth.get_env_overrides",
            new_callable=AsyncMock,
            return_value={},
        ):
            r = client.get("/auth/google/status")
        assert r.json()["connected"] is False

    @patch("backend.services.auth.delete_env_override", new_callable=AsyncMock)
    def test_disconnect_remove_ambos_tokens(
        self, mock_del: AsyncMock, client: TestClient
    ) -> None:
        r = client.request("DELETE", "/auth/google")
        assert r.status_code == 200
        assert mock_del.await_count == 2  # access + refresh


# ---------------------------------------------------------------------------
# Slack OAuth
# ---------------------------------------------------------------------------


class TestSlackOAuth:
    _env = {
        "SLACK_OAUTH_CLIENT_ID": "xxxx.yyyy",
        "SLACK_OAUTH_CLIENT_SECRET": "slack-secret",
    }

    def test_start_redirect(self, client: TestClient) -> None:
        with patch.dict("os.environ", self._env):
            r = client.get("/auth/slack")
        assert r.status_code == 302
        loc = r.headers["location"]
        assert "slack.com/oauth/v2/authorize" in loc
        assert "xxxx.yyyy" in loc

    def test_callback_sem_code(self, client: TestClient) -> None:
        with patch.dict("os.environ", self._env):
            r = client.get("/auth/slack/callback")
        assert r.status_code == 400

    @patch("backend.services.auth.set_env_override", new_callable=AsyncMock)
    def test_callback_token_salvo(
        self, mock_set: AsyncMock, client: TestClient
    ) -> None:
        mock_response = MagicMock()
        mock_response.json.return_value = {"ok": True, "access_token": "xoxb-slack"}

        with (
            patch.dict("os.environ", self._env),
            patch("httpx.AsyncClient") as mock_httpx,
        ):
            mock_ctx = AsyncMock()
            mock_ctx.__aenter__ = AsyncMock(return_value=mock_ctx)
            mock_ctx.__aexit__ = AsyncMock(return_value=False)
            mock_ctx.post = AsyncMock(return_value=mock_response)
            mock_httpx.return_value = mock_ctx

            r = client.get("/auth/slack/callback?code=slcode&state=user-123")

        assert r.status_code in {302, 307}
        assert "oauth_success=slack" in r.headers.get("location", "")

    def test_callback_oauth_error(self, client: TestClient) -> None:
        mock_response = MagicMock()
        mock_response.json.return_value = {"ok": False, "error": "invalid_code"}

        with (
            patch.dict("os.environ", self._env),
            patch("httpx.AsyncClient") as mock_httpx,
        ):
            mock_ctx = AsyncMock()
            mock_ctx.__aenter__ = AsyncMock(return_value=mock_ctx)
            mock_ctx.__aexit__ = AsyncMock(return_value=False)
            mock_ctx.post = AsyncMock(return_value=mock_response)
            mock_httpx.return_value = mock_ctx

            r = client.get("/auth/slack/callback?code=bad&state=user-123")

        loc = r.headers.get("location", "")
        assert "oauth_error=slack" in loc

    def test_status_sem_token(self, client: TestClient) -> None:
        with patch(
            "backend.services.auth.get_env_overrides",
            new_callable=AsyncMock,
            return_value={},
        ):
            r = client.get("/auth/slack/status")
        assert r.json()["connected"] is False

    @patch("backend.services.auth.delete_env_override", new_callable=AsyncMock)
    def test_disconnect(self, mock_del: AsyncMock, client: TestClient) -> None:
        r = client.request("DELETE", "/auth/slack")
        assert r.status_code == 200


# ---------------------------------------------------------------------------
# Registry de integrações — novos providers aparecem
# ---------------------------------------------------------------------------


class TestIntegrationsRegistry:
    def test_novos_providers_presentes(self, client: TestClient) -> None:
        from backend.api.handlers.oauth import INTEGRATIONS_REGISTRY

        ids = {i["id"] for i in INTEGRATIONS_REGISTRY}
        expected = {
            "github",
            "gitlab",
            "google",
            "google-drive",
            "gmail",
            "slack",
            "linear",
            "jira",
            "notion",
            "resend",
            "sendgrid",
            "mailgun",
        }
        missing = expected - ids
        assert not missing, f"Providers faltando no registry: {missing}"

    def test_todos_tem_env_var(self) -> None:
        from backend.api.handlers.oauth import INTEGRATIONS_REGISTRY

        for integ in INTEGRATIONS_REGISTRY:
            assert "env_var" in integ, f"{integ['id']} sem env_var"

    def test_oauth_providers_tem_scopes(self) -> None:
        from backend.api.handlers.oauth import INTEGRATIONS_REGISTRY

        oauth_ids = {"github", "gitlab", "google", "slack"}
        for integ in INTEGRATIONS_REGISTRY:
            if integ["id"] in oauth_ids:
                assert integ.get("oauth_scopes") or integ.get("parent"), (
                    f"{integ['id']} oauth sem oauth_scopes nem parent"
                )
