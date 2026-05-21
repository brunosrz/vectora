#!/usr/bin/env python3
"""Script para rodar coverage dos arquivos target."""

import subprocess
import sys

# Arquivos que queremos medir cobertura
TARGET_MODULES = [
    "vectora/services/background.py",
    "vectora/services/debug_dump.py",
    "vectora/services/embedding.py",
    "vectora/ui/setup_wizard.py",
    "vectora/ui/chat.py",
    "vectora/ui/commands.py",
    "vectora/nodes/debug.py",
    "vectora/mcp/client.py",
    "vectora/mcp/server.py",
    "vectora/services/telemetry.py",
    "vectora/tools/fs.py",
    "vectora/testing/fixtures.py",
]

# Testes para rodar
TEST_FILES = [
    "tests/unit/test_services_background_worker.py",
    "tests/unit/test_services_debug_dump.py",
    "tests/unit/test_services_embedding.py",
    "tests/unit/test_ui_setup_wizard.py",
    "tests/unit/test_ui_chat.py",
    "tests/unit/test_ui_commands.py",
    "tests/unit/test_nodes_debug.py",
    "tests/unit/test_mcp_basic.py",
    "tests/unit/test_services_telemetry.py",
    "tests/unit/test_tools_fs.py",
    "tests/unit/test_testing_fixtures.py",
]

# Montar comando de cobertura
cmd = (
    ["python", "-m", "pytest"]
    + TEST_FILES
    + ["--cov=vectora", "--cov-report=term-missing"]
)

# Executar
result = subprocess.run(cmd, cwd="/home/user/vectora")
sys.exit(result.returncode)
