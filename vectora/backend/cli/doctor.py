"""``vectora doctor`` — encontra e limpa sidecars órfãos (nats-server).

Mitigação imediata para processos já acumulados numa máquina antes desta
correção existir (ver Sprint NATS fix): varre TODOS os processos
``nats-server`` do sistema por nome de imagem, não só os PIDs conhecidos
pelo pid file de ``backend/scheduling/nats_sidecar.py`` — órfãos de
sessões anteriores ao fix (ou de bugs anteriores) podem ter caído fora
até dessa lista.
"""

from __future__ import annotations

import argparse
import shutil
import subprocess  # nosec B404 — só consulta/mata processos já identificados por nome, sem shell
import sys
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from rich.console import Console


def _find_nats_server_pids_win32() -> list[int]:
    tasklist = shutil.which("tasklist")
    if tasklist is None:
        return []
    try:
        out = subprocess.run(  # noqa: S603  # nosec B603
            [tasklist, "/NH", "/FI", "IMAGENAME eq nats-server.exe"],
            capture_output=True,
            text=True,
            timeout=5,
            check=False,
        )
    except Exception:
        return []
    pids: list[int] = []
    for line in (out.stdout or "").splitlines():
        parts = line.split()
        if len(parts) >= 2 and parts[1].isdigit():
            pids.append(int(parts[1]))
    return pids


def _find_nats_server_pids_posix() -> list[int]:
    pgrep = shutil.which("pgrep")
    if pgrep is None:
        return []
    try:
        out = subprocess.run(  # noqa: S603  # nosec B603
            [pgrep, "-f", "nats-server"],
            capture_output=True,
            text=True,
            timeout=5,
            check=False,
        )
    except Exception:
        return []
    return [int(p) for p in (out.stdout or "").split() if p.isdigit()]


def find_nats_server_pids() -> list[int]:
    """Varre o sistema por nome de imagem — não depende de nenhum PID
    file conhecido, então acha órfãos que o rastreamento normal já
    perdeu (ex.: de antes desta correção)."""
    if sys.platform == "win32":
        return _find_nats_server_pids_win32()
    return _find_nats_server_pids_posix()


def run_doctor(args: argparse.Namespace) -> None:
    from rich.console import Console

    from backend.scheduling.nats_sidecar import kill_orphan_pid

    console = Console()
    pids = find_nats_server_pids()

    if not pids:
        console.print("[green]✔ Nenhum sidecar nats-server órfão encontrado.[/green]")
        return

    console.print(
        f"[yellow]Encontrado(s) {len(pids)} processo(s) nats-server: {pids}[/yellow]"
    )

    yes = getattr(args, "yes", False)
    if not yes:
        answer = input("Finalizar todos? [y/N] ").strip().lower()
        if answer not in ("y", "yes", "s", "sim"):
            console.print("Cancelado — nenhum processo finalizado.")
            return

    for pid in pids:
        kill_orphan_pid(pid)

    console.print(f"[green]✔ {len(pids)} processo(s) finalizado(s).[/green]")
