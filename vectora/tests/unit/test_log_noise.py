"""Redução de ruído de log — deepagents e langchain não poluem o console.

Verifica que o QUIET_MODE silencia os loggers do deepagents e que o
_register_profiles() emite DEBUG (não INFO) após a mudança.
"""

from __future__ import annotations

import logging
from unittest.mock import MagicMock, patch


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


def test_profiles_register_emits_debug_not_info() -> None:
    """_register_profiles emite DEBUG, não INFO, para o sumário de perfis."""
    deepagents_mock = MagicMock()
    deepagents_mock.HarnessProfile = MagicMock(return_value=MagicMock())
    deepagents_mock.GeneralPurposeSubagentProfile = MagicMock(return_value=MagicMock())
    deepagents_mock.register_harness_profile = MagicMock()

    with (
        patch.dict("sys.modules", {"deepagents": deepagents_mock}),
        patch("logging.Logger.info") as mock_info,
        patch("logging.Logger.debug") as mock_debug,
    ):
        import importlib

        import backend.services.profiles as profiles_mod

        importlib.reload(profiles_mod)
        profiles_mod._register_profiles()

    called_info_msgs = [str(c) for c in mock_info.call_args_list]
    assert not any("perfis de harness registrados" in m for m in called_info_msgs), (
        "O sumário de perfis não deve ser INFO; deve ser DEBUG"
    )

    called_debug_msgs = [str(c) for c in mock_debug.call_args_list]
    assert any(
        "registrado" in m or "harness" in m.lower() for m in called_debug_msgs
    ), "O sumário de perfis deve ser emitido em DEBUG"
