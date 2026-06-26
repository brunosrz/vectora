"""TDD — RelayClient (backend/relay/__init__.py)"""

import asyncio
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
        from backend.relay.token import load_token

        assert load_token(relay_token_file) == "abc123"

    def test_retorna_none_sem_arquivo(self, relay_token_file: Path) -> None:
        from backend.relay.token import load_token

        assert load_token(relay_token_file) is None

    def test_salva_token(self, relay_token_file: Path) -> None:
        from backend.relay.token import save_token

        save_token("xyz789", relay_token_file)
        assert relay_token_file.read_text() == "xyz789"

    @pytest.mark.skipif(
        __import__("sys").platform == "win32",
        reason="Windows usa ACLs NTFS; chmod POSIX não aplica",
    )
    def test_token_salvo_tem_permissao_restrita(self, relay_token_file: Path) -> None:
        import stat

        from backend.relay.token import save_token

        save_token("xyz789", relay_token_file)
        mode = relay_token_file.stat().st_mode
        # arquivo não deve ser legível por outros (world)
        assert not (mode & stat.S_IROTH)


class TestRelayClientBackoff:
    @pytest.mark.asyncio
    async def test_backoff_dobra_a_cada_falha(self) -> None:
        from backend.relay import RelayClient

        client = RelayClient(
            relay_url="wss://relay.vectora.chat",
            jwt_getter=AsyncMock(return_value="tok"),
        )
        delays: list[float] = []

        async def fake_sleep(d: float) -> None:
            delays.append(d)
            if len(delays) >= 3:
                raise asyncio.CancelledError

        with patch("backend.relay.asyncio.sleep", fake_sleep):
            with patch(
                "backend.relay.RelayClient._connect_once",
                side_effect=ConnectionError("fail"),
            ):
                with patch(
                    "backend.relay.RelayClient._register", return_value="tok123"
                ):
                    try:
                        await client._connect_loop()
                    except asyncio.CancelledError:
                        pass

        assert len(delays) >= 2
        assert delays[1] == delays[0] * 2

    @pytest.mark.asyncio
    async def test_backoff_nao_ultrapassa_60s(self) -> None:
        from backend.relay import RelayClient

        client = RelayClient(
            relay_url="wss://relay.vectora.chat",
            jwt_getter=AsyncMock(return_value="tok"),
        )
        delays: list[float] = []

        async def fake_sleep(d: float) -> None:
            delays.append(d)
            if len(delays) >= 10:
                raise asyncio.CancelledError

        with patch("backend.relay.asyncio.sleep", fake_sleep):
            with patch(
                "backend.relay.RelayClient._connect_once",
                side_effect=ConnectionError("fail"),
            ):
                with patch(
                    "backend.relay.RelayClient._register", return_value="tok123"
                ):
                    try:
                        await client._connect_loop()
                    except asyncio.CancelledError:
                        pass

        assert all(d <= 60.0 for d in delays)
        assert max(delays) == 60.0


class TestRelayClientRegister:
    @pytest.mark.asyncio
    async def test_register_usa_jwt_e_fingerprint(self, relay_token_file: Path) -> None:
        from backend.relay import RelayClient

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

        with patch("backend.relay.aiohttp.ClientSession") as mock_session_cls:
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
        from backend.relay import RelayClient

        relay_token_file.write_text("existing")
        client = RelayClient(
            relay_url="wss://relay.vectora.chat",
            jwt_getter=AsyncMock(return_value="tok"),
            token_path=relay_token_file,
        )

        with patch("backend.relay.aiohttp.ClientSession") as mock_session_cls:
            token = await client._register()

        assert token == "existing"
        mock_session_cls.assert_not_called()


class TestRelayClientStop:
    @pytest.mark.asyncio
    async def test_stop_cancela_task(self) -> None:
        from backend.relay import RelayClient

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
        from backend.relay import RelayClient

        client = RelayClient(
            relay_url="wss://relay.vectora.chat",
            jwt_getter=AsyncMock(return_value="tok"),
        )
        await client.stop()  # não deve lançar erro
