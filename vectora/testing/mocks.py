import re
from typing import Any, Self

from langchain_core.language_models import BaseLLM
from langchain_core.messages import AIMessage, BaseMessage
from langchain_core.outputs import LLMResult

from vectora.testing.message_factory import (
    ai_message_text,
    ai_message_with_tool_call,
)


class MockLLM(BaseLLM):
    """Mock LLM that returns predefined responses based on input patterns.

    This allows deterministic testing of the graph without calling real LLMs.
    Pattern matching is used to decide which tool to call or what text to return.
    """

    @property
    def _llm_type(self) -> str:
        return "mock"

    def _generate(  # ty: ignore[invalid-method-override]
        self,
        messages: list[BaseMessage],
        stop: list[str] | None = None,
        **kwargs: Any,
    ) -> LLMResult:
        """Generate a response based on message content patterns."""
        if not messages:
            return LLMResult(generations=[[]])

        last_message = messages[-1].content if messages else ""

        if isinstance(last_message, str):
            response = self._match_pattern(last_message, messages)
        else:
            response = ai_message_text("I don't understand that input.")

        return LLMResult(generations=[[response]])  # ty: ignore[invalid-argument-type]

    def _match_pattern(self: Self, text: str, messages: list[BaseMessage]) -> AIMessage:
        """Match input text against patterns and return appropriate response."""
        text_lower = text.lower()

        if "multiply" in text_lower or "multiplica" in text_lower:
            return self._handle_multiply(text)

        if "hello" in text_lower or "olá" in text_lower or "oi" in text_lower:
            return ai_message_text("Olá! Sou um assistente de IA. Como posso ajudá-lo?")

        return ai_message_text("Entendi sua mensagem. Como posso ajudá-lo?")

    def _handle_multiply(self: Self, text: str) -> AIMessage:
        """Extract numbers from multiply request and create tool call."""
        numbers = re.findall(r"\d+", text)

        if len(numbers) >= 2:
            a = float(numbers[0])
            b = float(numbers[1])
            return ai_message_with_tool_call(
                "multiply",
                {"a": a, "b": b},
                f"I'll multiply {a} by {b}.",
            )

        return ai_message_text(
            "Por favor, forneça dois números para multiplicar. "
            "Exemplo: 'multiplique 5 por 3'"
        )

    async def _agenerate(  # ty: ignore[invalid-method-override]
        self,
        messages: list[BaseMessage],
        stop: list[str] | None = None,
        **kwargs: Any,
    ) -> LLMResult:
        """Async version of _generate."""
        return self._generate(messages, stop, **kwargs)

    def bind_tools(self, tools: list[Any], **kwargs: Any) -> MockLLM:
        """Bind tools to this mock LLM.

        Required by LangChain interface. Returns self for chaining.
        """
        self._tools = tools
        return self
