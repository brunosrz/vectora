"""GatewayClient (backend/services/gateway/__init__.py)"""

import asyncio
import contextlib
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import aiohttp
import pytest

from backend.services.gateway import GatewayMessage, GatewayRequestItem


@pytest.fixture
def gateway_token_file(tmp_path: Path) -> Path:
    return tmp_path / "gateway_token"


@pytest.fixture
def gateway_url() -> str:
    return "wss://gateway.vectora.chat"


class TestGatewayTokenPersistence:
    def test_carrega_token_existente(self, gateway_token_file: Path) -> None:
        gateway_token_file.write_text("abc123")
        from backend.services.gateway.token import load_token

        assert load_token(gateway_token_file) == "abc123"

    def test_retorna_none_sem_arquivo(self, gateway_token_file: Path) -> None:
        from backend.services.gateway.token import load_token

        assert load_token(gateway_token_file) is None

    def test_salva_token(self, gateway_token_file: Path) -> None:
        from backend.services.gateway.token import save_token

        save_token("xyz789", gateway_token_file)
        assert gateway_token_file.read_text() == "xyz789"

    @pytest.mark.skipif(
        __import__("sys").platform == "win32",
        reason="Windows usa ACLs NTFS; chmod POSIX não aplica",
    )
    def test_token_salvo_tem_permissao_restrita(self, gateway_token_file: Path) -> None:
        import stat

        from backend.services.gateway.token import save_token

        save_token("xyz789", gateway_token_file)
        mode = gateway_token_file.stat().st_mode
        # arquivo não deve ser legível por outros (world)
        assert not (mode & stat.S_IROTH)


class TestGatewayClientBackoff:
    @pytest.mark.asyncio
    async def test_backoff_dobra_a_cada_falha(self) -> None:
        """Jitter neutralizado (`random.uniform` fixo em 1.0) pra testar só
        a duplicação do backoff-base, sem a variação aleatória do sleep
        real — essa variação tem teste próprio abaixo."""
        from backend.services.gateway import GatewayClient

        client = GatewayClient(
            gateway_url="wss://gateway.vectora.chat",
            app_secret="test-app-secret",
        )
        delays: list[float] = []

        async def fake_sleep(d: float) -> None:
            delays.append(d)
            if len(delays) >= 3:
                raise asyncio.CancelledError

        with patch("backend.services.gateway.asyncio.sleep", fake_sleep):
            with patch("backend.services.gateway.random.uniform", return_value=1.0):
                with patch(
                    "backend.services.gateway.GatewayClient._connect_once",
                    side_effect=ConnectionError("fail"),
                ):
                    with patch(
                        "backend.services.gateway.GatewayClient._register",
                        return_value="tok123",
                    ):
                        with contextlib.suppress(asyncio.CancelledError):
                            await client._connect_loop()

        assert len(delays) >= 2
        assert delays[1] == delays[0] * 2

    @pytest.mark.asyncio
    async def test_backoff_nao_ultrapassa_60s(self) -> None:
        from backend.services.gateway import GatewayClient

        client = GatewayClient(
            gateway_url="wss://gateway.vectora.chat",
            app_secret="test-app-secret",
        )
        delays: list[float] = []

        async def fake_sleep(d: float) -> None:
            delays.append(d)
            if len(delays) >= 10:
                raise asyncio.CancelledError

        with patch("backend.services.gateway.asyncio.sleep", fake_sleep):
            with patch("backend.services.gateway.random.uniform", return_value=1.0):
                with patch(
                    "backend.services.gateway.GatewayClient._connect_once",
                    side_effect=ConnectionError("fail"),
                ):
                    with patch(
                        "backend.services.gateway.GatewayClient._register",
                        return_value="tok123",
                    ):
                        with contextlib.suppress(asyncio.CancelledError):
                            await client._connect_loop()

        assert all(d <= 60.0 for d in delays)
        assert max(delays) == 60.0

    @pytest.mark.asyncio
    async def test_jitter_faz_delays_variarem_mesmo_com_backoff_estavel(self) -> None:
        """Sem neutralizar `random.uniform` (jitter real): depois que o
        backoff-base satura em 60s (bem antes da 15ª tentativa: 1,2,4,...,
        60), os últimos delays vêm todos do MESMO backoff-base — só variam
        se o jitter estiver de fato sendo aplicado no sleep. Prova a defesa
        contra thundering herd (várias instalações reconectando ao mesmo
        tempo depois de o Worker do gateway reiniciar)."""
        from backend.services.gateway import GatewayClient

        client = GatewayClient(
            gateway_url="wss://gateway.vectora.chat",
            app_secret="test-app-secret",
        )
        delays: list[float] = []

        async def fake_sleep(d: float) -> None:
            delays.append(d)
            if len(delays) >= 15:
                raise asyncio.CancelledError

        with patch("backend.services.gateway.asyncio.sleep", fake_sleep):
            with patch(
                "backend.services.gateway.GatewayClient._connect_once",
                side_effect=ConnectionError("fail"),
            ):
                with patch(
                    "backend.services.gateway.GatewayClient._register",
                    return_value="tok123",
                ):
                    with contextlib.suppress(asyncio.CancelledError):
                        await client._connect_loop()

        stabilized = delays[-5:]
        assert len(set(stabilized)) > 1, "delays no teto deveriam variar (jitter real)"
        assert all(30.0 <= d <= 90.0 for d in stabilized)


class TestGatewayClientRegister:
    @pytest.mark.asyncio
    async def test_register_usa_app_secret_e_fingerprint(
        self, gateway_token_file: Path
    ) -> None:
        """O handshake de registro autentica com o secret fixo do produto
        (embutido no build), não mais um JWT por-instalação — o corpo carrega
        só o fingerprint da máquina."""
        from backend.services.gateway import GatewayClient

        mock_response = AsyncMock()
        mock_response.status = 200
        mock_response.json = AsyncMock(return_value={"token": "abc123"})

        client = GatewayClient(
            gateway_url="wss://gateway.vectora.chat",
            app_secret="fixed-product-secret",
            token_path=gateway_token_file,
            fingerprint="fp-machine-a",
        )

        with patch(
            "backend.services.gateway.aiohttp.ClientSession"
        ) as mock_session_cls:
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
        assert gateway_token_file.read_text() == "abc123"
        _, call_kwargs = mock_session.post.call_args
        assert call_kwargs["headers"]["Authorization"] == "Bearer fixed-product-secret"
        assert call_kwargs["json"] == {"fingerprint": "fp-machine-a"}

    @pytest.mark.asyncio
    async def test_duas_instalacoes_mesmo_secret_fingerprints_diferentes(
        self, tmp_path: Path
    ) -> None:
        """Erro/borda: o esquema antigo (JWT assinado por instalação) nunca
        batia contra um secret único no Worker — este teste prova que o novo
        esquema autentica corretamente duas instalações distintas usando o
        MESMO VECTORA_APP_SECRET, cada uma com seu próprio fingerprint."""
        from backend.services.gateway import GatewayClient

        for fp, expected_token in (("fp-a", "tok-a"), ("fp-b", "tok-b")):
            mock_response = AsyncMock()
            mock_response.status = 200
            mock_response.json = AsyncMock(return_value={"token": expected_token})

            client = GatewayClient(
                gateway_url="wss://gateway.vectora.chat",
                app_secret="shared-product-secret",
                token_path=tmp_path / f"gateway_token_{fp}",
                fingerprint=fp,
            )

            with patch(
                "backend.services.gateway.aiohttp.ClientSession"
            ) as mock_session_cls:
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

            assert token == expected_token
            _, call_kwargs = mock_session.post.call_args
            assert (
                call_kwargs["headers"]["Authorization"]
                == "Bearer shared-product-secret"
            )

    @pytest.mark.asyncio
    async def test_register_reutiliza_token_existente(
        self, gateway_token_file: Path
    ) -> None:
        from backend.services.gateway import GatewayClient

        gateway_token_file.write_text("existing")
        client = GatewayClient(
            gateway_url="wss://gateway.vectora.chat",
            app_secret="test-app-secret",
            token_path=gateway_token_file,
        )

        with patch(
            "backend.services.gateway.aiohttp.ClientSession"
        ) as mock_session_cls:
            token = await client._register()

        assert token == "existing"
        mock_session_cls.assert_not_called()


class TestGatewayClientStop:
    @pytest.mark.asyncio
    async def test_stop_cancela_task(self) -> None:
        from backend.services.gateway import GatewayClient

        client = GatewayClient(
            gateway_url="wss://gateway.vectora.chat",
            app_secret="test-app-secret",
        )
        mock_task = MagicMock()
        mock_task.cancel = MagicMock()
        mock_task.done = MagicMock(return_value=False)
        client._task = mock_task

        await client.stop()

        mock_task.cancel.assert_called_once()

    @pytest.mark.asyncio
    async def test_stop_idempotente_sem_task(self) -> None:
        from backend.services.gateway import GatewayClient

        client = GatewayClient(
            gateway_url="wss://gateway.vectora.chat",
            app_secret="test-app-secret",
        )
        await client.stop()  # não deve lançar erro


class _AsyncCtx:
    """Async context manager mínimo — envolve um valor síncrono, mesmo
    padrão de `aiohttp.ClientSession()`/`session.ws_connect()`."""

    def __init__(self, value):
        self._value = value

    async def __aenter__(self):
        return self._value

    async def __aexit__(self, *exc_info) -> None:
        return None


class TestGatewayClientConnectOnce:
    def _client(self):
        from backend.services.gateway import GatewayClient

        return GatewayClient(
            gateway_url="wss://gateway.vectora.chat",
            app_secret="test-app-secret",
        )

    @pytest.mark.asyncio
    async def test_fechamento_limpo_do_servidor_loga_warning_antes_de_reconectar(
        self, caplog
    ) -> None:
        """`_handle_messages` retornando sem lançar significa que o servidor
        fechou o socket sem frame de erro — sem log nenhum, isso reconecta
        em silêncio (várias linhas "conectado" seguidas, sem nenhum
        "desconectado" no meio), dificultando diagnosticar se o padrão
        coincide com outros sintomas."""
        client = self._client()
        ws = AsyncMock()
        session = MagicMock()
        session.ws_connect = MagicMock(return_value=_AsyncCtx(ws))

        with patch(
            "backend.services.gateway.aiohttp.ClientSession",
            return_value=_AsyncCtx(session),
        ):
            with patch.object(client, "_handle_messages", new=AsyncMock()):
                with caplog.at_level("WARNING", logger="backend.services.gateway"):
                    await client._connect_once("tok123")

        assert any(
            "fechada pelo servidor sem erro" in rec.message for rec in caplog.records
        )

    @pytest.mark.asyncio
    async def test_conexao_com_erro_nao_loga_o_warning_de_fechamento_limpo(
        self, caplog
    ) -> None:
        """Erro/borda: quando `_handle_messages` lança (ws error de verdade,
        já reportado por `_connect_loop` como "desconectado"), o novo
        warning de fechamento limpo não deve duplicar o log."""
        client = self._client()
        ws = AsyncMock()
        session = MagicMock()
        session.ws_connect = MagicMock(return_value=_AsyncCtx(ws))

        with patch(
            "backend.services.gateway.aiohttp.ClientSession",
            return_value=_AsyncCtx(session),
        ):
            with patch.object(
                client,
                "_handle_messages",
                new=AsyncMock(side_effect=ConnectionError("ws error: boom")),
            ):
                with caplog.at_level("WARNING", logger="backend.services.gateway"):
                    with pytest.raises(ConnectionError):
                        await client._connect_once("tok123")

        assert not any(
            "fechada pelo servidor sem erro" in rec.message for rec in caplog.records
        )

    @pytest.mark.asyncio
    async def test_local_session_tem_timeout_explicito_nao_o_default_de_5min(
        self,
    ) -> None:
        """Sem `timeout=` explícito, `local_session` usaria o
        `ClientTimeout(total=300)` default do aiohttp — como `_connect_once`
        aguarda `pending` no `finally` antes de reconectar, um handler local
        travado atrasaria a reconexão em até 5 minutos."""
        from backend.services.gateway import _LOCAL_FORWARD_TIMEOUT_S

        client = self._client()
        ws = AsyncMock()
        session = MagicMock()
        session.ws_connect = MagicMock(return_value=_AsyncCtx(ws))

        calls: list[tuple[tuple, dict]] = []

        def session_factory(*args, **kwargs):
            calls.append((args, kwargs))
            value = session if len(calls) == 1 else MagicMock()
            return _AsyncCtx(value)

        with patch(
            "backend.services.gateway.aiohttp.ClientSession",
            side_effect=session_factory,
        ):
            with patch.object(client, "_handle_messages", new=AsyncMock()):
                await client._connect_once("tok123")

        assert len(calls) == 2
        _, local_session_kwargs = calls[1]
        timeout = local_session_kwargs.get("timeout")
        assert timeout is not None
        assert timeout.total == _LOCAL_FORWARD_TIMEOUT_S
        assert timeout.total < 300

    @pytest.mark.asyncio
    async def test_reusa_a_mesma_local_session_entre_varios_forwards(self) -> None:
        """`local_session` é aberta UMA vez em `_connect_once` e reusada por
        todos os `_forward` da conexão — antes, cada `_forward` abria a
        própria `aiohttp.ClientSession()` (2 requests processadas = 3
        sessões: 1 do WS + 2 do forward; agora são só 2: 1 do WS + 1
        reusada)."""
        client = self._client()

        class _FakeMsg:
            def __init__(self, tp, data=None) -> None:
                self.type = tp
                self._data = data

            def json(self):
                return self._data

        class _FakeWS:
            def __init__(self, messages) -> None:
                self._messages = list(messages)

            def __aiter__(self):
                return self

            async def __anext__(self):
                if not self._messages:
                    raise StopAsyncIteration
                return self._messages.pop(0)

            async def send_json(self, _data) -> None:
                return None

        ws = _FakeWS(
            [
                _FakeMsg(
                    aiohttp.WSMsgType.TEXT,
                    {
                        "type": "request",
                        "id": "r1",
                        "method": "GET",
                        "path": "/a",
                        "headers": {},
                        "body": "",
                    },
                ),
                _FakeMsg(
                    aiohttp.WSMsgType.TEXT,
                    {
                        "type": "request",
                        "id": "r2",
                        "method": "GET",
                        "path": "/b",
                        "headers": {},
                        "body": "",
                    },
                ),
            ]
        )

        ws_owner_session = MagicMock()
        ws_owner_session.ws_connect = MagicMock(return_value=_AsyncCtx(ws))
        local_session_marker = MagicMock()

        created: list[object] = []

        def session_factory(*_args, **_kwargs):
            value = ws_owner_session if len(created) == 0 else local_session_marker
            created.append(value)
            return _AsyncCtx(value)

        sessions_seen: list[object] = []

        async def fake_forward(_ws, session_arg, req) -> None:
            sessions_seen.append(session_arg)

        with patch(
            "backend.services.gateway.aiohttp.ClientSession",
            side_effect=session_factory,
        ):
            with patch.object(client, "_forward", side_effect=fake_forward):
                await client._connect_once("tok123")

        assert len(created) == 2, "1 sessão pro WS + 1 reusada — não 1 por forward"
        assert sessions_seen == [local_session_marker, local_session_marker]


class TestGatewayClientDispatch:
    def _client(self):
        from backend.services.gateway import GatewayClient

        return GatewayClient(
            gateway_url="wss://gateway.vectora.chat",
            app_secret="test-app-secret",
        )

    @pytest.mark.asyncio
    async def test_ping_envia_pong(self) -> None:
        client = self._client()
        ws = AsyncMock()
        session = AsyncMock()
        pending: set[asyncio.Task[None]] = set()
        await client._dispatch(ws, session, {"type": "ping"}, pending)
        ws.send_json.assert_awaited_once_with({"type": "pong"})

    @pytest.mark.asyncio
    async def test_queued_encaminha_todos_itens(self) -> None:
        """`_dispatch` só AGENDA os `_forward` (task própria, ver
        `_spawn_forward`) — não espera terminar. `pending` guarda as tasks;
        `asyncio.gather` espera todas antes de checar quantas rodaram."""
        client = self._client()
        ws = AsyncMock()
        session = AsyncMock()
        pending: set[asyncio.Task[None]] = set()
        items: list[GatewayRequestItem] = [
            {"id": "1", "method": "POST", "path": "/w/a", "headers": {}, "body": ""},
            {"id": "2", "method": "POST", "path": "/w/b", "headers": {}, "body": ""},
        ]
        message: GatewayMessage = {"type": "queued", "items": items}
        with patch.object(client, "_forward", new=AsyncMock()) as mock_fwd:
            await client._dispatch(ws, session, message, pending)
            assert len(pending) == 2
            await asyncio.gather(*pending)
        assert mock_fwd.await_count == 2

    @pytest.mark.asyncio
    async def test_request_chama_forward(self) -> None:
        client = self._client()
        ws = AsyncMock()
        session = AsyncMock()
        pending: set[asyncio.Task[None]] = set()
        req: GatewayMessage = {
            "type": "request",
            "id": "abc",
            "method": "POST",
            "path": "/w/gh",
            "headers": {},
            "body": "",
        }
        with patch.object(client, "_forward", new=AsyncMock()) as mock_fwd:
            await client._dispatch(ws, session, req, pending)
            await asyncio.gather(*pending)
        mock_fwd.assert_awaited_once_with(ws, session, req)

    @pytest.mark.asyncio
    async def test_tipo_desconhecido_ignorado(self) -> None:
        client = self._client()
        ws = AsyncMock()
        session = AsyncMock()
        pending: set[asyncio.Task[None]] = set()
        await client._dispatch(
            ws, session, {"type": "unknown_msg"}, pending
        )  # sem exceção
        assert pending == set()

    @pytest.mark.asyncio
    async def test_erro_borda_task_sai_de_pending_ao_terminar(self) -> None:
        """`pending` não pode crescer sem limite — cada task se
        auto-remove via `add_done_callback` quando termina."""
        client = self._client()
        ws = AsyncMock()
        session = AsyncMock()
        pending: set[asyncio.Task[None]] = set()
        req: GatewayMessage = {
            "type": "request",
            "id": "abc",
            "method": "GET",
            "path": "/x",
            "headers": {},
            "body": "",
        }
        with patch.object(client, "_forward", new=AsyncMock()):
            await client._dispatch(ws, session, req, pending)
            assert len(pending) == 1
            (task,) = tuple(pending)
            await task
        assert pending == set()


class TestGatewayClientForward:
    def _client(self):
        from backend.services.gateway import GatewayClient

        return GatewayClient(
            gateway_url="wss://gateway.vectora.chat",
            app_secret="test-app-secret",
            local_url="http://localhost:8000",
        )

    @pytest.mark.asyncio
    async def test_forward_sucesso_envia_response(self) -> None:
        """`_forward` recebe a sessão local já pronta (reuso — ver
        `_connect_once`), não abre/fecha uma `aiohttp.ClientSession()`
        própria a cada chamada."""
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

        mock_session = MagicMock()
        mock_session.request = MagicMock(return_value=mock_resp)

        req: GatewayRequestItem = {
            "id": "req-1",
            "method": "POST",
            "path": "/webhook/github",
            "headers": {"Content-Type": "application/json"},
            "body": base64.b64encode(b'{"ref":"main"}').decode(),
        }
        await client._forward(ws, mock_session, req)

        call_kwargs = ws.send_json.call_args[0][0]
        assert call_kwargs["type"] == "response"
        assert call_kwargs["id"] == "req-1"
        assert call_kwargs["status"] == 200
        assert base64.b64decode(call_kwargs["body"]) == resp_body

    @pytest.mark.asyncio
    async def test_forward_erro_de_rede_envia_502(self) -> None:
        client = self._client()
        ws = AsyncMock()
        mock_session = MagicMock()
        mock_session.request = MagicMock(side_effect=ConnectionError("down"))

        await client._forward(
            ws,
            mock_session,
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

    @pytest.mark.asyncio
    async def test_erro_de_rede_nao_loga_headers_nem_body(self, caplog) -> None:
        """Erro/borda: `headers`/`body` podem carregar segredos (token
        `Authorization`, assinatura de webhook, `code` de callback OAuth) —
        o log de erro só pode conter method/path, nunca o request inteiro."""
        client = self._client()
        ws = AsyncMock()
        mock_session = MagicMock()
        mock_session.request = MagicMock(side_effect=ConnectionError("down"))

        with caplog.at_level("ERROR", logger="backend.services.gateway"):
            await client._forward(
                ws,
                mock_session,
                {
                    "id": "req-secret",
                    "method": "POST",
                    "path": "/webhook/github",
                    "headers": {"Authorization": "Bearer super-secret-token"},
                    "body": "codigo_oauth_sigiloso",
                },
            )

        record = next(
            r for r in caplog.records if "erro ao encaminhar request" in r.message
        )
        assert getattr(record, "method", None) == "POST"
        assert getattr(record, "path", None) == "/webhook/github"
        assert not hasattr(record, "headers")
        assert not hasattr(record, "body")
        assert not hasattr(record, "req")
        rendered = record.getMessage()
        assert "super-secret-token" not in rendered
        assert "codigo_oauth_sigiloso" not in rendered

    @pytest.mark.asyncio
    async def test_erro_borda_cancelamento_repropaga_sem_enviar_response(self) -> None:
        """`asyncio.CancelledError` (conexão fechando, `_connect_once`
        cancelando `pending`) precisa se propagar — não pode ser tratado
        como erro genérico e mascarado por um 502 enviado num socket que já
        pode estar fechando."""
        client = self._client()
        ws = AsyncMock()
        mock_session = MagicMock()
        mock_session.request = MagicMock(side_effect=asyncio.CancelledError())

        with pytest.raises(asyncio.CancelledError):
            await client._forward(
                ws,
                mock_session,
                {
                    "id": "req-3",
                    "method": "GET",
                    "path": "/x",
                    "headers": {},
                    "body": "",
                },
            )
        ws.send_json.assert_not_awaited()


class TestGatewayClientConcurrency:
    def _client(self):
        from backend.services.gateway import GatewayClient

        return GatewayClient(
            gateway_url="wss://gateway.vectora.chat",
            app_secret="test-app-secret",
        )

    @pytest.mark.asyncio
    async def test_segunda_request_nao_espera_a_primeira_lenta_terminar(self) -> None:
        """Bug real corrigido: `_dispatch` fazia `await self._forward(...)`
        direto — uma revisão de PR demorada bloqueava o loop de leitura do
        WebSocket inteiro, incl. um simples ping. Agora cada `_forward` é
        uma task própria (`_spawn_forward`): a segunda request termina
        mesmo com a primeira ainda presa."""
        client = self._client()
        ws = AsyncMock()
        session = AsyncMock()
        pending: set[asyncio.Task[None]] = set()

        started: list[str] = []
        finished: list[str] = []
        release_slow = asyncio.Event()

        async def fake_forward(ws_arg, session_arg, req) -> None:
            assert session_arg is session  # mesma sessão reusada nas duas
            started.append(req["id"])
            if req["id"] == "slow":
                await release_slow.wait()
            finished.append(req["id"])

        with patch.object(client, "_forward", side_effect=fake_forward):
            await client._dispatch(
                ws,
                session,
                {
                    "type": "request",
                    "id": "slow",
                    "method": "GET",
                    "path": "/a",
                    "headers": {},
                    "body": "",
                },
                pending,
            )
            await client._dispatch(
                ws,
                session,
                {
                    "type": "request",
                    "id": "fast",
                    "method": "GET",
                    "path": "/b",
                    "headers": {},
                    "body": "",
                },
                pending,
            )

            for _ in range(100):
                if "fast" in finished:
                    break
                await asyncio.sleep(0)

            assert "fast" in finished
            assert "slow" not in finished  # ainda preso em release_slow.wait()

            release_slow.set()
            await asyncio.gather(*pending)

        assert set(finished) == {"slow", "fast"}
        assert started == ["slow", "fast"]  # ordem de chegada preservada


class TestMachineFingerprint:
    def test_retorna_string_hex_de_32_chars(self) -> None:
        from backend.services.gateway import _machine_fingerprint

        fp = _machine_fingerprint()
        assert isinstance(fp, str)
        assert len(fp) == 32
        assert fp.isalnum()

    def test_usa_machine_id_linux(self, tmp_path: Path) -> None:
        import sys

        if sys.platform == "win32":
            pytest.skip("Linux-only path test")
        from backend.services.gateway import _machine_fingerprint

        machine_id_file = tmp_path / "machine-id"
        machine_id_file.write_text("abc123def456\n")

        with patch("backend.services.gateway.Path") as mock_path_cls:
            mock_path_cls.side_effect = lambda *args: (
                machine_id_file if args[0] == "/etc/machine-id" else Path(*args)
            )
            fp = _machine_fingerprint()

        assert isinstance(fp, str)
        assert len(fp) == 32

    def test_usa_hostname_como_fallback(self) -> None:
        import sys

        from backend.services.gateway import _machine_fingerprint

        if sys.platform == "win32":
            with patch("winreg.OpenKey", side_effect=OSError("no registry")):
                fp = _machine_fingerprint()
        else:
            with patch("backend.services.gateway.Path") as mock_path_cls:
                mock_p = MagicMock()
                mock_p.is_file.return_value = False
                mock_path_cls.return_value = mock_p
                fp = _machine_fingerprint()

        assert isinstance(fp, str)
        assert len(fp) == 32
