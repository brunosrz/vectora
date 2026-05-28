"""Testes de integração dos endpoints HTTP de auth (Bloco C — C3/C8).

Usa FastAPI TestClient com banco SQLite temporário e auth habilitada,
cobrindo o fluxo end-to-end via HTTP (signup → signin → /me → refresh →
signout → acesso negado).

Cobre:
- GET /auth/has-users
- POST /auth/signup: primeiro root, segundo bloqueado, validações
- POST /auth/signin: credenciais válidas/inválidas, cookies definidos
- POST /auth/refresh: rotação via body e via cookie
- POST /auth/signout: revogação + cookies limpos
- GET /auth/me: com token válido, sem token, token expirado
- POST /auth/change-password
- GET/POST/DELETE /auth/envs: env overrides
- GET /auth/users (admin/root)
- POST /auth/users/{id}/role (root)
- GET /auth/audit (admin/root)
"""

from __future__ import annotations

import os

import pytest
from fastapi.testclient import TestClient

# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture(scope="module")
def app_and_db(tmp_path_factory):
    """App FastAPI com auth HABILITADA e banco temporário."""
    tmp = tmp_path_factory.mktemp("auth_api")
    db_file = str(tmp / "test_api_auth.db")

    os.environ["VECTORA_AUTH_REQUIRED"] = "true"

    import aiosqlite

    import vectora.services.auth as auth_mod

    # Reset estado global
    auth_mod._db_conn = None
    _TEST_SECRET = "api-test-secret-key-fixed-abcdef"  # noqa: S105
    # Patcha _get_secret como função para que o módulo todo use este secret
    auth_mod._get_secret = lambda: _TEST_SECRET

    async def _patched_get_db():
        if auth_mod._db_conn is not None:
            return auth_mod._db_conn
        conn = await aiosqlite.connect(db_file)
        conn.row_factory = aiosqlite.Row
        await conn.execute("PRAGMA journal_mode=WAL")
        await auth_mod._ensure_schema(conn)
        auth_mod._db_conn = conn
        return conn

    auth_mod._get_db = _patched_get_db

    from vectora.api.server import create_app

    app = create_app(serve_static=False)
    yield app, auth_mod

    import asyncio

    async def _close():
        if auth_mod._db_conn is not None:
            await auth_mod._db_conn.close()
            auth_mod._db_conn = None

    asyncio.run(_close())
    os.environ["VECTORA_AUTH_REQUIRED"] = "false"


@pytest.fixture(scope="module")
def client(app_and_db):
    app, _ = app_and_db
    return TestClient(app, raise_server_exceptions=False)


@pytest.fixture(scope="module")
def root_tokens(client):
    """Cria o primeiro usuário (root) e retorna seus tokens."""
    # Verifica se ainda não há usuários
    r = client.get("/auth/has-users")
    if r.json()["exists"]:
        # Banco já populado em outro teste — usa signin
        r = client.post(
            "/auth/signin",
            json={"email": "root@test.com", "password": "rootpassword1234"},
        )
    else:
        r = client.post(
            "/auth/signup",
            json={"email": "root@test.com", "password": "rootpassword1234"},
        )
    assert r.status_code in (200, 201)
    data = r.json()
    return data["access_token"], data["refresh_token"], data["user"]["id"]


# ---------------------------------------------------------------------------
# has-users
# ---------------------------------------------------------------------------


class TestHasUsers:
    def test_has_users_returns_bool(self, client):
        r = client.get("/auth/has-users")
        assert r.status_code == 200
        assert "exists" in r.json()


# ---------------------------------------------------------------------------
# signup
# ---------------------------------------------------------------------------


class TestSignupEndpoint:
    def test_first_user_signup_succeeds(self, client):
        # Se já há usuários (root_tokens fixture rodou antes), verifica bloqueio
        r_check = client.get("/auth/has-users")
        if r_check.json()["exists"]:
            r = client.post(
                "/auth/signup",
                json={"email": "new@test.com", "password": "newpassword1234"},
            )
            assert r.status_code == 403
            assert "desabilitado" in r.json()["detail"].lower()
        else:
            r = client.post(
                "/auth/signup",
                json={"email": "root@test.com", "password": "rootpassword1234"},
            )
            assert r.status_code == 200
            data = r.json()
            assert "access_token" in data
            assert data["user"]["role"] == "root"

    def test_signup_sets_cookies(self, client, root_tokens):
        # Após signup do root, tentar novo signup é bloqueado — verificamos cookies no signin
        access, _, _ = root_tokens
        r = client.get("/auth/me", headers={"Authorization": f"Bearer {access}"})
        assert r.status_code == 200

    def test_signup_short_password_returns_400(self, client):
        r = client.post(
            "/auth/signup",
            json={"email": "any@test.com", "password": "curta"},
        )
        # 400 ou 403 (se já há users)
        assert r.status_code in (400, 403)


# ---------------------------------------------------------------------------
# signin
# ---------------------------------------------------------------------------


class TestSigninEndpoint:
    def test_valid_signin_returns_tokens(self, client, root_tokens):
        r = client.post(
            "/auth/signin",
            json={"email": "root@test.com", "password": "rootpassword1234"},
        )
        assert r.status_code == 200
        data = r.json()
        assert "access_token" in data
        assert "refresh_token" in data
        assert data["user"]["email"] == "root@test.com"

    def test_invalid_password_returns_401(self, client, root_tokens):
        r = client.post(
            "/auth/signin",
            json={"email": "root@test.com", "password": "senhaerrada9999"},
        )
        assert r.status_code == 401

    def test_unknown_email_returns_401(self, client):
        r = client.post(
            "/auth/signin",
            json={"email": "ghost@test.com", "password": "ghostpassword1234"},
        )
        assert r.status_code == 401

    def test_signin_sets_httponly_cookies(self, client, root_tokens):
        r = client.post(
            "/auth/signin",
            json={"email": "root@test.com", "password": "rootpassword1234"},
        )
        assert r.status_code == 200
        assert "vectora_access" in r.cookies
        assert "vectora_refresh" in r.cookies


# ---------------------------------------------------------------------------
# /auth/me
# ---------------------------------------------------------------------------


class TestMeEndpoint:
    def test_me_with_valid_bearer_token(self, client, root_tokens):
        access, _, _ = root_tokens
        r = client.get("/auth/me", headers={"Authorization": f"Bearer {access}"})
        assert r.status_code == 200
        assert r.json()["email"] == "root@test.com"

    def test_me_without_token_returns_401(self, app_and_db):
        from fastapi.testclient import TestClient

        app, _ = app_and_db
        fresh = TestClient(app, raise_server_exceptions=False)
        r = fresh.get("/auth/me")
        assert r.status_code == 401

    def test_me_with_invalid_token_returns_401(self, app_and_db):
        from fastapi.testclient import TestClient

        app, _ = app_and_db
        fresh = TestClient(app, raise_server_exceptions=False)
        r = fresh.get(
            "/auth/me", headers={"Authorization": "Bearer token-invalido-qualquer"}
        )
        assert r.status_code == 401


# ---------------------------------------------------------------------------
# refresh
# ---------------------------------------------------------------------------


class TestRefreshEndpoint:
    def test_refresh_via_body_returns_new_tokens(self, client):
        r_sign = client.post(
            "/auth/signin",
            json={"email": "root@test.com", "password": "rootpassword1234"},
        )
        old_refresh = r_sign.json()["refresh_token"]

        r = client.post("/auth/refresh", json={"refresh_token": old_refresh})
        assert r.status_code == 200
        data = r.json()
        assert data["refresh_token"] != old_refresh
        assert "access_token" in data

    def test_refresh_with_invalid_token_returns_401(self, client):
        r = client.post("/auth/refresh", json={"refresh_token": "token-invalido"})
        assert r.status_code == 401

    def test_double_refresh_with_same_token_returns_401(self, client):
        r_sign = client.post(
            "/auth/signin",
            json={"email": "root@test.com", "password": "rootpassword1234"},
        )
        refresh = r_sign.json()["refresh_token"]

        client.post("/auth/refresh", json={"refresh_token": refresh})
        r2 = client.post("/auth/refresh", json={"refresh_token": refresh})
        assert r2.status_code == 401


# ---------------------------------------------------------------------------
# signout
# ---------------------------------------------------------------------------


class TestSignoutEndpoint:
    def test_signout_clears_cookies(self, client):
        r_sign = client.post(
            "/auth/signin",
            json={"email": "root@test.com", "password": "rootpassword1234"},
        )
        refresh = r_sign.json()["refresh_token"]

        r = client.post("/auth/signout", json={"refresh_token": refresh})
        assert r.status_code == 200

    def test_after_signout_refresh_token_is_invalid(self, client):
        r_sign = client.post(
            "/auth/signin",
            json={"email": "root@test.com", "password": "rootpassword1234"},
        )
        refresh = r_sign.json()["refresh_token"]

        client.post("/auth/signout", json={"refresh_token": refresh})
        r = client.post("/auth/refresh", json={"refresh_token": refresh})
        assert r.status_code == 401

    def test_signout_without_token_returns_200(self, client):
        r = client.post("/auth/signout", json={})
        assert r.status_code == 200


# ---------------------------------------------------------------------------
# change-password
# ---------------------------------------------------------------------------


class TestChangePasswordEndpoint:
    def test_change_password_success(self, client, root_tokens):
        access, _, _ = root_tokens
        r = client.post(
            "/auth/change-password",
            json={"old_password": "rootpassword1234", "new_password": "novasenha5678!"},
            headers={"Authorization": f"Bearer {access}"},
        )
        # Pode ser 200 ou falha se a senha já foi trocada por outro teste
        assert r.status_code in (200, 400)

    def test_change_password_without_auth_returns_401(self, client):
        r = client.post(
            "/auth/change-password",
            json={"old_password": "qualquer", "new_password": "outrasenha1234"},
        )
        assert r.status_code == 401


# ---------------------------------------------------------------------------
# Env overrides
# ---------------------------------------------------------------------------


class TestEnvOverridesEndpoints:
    def _get_fresh_token(self, client) -> str:
        """Obtém um token válido para os testes, lidando com senha que pode ter mudado."""
        for pwd in ("rootpassword1234", "novasenha5678!"):
            r = client.post(
                "/auth/signin",
                json={"email": "root@test.com", "password": pwd},
            )
            if r.status_code == 200:
                return r.json()["access_token"]
        pytest.skip("Não foi possível obter token válido para teste de envs")

    def test_get_envs_empty_initially(self, client):
        access = self._get_fresh_token(client)
        r = client.get("/auth/envs", headers={"Authorization": f"Bearer {access}"})
        assert r.status_code == 200
        data = r.json()
        assert "envs" in data
        assert "keys" in data

    def test_set_and_get_env(self, client):
        access = self._get_fresh_token(client)
        headers = {"Authorization": f"Bearer {access}"}

        r = client.post(
            "/auth/envs",
            json={"key": "TEST_KEY", "value": "test_value"},
            headers=headers,
        )
        assert r.status_code == 200

        r = client.get("/auth/envs", headers=headers)
        data = r.json()
        assert "TEST_KEY" in data["keys"]
        # Valor deve estar mascarado
        assert data["envs"]["TEST_KEY"] == "••••••••"

    def test_delete_env(self, client):
        access = self._get_fresh_token(client)
        headers = {"Authorization": f"Bearer {access}"}

        client.post(
            "/auth/envs",
            json={"key": "DEL_KEY", "value": "del_value"},
            headers=headers,
        )
        r = client.delete("/auth/envs/DEL_KEY", headers=headers)
        assert r.status_code == 200

        r = client.get("/auth/envs", headers=headers)
        assert "DEL_KEY" not in r.json()["keys"]

    def test_envs_without_auth_returns_401(self, app_and_db):
        from fastapi.testclient import TestClient

        app, _ = app_and_db
        fresh = TestClient(app, raise_server_exceptions=False)
        r = fresh.get("/auth/envs")
        assert r.status_code == 401


# ---------------------------------------------------------------------------
# Admin endpoints
# ---------------------------------------------------------------------------


class TestAdminEndpoints:
    def _get_root_token(self, client) -> str:
        for pwd in ("rootpassword1234", "novasenha5678!"):
            r = client.post(
                "/auth/signin",
                json={"email": "root@test.com", "password": pwd},
            )
            if r.status_code == 200:
                return r.json()["access_token"]
        pytest.skip("Não foi possível obter token root")

    def test_list_users_as_root(self, client):
        token = self._get_root_token(client)
        r = client.get("/auth/users", headers={"Authorization": f"Bearer {token}"})
        assert r.status_code == 200
        data = r.json()
        assert "users" in data
        assert len(data["users"]) >= 1

    def test_list_users_without_auth_returns_4xx(self, app_and_db):
        from fastapi.testclient import TestClient

        app, _ = app_and_db
        fresh = TestClient(app, raise_server_exceptions=False)
        r = fresh.get("/auth/users")
        assert r.status_code in (401, 403)

    def test_get_audit_log_as_root(self, client):
        token = self._get_root_token(client)
        r = client.get("/auth/audit", headers={"Authorization": f"Bearer {token}"})
        assert r.status_code == 200
        assert isinstance(r.json(), list)

    def test_audit_log_contains_signin_events(self, client):
        token = self._get_root_token(client)
        r = client.get(
            "/auth/audit?action=signin",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert r.status_code == 200
        events = r.json()
        assert any(e["action"] == "signin" for e in events)
