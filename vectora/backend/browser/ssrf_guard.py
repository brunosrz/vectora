"""SSRF guard para `fetch_url` — bloqueia hosts que resolvem para IP
privado/loopback/link-local/metadata antes de qualquer requisição sair.

Sem isso, `fetch_url` (tanto o caminho Tavily quanto o fallback local via
Chromium) navegava pra qualquer URL — incluindo `169.254.169.254` (metadata
de nuvem) e `localhost:<porta>` (serviços internos da própria máquina,
incluindo o próprio backend Vectora). O fallback local é o caminho de maior
risco (Chromium real rodando na máquina do usuário/servidor), mas a checagem
entra nos dois caminhos como defesa em profundidade — custa pouco e fecha o
vetor por completo.

Resolve o DNS do host antes de checar o IP: bloquear só por string (recusar
"localhost" no texto) não pega DNS rebinding (domínio público apontando pro
range interno) nem IPs escritos em bases alternativas.
"""

from __future__ import annotations

import ipaddress
import logging
import socket
from urllib.parse import urlparse

logger = logging.getLogger(__name__)


def _is_blocked_ip(ip_str: str) -> bool:
    """True se o IP é privado/loopback/link-local/reservado/multicast."""
    try:
        ip = ipaddress.ip_address(ip_str)
    except ValueError:
        return True
    return (
        ip.is_private
        or ip.is_loopback
        or ip.is_link_local
        or ip.is_reserved
        or ip.is_multicast
        or ip.is_unspecified
    )


def is_url_ssrf_safe(url: str) -> bool:
    """True se `url` não resolve para nenhum IP bloqueado.

    Falha de resolução de DNS (host inexistente, timeout) também retorna
    False — mais seguro recusar do que deixar a requisição prosseguir sem
    saber pra onde vai.
    """
    try:
        host = urlparse(url).hostname
        if not host:
            return False
        infos = socket.getaddrinfo(host, None)
    except Exception:
        logger.warning("ssrf_guard: falha ao resolver host de %s", url, exc_info=True)
        return False
    return not any(_is_blocked_ip(str(info[4][0])) for info in infos)
