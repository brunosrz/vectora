"""Tools de observabilidade/controle avançado do browser (multi-aba,
console/network log) — mocka backend.browser.session (unit, sem depender de
Chromium instalado; a camada de sessão já é testada contra Chromium real em
test_browser_session_real.py)."""

from __future__ import annotations

import json
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest
from langchain_core.runnables import RunnableConfig

from backend.tools import browser_devtools as bd


def _config(workspace_id: str = "ws1") -> RunnableConfig:
    return RunnableConfig(configurable={"workspace_id": workspace_id})


# ---------------------------------------------------------------------------
# browser_list_tabs / browser_new_tab / browser_close_tab / browser_select_tab
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_browser_list_tabs_retorna_abas_da_sessao(monkeypatch):
    monkeypatch.setattr(
        bd,
        "list_tabs",
        AsyncMock(
            return_value=[
                {"tab_id": "t1", "url": "https://a.test", "active": True},
                {"tab_id": "t2", "url": "https://b.test", "active": False},
            ]
        ),
    )

    result = json.loads(await bd.browser_list_tabs.ainvoke({}, config=_config()))

    assert len(result["tabs"]) == 2
    assert result["tabs"][0]["active"] is True


@pytest.mark.asyncio
async def test_browser_new_tab_cria_aba_e_retorna_id(monkeypatch):
    monkeypatch.setattr(bd, "new_tab", AsyncMock(return_value="tab-abc"))

    result = json.loads(
        await bd.browser_new_tab.ainvoke(
            {"url": "https://example.com"}, config=_config()
        )
    )

    assert result == {"status": "ok", "tab_id": "tab-abc"}


@pytest.mark.asyncio
async def test_browser_new_tab_falha_devolve_erro_tipado(monkeypatch):
    monkeypatch.setattr(
        bd, "new_tab", AsyncMock(side_effect=RuntimeError("chromium crashed"))
    )

    result = json.loads(await bd.browser_new_tab.ainvoke({}, config=_config()))

    assert result["status"] == "error"


@pytest.mark.asyncio
async def test_browser_close_tab_sem_sessao_retorna_erro(monkeypatch):
    monkeypatch.setattr(bd, "has_browser_session", lambda _wid: False)

    result = json.loads(
        await bd.browser_close_tab.ainvoke({"tab_id": "t1"}, config=_config())
    )

    assert result["status"] == "error"


@pytest.mark.asyncio
async def test_browser_close_tab_id_inexistente_retorna_erro(monkeypatch):
    monkeypatch.setattr(bd, "has_browser_session", lambda _wid: True)
    monkeypatch.setattr(bd, "close_tab", AsyncMock(return_value=False))

    result = json.loads(
        await bd.browser_close_tab.ainvoke({"tab_id": "nao-existe"}, config=_config())
    )

    assert result["status"] == "error"


@pytest.mark.asyncio
async def test_browser_close_tab_sucesso(monkeypatch):
    monkeypatch.setattr(bd, "has_browser_session", lambda _wid: True)
    monkeypatch.setattr(bd, "close_tab", AsyncMock(return_value=True))

    result = json.loads(
        await bd.browser_close_tab.ainvoke({"tab_id": "t1"}, config=_config())
    )

    assert result == {"status": "ok", "tab_id": "t1"}


@pytest.mark.asyncio
async def test_browser_select_tab_troca_aba_ativa(monkeypatch):
    monkeypatch.setattr(bd, "has_browser_session", lambda _wid: True)
    monkeypatch.setattr(bd, "select_tab", AsyncMock(return_value=True))

    result = json.loads(
        await bd.browser_select_tab.ainvoke({"tab_id": "t2"}, config=_config())
    )

    assert result == {"status": "ok", "tab_id": "t2"}


@pytest.mark.asyncio
async def test_browser_select_tab_inexistente_retorna_erro(monkeypatch):
    monkeypatch.setattr(bd, "has_browser_session", lambda _wid: True)
    monkeypatch.setattr(bd, "select_tab", AsyncMock(return_value=False))

    result = json.loads(
        await bd.browser_select_tab.ainvoke({"tab_id": "nao-existe"}, config=_config())
    )

    assert result["status"] == "error"


# ---------------------------------------------------------------------------
# browser_list_console_messages / browser_clear_console
# ---------------------------------------------------------------------------


def _fake_tab(console=None, network=None):
    return SimpleNamespace(
        console_log=list(console or []),
        network_log=list(network or []),
    )


@pytest.mark.asyncio
async def test_browser_list_console_messages_respeita_limit(monkeypatch):
    messages = [{"type": "log", "text": f"msg {i}"} for i in range(5)]
    monkeypatch.setattr(bd, "get_tab_state", lambda _wid, _tid: _fake_tab(messages))

    result = json.loads(
        await bd.browser_list_console_messages.ainvoke({"limit": 2}, config=_config())
    )

    assert len(result["messages"]) == 2
    assert result["messages"][-1]["text"] == "msg 4"


@pytest.mark.asyncio
async def test_browser_list_console_messages_sem_sessao_retorna_erro(monkeypatch):
    monkeypatch.setattr(bd, "get_tab_state", lambda _wid, _tid: None)

    result = json.loads(
        await bd.browser_list_console_messages.ainvoke({}, config=_config())
    )

    assert result["status"] == "error"


@pytest.mark.asyncio
async def test_browser_clear_console_limpa_buffer(monkeypatch):
    tab = _fake_tab(console=[{"type": "log", "text": "x"}])
    monkeypatch.setattr(bd, "get_tab_state", lambda _wid, _tid: tab)

    result = json.loads(await bd.browser_clear_console.ainvoke({}, config=_config()))

    assert result == {"status": "ok"}
    assert tab.console_log == []


# ---------------------------------------------------------------------------
# browser_list_network_requests / browser_get_network_request
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_browser_list_network_requests_filtra_por_resource_type(monkeypatch):
    entries = [
        {"request_id": "r1", "url": "https://a", "resource_type": "document"},
        {"request_id": "r2", "url": "https://b", "resource_type": "xhr"},
    ]
    monkeypatch.setattr(
        bd, "get_tab_state", lambda _wid, _tid: _fake_tab(network=entries)
    )

    result = json.loads(
        await bd.browser_list_network_requests.ainvoke(
            {"resource_type": "xhr"}, config=_config()
        )
    )

    assert len(result["requests"]) == 1
    assert result["requests"][0]["request_id"] == "r2"


@pytest.mark.asyncio
async def test_browser_list_network_requests_sem_filtro_lista_todas(monkeypatch):
    entries = [
        {"request_id": "r1", "url": "https://a", "resource_type": "document"},
        {"request_id": "r2", "url": "https://b", "resource_type": "xhr"},
    ]
    monkeypatch.setattr(
        bd, "get_tab_state", lambda _wid, _tid: _fake_tab(network=entries)
    )

    result = json.loads(
        await bd.browser_list_network_requests.ainvoke({}, config=_config())
    )

    assert len(result["requests"]) == 2


@pytest.mark.asyncio
async def test_browser_get_network_request_encontrada(monkeypatch):
    entries = [{"request_id": "r1", "url": "https://a", "status": 200}]
    monkeypatch.setattr(
        bd, "get_tab_state", lambda _wid, _tid: _fake_tab(network=entries)
    )

    result = json.loads(
        await bd.browser_get_network_request.ainvoke(
            {"request_id": "r1"}, config=_config()
        )
    )

    assert result == entries[0]


@pytest.mark.asyncio
async def test_browser_get_network_request_nao_encontrada_retorna_erro(monkeypatch):
    monkeypatch.setattr(bd, "get_tab_state", lambda _wid, _tid: _fake_tab(network=[]))

    result = json.loads(
        await bd.browser_get_network_request.ainvoke(
            {"request_id": "nao-existe"}, config=_config()
        )
    )

    assert result["status"] == "error"


# ---------------------------------------------------------------------------
# browser_evaluate
# ---------------------------------------------------------------------------


def _fake_tab_with_page(evaluate_result=None, evaluate_error=None):
    async def _evaluate(script):
        if evaluate_error is not None:
            raise evaluate_error
        return evaluate_result

    page = SimpleNamespace(evaluate=_evaluate)
    return SimpleNamespace(page=page)


@pytest.mark.asyncio
async def test_browser_evaluate_retorna_resultado_serializado(monkeypatch):
    monkeypatch.setattr(
        bd, "get_tab_state", lambda _wid, _tid: _fake_tab_with_page(evaluate_result=42)
    )

    result = json.loads(
        await bd.browser_evaluate.ainvoke({"script": "1 + 41"}, config=_config())
    )

    assert result == {"status": "ok", "result": 42}


@pytest.mark.asyncio
async def test_browser_evaluate_sem_sessao_retorna_erro(monkeypatch):
    monkeypatch.setattr(bd, "get_tab_state", lambda _wid, _tid: None)

    result = json.loads(
        await bd.browser_evaluate.ainvoke({"script": "1"}, config=_config())
    )

    assert result["status"] == "error"


@pytest.mark.asyncio
async def test_browser_evaluate_erro_de_script_nao_propaga(monkeypatch):
    monkeypatch.setattr(
        bd,
        "get_tab_state",
        lambda _wid, _tid: _fake_tab_with_page(
            evaluate_error=RuntimeError("SyntaxError: unexpected token")
        ),
    )

    result = json.loads(
        await bd.browser_evaluate.ainvoke({"script": "{{{"}, config=_config())
    )

    assert result["status"] == "error"


# ---------------------------------------------------------------------------
# browser_set_dialog_policy
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_browser_set_dialog_policy_action_invalida_retorna_erro():
    result = json.loads(
        await bd.browser_set_dialog_policy.ainvoke(
            {"action": "close"}, config=_config()
        )
    )

    assert result["status"] == "error"


@pytest.mark.asyncio
async def test_browser_set_dialog_policy_sem_sessao_retorna_erro(monkeypatch):
    monkeypatch.setattr(bd, "set_dialog_policy", lambda *a, **k: False)

    result = json.loads(
        await bd.browser_set_dialog_policy.ainvoke(
            {"action": "accept"}, config=_config()
        )
    )

    assert result["status"] == "error"


@pytest.mark.asyncio
async def test_browser_set_dialog_policy_sucesso(monkeypatch):
    calls = []
    monkeypatch.setattr(
        bd,
        "set_dialog_policy",
        lambda wid, action, prompt_text=None, tab_id=None: (
            calls.append((wid, action, prompt_text, tab_id)) or True
        ),
    )

    result = json.loads(
        await bd.browser_set_dialog_policy.ainvoke(
            {"action": "accept", "prompt_text": "ok"}, config=_config()
        )
    )

    assert result == {"status": "ok"}
    assert calls == [("ws1", "accept", "ok", None)]


# ---------------------------------------------------------------------------
# browser_emulate
# ---------------------------------------------------------------------------


def _fake_tab_for_emulate():
    page = SimpleNamespace(set_viewport_size=AsyncMock())
    cdp = SimpleNamespace(send=AsyncMock())
    return SimpleNamespace(page=page, cdp=cdp)


@pytest.mark.asyncio
async def test_browser_emulate_sem_sessao_retorna_erro(monkeypatch):
    monkeypatch.setattr(bd, "get_tab_state", lambda _wid, _tid: None)

    result = json.loads(
        await bd.browser_emulate.ainvoke(
            {"viewport_width": 375, "viewport_height": 812}, config=_config()
        )
    )

    assert result["status"] == "error"


@pytest.mark.asyncio
async def test_browser_emulate_aplica_viewport(monkeypatch):
    tab = _fake_tab_for_emulate()
    monkeypatch.setattr(bd, "get_tab_state", lambda _wid, _tid: tab)

    result = json.loads(
        await bd.browser_emulate.ainvoke(
            {"viewport_width": 375, "viewport_height": 812}, config=_config()
        )
    )

    assert result == {"status": "ok", "applied": ["viewport"]}
    tab.page.set_viewport_size.assert_awaited_once_with({"width": 375, "height": 812})


@pytest.mark.asyncio
async def test_browser_emulate_aplica_cpu_throttle_via_cdp(monkeypatch):
    tab = _fake_tab_for_emulate()
    monkeypatch.setattr(bd, "get_tab_state", lambda _wid, _tid: tab)

    result = json.loads(
        await bd.browser_emulate.ainvoke({"cpu_throttle": 4}, config=_config())
    )

    assert result == {"status": "ok", "applied": ["cpu_throttle"]}
    tab.cdp.send.assert_awaited_once_with("Emulation.setCPUThrottlingRate", {"rate": 4})


@pytest.mark.asyncio
async def test_browser_emulate_network_throttle_invalido_retorna_erro(monkeypatch):
    tab = _fake_tab_for_emulate()
    monkeypatch.setattr(bd, "get_tab_state", lambda _wid, _tid: tab)

    result = json.loads(
        await bd.browser_emulate.ainvoke(
            {"network_throttle": "not-a-profile"}, config=_config()
        )
    )

    assert result["status"] == "error"


@pytest.mark.asyncio
async def test_browser_emulate_network_throttle_valido_chama_cdp(monkeypatch):
    tab = _fake_tab_for_emulate()
    monkeypatch.setattr(bd, "get_tab_state", lambda _wid, _tid: tab)

    result = json.loads(
        await bd.browser_emulate.ainvoke(
            {"network_throttle": "slow-3g"}, config=_config()
        )
    )

    assert result == {"status": "ok", "applied": ["network_throttle"]}
    tab.cdp.send.assert_awaited_once()
    assert tab.cdp.send.await_args.args[0] == "Network.emulateNetworkConditions"


@pytest.mark.asyncio
async def test_browser_emulate_sem_parametros_nao_aplica_nada(monkeypatch):
    tab = _fake_tab_for_emulate()
    monkeypatch.setattr(bd, "get_tab_state", lambda _wid, _tid: tab)

    result = json.loads(await bd.browser_emulate.ainvoke({}, config=_config()))

    assert result == {"status": "ok", "applied": []}
    tab.page.set_viewport_size.assert_not_awaited()
    tab.cdp.send.assert_not_awaited()


# ---------------------------------------------------------------------------
# browser_start_trace / browser_stop_trace
# ---------------------------------------------------------------------------


class _FakeCDPForTrace:
    def __init__(self) -> None:
        self._handlers: dict[str, list] = {}

        async def _send(method, params=None):
            if method == "Tracing.end":
                for h in self._handlers.get("Tracing.tracingComplete", []):
                    h({})

        self.send = AsyncMock(side_effect=_send)

    def on(self, event, handler):
        self._handlers.setdefault(event, []).append(handler)

    def emit(self, event, params):
        for h in self._handlers.get(event, []):
            h(params)


def _fake_tab_for_trace():
    return SimpleNamespace(cdp=_FakeCDPForTrace())


@pytest.mark.asyncio
async def test_browser_start_trace_sem_sessao_retorna_erro(monkeypatch):
    monkeypatch.setattr(bd, "get_tab_state", lambda _wid, _tid: None)

    result = json.loads(await bd.browser_start_trace.ainvoke({}, config=_config()))

    assert result["status"] == "error"


@pytest.mark.asyncio
async def test_browser_start_trace_ja_em_andamento_retorna_erro(monkeypatch):
    tab = _fake_tab_for_trace()
    monkeypatch.setattr(bd, "get_tab_state", lambda _wid, _tid: tab)

    first = json.loads(await bd.browser_start_trace.ainvoke({}, config=_config()))
    second = json.loads(await bd.browser_start_trace.ainvoke({}, config=_config()))

    assert first["status"] == "ok"
    assert second["status"] == "error"

    # limpa o estado global pra não vazar entre testes
    await bd.browser_stop_trace.ainvoke({}, config=_config())


@pytest.mark.asyncio
async def test_stop_trace_sem_start_retorna_erro(monkeypatch):
    tab = _fake_tab_for_trace()
    monkeypatch.setattr(bd, "get_tab_state", lambda _wid, _tid: tab)

    result = json.loads(await bd.browser_stop_trace.ainvoke({}, config=_config()))

    assert result["status"] == "error"


@pytest.mark.asyncio
async def test_start_e_stop_trace_resume_eventos_coletados(monkeypatch, tmp_path):
    tab = _fake_tab_for_trace()
    ws = SimpleNamespace(cwd=str(tmp_path))
    monkeypatch.setattr(bd, "get_tab_state", lambda _wid, _tid: tab)
    monkeypatch.setattr(
        "backend.workspace.workspace.workspace_registry",
        SimpleNamespace(get=lambda _id: ws),
    )

    await bd.browser_start_trace.ainvoke({}, config=_config())
    tab.cdp.emit(
        "Tracing.dataCollected",
        {"value": [{"cat": "toplevel", "name": "a"}, {"cat": "toplevel", "name": "b"}]},
    )

    result = json.loads(await bd.browser_stop_trace.ainvoke({}, config=_config()))

    assert result["status"] == "ok"
    assert result["summary"]["event_count"] == 2
    assert result["summary"]["categories"] == {"toplevel": 2}
    assert result["artifact_path"] is not None
    assert Path(result["artifact_path"]).exists()


# ---------------------------------------------------------------------------
# browser_take_heap_snapshot
# ---------------------------------------------------------------------------


def _sample_heap_snapshot() -> dict:
    return {
        "snapshot": {
            "meta": {
                "node_fields": [
                    "type",
                    "name",
                    "id",
                    "self_size",
                    "edge_count",
                    "trace_node_id",
                    "detachedness",
                ],
                "node_types": [
                    [
                        "hidden",
                        "array",
                        "string",
                        "object",
                        "code",
                        "closure",
                        "regexp",
                        "number",
                        "native",
                        "synthetic",
                        "concatenated string",
                        "sliced string",
                        "symbol",
                        "bigint",
                    ],
                    "string",
                    "number",
                    "number",
                    "number",
                    "number",
                    "number",
                ],
            }
        },
        "nodes": [3, 0, 1, 100, 0, 0, 0, 3, 1, 2, 50, 0, 0, 0],
        "edges": [],
        "strings": ["Foo", "Bar"],
    }


def _fake_tab_for_heap(snapshot: dict):
    cdp = SimpleNamespace()
    payload = json.dumps(snapshot)

    async def _send(method, params=None):
        if method == "HeapProfiler.takeHeapSnapshot":
            for h in cdp._handlers.get("HeapProfiler.addHeapSnapshotChunk", []):
                h({"chunk": payload})

    cdp._handlers = {}
    cdp.on = lambda event, handler: cdp._handlers.setdefault(event, []).append(handler)
    cdp.send = AsyncMock(side_effect=_send)
    return SimpleNamespace(cdp=cdp)


@pytest.mark.asyncio
async def test_browser_take_heap_snapshot_sem_sessao_retorna_erro(monkeypatch):
    monkeypatch.setattr(bd, "get_tab_state", lambda _wid, _tid: None)

    result = json.loads(
        await bd.browser_take_heap_snapshot.ainvoke({}, config=_config())
    )

    assert result["status"] == "error"


@pytest.mark.asyncio
async def test_browser_take_heap_snapshot_resume_top_construtores(
    monkeypatch, tmp_path
):
    tab = _fake_tab_for_heap(_sample_heap_snapshot())
    ws = SimpleNamespace(cwd=str(tmp_path))
    monkeypatch.setattr(bd, "get_tab_state", lambda _wid, _tid: tab)
    monkeypatch.setattr(
        "backend.workspace.workspace.workspace_registry",
        SimpleNamespace(get=lambda _id: ws),
    )

    result = json.loads(
        await bd.browser_take_heap_snapshot.ainvoke({}, config=_config())
    )

    assert result["status"] == "ok"
    top = {c["constructor"]: c for c in result["top_constructors"]}
    assert top["object:Foo"]["total_size"] == 100
    assert top["object:Bar"]["total_size"] == 50
    assert result["artifact_path"] is not None


# ---------------------------------------------------------------------------
# browser_lighthouse_audit
# ---------------------------------------------------------------------------


class _FakeLighthouseProc:
    def __init__(self, stdout: bytes, stderr: bytes = b"", returncode: int = 0) -> None:
        self._stdout = stdout
        self._stderr = stderr
        self.returncode = returncode

    async def communicate(self):
        return self._stdout, self._stderr


@pytest.mark.asyncio
async def test_browser_lighthouse_audit_npx_ausente_retorna_erro_tipado(monkeypatch):
    monkeypatch.setattr(
        bd.asyncio,
        "create_subprocess_exec",
        AsyncMock(side_effect=FileNotFoundError()),
    )

    result = json.loads(
        await bd.browser_lighthouse_audit.ainvoke(
            {"url": "http://localhost:3000"}, config=_config()
        )
    )

    assert result["status"] == "error"
    assert "node" in result["error"].lower() or "npx" in result["error"].lower()


@pytest.mark.asyncio
async def test_browser_lighthouse_audit_parseia_scores_e_oportunidades(monkeypatch):
    report = {
        "categories": {
            "performance": {"score": 0.8},
            "accessibility": {"score": 0.9},
        },
        "audits": {
            "render-blocking-resources": {
                "id": "render-blocking-resources",
                "title": "Eliminate render-blocking resources",
                "numericValue": 300,
                "details": {"type": "opportunity"},
            },
            "not-an-opportunity": {
                "id": "not-an-opportunity",
                "title": "x",
                "details": {"type": "table"},
            },
        },
    }
    monkeypatch.setattr(
        bd.asyncio,
        "create_subprocess_exec",
        AsyncMock(return_value=_FakeLighthouseProc(json.dumps(report).encode("utf-8"))),
    )

    result = json.loads(
        await bd.browser_lighthouse_audit.ainvoke(
            {"url": "http://localhost:3000"}, config=_config()
        )
    )

    assert result["status"] == "ok"
    assert result["scores"]["performance"] == 0.8
    assert len(result["top_opportunities"]) == 1
    assert result["top_opportunities"][0]["id"] == "render-blocking-resources"


@pytest.mark.asyncio
async def test_browser_lighthouse_audit_exit_code_nao_zero_retorna_erro(monkeypatch):
    monkeypatch.setattr(
        bd.asyncio,
        "create_subprocess_exec",
        AsyncMock(
            return_value=_FakeLighthouseProc(b"", b"chrome not found", returncode=1)
        ),
    )

    result = json.loads(
        await bd.browser_lighthouse_audit.ainvoke(
            {"url": "http://localhost:3000"}, config=_config()
        )
    )

    assert result["status"] == "error"


@pytest.mark.asyncio
async def test_browser_lighthouse_audit_sem_url_usa_url_da_aba_ativa(monkeypatch):
    tab = SimpleNamespace(page=SimpleNamespace(url="http://localhost:9999"))
    monkeypatch.setattr(bd, "get_tab_state", lambda _wid, _tid: tab)

    captured = {}

    async def _fake_exec(*args, **kwargs):
        captured["args"] = args
        return _FakeLighthouseProc(
            json.dumps({"categories": {}, "audits": {}}).encode()
        )

    monkeypatch.setattr(bd.asyncio, "create_subprocess_exec", _fake_exec)

    result = json.loads(await bd.browser_lighthouse_audit.ainvoke({}, config=_config()))

    assert result["status"] == "ok"
    assert "http://localhost:9999" in captured["args"]


@pytest.mark.asyncio
async def test_browser_lighthouse_audit_sem_url_e_sem_sessao_retorna_erro(monkeypatch):
    monkeypatch.setattr(bd, "get_tab_state", lambda _wid, _tid: None)

    result = json.loads(await bd.browser_lighthouse_audit.ainvoke({}, config=_config()))

    assert result["status"] == "error"
