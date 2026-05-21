from typing import Any

from langchain_core.messages import AIMessage, HumanMessage, ToolCall, ToolMessage


def human_message(text: str) -> HumanMessage:
    """Create a HumanMessage for test input.

    Args:
        text: The message text

    Returns:
        HumanMessage instance
    """
    return HumanMessage(content=text)


def ai_message_with_tool_call(
    tool_name: str,
    tool_input: dict[str, Any],
    response_text: str = "",
) -> AIMessage:
    """Create an AIMessage with a tool call for testing.

    Args:
        tool_name: Name of the tool to call (e.g., "multiply")
        tool_input: Arguments dict for the tool (e.g., {"a": 5, "b": 3})
        response_text: Optional text response before tool call

    Returns:
        AIMessage with tool call
    """
    tool_calls = [
        ToolCall(
            id=f"call_{tool_name}_test",
            name=tool_name,
            args=tool_input,
        )
    ]

    return AIMessage(
        content=response_text or f"I'll use the {tool_name} tool.",
        tool_calls=tool_calls,
    )


def ai_message_text(text: str) -> AIMessage:
    """Create a plain text AIMessage (no tool calls).

    Args:
        text: The response text

    Returns:
        AIMessage instance
    """
    return AIMessage(content=text)


def tool_message(
    tool_name: str,
    result: Any,
    tool_call_id: str = "call_test",
) -> ToolMessage:
    """Create a ToolMessage from tool execution result.

    Args:
        tool_name: Name of the tool that was called
        result: The result returned by the tool
        tool_call_id: The ID of the tool call this result belongs to

    Returns:
        ToolMessage instance
    """
    return ToolMessage(
        content=str(result),
        tool_call_id=tool_call_id,
        name=tool_name,
    )
