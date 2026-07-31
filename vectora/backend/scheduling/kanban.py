"""Modelo de Kanban sobre ``vectora_background_tasks``.

Extensão do schema existente, não um banco paralelo — o Vectora já tem
``BackgroundTask`` com ``kind="subagent"`` e worktree isolado
(``backend/scheduling/delegate.py``).

Três mecanismos vêm do Hermes (``hermes_cli/kanban_db.py``):

- **Claim atômico por CAS**: ``UPDATE ... WHERE status='ready' AND claim_lock
  IS NULL``. Ler-depois-escrever deixaria dois workers pegarem o mesmo card.
- **TTL no claim**: worker que morre sem liberar tem o card devolvido por
  expiração, em vez de deixá-lo preso em ``running`` para sempre.
- **Bloqueio tipado**: ``dependency`` fica em ``todo`` (não há ação humana
  possível, some do radar até a promoção automática); os demais vão pra
  ``blocked``, onde alguém precisa agir.

Invariante de produto: delegação síncrona (``task()`` no meio da conversa)
**não** participa do board — só background tasks. Isso já é o comportamento
do Vectora e é o mesmo desacoplamento do Hermes.
"""

from __future__ import annotations

import logging
from datetime import UTC, datetime, timedelta
from typing import Any

logger = logging.getLogger(__name__)

#: Ciclo completo. `triage` e `archived` ficam fora das colunas principais
#: da UI (ver Sprint 17), mas existem no modelo.
KANBAN_STATUSES: tuple[str, ...] = (
    "triage",
    "todo",
    "ready",
    "running",
    "blocked",
    "done",
    "archived",
)

#: `dependency` é resolvido pela máquina; os outros esperam uma pessoa.
BLOCK_KINDS: tuple[str, ...] = (
    "dependency",
    "needs_input",
    "capability",
    "transient",
)

_DEFAULT_CLAIM_TTL_S = 900


async def _get_db() -> Any:
    """Mesmo banco de `vectora_background_tasks` — não `checkpoints.db`.

    `vectora_background_tasks`/`vectora_task_links` vivem em
    `settings.db_dsn` (aplicado por `schema.sql`), não no banco de
    threads/checkpoints do LangGraph. Apontar pro `_get_db` de
    `threads.py` (erro corrigido aqui) fazia todo claim/status do Kanban
    cair num banco sem essas tabelas — silenciado pelo try/except do
    `tick()`, então o sintoma era só "nada do Kanban nunca atualiza".
    """
    from backend.scheduling.background_tasks import _get_db as _tasks_db

    return await _tasks_db()


def _agora() -> datetime:
    return datetime.now(UTC)


async def get_task_status(task_id: str) -> dict[str, Any]:
    db = await _get_db()
    async with db.execute(
        "SELECT status, block_kind, block_reason, claim_lock, claim_expires_at "
        "FROM vectora_background_tasks WHERE id = ?",
        (task_id,),
    ) as cur:
        row = await cur.fetchone()
    if row is None:
        msg = f"task {task_id!r} não existe"
        raise ValueError(msg)
    return dict(row)


async def set_status(task_id: str, status: str) -> None:
    if status not in KANBAN_STATUSES:
        msg = (
            f"status {status!r} fora da taxonomia — válidos: "
            f"{', '.join(KANBAN_STATUSES)}"
        )
        raise ValueError(msg)
    db = await _get_db()
    await db.execute(
        "UPDATE vectora_background_tasks SET status = ?, "
        "updated_at = datetime('now') WHERE id = ?",
        (status, task_id),
    )
    await db.commit()


async def claim_task(
    task_id: str, run_id: str, *, ttl_s: int = _DEFAULT_CLAIM_TTL_S
) -> bool:
    """Reivindica a task para `run_id`. `False` quando outro já pegou.

    O CAS está no `WHERE`: só troca de dono se ainda estiver `ready` e sem
    claim. Checar antes e gravar depois abriria a janela em que dois workers
    leem "livre" e ambos gravam.
    """
    expira = (_agora() + timedelta(seconds=ttl_s)).isoformat()
    db = await _get_db()
    cur = await db.execute(
        """
        UPDATE vectora_background_tasks
           SET status = 'running',
               claim_lock = ?,
               claim_expires_at = ?,
               updated_at = datetime('now')
         WHERE id = ?
           AND status = 'ready'
           AND claim_lock IS NULL
        """,
        (run_id, expira, task_id),
    )
    await db.commit()
    return cur.rowcount > 0


async def heartbeat_claim(
    task_id: str, run_id: str, *, ttl_s: int = _DEFAULT_CLAIM_TTL_S
) -> bool:
    """Estende o TTL do claim — não é um "estou vivo" simbólico.

    Só o dono do claim consegue estender: sem essa checagem, um worker
    zumbi manteria vivo o claim de outro.
    """
    expira = (_agora() + timedelta(seconds=ttl_s)).isoformat()
    db = await _get_db()
    cur = await db.execute(
        "UPDATE vectora_background_tasks SET claim_expires_at = ? "
        "WHERE id = ? AND claim_lock = ?",
        (expira, task_id, run_id),
    )
    await db.commit()
    return cur.rowcount > 0


async def release_stale_claims() -> int:
    """Devolve pra `ready` os claims expirados. Roda no tick do scheduler."""
    agora = _agora().isoformat()
    db = await _get_db()
    cur = await db.execute(
        """
        UPDATE vectora_background_tasks
           SET status = 'ready',
               claim_lock = NULL,
               claim_expires_at = NULL,
               updated_at = datetime('now')
         WHERE claim_lock IS NOT NULL
           AND claim_expires_at IS NOT NULL
           AND claim_expires_at < ?
        """,
        (agora,),
    )
    await db.commit()
    if cur.rowcount:
        logger.info("kanban: %s claim(s) expirado(s) devolvido(s)", cur.rowcount)
    return cur.rowcount


async def block_task(task_id: str, kind: str, reason: str) -> None:
    """Bloqueia a task. `dependency` fica em `todo`; o resto vai pra `blocked`."""
    if kind not in BLOCK_KINDS:
        msg = (
            f"tipo de bloqueio {kind!r} fora da taxonomia — válidos: "
            f"{', '.join(BLOCK_KINDS)}"
        )
        raise ValueError(msg)

    # Bloqueio por dependência não é acionável por ninguém: colocá-lo em
    # `blocked` encheria a coluna de cards que a pessoa não pode destravar.
    status = "todo" if kind == "dependency" else "blocked"

    db = await _get_db()
    await db.execute(
        "UPDATE vectora_background_tasks SET status = ?, block_kind = ?, "
        "block_reason = ?, claim_lock = NULL, claim_expires_at = NULL, "
        "updated_at = datetime('now') WHERE id = ?",
        (status, kind, reason, task_id),
    )
    await db.commit()


async def unblock_task(task_id: str) -> None:
    db = await _get_db()
    await db.execute(
        "UPDATE vectora_background_tasks SET status = 'ready', block_kind = NULL, "
        "block_reason = NULL, updated_at = datetime('now') WHERE id = ?",
        (task_id,),
    )
    await db.commit()


async def _depende_de(task_id: str) -> set[str]:
    """Ancestrais de `task_id` — usado pra detectar ciclo."""
    db = await _get_db()
    vistos: set[str] = set()
    fila = [task_id]
    while fila:
        atual = fila.pop()
        async with db.execute(
            "SELECT parent_id FROM vectora_task_links WHERE child_id = ?", (atual,)
        ) as cur:
            pais = [r["parent_id"] for r in await cur.fetchall()]
        for pai in pais:
            if pai not in vistos:
                vistos.add(pai)
                fila.append(pai)
    return vistos


async def add_dependency(parent_id: str, child_id: str) -> None:
    """`child_id` só fica pronto quando `parent_id` conclui."""
    if parent_id == child_id:
        msg = "dependência circular: uma task não pode depender de si mesma"
        raise ValueError(msg)

    # Ciclo trava os dois cards em `todo` para sempre, e o motivo não
    # aparece em lugar nenhum — recusar na criação é a única chance.
    if child_id in await _depende_de(parent_id):
        msg = (
            f"dependência circular: {parent_id!r} já depende (direta ou "
            f"indiretamente) de {child_id!r}"
        )
        raise ValueError(msg)

    db = await _get_db()
    await db.execute(
        "INSERT OR IGNORE INTO vectora_task_links (parent_id, child_id) VALUES (?, ?)",
        (parent_id, child_id),
    )
    await db.commit()


async def recompute_ready() -> int:
    """Promove pra `ready` as tasks em `todo` com todos os pais concluídos.

    Chamado quando uma task chega em `done`. Um filho com dois pais espera
    os dois — promover com um só o faria rodar sem o resultado do outro.
    """
    db = await _get_db()
    async with db.execute(
        """
        SELECT t.id
          FROM vectora_background_tasks t
         WHERE t.status = 'todo'
           AND EXISTS (
                 SELECT 1 FROM vectora_task_links l WHERE l.child_id = t.id
               )
           AND NOT EXISTS (
                 SELECT 1
                   FROM vectora_task_links l
                   JOIN vectora_background_tasks p ON p.id = l.parent_id
                  WHERE l.child_id = t.id
                    AND p.status != 'done'
               )
        """
    ) as cur:
        prontas = [r["id"] for r in await cur.fetchall()]

    for task_id in prontas:
        await db.execute(
            "UPDATE vectora_background_tasks SET status = 'ready', "
            "block_kind = NULL, block_reason = NULL, "
            "updated_at = datetime('now') WHERE id = ?",
            (task_id,),
        )
    await db.commit()
    return len(prontas)
