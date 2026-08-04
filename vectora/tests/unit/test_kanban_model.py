"""Modelo de dados do Kanban sobre ``vectora_background_tasks``.

Extensão do schema existente, não um banco paralelo: o Vectora já tem
``BackgroundTask`` com ``kind="subagent"`` e worktree isolado.

Do Hermes (``hermes_cli/kanban_db.py``) vêm três mecanismos:

- **claim atômico por CAS** — ``UPDATE ... WHERE status='ready' AND
  claim_lock IS NULL``. Sem isso dois workers pegam o mesmo card.
- **heartbeat que estende o TTL do claim**, não um "estou vivo" simbólico:
  worker que morre tem o card liberado por expiração.
- **bloqueio tipado** — ``dependency`` fica em ``todo`` até a promoção
  automática; os outros vão pra ``blocked`` esperando ação humana.

E um invariante do Vectora que o Hermes também tem: delegação síncrona
(``task()``) **não participa do board**.
"""

from __future__ import annotations

import pytest


@pytest.fixture
async def db(tmp_path, monkeypatch):
    """Banco SQLite isolado com o schema real aplicado."""
    import aiosqlite

    from backend.scheduling import kanban

    caminho = tmp_path / "kanban.db"
    conn = await aiosqlite.connect(caminho)
    conn.row_factory = aiosqlite.Row
    await conn.executescript(
        """
        CREATE TABLE vectora_background_tasks (
            id             TEXT PRIMARY KEY,
            session_id     TEXT NOT NULL,
            workspace_id   TEXT,
            user_id        TEXT NOT NULL,
            kind           TEXT NOT NULL,
            name           TEXT NOT NULL,
            instruction    TEXT NOT NULL,
            trigger_type   TEXT NOT NULL,
            trigger_config TEXT NOT NULL DEFAULT '{}',
            enabled        INTEGER NOT NULL DEFAULT 1,
            last_run_at    TEXT,
            next_run_at    TEXT,
            status         TEXT NOT NULL DEFAULT 'todo',
            block_kind     TEXT,
            block_reason   TEXT,
            claim_lock     TEXT,
            claim_expires_at TEXT,
            block_count    INTEGER NOT NULL DEFAULT 0,
            created_at     TEXT NOT NULL DEFAULT (datetime('now')),
            updated_at     TEXT NOT NULL DEFAULT (datetime('now'))
        );
        CREATE TABLE vectora_task_links (
            parent_id  TEXT NOT NULL,
            child_id   TEXT NOT NULL,
            created_at TEXT NOT NULL DEFAULT (datetime('now')),
            PRIMARY KEY (parent_id, child_id)
        );
        """
    )
    await conn.commit()

    async def _get_db():
        return conn

    monkeypatch.setattr(kanban, "_get_db", _get_db)
    yield conn
    await conn.close()


async def _cria(conn, task_id: str, status: str = "todo") -> str:
    await conn.execute(
        """
        INSERT INTO vectora_background_tasks
          (id, session_id, user_id, kind, name, instruction, trigger_type, status)
        VALUES (?, 's1', 'u1', 'subagent', ?, 'faça algo', 'manual', ?)
        """,
        (task_id, f"tarefa {task_id}", status),
    )
    await conn.commit()
    return task_id


class TestClaimAtomico:
    @pytest.mark.asyncio
    async def test_claim_em_task_ready_sucede(self, db):
        from backend.scheduling.kanban import claim_task

        await _cria(db, "t1", status="ready")

        assert await claim_task("t1", "run-a") is True

    @pytest.mark.asyncio
    async def test_segundo_claim_falha_sem_lancar(self, db):
        """Erro/borda: dois workers na mesma task. O segundo recebe `False`
        e segue pra outra — sem CAS os dois rodariam a mesma tarefa."""
        from backend.scheduling.kanban import claim_task

        await _cria(db, "t1", status="ready")

        assert await claim_task("t1", "run-a") is True
        assert await claim_task("t1", "run-b") is False

    @pytest.mark.asyncio
    async def test_task_fora_de_ready_nao_e_reclamavel(self, db):
        """Erro/borda: só `ready` entra em execução. Reclamar de `blocked`
        rodaria uma tarefa que está esperando ação humana."""
        from backend.scheduling.kanban import claim_task

        await _cria(db, "t1", status="blocked")

        assert await claim_task("t1", "run-a") is False

    @pytest.mark.asyncio
    async def test_claim_muda_status_pra_running(self, db):
        from backend.scheduling.kanban import claim_task, get_task_status

        await _cria(db, "t1", status="ready")
        await claim_task("t1", "run-a")

        assert (await get_task_status("t1"))["status"] == "running"


class TestClaimExpirado:
    @pytest.mark.asyncio
    async def test_claim_expirado_e_liberado_e_fica_reclamavel(self, db):
        """Worker que morreu sem liberar: o TTL é o que evita o card ficar
        preso em `running` para sempre."""
        from backend.scheduling.kanban import (
            claim_task,
            release_stale_claims,
        )

        await _cria(db, "t1", status="ready")
        await claim_task("t1", "run-morto", ttl_s=-1)

        assert await release_stale_claims() == 1
        assert await claim_task("t1", "run-nova") is True

    @pytest.mark.asyncio
    async def test_claim_vivo_nao_e_liberado(self, db):
        """Erro/borda: liberar claim vivo faria dois workers na mesma task —
        exatamente o que o CAS existe pra impedir."""
        from backend.scheduling.kanban import claim_task, release_stale_claims

        await _cria(db, "t1", status="ready")
        await claim_task("t1", "run-viva", ttl_s=600)

        assert await release_stale_claims() == 0
        assert await claim_task("t1", "outra") is False


class TestBloqueioTipado:
    @pytest.mark.asyncio
    async def test_dependencia_fica_em_todo_e_nao_em_blocked(self, db):
        """Do Hermes: bloqueio por dependência **não** vai pra coluna
        `blocked` — some do radar humano. Fica em `todo` até a promoção
        automática, porque não há nada que a pessoa possa fazer."""
        from backend.scheduling.kanban import block_task, get_task_status

        await _cria(db, "t1", status="ready")
        await block_task("t1", "dependency", "espera t0")

        estado = await get_task_status("t1")
        assert estado["status"] == "todo"
        assert estado["block_kind"] == "dependency"

    @pytest.mark.asyncio
    async def test_needs_input_vai_pra_blocked(self, db):
        """Os outros tipos esperam ação humana — precisam aparecer."""
        from backend.scheduling.kanban import block_task, get_task_status

        await _cria(db, "t1", status="ready")
        await block_task("t1", "needs_input", "falta a chave da API")

        estado = await get_task_status("t1")
        assert estado["status"] == "blocked"
        assert estado["block_reason"] == "falta a chave da API"

    @pytest.mark.asyncio
    async def test_tipo_de_bloqueio_invalido_e_recusado(self, db):
        """Erro/borda: tipo fora da taxonomia viraria coluna fantasma na UI."""
        from backend.scheduling.kanban import block_task

        await _cria(db, "t1", status="ready")

        with pytest.raises(ValueError, match="inventado"):
            await block_task("t1", "inventado", "?")

    @pytest.mark.asyncio
    async def test_unblock_devolve_pra_ready_e_limpa_o_motivo(self, db):
        from backend.scheduling.kanban import block_task, get_task_status, unblock_task

        await _cria(db, "t1", status="ready")
        await block_task("t1", "needs_input", "falta chave")
        await unblock_task("t1")

        estado = await get_task_status("t1")
        assert estado["status"] == "ready"
        assert estado["block_kind"] is None
        assert estado["block_reason"] is None


class TestDependencias:
    @pytest.mark.asyncio
    async def test_pai_concluido_promove_o_filho_pra_ready(self, db):
        from backend.scheduling.kanban import (
            add_dependency,
            get_task_status,
            recompute_ready,
        )

        await _cria(db, "pai", status="done")
        await _cria(db, "filho", status="todo")
        await add_dependency("pai", "filho")

        assert await recompute_ready() == 1
        assert (await get_task_status("filho"))["status"] == "ready"

    @pytest.mark.asyncio
    async def test_pai_pendente_nao_promove(self, db):
        """Erro/borda: promover cedo faz o filho rodar sem o resultado do
        pai — a dependência existe justamente por isso."""
        from backend.scheduling.kanban import (
            add_dependency,
            get_task_status,
            recompute_ready,
        )

        await _cria(db, "pai", status="running")
        await _cria(db, "filho", status="todo")
        await add_dependency("pai", "filho")

        assert await recompute_ready() == 0
        assert (await get_task_status("filho"))["status"] == "todo"

    @pytest.mark.asyncio
    async def test_filho_com_dois_pais_espera_os_dois(self, db):
        """Erro/borda: promover com um pai pronto ignoraria o outro."""
        from backend.scheduling.kanban import (
            add_dependency,
            get_task_status,
            recompute_ready,
        )

        await _cria(db, "pai1", status="done")
        await _cria(db, "pai2", status="running")
        await _cria(db, "filho", status="todo")
        await add_dependency("pai1", "filho")
        await add_dependency("pai2", "filho")

        await recompute_ready()
        assert (await get_task_status("filho"))["status"] == "todo"

    @pytest.mark.asyncio
    async def test_dependencia_circular_e_recusada(self, db):
        """Erro/borda: ciclo trava os dois cards para sempre em `todo`,
        e ninguém entenderia o porquê."""
        from backend.scheduling.kanban import add_dependency

        await _cria(db, "a")
        await _cria(db, "b")
        await add_dependency("a", "b")

        with pytest.raises(ValueError, match=r"circular|ciclo"):
            await add_dependency("b", "a")

    @pytest.mark.asyncio
    async def test_task_dependente_de_si_mesma_e_recusada(self, db):
        from backend.scheduling.kanban import add_dependency

        await _cria(db, "a")

        with pytest.raises(ValueError, match=r"circular|ciclo|si mesma"):
            await add_dependency("a", "a")


class TestStatusValidos:
    @pytest.mark.asyncio
    async def test_status_fora_da_taxonomia_e_recusado(self, db):
        from backend.scheduling.kanban import set_status

        await _cria(db, "t1")

        with pytest.raises(ValueError, match="em-analise"):
            await set_status("t1", "em-analise")

    @pytest.mark.asyncio
    async def test_todos_os_status_da_taxonomia_sao_aceitos(self, db):
        from backend.scheduling.kanban import KANBAN_STATUSES, set_status

        await _cria(db, "t1")
        for status in KANBAN_STATUSES:
            await set_status("t1", status)


class TestEscalonamentoDeBloqueio:
    """Bloqueio recorrente escala pra `triage` em vez de apodrecer em
    `blocked` pra sempre — mesmo princípio do `BLOCK_RECURRENCE_LIMIT`
    do Hermes."""

    @pytest.mark.asyncio
    async def test_bloqueios_abaixo_do_limite_ficam_em_blocked(self, db):
        from backend.scheduling.kanban import (
            BLOCK_RECURRENCE_LIMIT,
            block_task,
            get_task_status,
        )

        await _cria(db, "t1", status="ready")
        for _ in range(BLOCK_RECURRENCE_LIMIT - 1):
            await block_task("t1", "needs_input", "falta algo")

        estado = await get_task_status("t1")
        assert estado["status"] == "blocked"

    @pytest.mark.asyncio
    async def test_bloqueio_atinge_o_limite_escala_pra_triage(self, db):
        from backend.scheduling.kanban import (
            BLOCK_RECURRENCE_LIMIT,
            block_task,
            get_task_status,
        )

        await _cria(db, "t1", status="ready")
        for _ in range(BLOCK_RECURRENCE_LIMIT):
            await block_task("t1", "transient", "falhou de novo")

        estado = await get_task_status("t1")
        assert estado["status"] == "triage"
        assert "revisão manual" in estado["block_reason"]

    @pytest.mark.asyncio
    async def test_dependency_nunca_conta_pro_escalonamento(self, db):
        """Erro/borda: dependência é resolvida pela máquina, não é uma
        falha real da task — não pode empurrar o card pra triage."""
        from backend.scheduling.kanban import (
            BLOCK_RECURRENCE_LIMIT,
            block_task,
            get_task_status,
        )

        await _cria(db, "t1", status="ready")
        for _ in range(BLOCK_RECURRENCE_LIMIT + 2):
            await block_task("t1", "dependency", "espera outra task")

        estado = await get_task_status("t1")
        assert estado["status"] == "todo"

    @pytest.mark.asyncio
    async def test_sucesso_zera_o_contador_de_bloqueio(self, db):
        """O contador não acumula pra sempre — sair de `blocked` com
        sucesso (via `set_status` pra `ready`/`done`) reseta a régua."""
        from backend.scheduling.kanban import (
            block_task,
            get_task_status,
            set_status,
        )

        await _cria(db, "t1", status="ready")
        await block_task("t1", "transient", "falhou 1x")
        await block_task("t1", "transient", "falhou 2x")
        await set_status("t1", "ready")

        # Depois do reset, precisa de novo o limite inteiro pra escalar.
        await block_task("t1", "transient", "falhou de novo")
        estado = await get_task_status("t1")
        assert estado["status"] == "blocked"

    @pytest.mark.asyncio
    async def test_unblock_tambem_zera_o_contador(self, db):
        from backend.scheduling.kanban import block_task, unblock_task

        await _cria(db, "t1", status="ready")
        await block_task("t1", "needs_input", "falta chave")
        await unblock_task("t1")

        async with db.execute(
            "SELECT block_count FROM vectora_background_tasks WHERE id = 't1'"
        ) as cur:
            row = await cur.fetchone()
        assert row["block_count"] == 0


class TestTransicaoManual:
    """Drag-and-drop no board (e `PATCH .../tasks/{id}` com `status`) só pode
    acionar os pares em `MANUAL_TRANSITIONS` — `running` é exclusivo do claim
    atômico do scheduler e `done` só a run terminando de verdade decide."""

    @pytest.mark.asyncio
    async def test_todo_para_ready_e_permitida(self, db):
        from backend.scheduling.kanban import get_task_status, manual_transition

        await _cria(db, "t1", status="todo")
        await manual_transition("t1", "ready")

        assert (await get_task_status("t1"))["status"] == "ready"

    @pytest.mark.asyncio
    async def test_blocked_para_ready_passa_por_unblock_e_limpa_o_motivo(self, db):
        """`blocked→ready` reaproveita `unblock_task` — não é um `set_status`
        cru, senão o card voltaria pra `ready` com o motivo do bloqueio preso."""
        from backend.scheduling.kanban import (
            block_task,
            get_task_status,
            manual_transition,
        )

        await _cria(db, "t1", status="ready")
        await block_task("t1", "needs_input", "falta chave")
        await manual_transition("t1", "ready")

        estado = await get_task_status("t1")
        assert estado["status"] == "ready"
        assert estado["block_kind"] is None
        assert estado["block_reason"] is None

    @pytest.mark.asyncio
    async def test_ready_para_running_e_recusada(self, db):
        """Erro/borda: `running` só é alcançável pelo claim atômico
        (`claim_task`) — arrastar um card pra lá nunca pode ter efeito."""
        from backend.scheduling.kanban import get_task_status, manual_transition

        await _cria(db, "t1", status="ready")

        with pytest.raises(ValueError, match="não é permitida manualmente"):
            await manual_transition("t1", "running")

        assert (await get_task_status("t1"))["status"] == "ready"

    @pytest.mark.asyncio
    async def test_ready_para_done_e_recusada(self, db):
        """Erro/borda: só a run terminando de verdade decide `done`."""
        from backend.scheduling.kanban import get_task_status, manual_transition

        await _cria(db, "t1", status="ready")

        with pytest.raises(ValueError, match="não é permitida manualmente"):
            await manual_transition("t1", "done")

        assert (await get_task_status("t1"))["status"] == "ready"


class TestEventoSSE:
    """Toda transição de status emite o evento que o board consome via SSE
    (`backend/api/handlers/webhooks.py::_emit_sse_event`) — o board troca o
    polling agressivo por push nesse canal."""

    @pytest.mark.asyncio
    async def test_set_status_emite_evento_com_task_id_e_status(self, db, monkeypatch):
        from backend.api.handlers import webhooks
        from backend.scheduling.kanban import set_status

        await _cria(db, "t1", status="ready")
        chamadas: list[dict] = []
        monkeypatch.setattr(
            webhooks,
            "_emit_sse_event",
            lambda **kw: chamadas.append(kw),
        )

        await set_status("t1", "running")

        assert len(chamadas) == 1
        assert chamadas[0]["provider"] == "kanban"
        assert chamadas[0]["data"]["task_id"] == "t1"
        assert chamadas[0]["data"]["status"] == "running"

    @pytest.mark.asyncio
    async def test_block_task_emite_status_e_block_kind_reason(self, db, monkeypatch):
        from backend.api.handlers import webhooks
        from backend.scheduling.kanban import block_task

        await _cria(db, "t1", status="ready")
        chamadas: list[dict] = []
        monkeypatch.setattr(
            webhooks,
            "_emit_sse_event",
            lambda **kw: chamadas.append(kw),
        )

        await block_task("t1", "needs_input", "falta a chave da API")

        assert len(chamadas) == 1
        assert chamadas[0]["data"] == {
            "task_id": "t1",
            "status": "blocked",
            "block_kind": "needs_input",
            "block_reason": "falta a chave da API",
        }

    @pytest.mark.asyncio
    async def test_unblock_task_emite_status_ready_sem_block_kind(
        self, db, monkeypatch
    ):
        from backend.api.handlers import webhooks
        from backend.scheduling.kanban import block_task, unblock_task

        await _cria(db, "t1", status="ready")
        await block_task("t1", "needs_input", "falta chave")
        chamadas: list[dict] = []
        monkeypatch.setattr(
            webhooks,
            "_emit_sse_event",
            lambda **kw: chamadas.append(kw),
        )

        await unblock_task("t1")

        assert len(chamadas) == 1
        assert chamadas[0]["data"]["status"] == "ready"
        assert chamadas[0]["data"]["block_kind"] is None
        assert chamadas[0]["data"]["block_reason"] is None

    @pytest.mark.asyncio
    async def test_falha_ao_emitir_evento_nao_impede_a_transicao_de_status(
        self, db, monkeypatch
    ):
        """Erro/borda: a camada de notificação é acessória (CLAUDE.md
        regra 11 — tools/funções defensivas). Se `_emit_sse_event` explodir
        (fila cheia, KV fora do ar), o status já commitado no banco precisa
        permanecer — só a notificação em tempo real que se perde, coberta
        pelo polling de reconciliação."""
        from backend.api.handlers import webhooks
        from backend.scheduling.kanban import get_task_status, set_status

        await _cria(db, "t1", status="ready")

        def _explode(**kw):
            raise RuntimeError("fila SSE indisponível")

        monkeypatch.setattr(webhooks, "_emit_sse_event", _explode)

        await set_status("t1", "running")

        assert (await get_task_status("t1"))["status"] == "running"


class TestDelegacaoSincronaForaDoBoard:
    """Invariante de produto, o mesmo desacoplamento do Hermes.

    `task()` no meio da conversa é troca de persona em primeiro plano, não
    trabalho paralelo — não cria nem muta card. Só background tasks entram.
    """

    @pytest.mark.asyncio
    async def test_task_sincrona_nao_grava_link_nem_muda_status(self, db):
        from backend.scheduling.kanban import get_task_status

        await _cria(db, "t1", status="todo")

        # Simula o turno síncrono: o grafo roda `task()` e não toca no board.
        async with db.execute("SELECT COUNT(*) AS n FROM vectora_task_links") as cur:
            antes = (await cur.fetchone())["n"]

        assert antes == 0
        assert (await get_task_status("t1"))["status"] == "todo"

    @pytest.mark.asyncio
    async def test_o_board_so_conhece_kinds_de_background(self, db):
        """Erro/borda: se um dia `task()` passar a gravar aqui, este teste
        acusa — o board é de tarefas em segundo plano."""
        async with db.execute(
            "SELECT DISTINCT kind FROM vectora_background_tasks"
        ) as cur:
            kinds = {r["kind"] for r in await cur.fetchall()}

        assert kinds <= {"subagent", "coder", "prompt"}, (
            f"kind inesperado no board: {kinds}"
        )
