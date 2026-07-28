"""Tools de observabilidade e controle avançado do browser Chromium do
agente (CDP) — distinto de `backend/tools/browser.py`, que cobre só
navegação/interação básica (click/fill/scroll/screenshot) e gestão de dev
server. Aqui: múltiplas abas, console/network logs, `evaluate` de JS
arbitrário, dialogs, emulação, tracing de performance, heap snapshot e
Lighthouse.
"""

from __future__ import annotations

import asyncio
import json
import logging
import uuid
from pathlib import Path
from typing import Annotated, Any

from langchain.tools import tool
from langchain_core.runnables import RunnableConfig
from langchain_core.tools import InjectedToolArg

from backend.browser.session import (
    close_tab,
    get_tab_state,
    has_browser_session,
    list_tabs,
    new_tab,
    select_tab,
    set_dialog_policy,
)

logger = logging.getLogger(__name__)


def _workspace_id(config: RunnableConfig | None) -> str:
    raw = (
        str((config.get("configurable") or {}).get("workspace_id", ""))
        if config
        else ""
    )
    return raw or "default"


#: Perfis de `Network.emulateNetworkConditions` (CDP) — latência em ms,
#: throughput em bytes/s. "offline" zera o throughput.
_NETWORK_PROFILES: dict[str, dict[str, Any]] = {
    "offline": {
        "offline": True,
        "latency": 0,
        "downloadThroughput": 0,
        "uploadThroughput": 0,
    },
    "slow-3g": {
        "offline": False,
        "latency": 400,
        "downloadThroughput": 50 * 1024 // 8,
        "uploadThroughput": 50 * 1024 // 8,
    },
    "fast-3g": {
        "offline": False,
        "latency": 150,
        "downloadThroughput": 180 * 1024 // 8,
        "uploadThroughput": 84 * 1024 // 8,
    },
}

_NO_SESSION_ERROR = json.dumps(
    {
        "status": "error",
        "error": (
            "Nenhuma sessão de browser aberta neste workspace. Use "
            "`browser_navigate` ou `browser_new_tab` primeiro."
        ),
    }
)


@tool(
    extras={
        "render_hint": "json",
        "category": "browser",
        "destructive": False,
        "icon": "layout-grid",
    }
)
async def browser_list_tabs(
    config: Annotated[RunnableConfig, InjectedToolArg] = None,  # ty: ignore[invalid-parameter-default]
) -> str:
    """Lista as abas abertas na sessão de browser do workspace ativo.

    Returns:
        JSON `{"tabs": [{"tab_id", "url", "active"}, ...]}`.
    """
    workspace_id = _workspace_id(config)
    tabs = await list_tabs(workspace_id)
    return json.dumps({"tabs": tabs})


@tool(
    extras={
        "render_hint": "text",
        "category": "browser",
        "destructive": False,
        "icon": "plus-square",
    }
)
async def browser_new_tab(
    url: str | None = None,
    config: Annotated[RunnableConfig, InjectedToolArg] = None,  # ty: ignore[invalid-parameter-default]
) -> str:
    """Abre uma aba nova na sessão do workspace ativo (lança o browser se
    ainda não houver sessão) e a torna a aba ativa.

    Args:
        url: URL http(s) opcional pra já navegar a aba nova.

    Returns:
        JSON `{"status": "ok", "tab_id": "..."}` ou erro.
    """
    workspace_id = _workspace_id(config)
    try:
        tab_id = await new_tab(workspace_id, url=url)
        return json.dumps({"status": "ok", "tab_id": tab_id})
    except Exception as exc:
        logger.exception("browser_new_tab failed", extra={"url": url})
        return json.dumps({"status": "error", "error": str(exc)})


@tool(
    extras={
        "render_hint": "text",
        "category": "browser",
        "destructive": True,
        "icon": "x-square",
    }
)
async def browser_close_tab(
    tab_id: str,
    config: Annotated[RunnableConfig, InjectedToolArg] = None,  # ty: ignore[invalid-parameter-default]
) -> str:
    """Fecha uma aba pelo id. Nunca deixa a sessão sem nenhuma aba —
    fechar a última abre uma em branco no lugar.

    Args:
        tab_id: id da aba (de `browser_list_tabs`).
    """
    workspace_id = _workspace_id(config)
    if not has_browser_session(workspace_id):
        return _NO_SESSION_ERROR
    ok = await close_tab(workspace_id, tab_id)
    if not ok:
        return json.dumps(
            {"status": "error", "error": f"aba '{tab_id}' não encontrada"}
        )
    return json.dumps({"status": "ok", "tab_id": tab_id})


@tool(
    extras={
        "render_hint": "text",
        "category": "browser",
        "destructive": False,
        "icon": "layout-panel-left",
    }
)
async def browser_select_tab(
    tab_id: str,
    config: Annotated[RunnableConfig, InjectedToolArg] = None,  # ty: ignore[invalid-parameter-default]
) -> str:
    """Torna `tab_id` a aba ativa da sessão — as demais tools de browser
    (`browser_click`, `browser_screenshot`, etc.) passam a operar nela.

    Args:
        tab_id: id da aba (de `browser_list_tabs`).
    """
    workspace_id = _workspace_id(config)
    if not has_browser_session(workspace_id):
        return _NO_SESSION_ERROR
    ok = await select_tab(workspace_id, tab_id)
    if not ok:
        return json.dumps(
            {"status": "error", "error": f"aba '{tab_id}' não encontrada"}
        )
    return json.dumps({"status": "ok", "tab_id": tab_id})


@tool(
    extras={
        "render_hint": "json",
        "category": "browser",
        "destructive": False,
        "icon": "terminal",
    }
)
async def browser_list_console_messages(
    tab_id: str | None = None,
    limit: int = 50,
    config: Annotated[RunnableConfig, InjectedToolArg] = None,  # ty: ignore[invalid-parameter-default]
) -> str:
    """Lista as mensagens de console (log/warn/error/...) capturadas da aba
    desde que ela foi aberta.

    Args:
        tab_id: id da aba (padrão: aba ativa).
        limit: máximo de mensagens mais recentes a retornar.

    Returns:
        JSON `{"messages": [{"type", "text"}, ...]}`.
    """
    workspace_id = _workspace_id(config)
    tab = get_tab_state(workspace_id, tab_id)
    if tab is None:
        return _NO_SESSION_ERROR
    messages = list(tab.console_log)[-limit:]
    return json.dumps({"messages": messages})


@tool(
    extras={
        "render_hint": "text",
        "category": "browser",
        "destructive": True,
        "icon": "eraser",
    }
)
async def browser_clear_console(
    tab_id: str | None = None,
    config: Annotated[RunnableConfig, InjectedToolArg] = None,  # ty: ignore[invalid-parameter-default]
) -> str:
    """Limpa o buffer de mensagens de console capturadas da aba (não afeta
    o console real do browser, só o histórico que o agente lê).

    Args:
        tab_id: id da aba (padrão: aba ativa).
    """
    workspace_id = _workspace_id(config)
    tab = get_tab_state(workspace_id, tab_id)
    if tab is None:
        return _NO_SESSION_ERROR
    tab.console_log.clear()
    return json.dumps({"status": "ok"})


@tool(
    extras={
        "render_hint": "json",
        "category": "browser",
        "destructive": False,
        "icon": "network",
    }
)
async def browser_list_network_requests(
    tab_id: str | None = None,
    resource_type: str | None = None,
    limit: int = 50,
    config: Annotated[RunnableConfig, InjectedToolArg] = None,  # ty: ignore[invalid-parameter-default]
) -> str:
    """Lista as requisições de rede capturadas da aba desde que foi aberta.

    Args:
        tab_id: id da aba (padrão: aba ativa).
        resource_type: filtra por tipo (ex.: "xhr", "fetch", "document",
            "script", "stylesheet", "image") — omitido lista todos.
        limit: máximo de requisições mais recentes a retornar.

    Returns:
        JSON `{"requests": [{"request_id", "url", "method",
        "resource_type", "status"}, ...]}`.
    """
    workspace_id = _workspace_id(config)
    tab = get_tab_state(workspace_id, tab_id)
    if tab is None:
        return _NO_SESSION_ERROR
    entries = list(tab.network_log)
    if resource_type:
        entries = [e for e in entries if e.get("resource_type") == resource_type]
    return json.dumps({"requests": entries[-limit:]})


@tool(
    extras={
        "render_hint": "json",
        "category": "browser",
        "destructive": False,
        "icon": "network",
    }
)
async def browser_get_network_request(
    request_id: str,
    tab_id: str | None = None,
    config: Annotated[RunnableConfig, InjectedToolArg] = None,  # ty: ignore[invalid-parameter-default]
) -> str:
    """Detalhes de uma requisição de rede específica, pelo `request_id`
    retornado por `browser_list_network_requests`.

    Args:
        request_id: id da requisição.
        tab_id: id da aba (padrão: aba ativa).
    """
    workspace_id = _workspace_id(config)
    tab = get_tab_state(workspace_id, tab_id)
    if tab is None:
        return _NO_SESSION_ERROR
    for entry in tab.network_log:
        if entry.get("request_id") == request_id:
            return json.dumps(entry)
    return json.dumps(
        {"status": "error", "error": f"request '{request_id}' não encontrada"}
    )


@tool(
    extras={
        "render_hint": "json",
        "category": "browser",
        "destructive": True,
        "icon": "code",
    }
)
async def browser_evaluate(
    script: str,
    tab_id: str | None = None,
    config: Annotated[RunnableConfig, InjectedToolArg] = None,  # ty: ignore[invalid-parameter-default]
) -> str:
    """Executa JavaScript arbitrário no contexto da página e devolve o
    valor serializado do resultado. Perigoso (`destructive`) — o script
    roda com acesso total ao DOM/JS da página, pode mutar estado.

    Args:
        script: expressão ou função JS (ex.: `"document.title"`,
            `"() => document.querySelectorAll('a').length"`).
        tab_id: id da aba (padrão: aba ativa).

    Returns:
        JSON `{"status": "ok", "result": <valor>}` ou erro (sintaxe
        inválida, exceção lançada pelo script, etc. — nunca propaga crua).
    """
    workspace_id = _workspace_id(config)
    tab = get_tab_state(workspace_id, tab_id)
    if tab is None:
        return _NO_SESSION_ERROR
    try:
        result = await tab.page.evaluate(script)
        return json.dumps({"status": "ok", "result": result}, default=str)
    except Exception as exc:
        logger.exception("browser_evaluate failed")
        return json.dumps({"status": "error", "error": str(exc)})


@tool(
    extras={
        "render_hint": "text",
        "category": "browser",
        "destructive": False,
        "icon": "message-square",
    }
)
async def browser_set_dialog_policy(
    action: str,
    prompt_text: str | None = None,
    tab_id: str | None = None,
    config: Annotated[RunnableConfig, InjectedToolArg] = None,  # ty: ignore[invalid-parameter-default]
) -> str:
    """Define como a aba responde automaticamente a `alert`/`confirm`/
    `prompt` futuros — sem isso, um dialog trava a próxima ação
    (`browser_click` etc.) esperando decisão manual, que não existe no
    modo headless.

    Args:
        action: "accept" ou "dismiss".
        prompt_text: texto a preencher se o dialog for um `prompt()` e a
            ação for "accept" (ignorado em alert/confirm).
        tab_id: id da aba (padrão: aba ativa).
    """
    if action not in ("accept", "dismiss"):
        return json.dumps(
            {"status": "error", "error": "action deve ser 'accept' ou 'dismiss'"}
        )
    workspace_id = _workspace_id(config)
    ok = set_dialog_policy(workspace_id, action, prompt_text=prompt_text, tab_id=tab_id)
    if not ok:
        return _NO_SESSION_ERROR
    return json.dumps({"status": "ok"})


@tool(
    extras={
        "render_hint": "json",
        "category": "browser",
        "destructive": False,
        "icon": "smartphone",
    }
)
async def browser_emulate(
    viewport_width: int | None = None,
    viewport_height: int | None = None,
    device_scale_factor: float | None = None,
    cpu_throttle: float | None = None,
    network_throttle: str | None = None,
    tab_id: str | None = None,
    config: Annotated[RunnableConfig, InjectedToolArg] = None,  # ty: ignore[invalid-parameter-default]
) -> str:
    """Emula viewport/device/throttling na aba — útil pra testar layouts
    mobile ou comportamento sob rede/CPU lentos antes de screenshot.

    Args:
        viewport_width: largura do viewport em px (omitido não muda).
        viewport_height: altura do viewport em px (omitido não muda).
        device_scale_factor: fator de escala (ex.: 2 para retina/mobile).
        cpu_throttle: fator de desaceleração de CPU (ex.: 4 = 4x mais
            lento). Omitido não muda.
        network_throttle: perfil de rede — "offline", "slow-3g", "fast-3g",
            ou `None` pra remover throttling de rede.
        tab_id: id da aba (padrão: aba ativa).

    Returns:
        JSON `{"status": "ok", "applied": [...]}` com o que foi aplicado.
    """
    workspace_id = _workspace_id(config)
    tab = get_tab_state(workspace_id, tab_id)
    if tab is None:
        return _NO_SESSION_ERROR

    applied: list[str] = []
    try:
        if viewport_width is not None and viewport_height is not None:
            await tab.page.set_viewport_size(
                {"width": viewport_width, "height": viewport_height}
            )
            applied.append("viewport")

        if device_scale_factor is not None:
            await tab.cdp.send(
                "Emulation.setDeviceMetricsOverride",
                {
                    "width": viewport_width or 0,
                    "height": viewport_height or 0,
                    "deviceScaleFactor": device_scale_factor,
                    "mobile": False,
                },
            )
            applied.append("device_scale_factor")

        if cpu_throttle is not None:
            await tab.cdp.send("Emulation.setCPUThrottlingRate", {"rate": cpu_throttle})
            applied.append("cpu_throttle")

        if network_throttle is not None:
            await tab.cdp.send(
                "Network.emulateNetworkConditions", _NETWORK_PROFILES[network_throttle]
            )
            applied.append("network_throttle")

        return json.dumps({"status": "ok", "applied": applied})
    except KeyError:
        return json.dumps(
            {
                "status": "error",
                "error": (
                    f"network_throttle {network_throttle!r} inválido — use "
                    f"{sorted(_NETWORK_PROFILES)}"
                ),
            }
        )
    except Exception as exc:
        logger.exception("browser_emulate failed")
        return json.dumps({"status": "error", "error": str(exc)})


#: Buffers de trace/heap em voo, chaveados por `id(TabState)` — não fica no
#: TabState em si porque é um estado transitório de uma chamada de tool,
#: não algo que a aba carrega durante toda sua vida (diferente de
#: console_log/network_log).
_trace_buffers: dict[int, list[dict[str, Any]]] = {}


def _artifacts_dir(workspace_id: str) -> Path | None:
    """Diretório `.vectora/browser-artifacts/` do workspace, criado sob
    demanda. `None` se o workspace não existir/não tiver `cwd` — quem chama
    trata como "sem onde persistir" sem lançar."""
    try:
        from backend.workspace.workspace import workspace_registry

        ws = workspace_registry.get(workspace_id)
        cwd = getattr(ws, "cwd", None)
        if not cwd:
            return None
        d = Path(cwd) / ".vectora" / "browser-artifacts"
        d.mkdir(parents=True, exist_ok=True)
        return d
    except Exception:
        logger.debug(
            "browser_devtools: falha ao resolver artifacts_dir de %s", workspace_id
        )
        return None


@tool(
    extras={
        "render_hint": "json",
        "category": "browser",
        "destructive": False,
        "icon": "activity",
    }
)
async def browser_start_trace(
    tab_id: str | None = None,
    config: Annotated[RunnableConfig, InjectedToolArg] = None,  # ty: ignore[invalid-parameter-default]
) -> str:
    """Inicia a captura de um trace de performance (CDP Tracing) na aba —
    use antes de disparar a interação que você quer medir, depois chame
    `browser_stop_trace` pra encerrar e obter o resumo.

    Args:
        tab_id: id da aba (padrão: aba ativa).
    """
    workspace_id = _workspace_id(config)
    tab = get_tab_state(workspace_id, tab_id)
    if tab is None:
        return _NO_SESSION_ERROR

    key = id(tab)
    if key in _trace_buffers:
        return json.dumps(
            {"status": "error", "error": "já existe um trace em andamento nesta aba"}
        )

    events: list[dict[str, Any]] = []
    _trace_buffers[key] = events

    def _on_data(params: dict[str, Any]) -> None:
        events.extend(params.get("value", []))

    try:
        tab.cdp.on("Tracing.dataCollected", _on_data)
        await tab.cdp.send(
            "Tracing.start",
            {
                "categories": "devtools.timeline,disabled-by-default-devtools.timeline",
                "transferMode": "ReportEvents",
            },
        )
        return json.dumps({"status": "ok"})
    except Exception as exc:
        _trace_buffers.pop(key, None)
        logger.exception("browser_start_trace failed")
        return json.dumps({"status": "error", "error": str(exc)})


@tool(
    extras={
        "render_hint": "json",
        "category": "browser",
        "destructive": False,
        "icon": "activity",
    }
)
async def browser_stop_trace(
    tab_id: str | None = None,
    config: Annotated[RunnableConfig, InjectedToolArg] = None,  # ty: ignore[invalid-parameter-default]
) -> str:
    """Encerra a captura de trace iniciada por `browser_start_trace` e
    devolve um resumo (contagem de eventos por categoria) + o caminho do
    artifact com os eventos brutos.

    Args:
        tab_id: id da aba (padrão: aba ativa).
    """
    workspace_id = _workspace_id(config)
    tab = get_tab_state(workspace_id, tab_id)
    if tab is None:
        return _NO_SESSION_ERROR

    key = id(tab)
    if key not in _trace_buffers:
        return json.dumps(
            {"status": "error", "error": "nenhum trace em andamento nesta aba"}
        )

    try:
        done = asyncio.Event()

        def _on_complete(_params: dict[str, Any]) -> None:
            done.set()

        tab.cdp.on("Tracing.tracingComplete", _on_complete)
        await tab.cdp.send("Tracing.end")
        try:
            await asyncio.wait_for(done.wait(), timeout=10)
        except TimeoutError:
            logger.debug("browser_stop_trace: timeout esperando tracingComplete")

        events = _trace_buffers.pop(key, [])
        categories: dict[str, int] = {}
        for ev in events:
            cat = ev.get("cat", "unknown")
            categories[cat] = categories.get(cat, 0) + 1

        artifact_path = None
        artifacts_dir = _artifacts_dir(workspace_id)
        if artifacts_dir is not None:
            path = artifacts_dir / f"trace-{uuid.uuid4().hex[:8]}.json"
            path.write_text(json.dumps(events), encoding="utf-8")
            artifact_path = str(path)

        return json.dumps(
            {
                "status": "ok",
                "summary": {"event_count": len(events), "categories": categories},
                "artifact_path": artifact_path,
            }
        )
    except Exception as exc:
        _trace_buffers.pop(key, None)
        logger.exception("browser_stop_trace failed")
        return json.dumps({"status": "error", "error": str(exc)})


async def _take_heap_snapshot_via_cdp(cdp: Any) -> dict[str, Any]:
    """`HeapProfiler.takeHeapSnapshot` chega em chunks de string via evento
    (`HeapProfiler.addHeapSnapshotChunk`), concatenados aqui e parseados
    como o JSON único do formato de heap snapshot do V8."""
    chunks: list[str] = []

    def _on_chunk(params: dict[str, Any]) -> None:
        chunks.append(params.get("chunk", ""))

    cdp.on("HeapProfiler.addHeapSnapshotChunk", _on_chunk)
    await cdp.send("HeapProfiler.takeHeapSnapshot", {"reportProgress": False})
    return json.loads("".join(chunks))


def _summarize_heap_snapshot(
    data: dict[str, Any], top_n: int = 15
) -> list[dict[str, Any]]:
    """Agrega os nós do heap snapshot por (tipo, nome) — soma de
    `self_size` e contagem. Não é um analisador de grafo de retenção
    completo (sem cálculo de retained size via arestas), só um resumo
    suficiente pra apontar onde a memória está concentrada."""
    meta = data["snapshot"]["meta"]
    node_fields: list[str] = meta["node_fields"]
    node_types: list[Any] = meta["node_types"]
    strings: list[str] = data["strings"]
    nodes: list[int] = data["nodes"]

    fields_per_node = len(node_fields)
    type_idx = node_fields.index("type")
    name_idx = node_fields.index("name")
    size_idx = node_fields.index("self_size")
    type_names = node_types[type_idx] if isinstance(node_types[type_idx], list) else []

    totals: dict[str, int] = {}
    counts: dict[str, int] = {}
    for i in range(0, len(nodes) - fields_per_node + 1, fields_per_node):
        type_i = nodes[i + type_idx]
        name_i = nodes[i + name_idx]
        self_size = nodes[i + size_idx]
        type_name = type_names[type_i] if 0 <= type_i < len(type_names) else "unknown"
        name = strings[name_i] if 0 <= name_i < len(strings) else "?"
        key = f"{type_name}:{name}" if type_name == "object" else type_name
        totals[key] = totals.get(key, 0) + self_size
        counts[key] = counts.get(key, 0) + 1

    top = sorted(totals.items(), key=lambda kv: kv[1], reverse=True)[:top_n]
    return [
        {"constructor": key, "total_size": size, "count": counts[key]}
        for key, size in top
    ]


@tool(
    extras={
        "render_hint": "json",
        "category": "browser",
        "destructive": False,
        "icon": "database",
    }
)
async def browser_take_heap_snapshot(
    tab_id: str | None = None,
    config: Annotated[RunnableConfig, InjectedToolArg] = None,  # ty: ignore[invalid-parameter-default]
) -> str:
    """Tira um heap snapshot (CDP HeapProfiler) da aba e devolve um resumo
    dos construtores que mais ocupam memória. O snapshot bruto (formato V8)
    é persistido como artifact pra inspeção mais profunda se necessário.

    Args:
        tab_id: id da aba (padrão: aba ativa).
    """
    workspace_id = _workspace_id(config)
    tab = get_tab_state(workspace_id, tab_id)
    if tab is None:
        return _NO_SESSION_ERROR

    try:
        data = await _take_heap_snapshot_via_cdp(tab.cdp)
        top = _summarize_heap_snapshot(data)

        artifact_path = None
        artifacts_dir = _artifacts_dir(workspace_id)
        if artifacts_dir is not None:
            path = artifacts_dir / f"heap-{uuid.uuid4().hex[:8]}.json"
            path.write_text(json.dumps(data), encoding="utf-8")
            artifact_path = str(path)

        return json.dumps(
            {
                "status": "ok",
                "top_constructors": top,
                "artifact_path": artifact_path,
            }
        )
    except Exception as exc:
        logger.exception("browser_take_heap_snapshot failed")
        return json.dumps({"status": "error", "error": str(exc)})


@tool(
    extras={
        "render_hint": "json",
        "category": "browser",
        "destructive": False,
        "icon": "gauge",
    }
)
async def browser_lighthouse_audit(
    url: str | None = None,
    tab_id: str | None = None,
    config: Annotated[RunnableConfig, InjectedToolArg] = None,  # ty: ignore[invalid-parameter-default]
) -> str:
    """Roda um audit Lighthouse (performance/acessibilidade/best-practices/
    SEO) — via `npx lighthouse`, único ponto desta suíte que depende de
    Node instalado no sistema. Degrada com erro claro se Node/npx não
    estiverem disponíveis, sem quebrar as demais tools de browser.

    Args:
        url: URL a auditar (padrão: URL atual da aba).
        tab_id: id da aba usada só pra resolver a URL padrão.
    """
    workspace_id = _workspace_id(config)
    target_url = url
    if target_url is None:
        tab = get_tab_state(workspace_id, tab_id)
        if tab is None:
            return _NO_SESSION_ERROR
        target_url = tab.page.url

    try:
        proc = await asyncio.create_subprocess_exec(
            "npx",
            "lighthouse",
            target_url,
            "--output=json",
            "--quiet",
            "--chrome-flags=--headless",
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
        stdout, stderr = await proc.communicate()
    except FileNotFoundError:
        return json.dumps(
            {
                "status": "error",
                "error": (
                    "Lighthouse requer Node/npx instalado no sistema — não encontrado."
                ),
            }
        )
    except Exception as exc:
        logger.exception("browser_lighthouse_audit failed to spawn")
        return json.dumps({"status": "error", "error": str(exc)})

    if proc.returncode != 0:
        return json.dumps(
            {
                "status": "error",
                "error": (
                    f"lighthouse saiu com código {proc.returncode}: "
                    f"{stderr.decode(errors='replace')[:500]}"
                ),
            }
        )

    try:
        report = json.loads(stdout)
    except Exception as exc:
        return json.dumps(
            {
                "status": "error",
                "error": f"saída do lighthouse não é JSON válido: {exc}",
            }
        )

    categories = report.get("categories", {})
    scores = {
        name: (cat.get("score") if cat else None) for name, cat in categories.items()
    }
    audits = report.get("audits", {})
    opportunities = sorted(
        (
            a
            for a in audits.values()
            if a.get("details", {}).get("type") == "opportunity"
        ),
        key=lambda a: a.get("numericValue") or 0,
        reverse=True,
    )[:5]
    top_opportunities = [
        {
            "id": o.get("id"),
            "title": o.get("title"),
            "savings_ms": o.get("numericValue"),
        }
        for o in opportunities
    ]

    return json.dumps(
        {"status": "ok", "scores": scores, "top_opportunities": top_opportunities}
    )
