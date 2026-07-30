"""Ciclo de vida dos adapters de Connect.

Cada plataforma só sobe quando a credencial correspondente existe nos env
overrides do usuário. Melhor esforço, igual `nats_sidecar`/`electron_sidecar`:
falha ao iniciar um adapter é logada e não impede os outros nem o boot do
backend — uma credencial de Slack errada não pode derrubar o Vectora inteiro.
"""

from __future__ import annotations

import logging
import os
from typing import Any

logger = logging.getLogger(__name__)

#: Handle vivo por plataforma (Application do Telegram, Client do Discord,
#: handler do Slack, task do email). Vazio = nada rodando.
_running: dict[str, Any] = {}


def _env(name: str) -> str:
    return (os.environ.get(name) or "").strip()


def configured_platforms() -> set[str]:
    """Quais plataformas têm credencial completa agora.

    Slack só entra com os **dois** tokens: com apenas um, o Socket Mode falha
    na conexão e o usuário veria um erro sem entender o que faltou.
    """
    platforms: set[str] = set()
    if _env("TELEGRAM_BOT_TOKEN"):
        platforms.add("telegram")
    if _env("DISCORD_BOT_TOKEN"):
        platforms.add("discord")
    if _env("SLACK_BOT_TOKEN") and _env("SLACK_APP_TOKEN"):
        platforms.add("slack")
    if (
        _env("EMAIL_IMAP_HOST")
        and _env("EMAIL_IMAP_USER")
        and _env("EMAIL_IMAP_PASSWORD")
    ):
        platforms.add("email")
    return platforms


async def _start_platform(platform: str) -> Any:
    if platform == "telegram":
        from backend.services.connect import telegram

        return await telegram.start(_env("TELEGRAM_BOT_TOKEN"))
    if platform == "discord":
        from backend.services.connect import discord

        return await discord.start(_env("DISCORD_BOT_TOKEN"))
    if platform == "slack":
        from backend.services.connect import slack

        return await slack.start(_env("SLACK_BOT_TOKEN"), _env("SLACK_APP_TOKEN"))
    if platform == "email":
        from backend.services.connect import email

        config = email.EmailConfig(
            imap_host=_env("EMAIL_IMAP_HOST"),
            imap_user=_env("EMAIL_IMAP_USER"),
            imap_password=_env("EMAIL_IMAP_PASSWORD"),
            smtp_host=_env("EMAIL_SMTP_HOST") or _env("EMAIL_IMAP_HOST"),
        )
        return await email.start(config)
    msg = f"plataforma desconhecida: {platform!r}"
    raise ValueError(msg)


async def _stop_platform(platform: str, handle: Any) -> None:
    if platform == "telegram":
        from backend.services.connect import telegram

        await telegram.stop(handle)
    elif platform == "discord":
        from backend.services.connect import discord

        await discord.stop(handle)
    elif platform == "slack":
        from backend.services.connect import slack

        await slack.stop(handle)
    elif platform == "email":
        from backend.services.connect import email

        await email.stop(handle)


async def sync_adapters() -> dict[str, str]:
    """Reconcilia o que está rodando com o que está configurado.

    Chamado no boot e de novo quando o usuário salva credenciais nas Settings —
    é o mesmo caminho para ligar, desligar e reiniciar, então não há estado
    divergente entre "salvou o token" e "o bot está no ar".

    Devolve o status por plataforma (`started`/`stopped`/`running`/`failed:…`),
    consumível por um endpoint de diagnóstico.
    """
    desired = configured_platforms()
    status: dict[str, str] = {}

    for platform in sorted(set(_running) - desired):
        try:
            await _stop_platform(platform, _running.pop(platform))
            status[platform] = "stopped"
        except Exception as exc:
            logger.exception("connect.manager: falha ao parar %s", platform)
            status[platform] = f"failed: {exc}"

    for platform in sorted(desired):
        if platform in _running:
            status[platform] = "running"
            continue
        try:
            _running[platform] = await _start_platform(platform)
            status[platform] = "started"
        except Exception as exc:
            # Um adapter que não sobe (dependência ausente, token inválido)
            # nunca impede os outros nem o boot do backend.
            logger.warning("connect.manager: %s não iniciou (%s)", platform, exc)
            status[platform] = f"failed: {exc}"

    return status


async def stop_all() -> None:
    """Desliga tudo no shutdown do backend. Idempotente."""
    for platform in list(_running):
        try:
            await _stop_platform(platform, _running.pop(platform))
        except Exception:
            logger.exception("connect.manager: falha ao parar %s", platform)


def running_platforms() -> set[str]:
    return set(_running)
