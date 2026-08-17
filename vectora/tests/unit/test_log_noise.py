"""Redução de ruído de log — deepagents e langchain não poluem o console.

Verifica que o QUIET_MODE silencia os loggers do deepagents.
"""

from __future__ import annotations

import logging
from unittest.mock import patch


def test_deepagents_logger_silenced_in_quiet_mode() -> None:
    """Logger 'deepagents' fica em CRITICAL após setup_logging com QUIET_MODE."""
    import importlib

    import backend.services.log_setup as log_setup_mod

    root = logging.getLogger()
    orig_handlers = root.handlers[:]
    root.handlers.clear()

    with patch.dict("os.environ", {"QUIET_MODE": "true", "LOG_LEVEL": "INFO"}):
        importlib.reload(log_setup_mod)
        log_setup_mod.setup_logging()

    try:
        da_logger = logging.getLogger("deepagents")
        assert da_logger.level == logging.CRITICAL, (
            f"deepagents logger deveria estar em CRITICAL, está em {da_logger.level}"
        )
    finally:
        root.handlers = orig_handlers
        importlib.reload(log_setup_mod)


def test_harness_profiles_logger_silenced() -> None:
    """Logger 'deepagents.profiles.harness.harness_profiles' fica em CRITICAL."""
    import importlib

    import backend.services.log_setup as log_setup_mod

    root = logging.getLogger()
    orig_handlers = root.handlers[:]
    root.handlers.clear()

    with patch.dict("os.environ", {"QUIET_MODE": "true", "LOG_LEVEL": "INFO"}):
        importlib.reload(log_setup_mod)
        log_setup_mod.setup_logging()

    try:
        harness_logger = logging.getLogger(
            "deepagents.profiles.harness.harness_profiles"
        )
        assert harness_logger.level == logging.CRITICAL
    finally:
        root.handlers = orig_handlers
        importlib.reload(log_setup_mod)
