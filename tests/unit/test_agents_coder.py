"""Tests for vectora/agents/coder.py"""

from __future__ import annotations

from typing import TYPE_CHECKING
from unittest.mock import AsyncMock, patch

import pytest
from langchain_core.messages import AIMessage, HumanMessage

from vectora.agents.coder import SYSTEM_PROMPT, coder

if TYPE_CHECKING:
    from vectora.state import State


def test_system_prompt_exists():
    assert isinstance(SYSTEM_PROMPT, str)
    assert len(SYSTEM_PROMPT) > 200


def test_system_prompt_contains_identity():
    assert "Vectora" in SYSTEM_PROMPT
    assert "LangGraph" in SYSTEM_PROMPT


def test_system_prompt_describes_tools():
    assert "terminal" in SYSTEM_PROMPT
    assert "git" in SYSTEM_PROMPT
    assert "file" in SYSTEM_PROMPT.lower()


def test_system_prompt_git_policy():
    # deve documentar que git é livre
    assert "git" in SYSTEM_PROMPT
    assert (
        "confirmação" in SYSTEM_PROMPT
        or "permissão" in SYSTEM_PROMPT
        or "livre" in SYSTEM_PROMPT
    )


@pytest.mark.asyncio
async def test_coder_calls_invoke_llm():
    state: State = {
        "messages": [HumanMessage(content="cria um arquivo main.py")],
        "session_metadata": {},
    }
    mock_response = {"messages": [AIMessage(content="Criado!")]}

    with patch("vectora.agents.coder.invoke_llm", new_callable=AsyncMock) as mock_llm:
        mock_llm.return_value = mock_response
        result = await coder(state)

    mock_llm.assert_called_once()
    assert result == mock_response


@pytest.mark.asyncio
async def test_coder_passes_system_prompt():
    state: State = {"messages": [HumanMessage(content="test")], "session_metadata": {}}

    with patch("vectora.agents.coder.invoke_llm", new_callable=AsyncMock) as mock_llm:
        mock_llm.return_value = {"messages": [AIMessage(content="ok")]}
        await coder(state)

    _, kwargs = mock_llm.call_args
    assert kwargs["system_prompt"] is SYSTEM_PROMPT
