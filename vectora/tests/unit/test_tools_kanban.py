"""Tools de agente para o board Kanban (`backend/tools/kanban.py`).

`kanban_create`/`kanban_update_status` mutam `vectora_background_tasks` via
`backend.scheduling.background_tasks`/`backend.scheduling.kanban` — nunca por
SQL direto. `kanban_list` é só leitura. Cada caminho feliz tem o par de
erro/borda no mesmo teste (CLAUDE.md §18).
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import pytest

import backend
from backend.scheduling import background_tasks as bg
from backend.scheduling import kanban

_SCHEMA = (
    Path(backend.__file__).parent / "storage" / "migrations" / "sqlite" / "schema.sql"
)


@pytest.fixture
async def db(tmp_path, monkeypatch):
    """Banco SQLite temporário com o schema real aplicado.

    `_get_db` abre uma conexão nova por chamada; todas apontam pro mesmo
    arquivo, então o estado persiste entre operações — igual à produção.
    """
    db_path = str(tmp_path / "kanban_tools.db")
    up_sql = _SCHEMA.read_text(encoding="utf-8")

    import aiosqlite

    async def _connect() -> Any:
        conn: Any = await aiosqlite.connect(db_path)
        conn.row_factory = lambda c, r: dict(
            zip([col[0] for col in c.description], r, strict=False)
        )
        return conn

    setup = await _connect()
    await setup.executescript(up_sql)
    await setup.commit()
    await setup.close()

    monkeypatch.setattr(bg, "_get_db", _connect)
    return db_path


def _cfg(session_id: str = "s1", user_id: str = "u1") -> Any:
    """RunnableConfig — passado como 2º posicional de `.ainvoke()`, não no
    dict de argumentos: `config` é `InjectedToolArg`, o LangChain o injeta
    a partir daí, não do input da tool."""
    return {"configurable": {"thread_id": session_id, "user_id": user_id}}


class TestKanbanCreate:
    @pytest.mark.asyncio
    async def test_cria_card_e_aparece_no_board(self, db):
        from backend.tools.kanban import kanban_create

        out = json.loads(
            await kanban_create.ainvoke(
                {
                    "name": "Revisar PR #42",
                    "instruction": "Revise o PR e comente achados.",
                },
                _cfg(),
            )
        )
        assert out["status"] == "created"
        assert out["task_id"]

        task = await bg.get_task(out["task_id"])
        assert task is not None
        assert task.name == "Revisar PR #42"
        assert task.trigger_type == "manual"

    @pytest.mark.asyncio
    async def test_nome_ou_instrucao_vazios_retornam_erro_tipado_sem_lancar(self, db):
        """Erro/borda: parâmetro inválido não lança — vira erro tipado, e
        nenhuma linha é gravada no board."""
        from backend.tools.kanban import kanban_create

        out_nome = json.loads(
            await kanban_create.ainvoke(
                {"name": "  ", "instruction": "faça algo"}, _cfg()
            )
        )
        assert out_nome["status"] == "error"

        out_instrucao = json.loads(
            await kanban_create.ainvoke({"name": "card", "instruction": "  "}, _cfg())
        )
        assert out_instrucao["status"] == "error"

        assert await bg.list_tasks("s1") == []


class TestKanbanUpdateStatus:
    @pytest.mark.asyncio
    async def test_move_card_para_status_valido(self, db):
        from backend.tools.kanban import kanban_create, kanban_update_status

        created = json.loads(
            await kanban_create.ainvoke(
                {"name": "card", "instruction": "faça algo"}, _cfg()
            )
        )
        task_id = created["task_id"]

        out = json.loads(
            await kanban_update_status.ainvoke({"task_id": task_id, "status": "review"})
        )
        assert out["result"] == "ok"

        estado = await kanban.get_task_status(task_id)
        assert estado["status"] == "review"

    @pytest.mark.asyncio
    async def test_status_fora_da_taxonomia_retorna_erro_tipado_sem_lancar(self, db):
        """Erro/borda: `set_status` de baixo nível recusa a transição — o
        teste confirma que o erro chega tratado até o topo (a tool nunca
        propaga a `ValueError` crua)."""
        from backend.tools.kanban import kanban_create, kanban_update_status

        created = json.loads(
            await kanban_create.ainvoke(
                {"name": "card", "instruction": "faça algo"}, _cfg()
            )
        )
        task_id = created["task_id"]

        out = json.loads(
            await kanban_update_status.ainvoke(
                {"task_id": task_id, "status": "em-analise"}
            )
        )
        assert out["status"] == "error"
        assert "em-analise" in out["error"]

        # Nada mudou — o card continua na coluna original.
        estado = await kanban.get_task_status(task_id)
        assert estado["status"] != "em-analise"

    @pytest.mark.asyncio
    async def test_status_blocked_passa_por_block_task_com_kind_tipado(self, db):
        from backend.tools.kanban import kanban_create, kanban_update_status

        created = json.loads(
            await kanban_create.ainvoke(
                {"name": "card", "instruction": "faça algo"}, _cfg()
            )
        )
        task_id = created["task_id"]

        out = json.loads(
            await kanban_update_status.ainvoke(
                {
                    "task_id": task_id,
                    "status": "blocked",
                    "block_kind": "capability",
                    "block_reason": "falta ferramenta X",
                }
            )
        )
        assert out["result"] == "ok"

        estado = await kanban.get_task_status(task_id)
        assert estado["status"] == "blocked"
        assert estado["block_kind"] == "capability"


class TestKanbanList:
    @pytest.mark.asyncio
    async def test_lista_cards_reais_da_sessao(self, db):
        from backend.tools.kanban import kanban_create, kanban_list

        await kanban_create.ainvoke(
            {"name": "card 1", "instruction": "faça algo"}, _cfg()
        )
        await kanban_create.ainvoke(
            {"name": "card 2", "instruction": "faça outra coisa"}, _cfg()
        )

        out = json.loads(await kanban_list.ainvoke({}, _cfg()))
        assert out["status"] == "ok"
        assert {c["name"] for c in out["cards"]} == {"card 1", "card 2"}

    @pytest.mark.asyncio
    async def test_board_vazio_retorna_lista_vazia_sem_erro(self, db):
        """Erro/borda: sessão sem nenhum card não é uma falha — a coluna
        simplesmente vem vazia."""
        from backend.tools.kanban import kanban_list

        out = json.loads(await kanban_list.ainvoke({}, _cfg("sessao-nova")))
        assert out["status"] == "ok"
        assert out["cards"] == []

    @pytest.mark.asyncio
    async def test_filtra_por_status(self, db):
        from backend.tools.kanban import (
            kanban_create,
            kanban_list,
            kanban_update_status,
        )

        created = json.loads(
            await kanban_create.ainvoke(
                {"name": "card review", "instruction": "faça algo"}, _cfg()
            )
        )
        await kanban_create.ainvoke(
            {"name": "card ready", "instruction": "faça algo"}, _cfg()
        )
        await kanban_update_status.ainvoke(
            {"task_id": created["task_id"], "status": "review"}
        )

        out = json.loads(await kanban_list.ainvoke({"status": "review"}, _cfg()))
        assert [c["name"] for c in out["cards"]] == ["card review"]
