"""Budget por tarefa em segundo plano, com corte automático.

Inspirado no `budget_policies` do Paperclip (escopo empresa/projeto/agente,
`hardStopEnabled` que pausa o agente). O Vectora é local-first
single-tenant, então o escopo aqui é **a tarefa** — mas o problema é o mesmo:
hoje nada impede uma tarefa mal configurada de rodar em loop gastando API.

Duas decisões deliberadas:

- **Só a próxima run é barrada.** Abortar uma run em andamento trunca o
  output parcial — mesmo princípio já usado no tratamento de erro de
  streaming do chat.
- **Custo desconhecido não conta como zero.** Provider que não expõe
  `usage_metadata` não gastou nada; simplesmente não se sabe. Somar 0 faria
  o budget nunca estourar.
"""

from __future__ import annotations

import logging
from typing import Any

logger = logging.getLogger(__name__)

#: Preço por 1M de tokens, em centavos de dólar (entrada, saída).
#: Modelo fora da tabela devolve `None`: chutar daria um número inventado
#: que o usuário leria como real.
_PRECO_POR_MILHAO_CENTS: dict[str, tuple[float, float]] = {
    "openai:gpt-4o": (250.0, 1000.0),
    "openai:gpt-4o-mini": (15.0, 60.0),
    "openai:o3-mini": (110.0, 440.0),
    "anthropic:claude-opus-4-1": (1500.0, 7500.0),
    "anthropic:claude-sonnet-4-5": (300.0, 1500.0),
    "google_genai:gemini-2.5-pro": (125.0, 500.0),
    "google_genai:gemini-2.5-flash": (10.0, 40.0),
    "cohere:command-a-03-2025": (250.0, 1000.0),
}


async def _get_db() -> Any:
    """Mesmo banco de `vectora_background_tasks`/`vectora_background_runs` —
    não `checkpoints.db` (ver docstring equivalente em `kanban.py::_get_db`
    pro histórico do bug que essa correção fecha)."""
    from backend.scheduling.background_tasks import _get_db as _tasks_db

    return await _tasks_db()


def _preco(model_id: str) -> tuple[float, float] | None:
    if model_id in _PRECO_POR_MILHAO_CENTS:
        return _PRECO_POR_MILHAO_CENTS[model_id]
    # Ollama roda local: custo de API é zero de verdade, não desconhecido.
    if model_id.startswith("ollama:"):
        return (0.0, 0.0)
    return None


def estimate_cost_cents(model_id: str, usage: dict | None) -> float | None:
    """Custo estimado da run, ou `None` quando não dá pra saber.

    `None` é diferente de `0.0`: provider sem `usage_metadata` não gastou
    zero, apenas não informou.
    """
    if not usage:
        return None
    entrada = usage.get("input_tokens")
    saida = usage.get("output_tokens")
    if entrada is None and saida is None:
        return None

    precos = _preco(model_id)
    if precos is None:
        logger.info(
            "budget: modelo sem tabela de preço — custo fica desconhecido",
            extra={"model_id": model_id},
        )
        return None

    p_entrada, p_saida = precos
    return (int(entrada or 0) / 1_000_000) * p_entrada + (
        int(saida or 0) / 1_000_000
    ) * p_saida


async def record_run_cost(
    run_id: str, *, tokens_used: int | None, cost_cents: float | None
) -> None:
    """Persiste o consumo da run já concluída."""
    db = await _get_db()
    await db.execute(
        "UPDATE vectora_background_runs SET tokens_used = ?, "
        "estimated_cost_cents = ? WHERE id = ?",
        (tokens_used, cost_cents, run_id),
    )
    await db.commit()


async def accumulated_cents(task_id: str) -> tuple[float, int]:
    """`(total conhecido, quantas runs ficaram com custo desconhecido)`.

    O segundo valor existe pra a UI poder dizer "pelo menos X" em vez de
    fingir precisão que não há.
    """
    db = await _get_db()
    async with db.execute(
        "SELECT estimated_cost_cents FROM vectora_background_runs WHERE task_id = ?",
        (task_id,),
    ) as cur:
        linhas = await cur.fetchall()

    total = 0.0
    desconhecidas = 0
    for linha in linhas:
        valor = linha["estimated_cost_cents"]
        if valor is None:
            desconhecidas += 1
        else:
            total += float(valor)
    return total, desconhecidas


async def check_budget(task_id: str) -> bool:
    """`True` se a próxima run pode começar.

    Estourado: a task vira `blocked` com `block_kind="capability"` — a
    taxonomia do Sprint 16 pra "não dá pra continuar assim". O motivo fica
    no card em vez de a tarefa simplesmente parar de rodar em silêncio.
    """
    db = await _get_db()
    async with db.execute(
        "SELECT budget_cents FROM vectora_background_tasks WHERE id = ?",
        (task_id,),
    ) as cur:
        linha = await cur.fetchone()

    if linha is None:
        return True

    teto = linha["budget_cents"]
    if teto is None:
        # Sem budget definido o comportamento não muda — o corte é opt-in.
        return True

    total, desconhecidas = await accumulated_cents(task_id)
    if total < float(teto):
        return True

    from backend.scheduling.kanban import block_task

    detalhe = f"budget de {teto} centavos atingido (gasto {total:.2f})"
    if desconhecidas:
        detalhe += f", com {desconhecidas} run(s) de custo desconhecido"
    await block_task(task_id, "capability", detalhe)
    logger.info("budget: task %s bloqueada — %s", task_id, detalhe)
    return False
