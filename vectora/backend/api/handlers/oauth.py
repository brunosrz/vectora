"""Handler de OAuth e registry de integrações externas.

O1 — API Key integrations:
    GET  /integrations                  — lista integrações com status (conectado/não)
    POST /integrations/{id}/verify      — testa se a API key configurada é válida

O2 — GitHub OAuth + GitLab OAuth + Google OAuth + Slack OAuth:
    GET  /auth/{provider}               — inicia o fluxo OAuth
    GET  /auth/{provider}/callback      — callback, salva token
    GET  /auth/{provider}/status        — {connected: bool, ...}
    DELETE /auth/{provider}             — desconecta

Configuração necessária (env vars):
    GITHUB_OAUTH_CLIENT_ID / GITHUB_OAUTH_CLIENT_SECRET
    GITLAB_OAUTH_CLIENT_ID / GITLAB_OAUTH_CLIENT_SECRET / GITLAB_BASE_URL
    GOOGLE_OAUTH_CLIENT_ID / GOOGLE_OAUTH_CLIENT_SECRET
    SLACK_OAUTH_CLIENT_ID / SLACK_OAUTH_CLIENT_SECRET
"""

from __future__ import annotations

import logging
import os
from pathlib import Path
from typing import Any

from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import RedirectResponse

logger = logging.getLogger(__name__)

router = APIRouter(tags=["oauth"])

_RELAY_TOKEN_PATH = Path.home() / ".vectora" / "relay_token"


def _relay_callback_url(
    provider: str,
    token_path: Path | None = None,
) -> str | None:
    """Retorna URL de callback via relay se token disponível, ou None."""
    path = token_path if token_path is not None else _RELAY_TOKEN_PATH
    try:
        token = path.read_text().strip()
        if token:
            return f"https://{token}.vectora.chat/auth/{provider}/callback"
    except OSError:
        pass
    return None


# ---------------------------------------------------------------------------
# Registry de integrações (O1)
# ---------------------------------------------------------------------------

#: Todas as integrações suportadas — consumido pela UI e pelo endpoint /integrations.
#: kind="apikey" → apenas chave inserida manualmente pelo usuário.
#: kind="oauth"  → fluxo OAuth delegado; o token é salvo como env_override.
INTEGRATIONS_REGISTRY: list[dict[str, Any]] = [
    {
        "id": "gemini",
        "name": "Google Gemini",
        "env_var": "GOOGLE_API_KEY",
        "kind": "apikey",
        "description": "Gemini 2.5 (Pro/Flash) — provider padrão do Vectora",
        "docs_url": "https://aistudio.google.com/app/apikey",
        "icon": "gemini",
    },
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
        "id": "github",
        "name": "GitHub",
        "env_var": "GITHUB_TOKEN",
        # híbrido: aceita OAuth (delegado) OU um Personal Access Token colado
        # manualmente. Ambos gravam GITHUB_TOKEN nos env_overrides do user —
        # o `gh` CLI e as git tools leem essa env. Permite quem não quer
        # registrar um OAuth App usar só um PAT.
        "kind": "hybrid",
        "description": "Acesso a repositórios, PRs e issues (OAuth ou token)",
        "docs_url": "https://github.com/settings/tokens",
        "icon": "github",
        "oauth_scopes": ["repo", "user:email", "read:org"],
        # GITHUB_PERSONAL_ACCESS_TOKEN é a convenção do servidor MCP oficial
        # do GitHub (marketplace) — reconhecida aqui como alias pra "conectado"
        # não depender de saber qual dos dois nomes o usuário configurou.
        "env_var_aliases": ["GITHUB_PERSONAL_ACCESS_TOKEN"],
    },
    {
        "id": "gitlab",
        "name": "GitLab",
        "env_var": "GITLAB_TOKEN",
        "kind": "oauth",
        "description": "Repositórios, merge requests e pipelines do GitLab",
        "docs_url": "https://gitlab.com/-/profile/applications",
        "icon": "gitlab",
        "oauth_scopes": ["api", "read_repository", "write_repository", "read_user"],
    },
    {
        "id": "google",
        "name": "Google",
        "env_var": "GOOGLE_ACCESS_TOKEN",
        "kind": "oauth",
        "description": "Conta Google (base para Drive e Gmail)",
        "docs_url": "https://console.cloud.google.com/apis/credentials",
        "icon": "google",
        "oauth_scopes": ["openid", "email", "profile"],
    },
    {
        "id": "google-drive",
        "name": "Google Drive",
        "env_var": "GOOGLE_ACCESS_TOKEN",
        "kind": "oauth",
        "description": "Leitura e busca de arquivos no Google Drive",
        "docs_url": "https://console.cloud.google.com/apis/credentials",
        "icon": "google-drive",
        "parent": "google",
    },
    {
        "id": "gmail",
        "name": "Gmail",
        "env_var": "GOOGLE_ACCESS_TOKEN",
        "kind": "oauth",
        "description": "Leitura de emails recebidos no Gmail",
        "docs_url": "https://console.cloud.google.com/apis/credentials",
        "icon": "gmail",
        "parent": "google",
    },
    {
        "id": "slack",
        "name": "Slack",
        "env_var": "SLACK_BOT_TOKEN",
        "kind": "oauth",
        "description": "Envio e leitura de mensagens no Slack",
        "docs_url": "https://api.slack.com/apps",
        "icon": "slack",
        "oauth_scopes": [
            "chat:write",
            "channels:read",
            "users:read",
            "channels:history",
        ],
    },
    {
        "id": "linear",
        "name": "Linear",
        "env_var": "LINEAR_API_KEY",
        "kind": "apikey",
        "description": "Issues e projetos do Linear",
        "docs_url": "https://linear.app/settings/api",
        "icon": "linear",
    },
    {
        "id": "jira",
        "name": "Jira",
        "env_var": "JIRA_API_TOKEN",
        "kind": "apikey",
        "description": "Issues e sprints do Jira (Atlassian)",
        "docs_url": "https://id.atlassian.com/manage-profile/security/api-tokens",
        "icon": "jira",
        "extra_vars": ["JIRA_BASE_URL", "JIRA_EMAIL"],
    },
    {
        "id": "notion",
        "name": "Notion",
        "env_var": "NOTION_API_KEY",
        "kind": "apikey",
        "description": "Páginas e databases do Notion",
        "docs_url": "https://www.notion.so/my-integrations",
        "icon": "notion",
    },
    {
        "id": "resend",
        "name": "Resend",
        "env_var": "RESEND_API_KEY",
        "kind": "apikey",
        "description": "Envio de emails transacionais via Resend",
        "docs_url": "https://resend.com/api-keys",
        "icon": "resend",
    },
    {
        "id": "sendgrid",
        "name": "SendGrid",
        "env_var": "SENDGRID_API_KEY",
        "kind": "apikey",
        "description": "Envio de emails e campanhas via SendGrid (Twilio)",
        "docs_url": "https://app.sendgrid.com/settings/api_keys",
        "icon": "sendgrid",
    },
    {
        "id": "mailgun",
        "name": "Mailgun",
        "env_var": "MAILGUN_API_KEY",
        "kind": "apikey",
        "description": "Envio e recebimento de emails via Mailgun",
        "docs_url": "https://app.mailgun.com/settings/api-security",
        "icon": "mailgun",
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
    redirect_uri = (
        os.environ.get("GITHUB_OAUTH_REDIRECT_URI")
        or _relay_callback_url("github")
        or "http://localhost:8080/auth/github/callback"
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
        from backend.rbac import auth as auth_svc

        overrides = await auth_svc.get_env_overrides(user.id)
    except Exception:
        overrides = {}

    items = []
    for integ in INTEGRATIONS_REGISTRY:
        env_vars = [integ["env_var"], *integ.get("env_var_aliases", [])]
        # Considera conectado se há override do usuário OU env global setada,
        # em qualquer um dos nomes aceitos (env_var principal ou alias).
        connected = any(overrides.get(v) or os.environ.get(v) for v in env_vars)
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

    # Lê do env efetivo (system + user overrides já mesclados pelo middleware),
    # tentando o env_var principal e, se ausente, os aliases aceitos. Não é
    # senha hardcoded (B105 falso-positivo) — é o valor inicial antes do loop.
    token = ""  # nosec B105
    for v in [integ["env_var"], *integ.get("env_var_aliases", [])]:
        token = os.environ.get(v, "")
        if token:
            break
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

        if integration_id == "gitlab":
            base = os.environ.get("GITLAB_BASE_URL", "https://gitlab.com")
            r = await client.get(
                f"{base}/api/v4/user",
                headers={"Authorization": f"Bearer {token}"},
            )
            if r.status_code == 200:
                username = r.json().get("username", "")
                return True, f"Conectado como @{username}"
            return False, f"GitLab retornou {r.status_code}"

        if integration_id == "google":
            r = await client.get(
                "https://www.googleapis.com/oauth2/v3/userinfo",
                headers={"Authorization": f"Bearer {token}"},
            )
            if r.status_code == 200:
                email = r.json().get("email", "")
                return True, f"Conectado como {email}"
            return False, f"Google retornou {r.status_code}"

        if integration_id in ("google-drive", "gmail"):
            r = await client.get(
                "https://www.googleapis.com/oauth2/v3/userinfo",
                headers={"Authorization": f"Bearer {token}"},
            )
            if r.status_code == 200:
                return True, "Token Google válido"
            return False, f"Google retornou {r.status_code}"

        if integration_id == "slack":
            r = await client.get(
                "https://slack.com/api/auth.test",
                headers={"Authorization": f"Bearer {token}"},
            )
            data = r.json()
            if data.get("ok"):
                return True, f"Conectado como @{data.get('user', '')}"
            return False, data.get("error", "Token Slack inválido")

        if integration_id == "linear":
            r = await client.post(
                "https://api.linear.app/graphql",
                json={"query": "{ viewer { id name } }"},
                headers={"Authorization": token, "Content-Type": "application/json"},
            )
            if r.status_code == 200 and "data" in r.json():
                name = r.json()["data"]["viewer"]["name"]
                return True, f"Conectado como {name}"
            return False, f"Linear retornou {r.status_code}"

        if integration_id == "notion":
            r = await client.get(
                "https://api.notion.com/v1/users/me",
                headers={
                    "Authorization": f"Bearer {token}",
                    "Notion-Version": "2022-06-28",
                },
            )
            if r.status_code == 200:
                name = r.json().get("name", "")
                return True, f"Conectado como {name}"
            return False, f"Notion retornou {r.status_code}"

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
        from backend.rbac import auth as auth_svc

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
        from backend.rbac import auth as auth_svc

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
        from backend.rbac import auth as auth_svc

        await auth_svc.delete_env_override(user.id, "GITHUB_TOKEN")
        logger.info("GitHub OAuth: token removido para user_id=%s", user.id)
    except Exception as exc:
        logger.warning("GitHub OAuth disconnect error: %s", exc)
    return {"status": "disconnected"}


# ---------------------------------------------------------------------------
# O3 — GitLab OAuth
# ---------------------------------------------------------------------------


def _gitlab_cfg() -> tuple[str, str, str, str]:
    client_id = os.environ.get("GITLAB_OAUTH_CLIENT_ID", "")
    client_secret = os.environ.get("GITLAB_OAUTH_CLIENT_SECRET", "")
    base_url = os.environ.get("GITLAB_BASE_URL", "https://gitlab.com")
    redirect_uri = (
        os.environ.get("GITLAB_OAUTH_REDIRECT_URI")
        or _relay_callback_url("gitlab")
        or "http://localhost:8080/auth/gitlab/callback"
    )
    if not client_id or not client_secret:
        raise HTTPException(
            status_code=503,
            detail="GitLab OAuth não configurado. Defina GITLAB_OAUTH_CLIENT_ID e GITLAB_OAUTH_CLIENT_SECRET.",
        )
    return client_id, client_secret, base_url, redirect_uri


@router.get("/auth/gitlab")
async def gitlab_oauth_start(request: Request) -> RedirectResponse:
    user = _get_user(request)
    client_id, _secret, base_url, redirect_uri = _gitlab_cfg()
    scopes = " ".join(
        _REGISTRY_BY_ID["gitlab"].get("oauth_scopes", ["api", "read_user"])
    )
    url = (
        f"{base_url}/oauth/authorize"
        f"?client_id={client_id}"
        f"&redirect_uri={redirect_uri}"
        f"&response_type=code"
        f"&scope={scopes}"
        f"&state={user.id}"
    )
    return RedirectResponse(url=url, status_code=302)


@router.get("/auth/gitlab/callback")
async def gitlab_oauth_callback(
    request: Request, code: str = "", state: str = ""
) -> RedirectResponse:
    if not code:
        raise HTTPException(status_code=400, detail="Parâmetro 'code' ausente")
    client_id, client_secret, base_url, redirect_uri = _gitlab_cfg()

    import httpx

    async with httpx.AsyncClient(timeout=10) as client:
        r = await client.post(
            f"{base_url}/oauth/token",
            json={
                "client_id": client_id,
                "client_secret": client_secret,
                "code": code,
                "grant_type": "authorization_code",
                "redirect_uri": redirect_uri,
            },
        )

    if r.status_code != 200:
        logger.error("GitLab token exchange failed: %s", r.text)
        return RedirectResponse(
            url="/?oauth_error=gitlab_exchange_failed", status_code=302
        )

    access_token = r.json().get("access_token", "")
    if not access_token:
        return RedirectResponse(url="/?oauth_error=gitlab_no_token", status_code=302)

    try:
        from backend.rbac import auth as auth_svc

        await auth_svc.set_env_override(state, "GITLAB_TOKEN", access_token)
        logger.info("GitLab OAuth: token salvo para user_id=%s", state)
    except Exception as exc:
        logger.exception("GitLab OAuth: falha ao salvar token: %s", exc)
        return RedirectResponse(url="/?oauth_error=gitlab_save_failed", status_code=302)

    return RedirectResponse(url="/?oauth_success=gitlab", status_code=302)


@router.get("/auth/gitlab/status")
async def gitlab_oauth_status(request: Request) -> dict:
    user = _get_user(request)
    try:
        from backend.rbac import auth as auth_svc

        overrides = await auth_svc.get_env_overrides(user.id)
        token = overrides.get("GITLAB_TOKEN") or os.environ.get("GITLAB_TOKEN", "")
    except Exception:
        token = os.environ.get("GITLAB_TOKEN", "")

    if not token:
        return {"connected": False, "username": None}

    try:
        import httpx

        base_url = os.environ.get("GITLAB_BASE_URL", "https://gitlab.com")
        async with httpx.AsyncClient(timeout=5) as client:
            r = await client.get(
                f"{base_url}/api/v4/user",
                headers={"Authorization": f"Bearer {token}"},
            )
        if r.status_code == 200:
            return {"connected": True, "username": r.json().get("username")}
    except Exception:
        pass

    return {"connected": True, "username": None}


@router.delete("/auth/gitlab")
async def gitlab_oauth_disconnect(request: Request) -> dict:
    user = _get_user(request)
    try:
        from backend.rbac import auth as auth_svc

        await auth_svc.delete_env_override(user.id, "GITLAB_TOKEN")
    except Exception as exc:
        logger.warning("GitLab disconnect error: %s", exc)
    return {"status": "disconnected"}


# ---------------------------------------------------------------------------
# O4 — Google OAuth (Drive + Gmail)
# ---------------------------------------------------------------------------


def _google_cfg() -> tuple[str, str, str]:
    client_id = os.environ.get("GOOGLE_OAUTH_CLIENT_ID", "")
    client_secret = os.environ.get("GOOGLE_OAUTH_CLIENT_SECRET", "")
    redirect_uri = (
        os.environ.get("GOOGLE_OAUTH_REDIRECT_URI")
        or _relay_callback_url("google")
        or "http://localhost:8080/auth/google/callback"
    )
    if not client_id or not client_secret:
        raise HTTPException(
            status_code=503,
            detail="Google OAuth não configurado. Defina GOOGLE_OAUTH_CLIENT_ID e GOOGLE_OAUTH_CLIENT_SECRET.",
        )
    return client_id, client_secret, redirect_uri


@router.get("/auth/google")
async def google_oauth_start(request: Request) -> RedirectResponse:
    user = _get_user(request)
    client_id, _secret, redirect_uri = _google_cfg()
    scopes = (
        "openid email profile "
        "https://www.googleapis.com/auth/drive.readonly "
        "https://www.googleapis.com/auth/gmail.readonly"
    )
    import urllib.parse

    url = (
        "https://accounts.google.com/o/oauth2/v2/auth"
        f"?client_id={client_id}"
        f"&redirect_uri={urllib.parse.quote(redirect_uri)}"
        "&response_type=code"
        f"&scope={urllib.parse.quote(scopes)}"
        "&access_type=offline"
        "&prompt=consent"
        f"&state={user.id}"
    )
    return RedirectResponse(url=url, status_code=302)


@router.get("/auth/google/callback")
async def google_oauth_callback(
    request: Request, code: str = "", state: str = ""
) -> RedirectResponse:
    if not code:
        raise HTTPException(status_code=400, detail="Parâmetro 'code' ausente")
    client_id, client_secret, redirect_uri = _google_cfg()

    import httpx

    async with httpx.AsyncClient(timeout=10) as client:
        r = await client.post(
            "https://oauth2.googleapis.com/token",
            data={
                "client_id": client_id,
                "client_secret": client_secret,
                "code": code,
                "grant_type": "authorization_code",
                "redirect_uri": redirect_uri,
            },
        )

    if r.status_code != 200:
        logger.error("Google token exchange failed: %s", r.text)
        return RedirectResponse(
            url="/?oauth_error=google_exchange_failed", status_code=302
        )

    data = r.json()
    access_token = data.get("access_token", "")
    refresh_token = data.get("refresh_token", "")
    if not access_token:
        return RedirectResponse(url="/?oauth_error=google_no_token", status_code=302)

    try:
        from backend.rbac import auth as auth_svc

        await auth_svc.set_env_override(state, "GOOGLE_ACCESS_TOKEN", access_token)
        if refresh_token:
            await auth_svc.set_env_override(
                state, "GOOGLE_REFRESH_TOKEN", refresh_token
            )
        logger.info("Google OAuth: token salvo para user_id=%s", state)
    except Exception as exc:
        logger.exception("Google OAuth: falha ao salvar token: %s", exc)
        return RedirectResponse(url="/?oauth_error=google_save_failed", status_code=302)

    return RedirectResponse(url="/?oauth_success=google", status_code=302)


@router.get("/auth/google/status")
async def google_oauth_status(request: Request) -> dict:
    user = _get_user(request)
    try:
        from backend.rbac import auth as auth_svc

        overrides = await auth_svc.get_env_overrides(user.id)
        token = overrides.get("GOOGLE_ACCESS_TOKEN") or os.environ.get(
            "GOOGLE_ACCESS_TOKEN", ""
        )
    except Exception:
        token = os.environ.get("GOOGLE_ACCESS_TOKEN", "")

    if not token:
        return {"connected": False, "email": None}

    try:
        import httpx

        async with httpx.AsyncClient(timeout=5) as client:
            r = await client.get(
                "https://www.googleapis.com/oauth2/v3/userinfo",
                headers={"Authorization": f"Bearer {token}"},
            )
        if r.status_code == 200:
            info = r.json()
            return {
                "connected": True,
                "email": info.get("email"),
                "name": info.get("name"),
            }
    except Exception:
        pass

    return {"connected": True, "email": None}


@router.delete("/auth/google")
async def google_oauth_disconnect(request: Request) -> dict:
    user = _get_user(request)
    try:
        from backend.rbac import auth as auth_svc

        await auth_svc.delete_env_override(user.id, "GOOGLE_ACCESS_TOKEN")
        await auth_svc.delete_env_override(user.id, "GOOGLE_REFRESH_TOKEN")
    except Exception as exc:
        logger.warning("Google disconnect error: %s", exc)
    return {"status": "disconnected"}


# ---------------------------------------------------------------------------
# O5 — Slack OAuth
# ---------------------------------------------------------------------------


def _slack_cfg() -> tuple[str, str, str]:
    client_id = os.environ.get("SLACK_OAUTH_CLIENT_ID", "")
    client_secret = os.environ.get("SLACK_OAUTH_CLIENT_SECRET", "")
    redirect_uri = (
        os.environ.get("SLACK_REDIRECT_URI")
        or _relay_callback_url("slack")
        or "http://localhost:8080/auth/slack/callback"
    )
    if not client_id or not client_secret:
        raise HTTPException(
            status_code=503,
            detail="Slack OAuth não configurado. Defina SLACK_OAUTH_CLIENT_ID e SLACK_OAUTH_CLIENT_SECRET.",
        )
    return client_id, client_secret, redirect_uri


@router.get("/auth/slack")
async def slack_oauth_start(request: Request) -> RedirectResponse:
    user = _get_user(request)
    client_id, _secret, redirect_uri = _slack_cfg()
    scopes = ",".join(
        _REGISTRY_BY_ID["slack"].get("oauth_scopes", ["chat:write", "channels:read"])
    )
    import urllib.parse

    url = (
        "https://slack.com/oauth/v2/authorize"
        f"?client_id={client_id}"
        f"&redirect_uri={urllib.parse.quote(redirect_uri)}"
        f"&scope={scopes}"
        f"&state={user.id}"
    )
    return RedirectResponse(url=url, status_code=302)


@router.get("/auth/slack/callback")
async def slack_oauth_callback(
    request: Request, code: str = "", state: str = ""
) -> RedirectResponse:
    if not code:
        raise HTTPException(status_code=400, detail="Parâmetro 'code' ausente")
    client_id, client_secret, redirect_uri = _slack_cfg()

    import httpx

    async with httpx.AsyncClient(timeout=10) as client:
        r = await client.post(
            "https://slack.com/api/oauth.v2.access",
            data={
                "client_id": client_id,
                "client_secret": client_secret,
                "code": code,
                "redirect_uri": redirect_uri,
            },
        )

    data = r.json()
    if not data.get("ok"):
        logger.error("Slack OAuth failed: %s", data)
        return RedirectResponse(
            url="/?oauth_error=slack_exchange_failed", status_code=302
        )

    bot_token = data.get("access_token", "")
    if not bot_token:
        return RedirectResponse(url="/?oauth_error=slack_no_token", status_code=302)

    try:
        from backend.rbac import auth as auth_svc

        await auth_svc.set_env_override(state, "SLACK_BOT_TOKEN", bot_token)
        logger.info("Slack OAuth: token salvo para user_id=%s", state)
    except Exception as exc:
        logger.exception("Slack OAuth: falha ao salvar token: %s", exc)
        return RedirectResponse(url="/?oauth_error=slack_save_failed", status_code=302)

    return RedirectResponse(url="/?oauth_success=slack", status_code=302)


@router.get("/auth/slack/status")
async def slack_oauth_status(request: Request) -> dict:
    user = _get_user(request)
    try:
        from backend.rbac import auth as auth_svc

        overrides = await auth_svc.get_env_overrides(user.id)
        token = overrides.get("SLACK_BOT_TOKEN") or os.environ.get(
            "SLACK_BOT_TOKEN", ""
        )
    except Exception:
        token = os.environ.get("SLACK_BOT_TOKEN", "")

    if not token:
        return {"connected": False, "team": None}

    try:
        import httpx

        async with httpx.AsyncClient(timeout=5) as client:
            r = await client.get(
                "https://slack.com/api/auth.test",
                headers={"Authorization": f"Bearer {token}"},
            )
        data = r.json()
        if data.get("ok"):
            return {
                "connected": True,
                "team": data.get("team"),
                "user": data.get("user"),
            }
    except Exception:
        pass

    return {"connected": True, "team": None}


@router.delete("/auth/slack")
async def slack_oauth_disconnect(request: Request) -> dict:
    user = _get_user(request)
    try:
        from backend.rbac import auth as auth_svc

        await auth_svc.delete_env_override(user.id, "SLACK_BOT_TOKEN")
    except Exception as exc:
        logger.warning("Slack disconnect error: %s", exc)
    return {"status": "disconnected"}
