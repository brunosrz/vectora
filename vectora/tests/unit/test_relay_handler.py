"""TDD — backend/api/handlers/relay.py + services/auth.create_relay_jwt"""

from __future__ import annotations

from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi.testclient import TestClient

# ---------------------------------------------------------------------------
# create_relay_jwt
# ---------------------------------------------------------------------------


class TestCreateRelayJwt:
    def test_retorna_string_jwt(self) -> None:
        from backend.services.auth import create_relay_jwt

        token = create_relay_jwt()
        assert isinstance(token, str)
        assert token.count(".") == 2

    def test_decodifica_com_decode_access_token(self) -> None:
        from backend.services.auth import create_relay_jwt, decode_access_token

        token = create_relay_jwt()
        payload = decode_access_token(token)
        assert payload["sub"] == "relay-system"

    def test_exp_esta_no_futuro(self) -> None:
        import time

        from backend.services.auth import create_relay_jwt, decode_access_token

        token = create_relay_jwt(ttl_seconds=600)
        payload = decode_access_token(token)
        assert payload["exp"] > int(time.time())

    def test_ttl_personalizado(self) -> None:
        import time

        from backend.services.auth import create_relay_jwt, decode_access_token

        token = create_relay_jwt(ttl_seconds=120)
        payload = decode_access_token(token)
        assert payload["exp"] - int(time.time()) <= 120


# ---------------------------------------------------------------------------
# GET /relay/status — sem token salvo
# ---------------------------------------------------------------------------


class TestRelayStatusSemToken:
    def _app(self) -> TestClient:
        from fastapi import FastAPI

        from backend.api.handlers.relay import router

        app = FastAPI()

        @app.middleware("http")
        async def inject_user(request, call_next):
            request.state.user = {"id": "u1"}
            return await call_next(request)

        app.include_router(router)
        return TestClient(app)

    def test_retorna_desconectado_sem_token(self, tmp_path: Path) -> None:
        token_path = tmp_path / "relay_token"
        with patch("backend.api.handlers.relay._TOKEN_PATH", token_path):
            res = self._app().get("/relay/status")
        assert res.status_code == 200
        data = res.json()
        assert data["connected"] is False
        assert data["token"] is None
        assert data["subdomain"] is None

    def test_retorna_401_sem_autenticacao(self, tmp_path: Path) -> None:
        from fastapi import FastAPI

        from backend.api.handlers.relay import router

        app = FastAPI()
        app.include_router(router)
        client = TestClient(app, raise_server_exceptions=False)
        res = client.get("/relay/status")
        assert res.status_code == 401


# ---------------------------------------------------------------------------
# GET /relay/status — com token salvo
# ---------------------------------------------------------------------------


class TestRelayStatusComToken:
    def _app(self) -> TestClient:
        from fastapi import FastAPI

        from backend.api.handlers.relay import router

        app = FastAPI()

        @app.middleware("http")
        async def inject_user(request, call_next):
            request.state.user = {"id": "u1"}
            return await call_next(request)

        app.include_router(router)
        return TestClient(app)

    def test_retorna_status_do_worker(self, tmp_path: Path) -> None:
        token_path = tmp_path / "relay_token"
        token_path.write_text("abc123")

        mock_resp = AsyncMock()
        mock_resp.status = 200
        mock_resp.json = AsyncMock(return_value={"connected": True, "queued": 0})
        mock_ctx = AsyncMock()
        mock_ctx.__aenter__ = AsyncMock(return_value=mock_resp)
        mock_ctx.__aexit__ = AsyncMock(return_value=None)
        mock_session = AsyncMock()
        mock_session.get = MagicMock(return_value=mock_ctx)
        mock_session_ctx = AsyncMock()
        mock_session_ctx.__aenter__ = AsyncMock(return_value=mock_session)
        mock_session_ctx.__aexit__ = AsyncMock(return_value=None)

        with patch("backend.api.handlers.relay._TOKEN_PATH", token_path):
            with patch(
                "backend.api.handlers.relay.aiohttp.ClientSession",
                return_value=mock_session_ctx,
            ):
                res = self._app().get("/relay/status")

        assert res.status_code == 200
        data = res.json()
        assert data["connected"] is True
        assert data["token"] == "abc123"
        assert data["subdomain"] == "abc123.vectora.chat"
        assert data["webhook_base"] == "https://abc123.vectora.chat"

    def test_retorna_desconectado_se_worker_offline(self, tmp_path: Path) -> None:
        token_path = tmp_path / "relay_token"
        token_path.write_text("abc123")

        with patch("backend.api.handlers.relay._TOKEN_PATH", token_path):
            with patch(
                "backend.api.handlers.relay.aiohttp.ClientSession",
                side_effect=Exception("network error"),
            ):
                res = self._app().get("/relay/status")

        assert res.status_code == 200
        assert res.json()["connected"] is False


# ---------------------------------------------------------------------------
# POST /relay/revoke
# ---------------------------------------------------------------------------


class TestRelayRevoke:
    def _app(self) -> TestClient:
        from fastapi import FastAPI

        from backend.api.handlers.relay import router

        app = FastAPI()

        @app.middleware("http")
        async def inject_user(request, call_next):
            request.state.user = {"id": "u1"}
            return await call_next(request)

        app.include_router(router)
        return TestClient(app)

    def test_retorna_404_sem_token(self, tmp_path: Path) -> None:
        token_path = tmp_path / "relay_token"
        with patch("backend.api.handlers.relay._TOKEN_PATH", token_path):
            res = self._app().post("/relay/revoke")
        assert res.status_code == 404

    def test_revoga_e_deleta_arquivo(self, tmp_path: Path) -> None:
        token_path = tmp_path / "relay_token"
        token_path.write_text("abc123")

        mock_resp = AsyncMock()
        mock_resp.status = 200
        mock_ctx = AsyncMock()
        mock_ctx.__aenter__ = AsyncMock(return_value=mock_resp)
        mock_ctx.__aexit__ = AsyncMock(return_value=None)
        mock_session = AsyncMock()
        mock_session.delete = MagicMock(return_value=mock_ctx)
        mock_session_ctx = AsyncMock()
        mock_session_ctx.__aenter__ = AsyncMock(return_value=mock_session)
        mock_session_ctx.__aexit__ = AsyncMock(return_value=None)

        with patch("backend.api.handlers.relay._TOKEN_PATH", token_path):
            with patch(
                "backend.api.handlers.relay.aiohttp.ClientSession",
                return_value=mock_session_ctx,
            ):
                res = self._app().post("/relay/revoke")

        assert res.status_code == 200
        assert res.json()["revoked"] is True
        assert not token_path.exists()

    def test_revoga_mesmo_se_worker_falhar(self, tmp_path: Path) -> None:
        token_path = tmp_path / "relay_token"
        token_path.write_text("abc123")

        with patch("backend.api.handlers.relay._TOKEN_PATH", token_path):
            with patch(
                "backend.api.handlers.relay.aiohttp.ClientSession",
                side_effect=Exception("network error"),
            ):
                res = self._app().post("/relay/revoke")

        assert res.status_code == 200
        assert not token_path.exists()
