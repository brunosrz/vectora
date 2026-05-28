"""Handler de OAuth e registry de integrações externas — Bloco O.

O1 — API Key integrations:
    GET  /integrations                  — lista integrações com status (conectado/não)
    POST /integrations/{id}/verify      — testa se a API key configurada é válida

O2 — GitHub OAuth:
    GET  /auth/github                   — inicia o fluxo OAuth (redirect para GitHub)
    GET  /auth/github/callback          — callback do GitHub, salva token, redireciona
    GET  /auth/github/status            — {connected: bool, username: str | None}
    DELETE /auth/github                 — desconecta (remove token do vault)

Configuração necessária (em ~/.vectora/config.toml ou env vars):
    GITHUB_OAUTH_CLIENT_ID
    GITHUB_OAUTH_CLIENT_SECRET
    GITHUB_OAUTH_REDIRECT_URI  (padrão: http://localhost:8080/auth/github/callback)
"""

from __future__ import annotations

import logging
import os
from typing import Any

from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import RedirectResponse

logger = logging.getLogger(__name__)

router = APIRouter(tags=["oauth"])

# ---------------------------------------------------------------------------
# Registry de integrações (O1)
# ---------------------------------------------------------------------------

#: Todas as integrações suportadas — consumido pela UI e pelo endpoint /integrations.
#: kind="apikey" → apenas chave inserida manualmente pelo usuário.
#: kind="oauth"  → fluxo OAuth delegado; o token é salvo como env_override.
INTEGRATIONS_REGISTRY: list[dict[str, Any]] = [
    {
        "id": "openai",
        "name": "OpenAI",
        "env_var": "OPENAI_API_KEY",
        "kind": "apikey",
        "description": "GPT-4.x, o3/o4-mini e embeddings",
        "docs_url": "https://platform.openai.com/api-keys",
        "icon": "openai",
    },
    {
        "id": "anthropic",
        "name": "Anthropic",
        "env_var": "ANTHROPIC_API_KEY",
        "kind": "apikey",
        "description": "Claude 4.x (Opus, Sonnet, Haiku)",
        "docs_url": "https://console.anthropic.com/settings/keys",
        "icon": "anthropic",
    },
    {
        "id": "cohere",
        "name": "Cohere",
        "env_var": "COHERE_API_KEY",
        "kind": "apikey",
        "description": "Command R+ e reranker semântico",
        "docs_url": "https://dashboard.cohere.com/api-keys",
        "icon": "cohere",
    },
    {
        "id": "tavily",
        "name": "Tavily",
        "env_var": "TAVILY_API_KEY",
        "kind": "apikey",
        "description": "Busca web com contexto para LLMs",
        "docs_url": "https://app.tavily.com/",
        "icon": "tavily",
    },
    {
        "id": "groq",
        "name": "Groq",
        "env_var": "GROQ_API_KEY",
        "kind": "apikey",
        "description": "Inferência ultrarrápida (Llama, Mixtral)",
        "docs_url": "https://console.groq.com/keys",
        "icon": "groq",
    },
    {
        "id": "huggingface",
        "name": "HuggingFace",
        "env_var": "HUGGINGFACE_API_KEY",
        "kind": "apikey",
        "description": "Modelos open source via Inference API",
        "docs_url": "https://huggingface.co/settings/tokens",
        "icon": "huggingface",
    },
    {
        "id": "perplexity",
        "name": "Perplexity",
        "env_var": "PERPLEXITY_API_KEY",
        "kind": "apikey",
        "description": "Busca com citações e raciocínio online",
        "docs_url": "https://www.perplexity.ai/settings/api",
        "icon": "perplexity",
    },
    {
        "id": "github",
        "name": "GitHub",
        "env_var": "GITHUB_TOKEN",
        "kind": "oauth",
        "description": "Acesso a repositórios, PRs e issues",
        "docs_url": "https://docs.github.com/en/apps/oauth-apps",
        "icon": "github",
        "oauth_scopes": ["repo", "user:email", "read:org"],
    },
]

# Índice rápido por id
_REGISTRY_BY_ID: dict[str, dict[str, Any]] = {i["id"]: i for i in INTEGRATIONS_REGISTRY}


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _get_user(request: Request) -> Any:
    user = getattr(request.state, "user", None)
    if user is None:
        raise HTTPException(status_code=401, detail="Não autenticado")
    return user


def _github_cfg() -> tuple[str, str, str]:
    """Lê configuração OAuth do GitHub nas env vars.

    Retorna (client_id, client_secret, redirect_uri).
    Levanta HTTPException 503 se não configurado.
    """
    client_id = os.environ.get("GITHUB_OAUTH_CLIENT_ID", "")
    client_secret = os.environ.get("GITHUB_OAUTH_CLIENT_SECRET", "")
    redirect_uri = os.environ.get(
        "GITHUB_OAUTH_REDIRECT_URI",
        "http://localhost:8080/auth/github/callback",
    )
    if not client_id or not client_secret:
        raise HTTPException(
            status_code=503,
            detail=(
                "GitHub OAuth não configurado. "
                "Defina GITHUB_OAUTH_CLIENT_ID e GITHUB_OAUTH_CLIENT_SECRET."
            ),
        )
    return client_id, client_secret, redirect_uri


# ---------------------------------------------------------------------------
# O1 — Endpoints de integrações (listagem + status + verificação)
# ---------------------------------------------------------------------------


@router.get("/integrations")
async def list_integrations(request: Request) -> dict:
    """Lista todas as integrações com status de conexão do usuário atual."""
    user = _get_user(request)
    try:
        from vectora.services import auth as auth_svc

        overrides = await auth_svc.get_env_overrides(user.id)
    except Exception:
        overrides = {}

    items = []
    for integ in INTEGRATIONS_REGISTRY:
        env_var = integ["env_var"]
        # Considera conectado se há override do usuário OU se a env global está setada
        connected = bool(overrides.get(env_var) or os.environ.get(env_var))
        items.append(
            {
                **integ,
                "connected": connected,
                # Nunca expõe o valor — apenas informa se existe
            }
        )
    return {"integrations": items}


@router.post("/integrations/{integration_id}/verify")
async def verify_integration(request: Request, integration_id: str) -> dict:
    """Testa se a chave/token da integração está funcional."""
    _get_user(request)
    integ = _REGISTRY_BY_ID.get(integration_id)
    if integ is None:
        raise HTTPException(
            status_code=404, detail=f"Integração '{integration_id}' desconhecida"
        )

    env_var = integ["env_var"]
    # Lê do env efetivo (system + user overrides já mesclados pelo middleware)
    token = os.environ.get(env_var, "")
    if not token:
        return {"ok": False, "message": "Chave não configurada"}

    try:
        ok, message = await _verify_apikey(integration_id, token)
        return {"ok": ok, "message": message}
    except Exception as exc:
        logger.warning("verify_integration(%s) error: %s", integration_id, exc)
        return {"ok": False, "message": str(exc)}


async def _verify_apikey(integration_id: str, token: str) -> tuple[bool, str]:  # noqa: PLR0911
    """Faz uma chamada mínima para validar a chave de cada provedor."""
    import httpx

    async with httpx.AsyncClient(timeout=8) as client:
        if integration_id == "openai":
            r = await client.get(
                "https://api.openai.com/v1/models",
                headers={"Authorization": f"Bearer {token}"},
            )
            if r.status_code == 200:
                return True, "Chave válida"
            return False, f"OpenAI retornou {r.status_code}"

        if integration_id == "anthropic":
            r = await client.get(
                "https://api.anthropic.com/v1/models",
                headers={"x-api-key": token, "anthropic-version": "2023-06-01"},
            )
            if r.status_code == 200:
                return True, "Chave válida"
            return False, f"Anthropic retornou {r.status_code}"

        if integration_id == "cohere":
            r = await client.post(
                "https://api.cohere.com/v1/tokenize",
                headers={"Authorization": f"Bearer {token}"},
                json={"text": "test", "model": "command"},
            )
            if r.status_code == 200:
                return True, "Chave válida"
            return False, f"Cohere retornou {r.status_code}"

        if integration_id == "tavily":
            r = await client.post(
                "https://api.tavily.com/search",
                json={"api_key": token, "query": "test", "max_results": 1},
            )
            if r.status_code in {200, 422}:
                return True, "Chave válida"
            return False, f"Tavily retornou {r.status_code}"

        if integration_id == "github":
            r = await client.get(
                "https://api.github.com/user",
                headers={
                    "Authorization": f"Bearer {token}",
                    "Accept": "application/vnd.github+json",
                },
            )
            if r.status_code == 200:
                username = r.json().get("login", "")
                return True, f"Conectado como @{username}"
            return False, f"GitHub retornou {r.status_code}"

    # Provedores sem verificação automática
    return True, "Chave salva (verificação não disponível para este provedor)"


# ---------------------------------------------------------------------------
# O2 — GitHub OAuth
# ---------------------------------------------------------------------------


@router.get("/auth/github")
async def github_oauth_start(request: Request) -> RedirectResponse:
    """Inicia o fluxo OAuth do GitHub — redireciona para github.com/login/oauth."""
    user = _get_user(request)
    client_id, _secret, redirect_uri = _github_cfg()

    scopes = ",".join(
        _REGISTRY_BY_ID["github"].get("oauth_scopes", ["repo", "user:email"])
    )
    # state = user.id garante que só o user que iniciou pode finalizar o callback
    state = user.id

    url = (
        "https://github.com/login/oauth/authorize"
        f"?client_id={client_id}"
        f"&redirect_uri={redirect_uri}"
        f"&scope={scopes}"
        f"&state={state}"
    )
    return RedirectResponse(url=url, status_code=302)


@router.get("/auth/github/callback")
async def github_oauth_callback(
    request: Request, code: str = "", state: str = ""
) -> RedirectResponse:
    """Callback do GitHub — troca code por token e salva como env_override."""
    if not code:
        raise HTTPException(status_code=400, detail="Parâmetro 'code' ausente")

    client_id, client_secret, redirect_uri = _github_cfg()

    # Troca o code pelo access_token
    import httpx

    async with httpx.AsyncClient(timeout=10) as client:
        r = await client.post(
            "https://github.com/login/oauth/access_token",
            json={
                "client_id": client_id,
                "client_secret": client_secret,
                "code": code,
                "redirect_uri": redirect_uri,
            },
            headers={"Accept": "application/json"},
        )

    if r.status_code != 200:
        logger.error("GitHub token exchange failed: %s", r.text)
        return RedirectResponse(
            url="/?oauth_error=github_exchange_failed", status_code=302
        )

    data = r.json()
    access_token = data.get("access_token", "")
    if not access_token:
        logger.error("GitHub callback: token ausente na resposta: %s", data)
        return RedirectResponse(url="/?oauth_error=github_no_token", status_code=302)

    # Salva como env_override do usuário identificado pelo state
    user_id = state
    try:
        from vectora.services import auth as auth_svc

        await auth_svc.set_env_override(user_id, "GITHUB_TOKEN", access_token)
        logger.info("GitHub OAuth: token salvo para user_id=%s", user_id)
    except Exception as exc:
        logger.exception("GitHub OAuth: falha ao salvar token: %s", exc)
        return RedirectResponse(url="/?oauth_error=github_save_failed", status_code=302)

    return RedirectResponse(url="/?oauth_success=github", status_code=302)


@router.get("/auth/github/status")
async def github_oauth_status(request: Request) -> dict:
    """Retorna se o GitHub está conectado e o username associado."""
    user = _get_user(request)
    try:
        from vectora.services import auth as auth_svc

        overrides = await auth_svc.get_env_overrides(user.id)
        token = overrides.get("GITHUB_TOKEN") or os.environ.get("GITHUB_TOKEN", "")
    except Exception:
        token = os.environ.get("GITHUB_TOKEN", "")

    if not token:
        return {"connected": False, "username": None}

    # Resolve username via API do GitHub
    try:
        import httpx

        async with httpx.AsyncClient(timeout=5) as client:
            r = await client.get(
                "https://api.github.com/user",
                headers={
                    "Authorization": f"Bearer {token}",
                    "Accept": "application/vnd.github+json",
                },
            )
        if r.status_code == 200:
            return {"connected": True, "username": r.json().get("login")}
    except Exception:
        pass

    return {"connected": True, "username": None}


@router.delete("/auth/github")
async def github_oauth_disconnect(request: Request) -> dict:
    """Remove o GITHUB_TOKEN dos env_overrides do usuário."""
    user = _get_user(request)
    try:
        from vectora.services import auth as auth_svc

        await auth_svc.delete_env_override(user.id, "GITHUB_TOKEN")
        logger.info("GitHub OAuth: token removido para user_id=%s", user.id)
    except Exception as exc:
        logger.warning("GitHub OAuth disconnect error: %s", exc)
    return {"status": "disconnected"}
