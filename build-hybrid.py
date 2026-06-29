#!/usr/bin/env python
"""Build híbrido: Nuitka compila o pacote backend -> backend.pyd; PyInstaller
empacota launcher + backend.pyd + libs Python -> vectora.exe.

Uso:  python build-hybrid.py [--jobs N]   (NUITKA_JOBS=N também funciona)
"""

import os
import subprocess  # nosec B404
import sys
from pathlib import Path

ROOT = Path(__file__).parent
VECTORA = ROOT / "vectora"
SEP = os.pathsep

# Libs que o backend importa e que o PyInstaller NÃO vê (backend.pyd é opaco).
# Confirmar/expandir com o smoke test do .exe.
COLLECT_ALL = [
    "langchain",
    "langchain_core",
    "langgraph",
    "deepagents",
    "langchain_openai",
    "langchain_google_genai",
    "langchain_cohere",
    "fastapi",
    "starlette",
    "uvicorn",
    "pydantic",
    "pydantic_core",
    "google",
    "lancedb",
    "aiosqlite",
    "httpx",
]


def run(cmd: list, cwd: Path, desc: str, env: dict | None = None) -> None:
    print(f"\n{'=' * 70}\n-> {desc}\n{'=' * 70}\n$ {' '.join(map(str, cmd))}\n")
    merged = {**os.environ, **(env or {})}
    if subprocess.run(cmd, cwd=str(cwd), env=merged).returncode != 0:  # noqa: S603  # nosec B603
        sys.exit(f"FALHA: {desc}")


def main() -> None:
    jobs = os.environ.get("NUITKA_JOBS", "2")
    if "--jobs" in sys.argv:
        jobs = sys.argv[sys.argv.index("--jobs") + 1]

    # Fase 1 — Nuitka: pacote backend -> backend.pyd (só backend vira C)
    run(
        [
            "uv",
            "run",
            "nuitka",
            "--mode=package",
            "--msvc=latest",
            f"--jobs={jobs}",
            f"--output-dir={VECTORA / 'dist-nuitka'}",
            "--include-module=backend.services.ipc_pipe_win",
            f"--report={ROOT / 'nuitka-report.xml'}",
            "backend",
        ],
        cwd=VECTORA,
        desc="Nuitka --mode=package backend -> backend.pyd",
    )
    pyd = next((VECTORA / "dist-nuitka").glob("backend*.pyd"), None)
    if not pyd:
        sys.exit("backend.pyd não gerado")
    print(f"OK: {pyd}")

    # Fase 2 — PyInstaller: launcher + backend.pyd + libs -> vectora.exe
    collect: list[str] = []
    for pkg in COLLECT_ALL:
        collect += ["--collect-all", pkg]

    # Módulos declarados pelos hooks do PyInstaller mas não instalados no projeto.
    # Excluir explicitamente para silenciar os "Hidden import X not found!" warnings.
    exclude_modules = [
        "pycparser.lextab",  # gerado em runtime pelo pycparser, não existe no venv
        "pycparser.yacctab",  # idem
        "pysqlite2",  # dialeto opcional do SQLAlchemy
        "MySQLdb",  # dialeto opcional do SQLAlchemy
    ]
    excludes: list[str] = []
    for mod in exclude_modules:
        excludes += ["--exclude-module", mod]

    run(
        [
            "uv",
            "run",
            "python",
            "-m",
            "PyInstaller",
            "--onefile",
            "--name=vectora",
            f"--distpath={ROOT / 'dist'}",
            f"--workpath={ROOT / 'build' / 'pyinstaller'}",
            f"--specpath={ROOT / 'build'}",
            "--add-binary",
            f"{pyd}{SEP}.",
            "--add-data",
            f"{VECTORA / 'frontend' / 'dist'}{SEP}chat_static",
            "--add-data",
            f"{VECTORA / 'backend' / 'assets'}{SEP}backend/assets",
            *collect,
            *excludes,
            str(VECTORA / "launcher.py"),
        ],
        cwd=VECTORA,
        desc="PyInstaller -> vectora.exe",
        # Suprime SyntaxWarning do pacote `future` (escape sequences inválidas
        # em ficheiros de backports que o PyInstaller importa durante a análise).
        env={"PYTHONWARNINGS": "ignore::SyntaxWarning"},
    )
    exe = ROOT / "dist" / ("vectora.exe" if sys.platform == "win32" else "vectora")
    if not exe.exists():
        sys.exit(f"{exe} não gerado")
    print(f"\nBUILD OK — {exe}  ({exe.stat().st_size / 1048576:.1f} MB)")


if __name__ == "__main__":
    main()
