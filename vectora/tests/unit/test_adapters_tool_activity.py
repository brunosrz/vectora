"""ToolActivityEvent no adapt_stream.

O adaptador deve emitir `tool_activity` em on_tool_start (elapsed_ms=None)
e em on_tool_end (elapsed_ms≥0) para alimentar o AgentStatusLine.
"""

from __future__ import annotations

import json

import pytest

from backend.api.adapters import adapt_stream


@pytest.fixture(autouse=True)
def _isolated(_no_thread_persistence):
    pass


def _parse(sse: str) -> dict:
    assert sse.startswith("data: ")
    return json.loads(sse[len("data: ") :].strip())


async def _agen(events):
    for ev in events:
        yield ev


def _tool_start_event(tool_name: str, args: dict) -> dict:
    return {
        "event": "on_tool_start",
        "name": tool_name,
        "run_id": "run-abc",
        "data": {"input": args},
    }


def _tool_end_event(tool_name: str, output: str = "ok") -> dict:
    return {
        "event": "on_tool_end",
        "name": tool_name,
        "run_id": "run-abc",
        "data": {"output": output},
    }


@pytest.mark.asyncio
async def test_tool_activity_emitted_on_tool_start():
    """on_tool_start → tool_activity com elapsed_ms=None antes de tool_call."""
    events = [_tool_start_event("file_edit", {"path": "auth.py", "content": "..."})]
    out = [_parse(s) async for s in adapt_stream(_agen(events), "tid")]

    activity = [e for e in out if e["type"] == "tool_activity"]
    assert len(activity) == 1, "deve emitir exatamente 1 tool_activity no start"
    ev = activity[0]
    assert ev["tool_name"] == "file_edit"
    assert ev["elapsed_ms"] is None
    assert "args_preview" in ev


@pytest.mark.asyncio
async def test_tool_activity_args_preview_contains_path():
    """args_preview deve conter substring identificável do arquivo (path)."""
    events = [_tool_start_event("file_edit", {"path": "backend/api/auth.py"})]
    out = [_parse(s) async for s in adapt_stream(_agen(events), "tid")]

    activity = [e for e in out if e["type"] == "tool_activity"]
    assert "auth.py" in activity[0]["args_preview"]


@pytest.mark.asyncio
async def test_tool_activity_args_preview_truncated_to_80():
    """Previews muito longos devem ser truncados a no máximo 80 caracteres."""
    long_path = "a" * 200
    events = [_tool_start_event("file_edit", {"path": long_path})]
    out = [_parse(s) async for s in adapt_stream(_agen(events), "tid")]

    activity = [e for e in out if e["type"] == "tool_activity"]
    assert len(activity[0]["args_preview"]) <= 80


@pytest.mark.asyncio
async def test_tool_activity_emitted_on_tool_end_with_elapsed():
    """on_tool_end após on_tool_start → tool_activity com elapsed_ms ≥ 0."""
    events = [
        _tool_start_event("file_edit", {"path": "auth.py"}),
        _tool_end_event("file_edit"),
    ]
    out = [_parse(s) async for s in adapt_stream(_agen(events), "tid")]

    activities = [e for e in out if e["type"] == "tool_activity"]
    # start + end = 2 tool_activity events
    assert len(activities) == 2, (
        f"esperado 2 tool_activity, got {len(activities)}: {activities}"
    )
    end_ev = activities[1]
    assert end_ev["tool_name"] == "file_edit"
    assert isinstance(end_ev["elapsed_ms"], int)
    assert end_ev["elapsed_ms"] >= 0


@pytest.mark.asyncio
async def test_tool_activity_order_before_tool_call():
    """tool_activity (start) deve aparecer ANTES de tool_call na sequência SSE."""
    events = [_tool_start_event("web_search", {"query": "python async"})]
    out = [_parse(s) async for s in adapt_stream(_agen(events), "tid")]

    types = [e["type"] for e in out]
    assert "tool_activity" in types
    assert "tool_call" in types
    assert types.index("tool_activity") < types.index("tool_call")


@pytest.mark.asyncio
async def test_tool_activity_on_end_after_tool_result():
    """tool_activity (end) deve aparecer APÓS tool_result na sequência SSE."""
    events = [
        _tool_start_event("web_search", {"query": "python"}),
        _tool_end_event("web_search", "resultado"),
    ]
    out = [_parse(s) async for s in adapt_stream(_agen(events), "tid")]

    types = [e["type"] for e in out]
    activity_indices = [i for i, t in enumerate(types) if t == "tool_activity"]
    result_index = types.index("tool_result")
    # O segundo tool_activity (end) deve vir após tool_result
    assert activity_indices[1] > result_index


@pytest.mark.asyncio
async def test_multiple_tools_activity_tracked_independently():
    """Duas tools distintas geram dois pares de tool_activity com nomes corretos."""
    events = [
        _tool_start_event("file_edit", {"path": "a.py"}),
        _tool_end_event("file_edit"),
        _tool_start_event("web_search", {"query": "x"}),
        _tool_end_event("web_search"),
    ]
    out = [_parse(s) async for s in adapt_stream(_agen(events), "tid")]

    activities = [e for e in out if e["type"] == "tool_activity"]
    assert len(activities) == 4
    names = [a["tool_name"] for a in activities]
    assert names[0] == "file_edit"
    assert names[1] == "file_edit"
    assert names[2] == "web_search"
    assert names[3] == "web_search"
