"""Testes de `check_no_plan_comments.py` — hook de pre-commit que barra
proveniência de processo (plano ou ferramenta de IA) em código-fonte.
"""

from __future__ import annotations

from pathlib import Path

import pytest
from check_no_plan_comments import _find_violations, main

pytestmark = pytest.mark.usefixtures("tmp_path")


def _write(tmp_path: Path, name: str, content: str) -> str:
    path = tmp_path / name
    path.write_text(content, encoding="utf-8")
    return str(path)


class TestPlanoDeteccao:
    def test_bloqueia_sprint_numerado(self, tmp_path: Path) -> None:
        path = _write(tmp_path, "a.py", "# Sprint 3: ajusta cache\nx = 1\n")
        assert _find_violations(path) == [(1, "# Sprint 3: ajusta cache")]

    def test_bloqueia_bloco_com_letra_maiuscula(self, tmp_path: Path) -> None:
        path = _write(tmp_path, "a.ts", "// Bloco T10.4 concluído\nconst x = 1;\n")
        assert len(_find_violations(path)) == 1

    def test_bloqueia_fase_com_sufixo(self, tmp_path: Path) -> None:
        path = _write(tmp_path, "a.py", "# fase-2a do rollout\nx = 1\n")
        assert len(_find_violations(path)) == 1

    def test_erro_borda_bloco_minusculo_nao_bloqueia(self, tmp_path: Path) -> None:
        path = _write(tmp_path, "a.py", "# separa em um bloco de código só\nx = 1\n")
        assert _find_violations(path) == []


class TestFerramentaIaDeteccao:
    def test_bloqueia_coderabbit_case_insensitive(self, tmp_path: Path) -> None:
        path = _write(tmp_path, "a.tsx", "// Addressed by CodeRabbit\nconst x = 1;\n")
        assert len(_find_violations(path)) == 1

    def test_bloqueia_claude_code(self, tmp_path: Path) -> None:
        path = _write(tmp_path, "a.py", "# corrigido via Claude Code\nx = 1\n")
        assert len(_find_violations(path)) == 1

    def test_bloqueia_copilot(self, tmp_path: Path) -> None:
        path = _write(tmp_path, "a.js", "// sugestão do copilot\nconst x = 1;\n")
        assert len(_find_violations(path)) == 1

    def test_erro_borda_nome_de_variavel_claude_nao_bloqueia_sozinho(
        self, tmp_path: Path
    ) -> None:
        path = _write(
            tmp_path, "a.py", "# nenhuma referência de ferramenta aqui\nx = 1\n"
        )
        assert _find_violations(path) == []


class TestMain:
    def test_erro_borda_arquivo_limpo_retorna_zero(self, tmp_path: Path) -> None:
        path = _write(tmp_path, "a.py", "def soma(a, b):\n    return a + b\n")
        assert main([path]) == 0

    def test_erro_borda_arquivo_com_violacao_retorna_um(self, tmp_path: Path) -> None:
        path = _write(tmp_path, "a.py", "# Sprint 1\nx = 1\n")
        assert main([path]) == 1

    def test_erro_borda_arquivo_inexistente_nao_lanca_excecao(self) -> None:
        assert main(["C:/caminho/que/nao/existe.py"]) == 0

    def test_erro_borda_multiplos_arquivos_um_so_com_violacao(
        self, tmp_path: Path
    ) -> None:
        limpo = _write(tmp_path, "limpo.py", "x = 1\n")
        sujo = _write(tmp_path, "sujo.py", "# gerado com ChatGPT\nx = 1\n")
        assert main([limpo, sujo]) == 1
