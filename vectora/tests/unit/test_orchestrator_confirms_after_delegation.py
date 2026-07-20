"""Sprint 0.3 — o orchestrator/coder precisam sempre fechar o turno com texto
de confirmação depois de create_artifact/write_todos, mesmo quando a criação
aconteceu dentro de uma delegação via task(). Bug real observado ao vivo: o
turno terminava só com tool calls / subagent output cru, sem nenhuma frase
pro usuário, e o usuário achava que o pedido tinha falhado.
"""

from __future__ import annotations

from backend.agents.coder import SYSTEM_PROMPT as CODER_PROMPT
from backend.services.agent_factory import _ORCHESTRATOR_PROMPT


def test_orchestrator_exige_texto_apos_delegacao():
    assert "MUST close the turn with your" in _ORCHESTRATOR_PROMPT
    assert "create_artifact" in _ORCHESTRATOR_PROMPT
    assert "write_todos" in _ORCHESTRATOR_PROMPT


def test_orchestrator_nao_permite_turno_so_com_tool_calls():
    # Erro/borda: a instrução precisa nomear explicitamente o sintoma (turno
    # terminando só com tool call/subagent output) — não só uma frase vaga
    # tipo "seja educado", que o modelo pode ignorar.
    assert "ends with only tool calls" in _ORCHESTRATOR_PROMPT


def test_coder_confirma_path_do_artifact_e_contagem_de_todos():
    assert "create_artifact" in CODER_PROMPT
    assert "file path" in CODER_PROMPT
    assert "write_todos" in CODER_PROMPT
    assert "how many tasks" in CODER_PROMPT
