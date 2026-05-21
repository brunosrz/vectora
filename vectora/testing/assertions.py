from typing import Any

from langchain_core.messages import AIMessage, BaseMessage, ToolMessage


def assert_tool_called(
    messages: list[BaseMessage],
    tool_name: str,
) -> None:
    """Assert that a specific tool was called in the message sequence.

    Args:
        messages: List of messages from graph execution
        tool_name: Name of the tool to verify was called

    Raises:
        AssertionError: If tool was not called
    """
    for msg in messages:
        if isinstance(msg, AIMessage) and msg.tool_calls:
            for tool_call in msg.tool_calls:
                if tool_call.name == tool_name:  # ty: ignore[unresolved-attribute]
                    return

    msg_0 = f"Tool '{tool_name}' was not called. Messages: {[type(m).__name__ for m in messages]}"
    raise AssertionError(msg_0)


def assert_tool_called_with_args(
    messages: list[BaseMessage],
    tool_name: str,
    expected_args: dict[str, Any],
) -> None:
    """Assert that a specific tool was called with expected arguments.

    Args:
        messages: List of messages from graph execution
        tool_name: Name of the tool
        expected_args: Expected arguments dict

    Raises:
        AssertionError: If tool was not called with those args
    """
    for msg in messages:
        if isinstance(msg, AIMessage) and msg.tool_calls:
            for tool_call in msg.tool_calls:
                if tool_call.name == tool_name:  # ty: ignore[unresolved-attribute]
                    if tool_call.args == expected_args:  # ty: ignore[unresolved-attribute]
                        return
                    msg_0 = (
                        f"Tool '{tool_name}' called with {tool_call.args}, "  # ty: ignore[unresolved-attribute]
                        f"expected {expected_args}"
                    )
                    raise AssertionError(msg_0)

    msg_0 = f"Tool '{tool_name}' with args {expected_args} was not found in message sequence"
    raise AssertionError(msg_0)


def assert_tool_result_in_messages(
    messages: list[BaseMessage],
    tool_name: str,
    expected_result: Any,
) -> None:
    """Assert that a tool's result appears in the message sequence.

    Args:
        messages: List of messages from graph execution
        tool_name: Name of the tool
        expected_result: Expected result (will be converted to string)

    Raises:
        AssertionError: If result not found
    """
    expected_str = str(expected_result)

    for msg in messages:
        if isinstance(msg, ToolMessage) and msg.name == tool_name:
            if expected_str in msg.content:
                return

    msg_0 = f"Result '{expected_result}' from tool '{tool_name}' not found in messages"
    raise AssertionError(msg_0)


def assert_message_contains_text(
    messages: list[BaseMessage],
    text: str,
) -> None:
    """Assert that any message contains specific text.

    Args:
        messages: List of messages
        text: Text to find

    Raises:
        AssertionError: If text not found in any message
    """
    for msg in messages:
        if hasattr(msg, "content") and text in msg.content:
            return

    msg_0 = (
        f"Text '{text}' not found in any message. "
        f"Messages: {[getattr(m, 'content', '')[:50] for m in messages]}"
    )
    raise AssertionError(msg_0)


def assert_last_message_is_ai(messages: list[BaseMessage]) -> AIMessage:
    """Assert that the last message is from the AI.

    Args:
        messages: List of messages

    Returns:
        The last AIMessage

    Raises:
        AssertionError: If last message is not from AI
    """
    if not messages:
        msg = "No messages in sequence"
        raise AssertionError(msg)

    if not isinstance(messages[-1], AIMessage):
        msg = f"Last message is {type(messages[-1]).__name__}, expected AIMessage"
        raise AssertionError(msg)

    return messages[-1]
