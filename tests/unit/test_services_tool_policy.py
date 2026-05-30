"""Tests para vectora/services/tool_policy.py — política de tools por usuário (S5).

Allow-all por padrão; admin/self podem desabilitar tools por usuário. Persistido
por arquivo, isolado entre usuários. Diretório base redirecionado para tmp_path.
"""

from __future__ import annotations

import pytest

from vectora.services import tool_policy


@pytest.fixture(autouse=True)
def iso_dir(tmp_path, monkeypatch):
    monkeypatch.setattr(tool_policy, "_policy_dir", lambda: tmp_path / "tools")


def test_allow_all_by_default():
    assert tool_policy.is_allowed("u1", "terminal") is True
    assert tool_policy.get_disabled("u1") == []


def test_disable_tool():
    tool_policy.set_disabled("u1", ["terminal"])
    assert tool_policy.is_allowed("u1", "terminal") is False
    assert tool_policy.is_allowed("u1", "file_read") is True


def test_get_disabled_returns_list():
    tool_policy.set_disabled("u1", ["terminal", "file_write"])
    assert set(tool_policy.get_disabled("u1")) == {"terminal", "file_write"}


def test_reenable_by_setting_empty():
    tool_policy.set_disabled("u1", ["terminal"])
    tool_policy.set_disabled("u1", [])
    assert tool_policy.is_allowed("u1", "terminal") is True


def test_users_isolated():
    tool_policy.set_disabled("a", ["terminal"])
    assert tool_policy.is_allowed("a", "terminal") is False
    assert tool_policy.is_allowed("b", "terminal") is True


def test_persists_across_reads():
    tool_policy.set_disabled("u1", ["grep"])
    # Releitura vai ao disco
    assert tool_policy.get_disabled("u1") == ["grep"]
