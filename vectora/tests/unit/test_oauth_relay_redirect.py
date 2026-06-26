"""TDD — OAuth redirect_uri via relay quando token disponível."""

from __future__ import annotations

import os
from pathlib import Path
from unittest.mock import patch

import pytest


@pytest.fixture
def relay_token_file(tmp_path: Path) -> Path:
    return tmp_path / "relay_token"


class TestRelayRedirectUri:
    def test_usa_relay_quando_token_existe(self, relay_token_file: Path) -> None:
        relay_token_file.write_text("abc123")
        from backend.api.handlers.oauth import _relay_callback_url

        url = _relay_callback_url("github", token_path=relay_token_file)
        assert url == "https://abc123.vectora.chat/auth/github/callback"

    def test_retorna_none_sem_token(self, relay_token_file: Path) -> None:
        from backend.api.handlers.oauth import _relay_callback_url

        url = _relay_callback_url("github", token_path=relay_token_file)
        assert url is None

    def test_funciona_com_qualquer_provider(self, relay_token_file: Path) -> None:
        relay_token_file.write_text("xyz789")
        from backend.api.handlers.oauth import _relay_callback_url

        assert _relay_callback_url("slack", token_path=relay_token_file) == (
            "https://xyz789.vectora.chat/auth/slack/callback"
        )
        assert _relay_callback_url("google", token_path=relay_token_file) == (
            "https://xyz789.vectora.chat/auth/google/callback"
        )


class TestGithubCfgRedirect:
    def test_env_var_tem_prioridade_sobre_relay(self, relay_token_file: Path) -> None:
        relay_token_file.write_text("abc123")
        env = {
            "GITHUB_OAUTH_CLIENT_ID": "cid",
            "GITHUB_OAUTH_CLIENT_SECRET": "csec",
            "GITHUB_OAUTH_REDIRECT_URI": "https://custom.example.com/auth/github/callback",
        }
        from backend.api.handlers.oauth import _github_cfg

        with patch.dict(os.environ, env):
            with patch(
                "backend.api.handlers.oauth._RELAY_TOKEN_PATH", relay_token_file
            ):
                _, _, redirect_uri = _github_cfg()
        assert redirect_uri == "https://custom.example.com/auth/github/callback"

    def test_usa_relay_quando_nao_ha_env_var(self, relay_token_file: Path) -> None:
        relay_token_file.write_text("abc123")
        env = {
            "GITHUB_OAUTH_CLIENT_ID": "cid",
            "GITHUB_OAUTH_CLIENT_SECRET": "csec",
        }
        env.pop("GITHUB_OAUTH_REDIRECT_URI", None)
        from backend.api.handlers.oauth import _github_cfg

        with patch.dict(os.environ, env, clear=False):
            os.environ.pop("GITHUB_OAUTH_REDIRECT_URI", None)
            with patch(
                "backend.api.handlers.oauth._RELAY_TOKEN_PATH", relay_token_file
            ):
                _, _, redirect_uri = _github_cfg()
        assert redirect_uri == "https://abc123.vectora.chat/auth/github/callback"

    def test_usa_localhost_sem_relay_sem_env_var(self, relay_token_file: Path) -> None:
        env = {
            "GITHUB_OAUTH_CLIENT_ID": "cid",
            "GITHUB_OAUTH_CLIENT_SECRET": "csec",
        }
        from backend.api.handlers.oauth import _github_cfg

        with patch.dict(os.environ, env, clear=False):
            os.environ.pop("GITHUB_OAUTH_REDIRECT_URI", None)
            with patch(
                "backend.api.handlers.oauth._RELAY_TOKEN_PATH", relay_token_file
            ):
                _, _, redirect_uri = _github_cfg()
        assert redirect_uri == "http://localhost:8080/auth/github/callback"
