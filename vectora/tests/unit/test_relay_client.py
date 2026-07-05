"""TDD — RelayClient (backend/relay/__init__.py)"""

import asyncio
import contextlib
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import pytest


@pytest.fixture
def relay_token_file(tmp_path: Path) -> Path:
    return tmp_path / "relay_token"


@pytest.fixture
def relay_url() -> str:
    return "wss://relay.vectora.chat"


class TestRelayTokenPersistence:
    def test_carrega_token_existente(self, relay_token_file: Path) -> None:
        relay_token_file.write_text("abc123")
        from backend.services.relay.token import load_token

        assert load_token(relay_token_file) == "abc123"

    def test_retorna_none_sem_arquivo(self, relay_token_file: Path) -> None:
        from backend.services.relay.token import load_token

        assert load_token(relay_token_file) is None

    def test_salva_token(self, relay_token_file: Path) -> None:
        from backend.services.relay.token import save_token

        save_token("xyz789", relay_token_file)
        assert relay_token_file.read_text() == "xyz789"

    @pytest.mark.skipif(
        __import__("sys").platform == "win32",
        reason="Windows usa ACLs NTFS; chmod POSIX não aplica",
    )
    def test_token_salvo_tem_permissao_restrita(self, relay_token_file: Path) -> None:
        import stat

        from backend.services.relay.token import save_token

        save_token("xyz789", relay_token_file)
        mode = relay_token_file.stat().st_mode
        # arquivo não deve ser legível por outros (world)
        assert not (mode & stat.S_IROTH)


class TestRelayClientBackoff:
    @pytest.mark.asyncio
    async def test_backoff_dobra_a_cada_falha(self) -> None:
        from backend.services.relay import RelayClient

        client = RelayClient(
            relay_url="wss://relay.vectora.chat",
            jwt_getter=AsyncMock(return_value="tok"),
        )
        delays: list[float] = []

        async def fake_sleep(d: float) -> None:
            delays.append(d)
            if len(delays) >= 3:
                raise asyncio.CancelledError

        with patch("backend.services.relay.asyncio.sleep", fake_sleep):
            with patch(
                "backend.services.relay.RelayClient._connect_once",
                side_effect=ConnectionError("fail"),
            ):
                with patch(
                    "backend.services.relay.RelayClient._register",
                    return_value="tok123",
                ):
                    with contextlib.suppress(asyncio.CancelledError):
                        await client._connect_loop()

        assert len(delays) >= 2
        assert delays[1] == delays[0] * 2

    @pytest.mark.asyncio
    async def test_backoff_nao_ultrapassa_60s(self) -> None:
        from backend.services.relay import RelayClient

        client = RelayClient(
            relay_url="wss://relay.vectora.chat",
            jwt_getter=AsyncMock(return_value="tok"),
        )
        delays: list[float] = []

        async def fake_sleep(d: float) -> None:
            delays.append(d)
            if len(delays) >= 10:
                raise asyncio.CancelledError

        with patch("backend.services.relay.asyncio.sleep", fake_sleep):
            with patch(
                "backend.services.relay.RelayClient._connect_once",
                side_effect=ConnectionError("fail"),
            ):
                with patch(
                    "backend.services.relay.RelayClient._register",
                    return_value="tok123",
                ):
                    with contextlib.suppress(asyncio.CancelledError):
                        await client._connect_loop()

        assert all(d <= 60.0 for d in delays)
        assert max(delays) == 60.0


class TestRelayClientRegister:
    @pytest.mark.asyncio
    async def test_register_usa_jwt_e_fingerprint(self, relay_token_file: Path) -> None:
        from backend.services.relay import RelayClient

        mock_response = AsyncMock()
        mock_response.status = 200
        mock_response.json = AsyncMock(
            return_value={
                "token": "abc123",
                "subdomain": "abc123.vectora.chat",
                "websocket_url": "wss://relay.vectora.chat/ws/abc123",
            }
        )

        jwt_getter = AsyncMock(return_value="valid-jwt-token")
        client = RelayClient(
            relay_url="wss://relay.vectora.chat",
            jwt_getter=jwt_getter,
            token_path=relay_token_file,
        )

        with patch("backend.services.relay.aiohttp.ClientSession") as mock_session_cls:
            mock_session = AsyncMock()
            mock_session.__aenter__ = AsyncMock(return_value=mock_session)
            mock_session.__aexit__ = AsyncMock(return_value=None)
            mock_session.post = MagicMock(
                return_value=AsyncMock(
                    __aenter__=AsyncMock(return_value=mock_response),
                    __aexit__=AsyncMock(return_value=None),
                )
            )
            mock_session_cls.return_value = mock_session

            token = await client._register()

        assert token == "abc123"
        assert relay_token_file.read_text() == "abc123"

    @pytest.mark.asyncio
    async def test_register_reutiliza_token_existente(
        self, relay_token_file: Path
    ) -> None:
        from backend.services.relay import RelayClient

        relay_token_file.write_text("existing")
        client = RelayClient(
            relay_url="wss://relay.vectora.chat",
            jwt_getter=AsyncMock(return_value="tok"),
            token_path=relay_token_file,
        )

        with patch("backend.services.relay.aiohttp.ClientSession") as mock_session_cls:
            token = await client._register()

        assert token == "existing"
        mock_session_cls.assert_not_called()


class TestRelayClientStop:
    @pytest.mark.asyncio
    async def test_stop_cancela_task(self) -> None:
        from backend.services.relay import RelayClient

        client = RelayClient(
            relay_url="wss://relay.vectora.chat",
            jwt_getter=AsyncMock(return_value="tok"),
        )
        mock_task = MagicMock()
        mock_task.cancel = MagicMock()
        mock_task.done = MagicMock(return_value=False)
        client._task = mock_task

        await client.stop()

        mock_task.cancel.assert_called_once()

    @pytest.mark.asyncio
    async def test_stop_idempotente_sem_task(self) -> None:
        from backend.services.relay import RelayClient

        client = RelayClient(
            relay_url="wss://relay.vectora.chat",
            jwt_getter=AsyncMock(return_value="tok"),
        )
        await client.stop()  # não deve lançar erro


class TestRelayClientDispatch:
    def _client(self):
        from backend.services.relay import RelayClient

        return RelayClient(
            relay_url="wss://relay.vectora.chat",
            jwt_getter=AsyncMock(return_value="tok"),
        )

    @pytest.mark.asyncio
    async def test_ping_envia_pong(self) -> None:
        client = self._client()
        ws = AsyncMock()
        await client._dispatch(ws, {"type": "ping"})
        ws.send_json.assert_awaited_once_with({"type": "pong"})

    @pytest.mark.asyncio
    async def test_queued_encaminha_todos_itens(self) -> None:
        client = self._client()
        ws = AsyncMock()
        items = [
            {"id": "1", "method": "POST", "path": "/w/a", "headers": {}, "body": ""},
            {"id": "2", "method": "POST", "path": "/w/b", "headers": {}, "body": ""},
        ]
        with patch.object(client, "_forward", new=AsyncMock()) as mock_fwd:
            await client._dispatch(ws, {"type": "queued", "items": items})
        assert mock_fwd.await_count == 2

    @pytest.mark.asyncio
    async def test_request_chama_forward(self) -> None:
        client = self._client()
        ws = AsyncMock()
        req = {
            "type": "request",
            "id": "abc",
            "method": "POST",
            "path": "/w/gh",
            "headers": {},
            "body": "",
        }
        with patch.object(client, "_forward", new=AsyncMock()) as mock_fwd:
            await client._dispatch(ws, req)
        mock_fwd.assert_awaited_once_with(ws, req)

    @pytest.mark.asyncio
    async def test_tipo_desconhecido_ignorado(self) -> None:
        client = self._client()
        ws = AsyncMock()
        await client._dispatch(ws, {"type": "unknown_msg"})  # sem exceção


class TestRelayClientForward:
    def _client(self):
        from backend.services.relay import RelayClient

        return RelayClient(
            relay_url="wss://relay.vectora.chat",
            jwt_getter=AsyncMock(return_value="tok"),
            local_url="http://localhost:8000",
        )

    @pytest.mark.asyncio
    async def test_forward_sucesso_envia_response(self) -> None:
        import base64

        client = self._client()
        ws = AsyncMock()

        resp_body = b'{"ok": true}'
        mock_resp = AsyncMock()
        mock_resp.status = 200
        mock_resp.headers = {"Content-Type": "application/json"}
        mock_resp.read = AsyncMock(return_value=resp_body)
        mock_resp.__aenter__ = AsyncMock(return_value=mock_resp)
        mock_resp.__aexit__ = AsyncMock(return_value=None)

        mock_session = AsyncMock()
        mock_session.request = MagicMock(return_value=mock_resp)
        mock_session.__aenter__ = AsyncMock(return_value=mock_session)
        mock_session.__aexit__ = AsyncMock(return_value=None)

        req = {
            "id": "req-1",
            "method": "POST",
            "path": "/webhook/github",
            "headers": {"Content-Type": "application/json"},
            "body": base64.b64encode(b'{"ref":"main"}').decode(),
        }
        with patch(
            "backend.services.relay.aiohttp.ClientSession", return_value=mock_session
        ):
            await client._forward(ws, req)

        call_kwargs = ws.send_json.call_args[0][0]
        assert call_kwargs["type"] == "response"
        assert call_kwargs["id"] == "req-1"
        assert call_kwargs["status"] == 200
        assert base64.b64decode(call_kwargs["body"]) == resp_body

    @pytest.mark.asyncio
    async def test_forward_erro_de_rede_envia_502(self) -> None:
        client = self._client()
        ws = AsyncMock()

        with patch(
            "backend.services.relay.aiohttp.ClientSession",
            side_effect=ConnectionError("down"),
        ):
            await client._forward(
                ws,
                {
                    "id": "req-2",
                    "method": "GET",
                    "path": "/health",
                    "headers": {},
                    "body": "",
                },
            )

        call_kwargs = ws.send_json.call_args[0][0]
        assert call_kwargs["status"] == 502
        assert call_kwargs["id"] == "req-2"


class TestMachineFingerprint:
    def test_retorna_string_hex_de_32_chars(self) -> None:
        from backend.services.relay import _machine_fingerprint

        fp = _machine_fingerprint()
        assert isinstance(fp, str)
        assert len(fp) == 32
        assert fp.isalnum()

    def test_usa_machine_id_linux(self, tmp_path: Path) -> None:
        import sys

        if sys.platform == "win32":
            pytest.skip("Linux-only path test")
        from backend.services.relay import _machine_fingerprint

        machine_id_file = tmp_path / "machine-id"
        machine_id_file.write_text("abc123def456\n")

        with patch("backend.services.relay.Path") as mock_path_cls:
            mock_path_cls.side_effect = lambda *args: (
                machine_id_file if args[0] == "/etc/machine-id" else Path(*args)
            )
            fp = _machine_fingerprint()

        assert isinstance(fp, str)
        assert len(fp) == 32

    def test_usa_hostname_como_fallback(self) -> None:
        import sys

        from backend.services.relay import _machine_fingerprint

        if sys.platform == "win32":
            with patch("winreg.OpenKey", side_effect=OSError("no registry")):
                fp = _machine_fingerprint()
        else:
            with patch("backend.services.relay.Path") as mock_path_cls:
                mock_p = MagicMock()
                mock_p.is_file.return_value = False
                mock_path_cls.return_value = mock_p
                fp = _machine_fingerprint()

        assert isinstance(fp, str)
        assert len(fp) == 32
