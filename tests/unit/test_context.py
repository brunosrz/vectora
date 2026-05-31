"""Tests for vectora/context.py"""

from __future__ import annotations

import dataclasses

import pytest

from src.context import Context


def test_context_required_fields():
    ctx = Context(user_type="free", thread_id=1)
    assert ctx.user_type == "free"
    assert ctx.thread_id == 1


def test_context_user_id_default():
    ctx = Context(user_type="plus", thread_id=42)
    assert ctx.user_id == "default"


def test_context_immutable():
    ctx = Context(user_type="free", thread_id=1)
    try:
        ctx.user_type = "plus"  # type: ignore[misc]  # ty: ignore[invalid-assignment]
        pytest.fail("should be immutable")
    except (TypeError, dataclasses.FrozenInstanceError, AttributeError):
        pass  # esperado — frozen dataclass


def test_context_is_dataclass():
    assert dataclasses.is_dataclass(Context)


def test_context_different_user_types():
    for utype in ("free", "plus", "admin"):
        ctx = Context(user_type=utype, thread_id=1)
        assert ctx.user_type == utype
