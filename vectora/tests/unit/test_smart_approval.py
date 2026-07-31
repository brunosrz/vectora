"""Aprovação inteligente de comandos — avaliador auxiliar + allowlist.

Invariante crítico, o mesmo em todos os testes deste arquivo: esta camada
**nunca** substitui o HITL sozinha. `evaluate_command` só devolve um booleano
de anotação (`pre_approved`) — quem decide se a tool executa continua sendo
`_REQUIRE_APPROVAL`/`_mode_should_interrupt`, que nem sabe que esta camada
existe. Mais conservador que o Hermes (que auto-executa), alinhado ao HITL
sempre já vinculante do produto.

Cada caminho feliz tem o par de erro/borda no mesmo teste (CLAUDE.md §18).
"""

from __future__ import annotations

import pytest

from backend.services import smart_approval as sa


@pytest.fixture(autouse=True)
def _runtime_settings_isolado(tmp_path, monkeypatch):
    """Evita que os testes leiam/gravem no `app_settings` real do usuário."""
    from backend.workspace.runtime_settings import RuntimeSettings

    isolado = RuntimeSettings(tmp_path / "rt.db")
    monkeypatch.setattr(sa, "_runtime_settings", lambda: isolado)
    return isolado


class TestAssinatura:
    def test_terminal_usa_o_comando_exato(self):
        # Happy: mesmo comando → mesma assinatura.
        a = sa._signature("terminal", {"command": "git status"})
        b = sa._signature("terminal", {"command": "git status"})
        assert a == b

        # Erro/borda: comando diferente não pode colidir — allowlist por
        # comando exato, não por tool inteira (senão "git status" liberaria
        # "git push --force" também).
        c = sa._signature("terminal", {"command": "git push --force"})
        assert a != c

    def test_outras_tools_usam_so_o_nome(self):
        assert sa._signature("delete_skill", {"skill_id": "x"}) == sa._signature(
            "delete_skill", {"skill_id": "y"}
        )


class TestAllowlist:
    def test_add_get_remove_roundtrip(self):
        assert sa.get_allowlist("ws1") == []

        sinais = sa.add_to_allowlist("ws1", "terminal", {"command": "git status"})
        assert sinais == sa.get_allowlist("ws1")
        assert sa.is_allowlisted("ws1", "terminal", {"command": "git status"}) is True

        restante = sa.remove_from_allowlist("ws1", sinais[0])
        assert restante == []
        assert sa.is_allowlisted("ws1", "terminal", {"command": "git status"}) is False

    def test_workspace_vazio_e_recusado_na_escrita(self):
        """Erro/borda: allowlist é por workspace — sem id não há onde
        persistir, e gravar sob chave vazia vazaria entre workspaces."""
        with pytest.raises(ValueError, match="workspace_id"):
            sa.add_to_allowlist("", "terminal", {"command": "git status"})

    def test_workspace_desconhecido_na_leitura_devolve_vazio_sem_lancar(self):
        assert sa.get_allowlist("ws-nunca-existiu") == []
        assert sa.is_allowlisted("ws-nunca-existiu", "terminal", {}) is False

    def test_allowlists_de_workspaces_diferentes_nao_se_misturam(self):
        sa.add_to_allowlist("ws-a", "terminal", {"command": "git status"})

        assert sa.is_allowlisted("ws-a", "terminal", {"command": "git status"}) is True
        assert sa.is_allowlisted("ws-b", "terminal", {"command": "git status"}) is False

    def test_adicionar_duplicata_nao_duplica(self):
        sa.add_to_allowlist("ws1", "terminal", {"command": "git status"})
        sinais = sa.add_to_allowlist("ws1", "terminal", {"command": "git status"})
        assert len(sinais) == 1


class TestEvaluateCommand:
    @pytest.mark.asyncio
    async def test_allowlisted_pre_aprova_sem_chamar_llm(self):
        chamou = {"llm": False}

        async def _nunca(*_a, **_k):
            chamou["llm"] = True
            return True

        sa.add_to_allowlist("ws1", "terminal", {"command": "git status"})

        resultado = await sa.evaluate_command(
            "terminal",
            {"command": "git status"},
            workspace_id="ws1",
            ask_llm=_nunca,
        )

        assert resultado is True
        assert chamou["llm"] is False

    @pytest.mark.asyncio
    async def test_nao_allowlisted_consulta_o_avaliador_auxiliar(self):
        async def _diz_seguro(_tool_name, _args):
            return True

        resultado = await sa.evaluate_command(
            "terminal",
            {"command": "ls"},
            workspace_id="ws1",
            ask_llm=_diz_seguro,
        )

        assert resultado is True

        async def _diz_revisar(_tool_name, _args):
            return False

        recusado = await sa.evaluate_command(
            "terminal",
            {"command": "rm -rf /"},
            workspace_id="ws1",
            ask_llm=_diz_revisar,
        )
        assert recusado is False

    @pytest.mark.asyncio
    async def test_falha_do_avaliador_degrada_pra_sem_pre_aprovacao(self):
        """Regra 11: falha na camada acessória nunca impede o HITL normal —
        `evaluate_command` nunca lança, e o padrão seguro é `False`
        (continua pedindo aprovação sem o atalho visual)."""

        async def _explode(_tool_name, _args):
            raise RuntimeError("provider fora do ar")

        resultado = await sa.evaluate_command(
            "terminal",
            {"command": "git status"},
            workspace_id="ws1",
            ask_llm=_explode,
        )

        assert resultado is False

    @pytest.mark.asyncio
    async def test_pre_aprovacao_nunca_e_usada_pra_pular_o_hitl(self):
        """Trava o invariante do sprint: `evaluate_command` é uma função pura
        que devolve bool — nenhuma tool nem tool call é executada aqui. Quem
        decide pausar é `_REQUIRE_APPROVAL`, que não importa este módulo."""
        import backend.services.middleware as mw

        assert "smart_approval" not in mw.__dict__.get("__file__", "")
        # A dependência é de fora pra dentro (adapters chama smart_approval),
        # nunca o contrário — middleware não conhece este módulo.
        import inspect

        fonte_middleware = inspect.getsource(mw)
        assert "smart_approval" not in fonte_middleware
