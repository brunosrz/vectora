#!/usr/bin/env python3
"""Script para verificar cobertura dos arquivos-alvo."""

import subprocess
import sys

# Arquivos targets que devem ter 50% de cobertura
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

# Rodar pytest com cobertura
cmd = [
    "python",
    "-m",
    "pytest",
    "tests/unit/",
    "--cov=vectora",
    "--cov-report=term-missing",
    "--tb=no",
    "-q",
]

print("Executando testes com cobertura completa...")
print("=" * 60)

result = subprocess.run(cmd, capture_output=True, text=True)

# Extrair output
output_lines = result.stdout.split("\n")

# Procurar por linhas de cobertura dos nossos arquivos
print("\nCOVERTURA DOS ARQUIVOS TARGET:")
print("=" * 60)

coverage_data = {}
in_coverage_table = False

for line in output_lines:
    line = line.strip()

    # Procurar por linhas de cobertura
    for target in TARGET_MODULES:
        if target in line or target.replace("/", "\\") in line:
            # Extrair % de cobertura
            parts = line.split()
            for i, part in enumerate(parts):
                if "%" in part:
                    coverage_pct = int(part.rstrip("%"))
                    print(f"  {target}: {coverage_pct}%", end="")
                    if coverage_pct >= 50:
                        print(" ✅")
                    else:
                        print(f" (Precisa de {50 - coverage_pct}%)")
                    break
            break

print("\n" + "=" * 60)
print(result.stdout)
