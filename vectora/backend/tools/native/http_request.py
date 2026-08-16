"""Tool: HTTP GET/POST/PUT requests (async)."""

import json

import httpx

from backend.tools.registry import ToolExtras, vtool


@vtool(
    extras=ToolExtras(
        render_hint="text",
        category="native",
        destructive=False,
        icon="globe",
    )
)
async def http_request(
    method: str, url: str, body: str | None = None, headers: str | None = None
) -> str:
    """Faz requisição HTTP async.

    Args:
        method: GET, POST, PUT, DELETE
        url: URL completa
        body: JSON body (opcional)
        headers: JSON headers (opcional)

    Returns:
        Response body ou erro
    """
    try:
        async with httpx.AsyncClient(timeout=10) as client:
            req_headers = {}
            if headers:
                req_headers = json.loads(headers)
            req_body = None
            if body:
                req_body = body

            resp = await client.request(
                method.upper(), url, content=req_body, headers=req_headers
            )
            return resp.text
    except Exception as e:
        return f"error: {e}"
