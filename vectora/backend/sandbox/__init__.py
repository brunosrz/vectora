"""AI Jail nativo — sandbox de execução por workspace (`vectora.toml`, seção
`[sandbox]`). MVP Linux-first via bubblewrap; ver `runner.py` para o ponto
de integração único usado pelas tools (`terminal`, git).
"""

from __future__ import annotations

from backend.sandbox.linux import SandboxResult
from backend.sandbox.policy import SandboxPolicy, parse_policy
from backend.sandbox.runner import run_sandboxed

__all__ = ["SandboxPolicy", "SandboxResult", "parse_policy", "run_sandboxed"]
