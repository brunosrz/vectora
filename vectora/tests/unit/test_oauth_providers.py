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

    @patch("backend.rbac.auth.set_env_override", new_callable=AsyncMock)
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
                "backend.rbac.auth.get_env_overrides",
                new_callable=AsyncMock,
                return_value={},
            ),
        ):
            r = client.get("/auth/gitlab/status")
        assert r.status_code == 200
        assert r.json()["connected"] is False

    @patch("backend.rbac.auth.delete_env_override", new_callable=AsyncMock)
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

    @patch("backend.rbac.auth.set_env_override", new_callable=AsyncMock)
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
            "backend.rbac.auth.get_env_overrides",
            new_callable=AsyncMock,
            return_value={},
        ):
            r = client.get("/auth/google/status")
        assert r.json()["connected"] is False

    @patch("backend.rbac.auth.delete_env_override", new_callable=AsyncMock)
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

    @patch("backend.rbac.auth.set_env_override", new_callable=AsyncMock)
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
            "backend.rbac.auth.get_env_overrides",
            new_callable=AsyncMock,
            return_value={},
        ):
            r = client.get("/auth/slack/status")
        assert r.json()["connected"] is False

    @patch("backend.rbac.auth.delete_env_override", new_callable=AsyncMock)
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


# ---------------------------------------------------------------------------
# GET /integrations — connected via env_var_aliases (Sprint B: token sem relay)
# ---------------------------------------------------------------------------


class TestOauthConfiguredFlag:
    """`oauth_configured` só é true quando o operador registrou o app
    próprio no provider (GitHub App pro GitHub, OAuth App clássico pros
    demais) com CLIENT_ID+SECRET — sem isso, "Conectar via OAuth" sempre
    falharia com 503 e a UI usa esta flag pra nunca oferecer o botão."""

    def test_sem_client_id_secret_oauth_configured_false(
        self, client: TestClient, monkeypatch
    ) -> None:
        for var in ("GITLAB_OAUTH_CLIENT_ID", "GITLAB_OAUTH_CLIENT_SECRET"):
            monkeypatch.delenv(var, raising=False)
        with patch("backend.rbac.auth.get_env_overrides", AsyncMock(return_value={})):
            resp = client.get("/integrations")
        gitlab = next(i for i in resp.json()["integrations"] if i["id"] == "gitlab")
        assert gitlab["oauth_configured"] is False

    def test_com_client_id_e_secret_oauth_configured_true(
        self, client: TestClient, monkeypatch
    ) -> None:
        monkeypatch.setenv("GITLAB_OAUTH_CLIENT_ID", "cid")
        monkeypatch.setenv("GITLAB_OAUTH_CLIENT_SECRET", "csecret")
        with patch("backend.rbac.auth.get_env_overrides", AsyncMock(return_value={})):
            resp = client.get("/integrations")
        gitlab = next(i for i in resp.json()["integrations"] if i["id"] == "gitlab")
        assert gitlab["oauth_configured"] is True

    def test_provider_filho_herda_configuracao_do_pai(
        self, client: TestClient, monkeypatch
    ) -> None:
        """google-drive/gmail não têm CLIENT_ID próprio — usam o do
        provider pai ("google", via `parent`)."""
        monkeypatch.setenv("GOOGLE_OAUTH_CLIENT_ID", "cid")
        monkeypatch.setenv("GOOGLE_OAUTH_CLIENT_SECRET", "csecret")
        with patch("backend.rbac.auth.get_env_overrides", AsyncMock(return_value={})):
            resp = client.get("/integrations")
        drive = next(
            i for i in resp.json()["integrations"] if i["id"] == "google-drive"
        )
        assert drive["oauth_configured"] is True

    def test_provider_apikey_nunca_tem_oauth_configured(
        self, client: TestClient
    ) -> None:
        with patch("backend.rbac.auth.get_env_overrides", AsyncMock(return_value={})):
            resp = client.get("/integrations")
        gemini = next(i for i in resp.json()["integrations"] if i["id"] == "gemini")
        assert gemini["oauth_configured"] is False


class TestListIntegrationsAlias:
    def test_github_connected_via_alias_sem_env_var_principal(
        self, client: TestClient, monkeypatch
    ) -> None:
        """Erro/borda: usuário configurou só GITHUB_PERSONAL_ACCESS_TOKEN (o
        nome que o MCP marketplace usa), sem GITHUB_TOKEN — o card GitHub
        ainda deve aparecer conectado, não depende do relay."""
        monkeypatch.delenv("GITHUB_TOKEN", raising=False)
        monkeypatch.setenv("GITHUB_PERSONAL_ACCESS_TOKEN", "ghp_fake")
        with patch("backend.rbac.auth.get_env_overrides", AsyncMock(return_value={})):
            resp = client.get("/integrations")
        assert resp.status_code == 200
        github = next(i for i in resp.json()["integrations"] if i["id"] == "github")
        assert github["connected"] is True

    def test_gemini_desconectado_sem_google_api_key(
        self, client: TestClient, monkeypatch
    ) -> None:
        monkeypatch.delenv("GOOGLE_API_KEY", raising=False)
        with patch("backend.rbac.auth.get_env_overrides", AsyncMock(return_value={})):
            resp = client.get("/integrations")
        assert resp.status_code == 200
        gemini = next(i for i in resp.json()["integrations"] if i["id"] == "gemini")
        assert gemini["connected"] is False

    def test_gemini_conectado_com_google_api_key(
        self, client: TestClient, monkeypatch
    ) -> None:
        monkeypatch.setenv("GOOGLE_API_KEY", "AIza-fake")
        with patch("backend.rbac.auth.get_env_overrides", AsyncMock(return_value={})):
            resp = client.get("/integrations")
        assert resp.status_code == 200
        gemini = next(i for i in resp.json()["integrations"] if i["id"] == "gemini")
        assert gemini["connected"] is True
