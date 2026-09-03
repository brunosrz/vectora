"""Testes de `check_no_plan_pr_metadata.py` — checagem de CI que barra
proveniência de processo (plano ou ferramenta de IA) em título/descrição de
PR (CLAUDE.md §1, que cobre também mensagens de PR).
"""

from __future__ import annotations

import pytest
from check_no_plan_pr_metadata import _strip_bot_blocks, main


def _run(monkeypatch: pytest.MonkeyPatch, title: str, body: str) -> int:
    monkeypatch.setenv("PR_TITLE", title)
    monkeypatch.setenv("PR_BODY", body)
    return main()


class TestTitulo:
    def test_bloqueia_sprint_no_titulo(self, monkeypatch: pytest.MonkeyPatch) -> None:
        assert _run(monkeypatch, "fix: Sprint 3 do túnel", "") == 1

    def test_titulo_normal_passa(self, monkeypatch: pytest.MonkeyPatch) -> None:
        assert _run(monkeypatch, "fix(gateway): hardening do túnel", "") == 0


class TestDescricao:
    def test_bloqueia_sprint_na_descricao(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        body = "## Resumo (Sprint E do plano)\nEnxuga o build.\n"
        assert _run(monkeypatch, "fix: enxuga build", body) == 1

    def test_bloqueia_bloco_com_letra_maiuscula(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        assert _run(monkeypatch, "fix: x", "Conclui o Bloco T10.4\n") == 1

    def test_erro_borda_bloco_minusculo_nao_bloqueia(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        body = "Separa em um bloco de código só, sem plano nenhum.\n"
        assert _run(monkeypatch, "fix: x", body) == 0

    def test_bloqueia_claude_code_na_descricao(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        assert _run(monkeypatch, "fix: x", "Corrigido via Claude Code.\n") == 1

    def test_descricao_normal_passa(self, monkeypatch: pytest.MonkeyPatch) -> None:
        body = "## Resumo\nCorrige o cross-arch fallback do updater.\n"
        assert _run(monkeypatch, "fix: cross-arch", body) == 0

    def test_erro_borda_referencia_a_claude_md_na_descricao_nao_bloqueia(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        body = "CLAUDE.md §1 cobre também mensagens de PR.\n"
        assert _run(monkeypatch, "fix: x", body) == 0

    def test_erro_borda_sem_body_nao_quebra(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.setenv("PR_TITLE", "fix: x")
        monkeypatch.delenv("PR_BODY", raising=False)
        assert main() == 0


class TestStripBotBlocks:
    def test_remove_bloco_de_resumo_do_coderabbit(self) -> None:
        body = (
            "## Resumo\nTexto normal.\n\n"
            "<!-- This is an auto-generated comment: summarize by coderabbit.ai -->\n"
            "menção a CodeRabbit e Sprint 9 aqui dentro\n"
            "<!-- end of auto-generated comment: summarize by coderabbit.ai -->\n"
        )
        stripped = _strip_bot_blocks(body)
        assert "coderabbit" not in stripped.lower()
        assert "sprint" not in stripped.lower()
        assert "Texto normal." in stripped

    def test_erro_borda_pr_revisado_pelo_coderabbit_nao_bloqueia_sozinho(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """O rodapé que o próprio bot insere não pode reprovar o PR — só
        texto escrito por um humano no corpo conta como violação."""
        body = (
            "## Resumo\nCorrige o bug.\n\n"
            "<!-- This is an auto-generated comment: release notes by coderabbit.ai -->\n"
            "## Summary by CodeRabbit\n* Corrigido o Sprint 3.\n"
            "<!-- end of auto-generated comment: release notes by coderabbit.ai -->\n"
        )
        assert _run(monkeypatch, "fix: corrige bug", body) == 0
