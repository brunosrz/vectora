"""Tests for src/version.py"""

from __future__ import annotations

import json
import re
import tomllib
from pathlib import Path

from backend.version import __version__

_MONOREPO_ROOT = Path(__file__).resolve().parents[3]


def test_version_is_string():
    assert isinstance(__version__, str)


def test_version_semver():
    assert re.match(r"^\d+\.\d+\.\d+", __version__), f"Not semver: {__version__}"


def test_pyproject_version_bate_com_frontend_package_json():
    """Regressão do bug real (2026-08-30): electron-builder deriva o nome do
    instalador e o conteúdo do latest.yml de frontend/package.json, não de
    pyproject.toml — se os dois divergirem, o instalador publicado mente sua
    própria versão e o electron-updater recusa a atualização real como
    "downgrade". Sem release-please-config.json::extra-files sincronizando
    os dois, esse teste é o único jeito de pegar a divergência antes do
    build de produção."""
    pyproject = tomllib.loads(
        (_MONOREPO_ROOT / "vectora" / "pyproject.toml").read_text(encoding="utf-8")
    )
    frontend_pkg = json.loads(
        (_MONOREPO_ROOT / "vectora" / "frontend" / "package.json").read_text(
            encoding="utf-8"
        )
    )
    assert pyproject["project"]["version"] == frontend_pkg["version"], (
        "vectora/pyproject.toml e vectora/frontend/package.json com versões "
        "diferentes — o instalador publicado terá o número de versão errado."
    )


def test_release_please_config_sincroniza_frontend_package_json():
    """Sem essa entrada, release-please bumpa só pyproject.toml a cada
    release e o teste acima volta a falhar na release seguinte.

    release-please-config.json rastreia o monorepo INTEIRO como um único
    pacote (chave "." — path é interpretado literalmente pelo release-please,
    não é um nome arbitrário; uma chave "vectora" faria o path virar
    `vectora/`, restringindo commits contados só àquela pasta). Os paths de
    extra-files, por isso, são relativos à raiz do repo."""
    config = json.loads(
        (_MONOREPO_ROOT / "release-please-config.json").read_text(encoding="utf-8")
    )
    extra_files = config["packages"]["."].get("extra-files", [])
    paths = {
        entry.get("path") if isinstance(entry, dict) else entry for entry in extra_files
    }
    assert "vectora/frontend/package.json" in paths
    assert "vectora/pyproject.toml" in paths
