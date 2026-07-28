"""ensure_app_secret (backend/services/gateway/secret.py) — auto-geração do
VECTORA_APP_SECRET por instalação (Sprint 11.1). Sem secret, o
GatewayClient nunca chama POST /register e o gateway fica sempre
never_connected."""

from __future__ import annotations

import os

import pytest


@pytest.fixture
def _restore_settings():
    from backend.settings import settings

    original = settings.vectora_app_secret
    yield settings
    object.__setattr__(settings, "vectora_app_secret", original)


class TestEnsureAppSecret:
    def test_gera_e_persiste_quando_ausente(
        self, tmp_path, monkeypatch, _restore_settings
    ):
        from backend.services.gateway import secret as secret_mod

        object.__setattr__(_restore_settings, "vectora_app_secret", "")
        monkeypatch.delenv("VECTORA_APP_SECRET", raising=False)
        env_file = tmp_path / ".env"
        monkeypatch.setattr(
            "backend.services.env_keys.default_env_file", lambda: env_file
        )

        result = secret_mod.ensure_app_secret()

        assert len(result) == 64  # secrets.token_hex(32) -> 64 hex chars
        assert os.environ["VECTORA_APP_SECRET"] == result
        assert _restore_settings.vectora_app_secret == result
        assert env_file.exists()
        assert f"VECTORA_APP_SECRET={result}" in env_file.read_text()

    def test_idempotente_nao_regera_se_ja_existe_em_settings(
        self, monkeypatch, _restore_settings
    ):
        from backend.services.gateway import secret as secret_mod

        object.__setattr__(_restore_settings, "vectora_app_secret", "existing-secret")
        monkeypatch.delenv("VECTORA_APP_SECRET", raising=False)

        result = secret_mod.ensure_app_secret()

        assert result == "existing-secret"
        assert "VECTORA_APP_SECRET" not in os.environ

    def test_idempotente_nao_regera_se_ja_existe_no_ambiente(
        self, monkeypatch, _restore_settings
    ):
        from backend.services.gateway import secret as secret_mod

        object.__setattr__(_restore_settings, "vectora_app_secret", "")
        monkeypatch.setenv("VECTORA_APP_SECRET", "from-env")

        result = secret_mod.ensure_app_secret()

        assert result == "from-env"
