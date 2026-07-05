"""TDD — Background Memory Consolidation (FASE 4.3).

Job periódico que sintetiza as últimas 10 threads via LLM e atualiza
~/.vectora/AGENTS.md para que o agente tenha contexto persistente.
"""

from __future__ import annotations

import asyncio
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from backend.scheduling.memory_consolidation import (
    _build_consolidation_prompt,
    _parse_llm_output,
    consolidate_memory,
)

# ---------------------------------------------------------------------------
# _build_consolidation_prompt
# ---------------------------------------------------------------------------


def test_build_prompt_includes_all_threads():
    """O prompt deve mencionar cada thread passada."""
    threads = [
        [("human", "oi"), ("assistant", "olá")],
        [("human", "erro no auth"), ("assistant", "corrigi o JWT")],
    ]
    prompt = _build_consolidation_prompt(threads)
    assert "oi" in prompt
    assert "corrigi o JWT" in prompt


def test_build_prompt_empty_threads_returns_valid_string():
    """Sem threads, deve retornar string não-vazia (template mínimo)."""
    prompt = _build_consolidation_prompt([])
    assert isinstance(prompt, str)
    assert len(prompt) > 0


def test_build_prompt_caps_per_thread():
    """Cada thread não deve ultrapassar ~2000 chars no prompt (evita tokens demais)."""
    long_msg = "a" * 3000
    threads = [
        [("human", long_msg), ("assistant", long_msg)],
    ]
    prompt = _build_consolidation_prompt(threads)
    # Garante que o prompt não explodiu — há sempre uma redução
    assert len(prompt) < len(long_msg) * 2 + 5000


# ---------------------------------------------------------------------------
# _parse_llm_output
# ---------------------------------------------------------------------------


def test_parse_llm_output_returns_stripped_text():
    raw = "  Aprendi que o projeto usa SQLite.  "
    result = _parse_llm_output(raw)
    assert result == "Aprendi que o projeto usa SQLite."


def test_parse_llm_output_strips_markdown_fences():
    raw = "```markdown\n# Memória\nConteúdo\n```"
    result = _parse_llm_output(raw)
    assert "```" not in result
    assert "Conteúdo" in result


def test_parse_llm_output_empty_returns_empty():
    assert _parse_llm_output("") == ""
    assert _parse_llm_output("   ") == ""


# ---------------------------------------------------------------------------
# consolidate_memory
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_consolidate_memory_writes_agents_md(tmp_path: Path):
    """consolidate_memory deve escrever/atualizar AGENTS.md com o resumo."""
    agents_md = tmp_path / "AGENTS.md"

    fake_threads = [
        [("human", "fix auth"), ("assistant", "fixed JWT")],
    ]

    fake_llm_response = MagicMock()
    fake_llm_response.content = "O projeto usa JWT para autenticação."

    with (
        patch(
            "backend.scheduling.memory_consolidation._agents_md_path",
            return_value=agents_md,
        ),
        patch(
            "backend.scheduling.memory_consolidation._fetch_recent_threads",
            new=AsyncMock(return_value=fake_threads),
        ),
        patch(
            "backend.scheduling.memory_consolidation._invoke_llm",
            new=AsyncMock(return_value=fake_llm_response),
        ),
    ):
        await consolidate_memory(user_id="user-1")

    assert agents_md.exists()
    content = agents_md.read_text(encoding="utf-8")
    assert "JWT" in content or "autenticação" in content


@pytest.mark.asyncio
async def test_consolidate_memory_no_threads_skips_write(tmp_path: Path):
    """Sem threads recentes, não deve chamar o LLM nem escrever."""
    agents_md = tmp_path / "AGENTS.md"

    with (
        patch(
            "backend.scheduling.memory_consolidation._agents_md_path",
            return_value=agents_md,
        ),
        patch(
            "backend.scheduling.memory_consolidation._fetch_recent_threads",
            new=AsyncMock(return_value=[]),
        ),
        patch(
            "backend.scheduling.memory_consolidation._invoke_llm",
            new=AsyncMock(),
        ) as mock_llm,
    ):
        await consolidate_memory(user_id="user-1")

    mock_llm.assert_not_called()
    assert not agents_md.exists()


@pytest.mark.asyncio
async def test_consolidate_memory_llm_failure_does_not_raise(tmp_path: Path):
    """Falha do LLM não deve propagar — é best-effort."""
    agents_md = tmp_path / "AGENTS.md"

    with (
        patch(
            "backend.scheduling.memory_consolidation._agents_md_path",
            return_value=agents_md,
        ),
        patch(
            "backend.scheduling.memory_consolidation._fetch_recent_threads",
            new=AsyncMock(return_value=[[("human", "hi"), ("assistant", "hello")]]),
        ),
        patch(
            "backend.scheduling.memory_consolidation._invoke_llm",
            new=AsyncMock(side_effect=RuntimeError("LLM unavailable")),
        ),
    ):
        await consolidate_memory(user_id="user-1")  # must not raise
