"""Testes do serviço de licença (Bloco T.12.7)."""

from __future__ import annotations

import json
import os
from datetime import UTC, datetime, timedelta
from pathlib import Path

import pytest

from src.services import license as lic


@pytest.fixture(autouse=True)
def isolate_cache(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """Redireciona o cache para tmp e zera env relevantes."""
    cache = tmp_path / "license_cache.json"
    monkeypatch.setattr(lic, "CACHE_PATH", cache)
    for var in ("VECTORA_TOKEN", "VECTORA_LICENSE_BYPASS", "VECTORA_LICENSE_URL"):
        monkeypatch.delenv(var, raising=False)


def _write_cache_fixture(payload: dict) -> None:
    lic.CACHE_PATH.parent.mkdir(parents=True, exist_ok=True)
    lic.CACHE_PATH.write_text(json.dumps(payload), encoding="utf-8")


def test_bypass_returns_active_pro(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("VECTORA_LICENSE_BYPASS", "1")
    info = lic.validate_license_sync()
    assert info.tier == "pro"
    assert info.status == "active"
    assert info.days_remaining > 300


def test_missing_token_raises() -> None:
    with pytest.raises(lic.LicenseError, match="VECTORA_TOKEN"):
        lic.validate_license_sync()


def test_cache_fresh_returns_cached(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("VECTORA_TOKEN", "tok_abc")
    _write_cache_fixture(
        {
            "tier": "plus",
            "status": "active",
            "days_remaining": 25,
            "expires_at": "2027-01-01",
            "validated_at": datetime.now(UTC).isoformat(),
        }
    )
    info = lic.validate_license_sync()
    assert info.cached is True
    assert info.tier == "plus"
    assert info.days_remaining == 25


def test_cache_stale_offline_within_48h(monkeypatch: pytest.MonkeyPatch) -> None:
    """Cache ficou >6h mas <48h → ainda devolve em modo offline graceful."""
    monkeypatch.setenv("VECTORA_TOKEN", "tok_abc")
    monkeypatch.setenv("VECTORA_LICENSE_URL", "http://127.0.0.1:1/should-fail")
    stale = (datetime.now(UTC) - timedelta(hours=10)).isoformat()
    _write_cache_fixture(
        {
            "tier": "plus",
            "status": "active",
            "days_remaining": 25,
            "expires_at": "2027-01-01",
            "validated_at": stale,
        }
    )
    info = lic.validate_license_sync()
    assert info.cached is True
    assert info.status == "active"


def test_read_cached_status_returns_none_when_no_cache() -> None:
    assert lic.read_cached_status() is None


def test_read_cached_status_returns_info() -> None:
    _write_cache_fixture(
        {
            "tier": "pro",
            "status": "trial",
            "days_remaining": 5,
            "expires_at": "2026-06-30",
            "validated_at": datetime.now(UTC).isoformat(),
        }
    )
    info = lic.read_cached_status()
    assert info is not None
    assert info.tier == "pro"
    assert info.status == "trial"
    assert info.days_remaining == 5
