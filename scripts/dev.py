"""
Runner de desenvolvimento — sobe backend e frontend simultaneamente.

Uso:
    uv run python scripts/dev.py [--port 8080]

Comportamento:
- Backend  : vectora server chat --port <PORT>   (FastAPI + proxy Next.js)
- Frontend : pnpm --dir chat dev                 (Next.js com hot-reload)
- Output de ambos aparece no mesmo terminal, prefixado por [backend] / [chat].
- Ctrl+C encerra os dois processos de forma limpa em qualquer SO.
- Se um dos processos morrer inesperadamente, o outro é encerrado junto.
"""

from __future__ import annotations

import os
import shutil
import signal
import subprocess  # nosec B404 — script de dev controlado, args hardcoded
import sys
import threading
import time

# ── Configuração ──────────────────────────────────────────────────────────────

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

PORT = "8080"
for i, arg in enumerate(sys.argv[1:], 1):
    if arg in ("--port", "-p") and i < len(sys.argv) - 1:
        PORT = sys.argv[i + 1]
        break

# ── Cores ANSI (desabilitadas no Windows sem suporte a VT) ───────────────────

if sys.platform == "win32":
    import ctypes

    ENABLE_VT = 0x0004
    kernel = ctypes.windll.kernel32  # type: ignore[attr-defined]
    handle = kernel.GetStdHandle(-11)
    mode = ctypes.c_ulong()
    kernel.GetConsoleMode(handle, ctypes.byref(mode))
    kernel.SetConsoleMode(handle, mode.value | ENABLE_VT)

RESET = "\033[0m"
BOLD = "\033[1m"
BLUE = "\033[94m"
GREEN = "\033[92m"
YELLOW = "\033[93m"
RED = "\033[91m"


def _prefix(text: str, color: str) -> str:
    return f"{color}{BOLD}{text}{RESET}"


# ── Resolve pnpm ──────────────────────────────────────────────────────────────


def find_pnpm() -> str:
    """Localiza o executável pnpm, preferindo pnpm.cmd no Windows."""
    if sys.platform == "win32":
        for name in ("pnpm.cmd", "pnpm.exe", "pnpm"):
            found = shutil.which(name)
            if found:
                return found
    found = shutil.which("pnpm")
    return found or "pnpm"


# ── Streaming de output ───────────────────────────────────────────────────────


def _stream(proc: subprocess.Popen, prefix: str) -> None:
    """Lê stdout do processo linha a linha e repassa com prefixo."""
    assert proc.stdout is not None
    try:
        for raw in proc.stdout:
            line = (
                raw if isinstance(raw, str) else raw.decode("utf-8", errors="replace")
            )
            sys.stdout.write(f"{prefix} {line}")
            sys.stdout.flush()
    except Exception:
        pass


# ── Main ──────────────────────────────────────────────────────────────────────


def main() -> None:
    pnpm = find_pnpm()

    env = {**os.environ, "VECTORA_LICENSE_BYPASS": "1"}

    backend_cmd = ["uv", "run", "vectora", "server", "chat", "--port", PORT]
    frontend_cmd = [pnpm, "--dir", "chat", "dev"]

    print(f"\n{BOLD}>> Vectora dev — backend ({PORT}) + Next.js (3000){RESET}")
    print(f"   Backend : {' '.join(backend_cmd)}")
    print(f"   Frontend: {' '.join(frontend_cmd)}")
    print(f"   Ctrl+C encerra ambos\n")

    backend = subprocess.Popen(  # nosec B603
        backend_cmd,
        cwd=ROOT,
        env=env,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        bufsize=1,
    )
    frontend = subprocess.Popen(  # nosec B603
        frontend_cmd,
        cwd=ROOT,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        bufsize=1,
    )

    procs = [backend, frontend]

    backend_prefix = _prefix("[backend]", BLUE)
    frontend_prefix = _prefix("[chat]   ", GREEN)

    threading.Thread(
        target=_stream, args=(backend, backend_prefix), daemon=True
    ).start()
    threading.Thread(
        target=_stream, args=(frontend, frontend_prefix), daemon=True
    ).start()

    def shutdown(sig: int | None = None, frame: object = None) -> None:
        print(f"\n{YELLOW}>> Encerrando processos...{RESET}")
        for p in procs:
            if p.poll() is None:
                p.terminate()
        for p in procs:
            try:
                p.wait(timeout=5)
            except subprocess.TimeoutExpired:
                p.kill()
        sys.exit(0)

    signal.signal(signal.SIGINT, shutdown)
    signal.signal(signal.SIGTERM, shutdown)

    # Aguarda — encerra ambos se qualquer um cair inesperadamente.
    while True:
        for p in procs:
            code = p.poll()
            if code is not None:
                label = "backend" if p is backend else "frontend"
                print(
                    f"\n{RED}>> {label} encerrou com código {code} — encerrando...{RESET}"
                )
                shutdown()
        time.sleep(0.4)


if __name__ == "__main__":
    main()
