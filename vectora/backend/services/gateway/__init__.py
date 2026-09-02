"""Gateway client — mantém WebSocket persistente com gateway.vectora.chat.

Cada instância do vectora recebe um subdomínio único (ex:
x7k2m.vectora.chat). Webhooks e callbacks OAuth externos chegam pelo gateway
e são despachados ao FastAPI local sem abrir porta TCP pública.
"""

from __future__ import annotations

import asyncio
import logging
import random
from pathlib import Path

import aiohttp

from backend.services.gateway.token import load_token, save_token

logger = logging.getLogger(__name__)

_DEFAULT_TOKEN_PATH = Path.home() / ".vectora" / "gateway_token"
_REGISTER_PATH = "/register"
_WS_PATH = "/ws/"
_BACKOFF_INITIAL = 1.0
_BACKOFF_MAX = 60.0
#: Jitter aplicado ao sleep de reconexão (não ao estado interno do backoff
#: exponencial) — evita thundering herd quando o Worker do gateway reinicia
#: e todas as instâncias tentam reconectar no mesmo instante.
_BACKOFF_JITTER = (0.5, 1.5)


class GatewayClient:
    """WebSocket client que mantém conexão com o gateway e repassa requests ao backend local."""

    def __init__(
        self,
        gateway_url: str,
        app_secret: str,
        local_url: str = "http://localhost:8000",
        token_path: Path = _DEFAULT_TOKEN_PATH,
        fingerprint: str | None = None,
    ) -> None:
        self._gateway_url = gateway_url.rstrip("/")
        self._http_base = self._gateway_url.replace("wss://", "https://").replace(
            "ws://", "http://"
        )
        self._app_secret = app_secret
        self._local_url = local_url.rstrip("/")
        self._token_path = token_path
        self._fingerprint = fingerprint or _machine_fingerprint()
        self._task: asyncio.Task[None] | None = None
        #: Serializa `ws.send_json` — `_forward` roda concorrente (uma task
        #: por request em voo), e aiohttp não garante frames intactos se
        #: `send_json`/`send_str` forem chamados de tasks diferentes ao
        #: mesmo tempo na mesma conexão.
        self._ws_send_lock = asyncio.Lock()

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def start(self) -> None:
        """Inicia o loop de conexão em background (idempotente)."""
        if self._task and not self._task.done():
            return
        self._task = asyncio.create_task(self._connect_loop(), name="gateway-client")

    async def stop(self) -> None:
        """Cancela o loop de conexão (idempotente)."""
        if self._task and not self._task.done():
            self._task.cancel()
        self._task = None

    # ------------------------------------------------------------------
    # Internals
    # ------------------------------------------------------------------

    async def _register(self) -> str:
        """Retorna token existente ou registra novo no gateway e persiste."""
        existing = load_token(self._token_path)
        if existing:
            return existing

        async with aiohttp.ClientSession() as session:
            async with session.post(
                f"{self._http_base}{_REGISTER_PATH}",
                headers={"Authorization": f"Bearer {self._app_secret}"},
                json={"fingerprint": self._fingerprint},
            ) as resp:
                resp.raise_for_status()
                data: dict[str, str] = await resp.json()

        token: str = data["token"]
        save_token(token, self._token_path)
        logger.info("gateway: token registrado — %s.vectora.chat", token)
        return token

    async def _connect_loop(self) -> None:
        """Loop infinito com backoff exponencial até cancelamento."""
        backoff = _BACKOFF_INITIAL
        token = await self._register()

        while True:
            try:
                await self._connect_once(token)
                backoff = _BACKOFF_INITIAL
            except asyncio.CancelledError:
                raise
            except Exception as exc:
                # jitter de timing (reconexão), não uso criptográfico
                sleep_for = backoff * random.uniform(  # noqa: S311  # nosec B311
                    *_BACKOFF_JITTER
                )
                logger.warning(
                    "gateway: desconectado (%s), retry em %.1fs", exc, sleep_for
                )
                await asyncio.sleep(sleep_for)
                backoff = min(backoff * 2, _BACKOFF_MAX)

    async def _connect_once(self, token: str) -> None:
        """Abre WebSocket, processa mensagens até fechar.

        Duas sessões aiohttp com propósitos distintos: `session` é dona do
        WebSocket com o gateway; `local_session` é reusada por TODOS os
        `_forward` desta conexão (fala com o FastAPI local) — antes cada
        `_forward` abria/fechava sua própria sessão, sem reuso de conexão.
        """
        ws_url = f"{self._gateway_url}{_WS_PATH}{token}"
        pending: set[asyncio.Task[None]] = set()
        async with (
            aiohttp.ClientSession() as session,
            aiohttp.ClientSession() as local_session,
        ):
            try:
                async with session.ws_connect(ws_url) as ws:
                    logger.info("gateway: conectado em %s", ws_url)
                    await self._handle_messages(ws, local_session, pending)
                    # `_handle_messages` só retorna sem lançar quando o
                    # servidor fecha o socket sem frame de erro (`async for`
                    # simplesmente esgota). Sem este log, isso reconecta em
                    # silêncio — várias linhas "conectado" seguidas, sem
                    # nenhum "desconectado" no meio, dificultando
                    # diagnosticar se o padrão coincide com outros sintomas
                    # (ex.: o processo sendo derrubado logo depois de
                    # conectar).
                    logger.warning(
                        "gateway: conexão fechada pelo servidor sem erro — reconectando"
                    )
            finally:
                # Espera (não cancela) requests em voo antes de fechar
                # `local_session`/`ws` — um webhook/callback OAuth já
                # despachado como task não pode ser silenciosamente
                # descartado só porque o WebSocket fechou por perto. O
                # backend local é o mesmo processo (loopback), então esses
                # forwards terminam rápido; não há caminho realista de
                # travar aqui pra sempre.
                if pending:
                    await asyncio.gather(*pending, return_exceptions=True)

    async def _handle_messages(
        self,
        ws: aiohttp.ClientWebSocketResponse,
        local_session: aiohttp.ClientSession,
        pending: set[asyncio.Task[None]],
    ) -> None:
        """Recebe mensagens do gateway e despacha ao FastAPI local."""
        async for msg in ws:
            if msg.type == aiohttp.WSMsgType.TEXT:
                await self._dispatch(ws, local_session, msg.json(), pending)
            elif msg.type == aiohttp.WSMsgType.ERROR:
                raise ConnectionError(f"ws error: {ws.exception()}")

    async def _dispatch(
        self,
        ws: aiohttp.ClientWebSocketResponse,
        local_session: aiohttp.ClientSession,
        message: dict,
        pending: set[asyncio.Task[None]],
    ) -> None:
        kind = message.get("type")

        if kind == "ping":
            async with self._ws_send_lock:
                await ws.send_json({"type": "pong"})
            return

        if kind == "queued":
            for item in message.get("items", []):
                self._spawn_forward(ws, local_session, item, pending)
            return

        if kind == "request":
            self._spawn_forward(ws, local_session, message, pending)

    def _spawn_forward(
        self,
        ws: aiohttp.ClientWebSocketResponse,
        local_session: aiohttp.ClientSession,
        req: dict,
        pending: set[asyncio.Task[None]],
    ) -> None:
        """Despacha `_forward` como task própria — o loop de leitura do
        WebSocket (`_handle_messages`) segue lendo a próxima mensagem sem
        esperar o round-trip HTTP local completar. Antes, `await` direto
        serializava tudo na mesma conexão: uma revisão de PR demorada
        bloqueava até um simples ping. `pending` guarda referência forte —
        sem isso a task pode ser coletada pelo GC no meio do voo (gotcha
        conhecido do `asyncio.create_task`).
        """
        task = asyncio.create_task(self._forward(ws, local_session, req))
        pending.add(task)
        task.add_done_callback(pending.discard)

    async def _forward(
        self,
        ws: aiohttp.ClientWebSocketResponse,
        local_session: aiohttp.ClientSession,
        req: dict,
    ) -> None:
        """Encaminha request ao FastAPI local e devolve response ao gateway."""
        import base64

        req_id: str = req["id"]
        try:
            body_bytes = base64.b64decode(req.get("body", ""))
            async with local_session.request(
                method=req["method"],
                url=f"{self._local_url}{req['path']}",
                headers=req.get("headers", {}),
                data=body_bytes,
            ) as resp:
                resp_body = base64.b64encode(await resp.read()).decode()
                resp_headers = dict(resp.headers)
                async with self._ws_send_lock:
                    await ws.send_json(
                        {
                            "type": "response",
                            "id": req_id,
                            "status": resp.status,
                            "headers": resp_headers,
                            "body": resp_body,
                        }
                    )
        except asyncio.CancelledError:
            raise
        except Exception:
            logger.exception(
                "gateway: erro ao encaminhar request %s", req_id, extra={"req": req}
            )
            async with self._ws_send_lock:
                await ws.send_json(
                    {
                        "type": "response",
                        "id": req_id,
                        "status": 502,
                        "headers": {},
                        "body": "",
                    }
                )


def _machine_fingerprint() -> str:
    """Fingerprint estável por máquina — SHA-256 do machine-id ou hostname."""
    import hashlib
    import socket
    import sys

    if sys.platform == "win32":
        try:
            import winreg

            with winreg.OpenKey(
                winreg.HKEY_LOCAL_MACHINE,
                r"SOFTWARE\Microsoft\Cryptography",
            ) as key:
                raw, _ = winreg.QueryValueEx(key, "MachineGuid")
                return hashlib.sha256(str(raw).encode()).hexdigest()[:32]
        except Exception:
            pass
    else:
        for p in (Path("/etc/machine-id"), Path("/var/lib/dbus/machine-id")):
            try:
                if p.is_file():
                    raw = p.read_text().strip()
                    return hashlib.sha256(raw.encode()).hexdigest()[:32]
            except OSError:
                pass

    return hashlib.sha256(socket.getfqdn().encode()).hexdigest()[:32]


__all__ = ["GatewayClient"]
