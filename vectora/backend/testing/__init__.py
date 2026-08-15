"""Test Fixtures and Utilities for Unit Testing.

Fixtures de banco (checkpointer/temp_db), factories de `VMessage` e
assertions — tudo nativo, sem `langchain_core`.
"""

from __future__ import annotations

from backend.testing.assertions import (
    assert_last_message_is_ai,
    assert_message_contains_text,
    assert_tool_called,
    assert_tool_called_with_args,
    assert_tool_result_in_messages,
)
from backend.testing.fixtures import (
    checkpointer,
    temp_db,
)
from backend.testing.message_factory import (
    make_assistant_message,
    make_tool_result,
    make_user_message,
)
from backend.testing.mocks import FakeChatClient, text_chunk, text_response

__all__ = [
    "FakeChatClient",
    "assert_last_message_is_ai",
    "assert_message_contains_text",
    "assert_tool_called",
    "assert_tool_called_with_args",
    "assert_tool_result_in_messages",
    "checkpointer",
    "make_assistant_message",
    "make_tool_result",
    "make_user_message",
    "temp_db",
    "text_chunk",
    "text_response",
]
