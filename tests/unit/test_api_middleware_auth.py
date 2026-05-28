"""Testes unitários para vectora/api/middleware/auth.py (Bloco C — C4).

Cobre:
- _is_public_route: rotas públicas corretas e rotas privadas
- _auth_enabled: lê variável de ambiente em tempo de request
- AuthMiddleware: passa em rotas públicas, bloqueia privadas sem token,
  injeta request.state.user em rotas protegidas com token válido
"""

from __future__ import annotations

import os

import pytest

# ---------------------------------------------------------------------------
# _is_public_route
# ---------------------------------------------------------------------------


class TestIsPublicRoute:
    def test_auth_prefix_is_public(self):
        from vectora.api.middleware.auth import _is_public_route

        assert _is_public_route("/auth/signin") is True
        assert _is_public_route("/auth/signup") is True
        assert _is_public_route("/auth/has-users") is True
        assert _is_public_route("/auth/refresh") is True

    def test_health_is_public(self):
        from vectora.api.middleware.auth import _is_public_route

        assert _is_public_route("/health") is True

    def test_docs_is_public(self):
        from vectora.api.middleware.auth import _is_public_route

        assert _is_public_route("/docs") is True
        assert _is_public_route("/openapi.json") is True

    def test_static_files_are_public(self):
        from vectora.api.middleware.auth import _is_public_route

        assert _is_public_route("/static/app.js") is True
        assert _is_public_route("/favicon.ico") is True
        assert _is_public_route("/assets/logo.png") is True

    def test_chat_endpoints_are_private(self):
        from vectora.api.middleware.auth import _is_public_route

        assert _is_public_route("/vectora.chat.v1.ChatService/StreamChat") is False
        assert _is_public_route("/vectora.chat.v1.ThreadService/ListThreads") is False

    def test_metrics_is_private(self):
        from vectora.api.middleware.auth import _is_public_route

        assert _is_public_route("/metrics") is False

    def test_root_path_is_private(self):
        from vectora.api.middleware.auth import _is_public_route

        assert _is_public_route("/") is False


# ---------------------------------------------------------------------------
# _auth_enabled
# ---------------------------------------------------------------------------


class TestAuthEnabled:
    def test_true_by_default(self, monkeypatch):
        from vectora.api.middleware import auth as m

        monkeypatch.delenv("VECTORA_AUTH_REQUIRED", raising=False)
        assert m._auth_enabled() is True

    def test_false_when_set_false(self, monkeypatch):
        from vectora.api.middleware import auth as m

        monkeypatch.setenv("VECTORA_AUTH_REQUIRED", "false")
        assert m._auth_enabled() is False

    def test_false_when_set_0(self, monkeypatch):
        from vectora.api.middleware import auth as m

        monkeypatch.setenv("VECTORA_AUTH_REQUIRED", "0")
        assert m._auth_enabled() is False

    def test_true_when_set_true(self, monkeypatch):
        from vectora.api.middleware import auth as m

        monkeypatch.setenv("VECTORA_AUTH_REQUIRED", "true")
        assert m._auth_enabled() is True

    def test_case_insensitive(self, monkeypatch):
        from vectora.api.middleware import auth as m

        monkeypatch.setenv("VECTORA_AUTH_REQUIRED", "FALSE")
        assert m._auth_enabled() is False


# ---------------------------------------------------------------------------
# AuthMiddleware via TestClient (integração mínima)
# ---------------------------------------------------------------------------


@pytest.fixture()
def auth_client(tmp_path, monkeypatch):
    """App com auth habilitada e banco temporário."""
    os.environ["VECTORA_AUTH_REQUIRED"] = "true"

    import aiosqlite

    import vectora.services.auth as auth_mod

    auth_mod._db_conn = None
    auth_mod._get_secret = lambda: "middleware-test-secret-abcdef"

    db_file = str(tmp_path / "mw_test.db")

    async def _patched_get_db():
        if auth_mod._db_conn is not None:
            return auth_mod._db_conn
        conn = await aiosqlite.connect(db_file)
        conn.row_factory = aiosqlite.Row
        await conn.execute("PRAGMA journal_mode=WAL")
        await auth_mod._ensure_schema(conn)
        auth_mod._db_conn = conn
        return conn

    monkeypatch.setattr(auth_mod, "_get_db", _patched_get_db)

    from fastapi.testclient import TestClient

    from vectora.api.server import create_app

    app = create_app(serve_static=False)
    client = TestClient(app, raise_server_exceptions=False)
    yield client

    # Limpeza
    import asyncio

    async def _close():
        if auth_mod._db_conn is not None:
            await auth_mod._db_conn.close()
            auth_mod._db_conn = None

    asyncio.run(_close())
    os.environ["VECTORA_AUTH_REQUIRED"] = "false"


class TestAuthMiddlewareIntegration:
    def test_public_route_passes_without_token(self, auth_client):
        r = auth_client.get("/health")
        assert r.status_code == 200

    def test_auth_route_passes_without_token(self, auth_client):
        r = auth_client.get("/auth/has-users")
        assert r.status_code == 200

    def test_private_route_without_token_returns_401(self, auth_client):
        r = auth_client.get("/auth/me")
        assert r.status_code == 401

    def test_private_route_with_invalid_bearer_returns_401(self, auth_client):
        r = auth_client.get(
            "/auth/me", headers={"Authorization": "Bearer token-invalido"}
        )
        assert r.status_code == 401

    def test_private_route_with_valid_token_passes(self, auth_client):
        # Cria usuário e obtém token
        r_signup = auth_client.post(
            "/auth/signup",
            json={"email": "mw@test.com", "password": "middlewaretest1234"},
        )
        assert r_signup.status_code == 200
        access = r_signup.json()["access_token"]

        r = auth_client.get("/auth/me", headers={"Authorization": f"Bearer {access}"})
        assert r.status_code == 200
        assert r.json()["email"] == "mw@test.com"

    def test_private_route_with_cookie_token_passes(self, auth_client):
        # Signup para ter cookies definidos
        r = auth_client.post(
            "/auth/signup",
            json={"email": "cookie@test.com", "password": "cookietest12345"},
        )
        # Se bloqueado (já há users), faz signin
        if r.status_code == 403:
            r = auth_client.post(
                "/auth/signin",
                json={"email": "mw@test.com", "password": "middlewaretest1234"},
            )
        assert r.status_code == 200
        # O TestClient mantém cookies automaticamente após set_cookie
        r_me = auth_client.get("/auth/me")
        assert r_me.status_code == 200
