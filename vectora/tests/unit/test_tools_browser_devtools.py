"""Tools de observabilidade/controle avançado do browser (multi-aba,
console/network log) — mocka backend.browser.session (unit, sem depender de
Chromium instalado; a camada de sessão já é testada contra Chromium real em
test_browser_session_real.py)."""

from __future__ import annotations

import json
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
