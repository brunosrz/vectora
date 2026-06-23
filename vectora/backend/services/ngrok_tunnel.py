"""Túnel ngrok para desenvolvimento local.

Abre um túnel público na porta do Vectora (8080 por padrão) para que provedores
externos (GitHub, Slack, Linear) consigam entregar webhooks no localhost.

A URL pública fica disponível via ``get_public_url()`` e é exposta pelo endpoint
``GET /webhook/ngrok-url`` para o frontend exibir na página de integrações.
"""

from __future__ import annotations

import logging
import os

logger = logging.getLogger(__name__)

_public_url: str | None = None
_tunnel: object | None = None


def get_public_url() -> str | None:
    """Retorna a URL pública do túnel ativo, ou None se não estiver rodando."""
    return _public_url


def start_tunnel(port: int = 8080) -> str | None:
    """Inicia o túnel ngrok na porta indicada.

    Usa NGROK_AUTHTOKEN das settings (ou variável de ambiente direta).
    Retorna a URL pública ou None se ngrok não estiver disponível/configurado.
    Idempotente — se o túnel já estiver ativo, retorna a URL existente.
    """
    global _public_url, _tunnel

    if _public_url is not None:
        return _public_url

    from backend.settings import get_settings

    cfg = get_settings()

    if not cfg.ngrok_enabled:
        logger.info("ngrok_tunnel: desativado por configuração (NGROK_ENABLED=false)")
        return None

    try:
        from pyngrok import conf, ngrok  # type: ignore[import-untyped]

        authtoken = cfg.ngrok_authtoken or os.environ.get("NGROK_AUTHTOKEN", "")
        if authtoken:
            conf.get_default().auth_token = authtoken
        else:
            logger.info(
                "ngrok_tunnel: sem NGROK_AUTHTOKEN — túnel iniciado sem autenticação "
                "(URL temporária, 1 sessão simultânea, limite de 40 req/min)"
            )

        _tunnel = ngrok.connect(str(port), "http")
        _public_url = getattr(_tunnel, "public_url", None)

        if _public_url and _public_url.startswith("http://"):
            _public_url = "https://" + _public_url[len("http://") :]

        logger.info(
            "ngrok_tunnel: túnel aberto — URL pública: %s  →  localhost:%d",
            _public_url,
            port,
        )
        logger.info(
            "ngrok_tunnel: configure a Webhook URL no GitHub/Slack/Linear como: %s/webhook/<provider>",
            _public_url,
        )
        return _public_url

    except ImportError:
        logger.warning("ngrok_tunnel: pyngrok não instalado — execute 'uv sync'")
        return None
    except Exception as exc:
        logger.warning("ngrok_tunnel: falha ao iniciar túnel — %s", exc)
        return None


def stop_tunnel() -> None:
    """Para o túnel ngrok e limpa o estado. Idempotente."""
    global _public_url, _tunnel

    if _tunnel is None:
        return

    try:
        from pyngrok import ngrok  # type: ignore[import-untyped]

        ngrok.disconnect(getattr(_tunnel, "public_url", ""))
        ngrok.kill()
        logger.info("ngrok_tunnel: túnel encerrado")
    except Exception as exc:
        logger.debug("ngrok_tunnel: erro ao encerrar túnel — %s", exc)
    finally:
        _public_url = None
        _tunnel = None
