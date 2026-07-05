"""Relay client — mantém WebSocket persistente com relay.vectora.chat.

Cada instância do vectora recebe um subdomínio único (ex: x7k2m.vectora.chat).
Webhooks e callbacks OAuth externos chegam pelo relay e são despachados ao
FastAPI local sem abrir porta TCP pública.
"""

from __future__ import annotations

import asyncio
import logging
from collections.abc import Callable, Coroutine
from pathlib import Path
from typing import Any

import aiohttp

from backend.services.relay.token import load_token, save_token

logger = logging.getLogger(__name__)

_DEFAULT_TOKEN_PATH = Path.home() / ".vectora" / "relay_token"
_REGISTER_PATH = "/register"
_WS_PATH = "/ws/"
_BACKOFF_INITIAL = 1.0
_BACKOFF_MAX = 60.0


class RelayClient:
    """WebSocket client que mantém conexão com o relay e repassa requests ao backend local."""

    def __init__(
        self,
        relay_url: str,
        jwt_getter: Callable[[], Coroutine[Any, Any, str]],
        local_url: str = "http://localhost:8000",
        token_path: Path = _DEFAULT_TOKEN_PATH,
        fingerprint: str | None = None,
    ) -> None:
        self._relay_url = relay_url.rstrip("/")
        self._http_base = self._relay_url.replace("wss://", "https://").replace(
            "ws://", "http://"
        )
        self._jwt_getter = jwt_getter
        self._local_url = local_url.rstrip("/")
        self._token_path = token_path
        self._fingerprint = fingerprint or _machine_fingerprint()
        self._task: asyncio.Task[None] | None = None

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def start(self) -> None:
        """Inicia o loop de conexão em background (idempotente)."""
        if self._task and not self._task.done():
            return
        self._task = asyncio.create_task(self._connect_loop(), name="relay-client")

    async def stop(self) -> None:
        """Cancela o loop de conexão (idempotente)."""
        if self._task and not self._task.done():
            self._task.cancel()
        self._task = None

    # ------------------------------------------------------------------
    # Internals
    # ------------------------------------------------------------------

    async def _register(self) -> str:
        """Retorna token existente ou registra novo no relay e persiste."""
        existing = load_token(self._token_path)
        if existing:
            return existing

        jwt = await self._jwt_getter()
        async with aiohttp.ClientSession() as session:
            async with session.post(
                f"{self._http_base}{_REGISTER_PATH}",
                json={"jwt": jwt, "fingerprint": self._fingerprint},
            ) as resp:
                resp.raise_for_status()
                data: dict[str, str] = await resp.json()

        token: str = data["token"]
        save_token(token, self._token_path)
        logger.info("relay: token registrado — %s.vectora.chat", token)
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
                logger.warning("relay: desconectado (%s), retry em %.0fs", exc, backoff)
                await asyncio.sleep(backoff)
                backoff = min(backoff * 2, _BACKOFF_MAX)

    async def _connect_once(self, token: str) -> None:
        """Abre WebSocket, processa mensagens até fechar."""
        ws_url = f"{self._relay_url}{_WS_PATH}{token}"
        async with aiohttp.ClientSession() as session:
            async with session.ws_connect(ws_url) as ws:
                logger.info("relay: conectado em %s", ws_url)
                await self._handle_messages(ws)

    async def _handle_messages(self, ws: aiohttp.ClientWebSocketResponse) -> None:
        """Recebe mensagens do relay e despacha ao FastAPI local."""
        async for msg in ws:
            if msg.type == aiohttp.WSMsgType.TEXT:
                await self._dispatch(ws, msg.json())
            elif msg.type == aiohttp.WSMsgType.ERROR:
                raise ConnectionError(f"ws error: {ws.exception()}")

    async def _dispatch(
        self, ws: aiohttp.ClientWebSocketResponse, message: dict[str, Any]
    ) -> None:
        kind = message.get("type")

        if kind == "ping":
            await ws.send_json({"type": "pong"})
            return

        if kind == "queued":
            for item in message.get("items", []):
                await self._forward(ws, item)
            return

        if kind == "request":
            await self._forward(ws, message)

    async def _forward(
        self, ws: aiohttp.ClientWebSocketResponse, req: dict[str, Any]
    ) -> None:
        """Encaminha request ao FastAPI local e devolve response ao relay."""
        import base64

        req_id: str = req["id"]
        try:
            body_bytes = base64.b64decode(req.get("body", ""))
            async with aiohttp.ClientSession() as session:
                async with session.request(
                    method=req["method"],
                    url=f"{self._local_url}{req['path']}",
                    headers=req.get("headers", {}),
                    data=body_bytes,
                ) as resp:
                    resp_body = base64.b64encode(await resp.read()).decode()
                    resp_headers = dict(resp.headers)
                    await ws.send_json(
                        {
                            "type": "response",
                            "id": req_id,
                            "status": resp.status,
                            "headers": resp_headers,
                            "body": resp_body,
                        }
                    )
        except Exception:
            logger.exception(
                "relay: erro ao encaminhar request %s", req_id, extra={"req": req}
            )
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


__all__ = ["RelayClient"]
