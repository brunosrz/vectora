"""Tests para src/api/handlers/artifacts.py (Bloco T cont., T8).

Cobre:
- list_artifacts vazia para session_id sem pasta.
- list_artifacts ordena por mtime descendente (mais novos primeiro).
- get_artifact devolve o markdown completo.
- Sanitização anti-traversal em slug e session_id (.. e barras).
- Preview de 200 chars no list.
"""

from __future__ import annotations

import os
import time
from pathlib import Path

import pytest

# ---------------------------------------------------------------------------
# Fixture — redireciona ~ para uma pasta temporária por teste
# ---------------------------------------------------------------------------


@pytest.fixture
def fake_home(tmp_path, monkeypatch):
    """Faz ``Path.home()`` apontar para tmp_path. Aplica em HOME e USERPROFILE
    (Windows usa o segundo). Os helpers do handler chamam ``Path.home()``."""
    monkeypatch.setenv("HOME", str(tmp_path))
    monkeypatch.setenv("USERPROFILE", str(tmp_path))
    # Path.home() consulta os envs acima — não precisa de monkeypatch direto.
    return tmp_path


def _write_artifact(home: Path, session_id: str, slug: str, content: str) -> Path:
    """Cria um arquivo de artifact dentro de ~/.vectora/artifacts/<session>/."""
    base = home / ".vectora" / "artifacts" / session_id
    base.mkdir(parents=True, exist_ok=True)
    path = base / f"{slug}.md"
    path.write_text(content, encoding="utf-8")
    return path


# ---------------------------------------------------------------------------
# list_artifacts
# ---------------------------------------------------------------------------


class TestListArtifacts:
    @pytest.mark.asyncio
    async def test_empty_for_unknown_session(self, fake_home):
        from backend.api.handlers.artifacts import list_artifacts

        resp = await list_artifacts(session_id="never-existed")
        assert resp.artifacts == []

    @pytest.mark.asyncio
    async def test_empty_for_blank_session_id(self, fake_home):
        from backend.api.handlers.artifacts import list_artifacts

        resp = await list_artifacts(session_id="")
        assert resp.artifacts == []

    @pytest.mark.asyncio
    async def test_lists_existing_artifacts(self, fake_home):
        from backend.api.handlers.artifacts import list_artifacts

        _write_artifact(fake_home, "sess1", "plano-x", "# Plano X\n\ncorpo")
        _write_artifact(fake_home, "sess1", "spec-y", "# Spec Y\n\ndetalhe")

        resp = await list_artifacts(session_id="sess1")
        slugs = [Path(a.path).stem for a in resp.artifacts]
        assert "plano-x" in slugs
        assert "spec-y" in slugs

    @pytest.mark.asyncio
    async def test_orders_by_mtime_desc(self, fake_home):
        """Mais recentes primeiro — o usuário vê o último plano no topo."""
        from backend.api.handlers.artifacts import list_artifacts

        a = _write_artifact(fake_home, "ord", "antigo", "velho")
        # Garante mtimes diferentes (tolerância de 1s em sistemas com mtime granular)
        past = time.time() - 60
        os.utime(a, (past, past))
        _write_artifact(fake_home, "ord", "novo", "recente")

        resp = await list_artifacts(session_id="ord")
        slugs = [Path(art.path).stem for art in resp.artifacts]
        assert slugs[0] == "novo"
        assert slugs[1] == "antigo"

    @pytest.mark.asyncio
    async def test_content_preview_truncated_to_200(self, fake_home):
        """O preview no list é limitado — não devolve markdown gigante."""
        from backend.api.handlers.artifacts import list_artifacts

        big = "X" * 1000
        _write_artifact(fake_home, "prev", "huge", big)
        resp = await list_artifacts(session_id="prev")
        assert resp.artifacts[0].content_preview is not None
        assert len(resp.artifacts[0].content_preview) <= 200

    @pytest.mark.asyncio
    async def test_session_id_traversal_is_stripped(self, fake_home):
        """`..` e barras no session_id são removidos — não foge da pasta."""
        from backend.api.handlers.artifacts import list_artifacts

        # Cria artifact numa sessão legítima.
        _write_artifact(fake_home, "legit", "plano", "ok")
        # Cria também um artifact "irmão" que NÃO deveria vazar via traversal.
        bad = fake_home / ".vectora" / "artifacts" / "outra" / "secreto.md"
        bad.parent.mkdir(parents=True, exist_ok=True)
        bad.write_text("segredo", encoding="utf-8")

        # Tenta atacar via "..".
        resp = await list_artifacts(session_id="legit/../outra")
        # O sanitize remove "/" e ".." — vira "legitoutra" (sessão inexistente).
        # Não pode ter "secreto" no resultado.
        paths = [a.path for a in resp.artifacts]
        assert not any("secreto" in p for p in paths)


# ---------------------------------------------------------------------------
# get_artifact
# ---------------------------------------------------------------------------


class TestGetArtifact:
    @pytest.mark.asyncio
    async def test_returns_content(self, fake_home):
        from backend.api.handlers.artifacts import get_artifact

        _write_artifact(fake_home, "g1", "meu-plano", "# Conteúdo\n\nlinha")
        resp = await get_artifact("meu-plano", session_id="g1")
        assert "Conteúdo" in resp.content
        assert resp.slug == "meu-plano"
        assert resp.session_id == "g1"
        assert resp.created_at  # ISO 8601 do mtime

    @pytest.mark.asyncio
    async def test_returns_empty_for_missing(self, fake_home):
        from backend.api.handlers.artifacts import get_artifact

        resp = await get_artifact("nao-existe", session_id="g1")
        assert resp.content == ""

    @pytest.mark.asyncio
    async def test_slug_traversal_is_stripped(self, fake_home):
        """Slug com `..` e barras não consegue ler arquivos fora da pasta."""
        from backend.api.handlers.artifacts import get_artifact

        # Cria um arquivo "real" na pasta da sessão e outro fora.
        _write_artifact(fake_home, "safe", "ok", "interno")
        outside = fake_home / ".vectora" / "artifacts" / "safe.md"
        outside.write_text("FORA", encoding="utf-8")

        resp = await get_artifact("../safe", session_id="safe")
        # ".." e "/" removidos pelo handler — vira "safe.md" dentro de
        # ~/.vectora/artifacts/safe/safe.md, que não existe → content vazio.
        assert resp.content == ""
        assert "FORA" not in resp.content

    @pytest.mark.asyncio
    async def test_session_id_traversal_is_stripped_in_get(self, fake_home):
        from backend.api.handlers.artifacts import get_artifact

        # Cria o "secreto" fora da pasta esperada.
        bad = fake_home / ".vectora" / "artifacts" / "boom" / "secreto.md"
        bad.parent.mkdir(parents=True, exist_ok=True)
        bad.write_text("segredo", encoding="utf-8")

        resp = await get_artifact("secreto", session_id="legit/../boom")
        # Sanitização junta tudo numa string sem traversal.
        assert "segredo" not in resp.content
