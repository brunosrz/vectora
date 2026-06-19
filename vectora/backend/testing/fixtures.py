import os
import tempfile
from collections.abc import AsyncGenerator
from pathlib import Path

import pytest
from langgraph.checkpoint.sqlite.aio import AsyncSqliteSaver

from backend.testing.mocks import MockLLM


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
