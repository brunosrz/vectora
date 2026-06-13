import os
import tempfile
from collections.abc import AsyncGenerator
from pathlib import Path

import pytest
from langchain_core.messages import SystemMessage
from langgraph.checkpoint.sqlite.aio import AsyncSqliteSaver
from langgraph.graph.state import CompiledStateGraph

from backend.agents.orchestrator import _ORCHESTRATOR_PROMPT as _DEFAULT_SYSTEM_PROMPT
from backend.context import Context
from backend.state import State
from backend.testing.mocks import MockLLM


@pytest.fixture
def test_context() -> Context:
    """Provide a test context with user_type='plus'."""
    return Context(user_type="plus", thread_id=1)


@pytest.fixture
def mock_llm() -> MockLLM:
    """Provide a mock LLM for deterministic testing."""
    return MockLLM()


@pytest.fixture
async def temp_db() -> AsyncGenerator[str]:
    """Create a temporary SQLite database for testing.

    Yields the file path (not DSN), cleans up after test.
    """
    temp_dir = tempfile.mkdtemp()
    db_path = Path(temp_dir) / "test.db"

    yield str(db_path)

    if db_path.exists():
        db_path.unlink()


@pytest.fixture
async def checkpointer(temp_db: str) -> AsyncGenerator[AsyncSqliteSaver]:
    """Provide an AsyncSqliteSaver with temporary database.

    The checkpointer is used for persisting graph state.
    """
    async with AsyncSqliteSaver.from_conn_string(temp_db) as saver:
        yield saver


@pytest.fixture
def vector_store_dir() -> str:
    """Provide a temporary LanceDB directory for testing.

    LanceDB is used for vector storage in tests.
    This is automatically cleaned up after the test.
    """
    temp_dir = tempfile.mkdtemp()
    os.environ["LANCEDB_DIR"] = temp_dir
    return temp_dir


@pytest.fixture
async def test_graph(
    mock_llm: MockLLM, checkpointer: AsyncSqliteSaver
) -> CompiledStateGraph[State, Context, State, State]:  # ty: ignore[invalid-type-arguments]
    """Provide a compiled graph with mock LLM.

    This is the main fixture for testing the graph execution.
    Uses a mock LLM instead of real Ollama for deterministic responses.
    """

    async def call_llm_with_mock(state: State, runtime: dict) -> dict:
        """Call LLM using the mock instead of real providers."""
        from backend.tools import TOOLS

        llm_with_tools = mock_llm.bind_tools(TOOLS)

        # Prepend Vectora system prompt
        system_prompt = SystemMessage(content=_DEFAULT_SYSTEM_PROMPT)
        messages_with_system = [system_prompt, *list(state["messages"])]

        result_text = ""
        async for chunk in llm_with_tools.astream(messages_with_system):
            if isinstance(chunk, str):
                result_text += chunk

        # For testing, create a simple AI message from the streamed content
        from langchain_core.messages import AIMessage

        result = AIMessage(content=result_text)
        return {"messages": [result]}

    from langgraph.constants import END, START
    from langgraph.graph.state import StateGraph
    from langgraph.prebuilt.tool_node import ToolNode, tools_condition

    from backend.tools import TOOLS

    builder = StateGraph(  # type: ignore[type-arg,arg-type]
        state_schema=State,  # ty: ignore[invalid-argument-type]
        context_schema=Context,
        input_schema=State,  # ty: ignore[invalid-argument-type]
        output_schema=State,  # ty: ignore[invalid-argument-type]
    )

    tool_node = ToolNode(tools=TOOLS)

    builder.add_node("call_llm", call_llm_with_mock)  # ty: ignore[invalid-argument-type]
    builder.add_node("tools", tool_node)

    builder.add_edge(START, "call_llm")
    builder.add_conditional_edges("call_llm", tools_condition, ["tools", END])
    builder.add_edge("tools", "call_llm")

    return builder.compile(checkpointer=checkpointer)  # type: ignore
