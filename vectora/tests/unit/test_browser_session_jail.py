"""Perfil de browser isolado por workspace com `[sandbox]` habilitado."""

from __future__ import annotations

from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock

import pytest

from backend.browser import session as browser_session


@pytest.fixture(autouse=True)
async def _clean_sessions():
    await browser_session.close_all_browser_sessions()
    yield
    await browser_session.close_all_browser_sessions()


def test_jailed_profile_dir_ausente_sem_sandbox(tmp_path, monkeypatch):
    ws = SimpleNamespace(cwd=str(tmp_path))
    monkeypatch.setattr(
        "backend.workspace.workspace.workspace_registry",
        SimpleNamespace(get=lambda _id: ws),
    )
    (tmp_path / "vectora.toml").write_text("[workspace]\nname = 'x'\n")

    assert browser_session._jailed_profile_dir("ws-1") is None


def test_jailed_profile_dir_criado_quando_sandbox_habilitado(tmp_path, monkeypatch):
    ws = SimpleNamespace(cwd=str(tmp_path))
    monkeypatch.setattr(
        "backend.workspace.workspace.workspace_registry",
        SimpleNamespace(get=lambda _id: ws),
    )
    (tmp_path / "vectora.toml").write_text("[sandbox]\nenabled = true\n")

    profile_dir = browser_session._jailed_profile_dir("ws-1")

    assert profile_dir is not None
    assert profile_dir.is_dir()
    assert profile_dir.name == "ws-1"


def test_jailed_profile_dir_workspace_inexistente_retorna_none():
    assert browser_session._jailed_profile_dir("") is None


def test_jailed_profile_dir_erro_ao_resolver_workspace_nao_lanca(monkeypatch):
    def _boom(_id: str):
        raise RuntimeError("registry indisponível")

    monkeypatch.setattr(
        "backend.workspace.workspace.workspace_registry",
        SimpleNamespace(get=_boom),
    )

    assert browser_session._jailed_profile_dir("ws-1") is None


@pytest.mark.asyncio
async def test_get_browser_page_usa_launch_persistent_context_quando_jailado(
    tmp_path, monkeypatch
):
    ws = SimpleNamespace(cwd=str(tmp_path))
    monkeypatch.setattr(
        "backend.workspace.workspace.workspace_registry",
        SimpleNamespace(get=lambda _id: ws),
    )
    (tmp_path / "vectora.toml").write_text("[sandbox]\nenabled = true\n")

    fake_page = MagicMock()
    fake_page.on = MagicMock()
    fake_page.context = SimpleNamespace(
        new_cdp_session=AsyncMock(return_value=MagicMock())
    )
    fake_context = SimpleNamespace(pages=[fake_page], close=AsyncMock())
    fake_playwright = SimpleNamespace(
        chromium=SimpleNamespace(
            launch_persistent_context=AsyncMock(return_value=fake_context),
            launch=AsyncMock(side_effect=AssertionError("não deveria lançar efêmero")),
        )
    )
    monkeypatch.setattr(
        "playwright.async_api.async_playwright",
        lambda: SimpleNamespace(start=AsyncMock(return_value=fake_playwright)),
    )

    page = await browser_session.get_browser_page("ws-jailed")

    assert page is fake_page
    fake_playwright.chromium.launch_persistent_context.assert_awaited_once()
    call_args = fake_playwright.chromium.launch_persistent_context.await_args
    assert call_args.args[0].endswith("ws-jailed")


@pytest.mark.asyncio
async def test_get_browser_page_usa_launch_efemero_sem_sandbox(monkeypatch):
    monkeypatch.setattr("backend.browser.session._jailed_profile_dir", lambda _id: None)

    fake_page = MagicMock()
    fake_page.on = MagicMock()
    fake_page.context = SimpleNamespace(
        new_cdp_session=AsyncMock(return_value=MagicMock())
    )
    fake_browser = SimpleNamespace(
        new_page=AsyncMock(return_value=fake_page), close=AsyncMock()
    )
    fake_playwright = SimpleNamespace(
        chromium=SimpleNamespace(launch=AsyncMock(return_value=fake_browser))
    )
    monkeypatch.setattr(
        "playwright.async_api.async_playwright",
        lambda: SimpleNamespace(start=AsyncMock(return_value=fake_playwright)),
    )

    page = await browser_session.get_browser_page("ws-normal")

    assert page is fake_page
    fake_playwright.chromium.launch.assert_awaited_once()
