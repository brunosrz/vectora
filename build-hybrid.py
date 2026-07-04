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
    # sqlite_vec expõe só um .dll de dados (vec0.dll), sem import Python que o
    # PyInstaller rastreie — sem --collect-all aqui, o binário nunca entra no
    # bundle e langgraph.store.sqlite.aio explode com "OperationalError: Não
    # foi possível encontrar o módulo especificado" ao tentar carregá-lo.
    "sqlite_vec",
    # tiktoken usa um sistema de plugins via namespace package: o registry faz
    # pkgutil.iter_modules(tiktoken_ext.__path__) para descobrir os encoders.
    # PyInstaller não vê esse import dentro do backend.pyd compilado.
    "tiktoken",
    "tiktoken_ext",
]

# Módulos que precisam de hidden-import adicional além do collect-all.
# tiktoken_ext.openai_public é o plugin que define cl100k_base, p50k_base etc.;
# em ambiente congelado pkgutil.iter_modules pode não enumerar namespace packages
# automaticamente — o hidden-import garante que o módulo entre no bundle.
HIDDEN_IMPORTS = [
    "tiktoken_ext.openai_public",
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
    hidden: list[str] = []
    for mod in HIDDEN_IMPORTS:
        hidden += ["--hidden-import", mod]

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
            # --onedir (pasta) em vez de --onefile: os arquivos ficam soltos e
            # SEM compressão, então entre versões as libs/DLLs não-alteradas ficam
            # byte-idênticas → o blockmap do electron-updater baixa só o que mudou
            # (delta real de poucos MB, não 1.5GB). Não muda a segurança: backend.pyd
            # continua C, libs continuam Python bytecode.
            "--onedir",
            "--noconfirm",
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
            *hidden,
            *excludes,
            str(VECTORA / "launcher.py"),
        ],
        cwd=VECTORA,
        desc="PyInstaller -> vectora.exe",
        # Suprime SyntaxWarning do pacote `future` (escape sequences inválidas
        # em ficheiros de backports que o PyInstaller importa durante a análise).
        env={"PYTHONWARNINGS": "ignore::SyntaxWarning"},
    )
    # --onedir gera a pasta dist/vectora/ com vectora[.exe] + _internal/.
    exe_name = "vectora.exe" if sys.platform == "win32" else "vectora"
    exe = ROOT / "dist" / "vectora" / exe_name
    if not exe.exists():
        sys.exit(f"{exe} não gerado")
    dist_dir = ROOT / "dist" / "vectora"
    total_mb = (
        sum(f.stat().st_size for f in dist_dir.rglob("*") if f.is_file()) / 1048576
    )
    print(f"\nBUILD OK — {dist_dir}  ({total_mb:.1f} MB na pasta)")


if __name__ == "__main__":
    main()
