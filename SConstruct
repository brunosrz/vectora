"""
Vectora — SConstruct (SCons build file)

Uso (PowerShell / cmd, sem Git bash):
    scons               → exibe ajuda
    scons dev           → backend + Next.js dev (Ctrl+C encerra ambos)
    scons release       → build completo + instalador para o SO atual
    scons release-win   → instalador Windows (.msi + .exe NSIS)
    scons release-mac   → instalador macOS (.dmg universal)
    scons release-linux → instaladores Linux (.AppImage + .deb + .rpm)
    scons build-chat    → Next.js export → chat/out/
    scons build-nuitka  → Nuitka onefile → dist-nuitka/
    scons build-desktop → TypeScript Electron → desktop/dist/
    scons package       → electron-builder → desktop/dist-electron/
    scons tests         → pytest (unit + stress + ...) com coverage + vitest do chat
    scons tests-full    → idem + tests/integration + tests/e2e (requer API keys)
    scons lint          → ruff + ty + tsc + oxlint
    scons clean         → remove outputs de build

Pré-requisitos: uv, pnpm, nuitka (incluído no uv.lock)
Instalar SCons: pip install scons (ou uv add --dev scons)
"""

import os
import shutil
import subprocess
import sys

# ── Helpers ───────────────────────────────────────────────────────────────────

ROOT = Dir(".").abspath


def _find_pnpm() -> str:
    """Localiza pnpm, preferindo pnpm.cmd no Windows."""
    if sys.platform == "win32":
        for name in ("pnpm.cmd", "pnpm.exe", "pnpm"):
            found = shutil.which(name)
            if found:
                return found
    return shutil.which("pnpm") or "pnpm"


PNPM = _find_pnpm()


def _run(cmd: list[str], env: dict | None = None) -> None:
    """Executa um comando, falha se o código de retorno for ≠ 0."""
    merged = {**os.environ, **(env or {})}
    print(f"\n>> {' '.join(str(c) for c in cmd)}")
    result = subprocess.run(cmd, cwd=ROOT, env=merged)
    if result.returncode != 0:
        raise SystemExit(result.returncode)


# ── Ações ─────────────────────────────────────────────────────────────────────


def _action_build_chat(target, source, env):
    """Build da SPA Vite em `chat/dist/`.

    O FastAPI faz `StaticFiles.mount` apontando para esta pasta em prod
    (extraída pelo Nuitka como `chat_static/`) ou diretamente para
    `chat/dist/` em dev.
    """
    _run([PNPM, "--dir", "chat", "install", "--frozen-lockfile"])
    _run([PNPM, "--dir", "chat", "build"])

    dist = os.path.join(ROOT, "chat", "dist")
    if not os.path.isdir(dist) or not os.path.isfile(os.path.join(dist, "index.html")):
        raise SystemExit(
            "ERRO: chat/dist/index.html não foi gerado. "
            "Verifique a configuração do Vite em chat/vite.config.ts."
        )
    print(f">> chat dist pronto em {dist}")


def _action_build_nuitka(target, source, env):
    """Compila o launcher Python embutindo a SPA Vite como data dir.

    `chat/dist/` é incluído como `chat_static/` no binário. Em runtime,
    o FastAPI (src/api/server.py::_chat_static_root) localiza essa pasta
    via `__compiled__.containing_dir` ou `NUITKA_ONEFILE_PARENT` e
    serve via `StaticFiles`.
    """
    _run(
        [
            "uv", "run", "nuitka",
            "--mode=onefile",
            "--include-data-dir=chat/dist=chat_static",
            "--enable-plugin=multiprocessing",
            "--enable-plugin=anti-bloat",
            "--output-filename=vectora",
            "--output-dir=dist-nuitka",
            "src/launcher.py",
        ]
    )


def _action_install_desktop(target, source, env):
    _run([PNPM, "--dir", "desktop", "install", "--frozen-lockfile"])


def _action_build_desktop(target, source, env):
    _run([PNPM, "--dir", "desktop", "build"])


def _action_package(target, source, env, platform=""):
    cmd = [PNPM, "--dir", "desktop"]
    if platform:
        cmd.append(f"dist:{platform}")
    else:
        cmd.append("dist")
    _run(cmd)


def _action_dev(target, source, env):
    _run(["uv", "run", "python", "scripts/dev.py"])


def _action_tests(target, source, env, *, include_external: bool = False):
    """Roda a suíte de testes Python (pytest + coverage) e a do chat (vitest).

    Default (``scons tests``): unit + stress + qualquer pasta sem marker;
    pula ``integration`` e ``e2e`` que exigem GOOGLE_API_KEY / COHERE_API_KEY /
    gemini CLI. Use ``scons tests-full`` para incluir essas suítes.
    """
    pytest_cmd = [
        "uv", "run", "pytest", "tests",
        "--cov=src",
        "--cov-report=term-missing:skip-covered",
        "--cov-report=html:htmlcov",
        "--tb=short",
    ]
    if not include_external:
        pytest_cmd += ["-m", "not e2e and not integration"]
    _run(pytest_cmd)
    _run([PNPM, "--dir", "chat", "test"])


def _action_test_legacy(target, source, env):
    """Compat: ``scons test`` continua rodando só `tests/unit/`."""
    _run(["uv", "run", "pytest", "tests/unit/", "-v", "--tb=short"])


def _action_lint(target, source, env):
    _run(["uv", "run", "ruff", "check", "src", "tests"])
    _run(["uv", "run", "ty", "check", "src", "tests"])
    _run([PNPM, "--dir", "chat", "exec", "tsc", "--noEmit"])
    _run([PNPM, "--dir", "chat", "exec", "oxlint"])


def _action_clean(target, source, env):
    for path in [
        "dist-nuitka",
        "chat/dist",
        "chat/.next",
        "chat/out",
        "desktop/dist",
        "desktop/dist-electron",
    ]:
        full = os.path.join(ROOT, path.replace("/", os.sep))
        if os.path.exists(full):
            shutil.rmtree(full)
            print(f">> removido: {path}")


def _action_help(target, source, env):
    sys.stdout.write("""
  Vectora -- alvos SCons

  Produto final
    scons release          build completo + instalador para o SO atual
    scons release-win      instalador Windows (.msi + .exe NSIS)
    scons release-mac      instalador macOS (.dmg universal)
    scons release-linux    instaladores Linux (.AppImage + .deb + .rpm)

  Passos individuais
    scons build-chat       Vite SPA build -> chat/dist/
    scons build-nuitka     Nuitka onefile -> dist-nuitka/  (10-30 min)
    scons build-desktop    TypeScript Electron -> desktop/dist/
    scons package          electron-builder -> desktop/dist-electron/

  Desenvolvimento
    scons dev              backend (8080) + Vite dev (5173)
    scons dev-backend      apenas backend
    scons dev-chat         apenas Vite dev

  Qualidade
    scons tests            pytest tests/ + coverage + vitest do chat
                           (pula -m e2e e -m integration)
    scons tests-full       idem + integration + e2e (requer API keys)
    scons test             [legado] pytest tests/unit/ apenas
    scons lint             ruff + ty + tsc + oxlint
    scons clean            remove todos os outputs de build
""")
    sys.stdout.flush()


# ── Alvos SCons ───────────────────────────────────────────────────────────────

env = Environment(ENV=os.environ)

# Desabilita a varredura implícita de dependências — somos nós que controlamos.
env.Decider("timestamp-match")


def _cmd(name: str, action, deps: list = []):
    """Cria um target PHONY com dependências."""
    t = env.Command(f"_{name}", deps, action)
    env.AlwaysBuild(t)
    env.Alias(name, t)
    return t


# Passos individuais
_build_chat    = _cmd("build-chat",    _action_build_chat)
_build_nuitka  = _cmd("build-nuitka",  _action_build_nuitka,  deps=[_build_chat])
_inst_desktop  = _cmd("install-desktop", _action_install_desktop)
_build_desktop = _cmd("build-desktop", _action_build_desktop,  deps=[_inst_desktop])
_package       = _cmd("package",       lambda target, source, env: _action_package(target, source, env),
                       deps=[_build_desktop])

# Releases por plataforma
_rel_win   = _cmd("release-win",   lambda target, source, env: _action_package(target, source, env, "win"),
                   deps=[_build_chat, _build_nuitka, _build_desktop])
_rel_mac   = _cmd("release-mac",   lambda target, source, env: _action_package(target, source, env, "mac"),
                   deps=[_build_chat, _build_nuitka, _build_desktop])
_rel_linux = _cmd("release-linux", lambda target, source, env: _action_package(target, source, env, "linux"),
                   deps=[_build_chat, _build_nuitka, _build_desktop])
_release   = _cmd("release",       lambda target, source, env: _action_package(target, source, env),
                   deps=[_build_chat, _build_nuitka, _build_desktop])

# Dev
_cmd("dev",         _action_dev)
_cmd("dev-backend", lambda target, source, env: _run(
    ["uv", "run", "vectora", "server", "chat", "--port", "8080"],
    env={"VECTORA_LICENSE_BYPASS": "1"},
))
_cmd("dev-chat",    lambda target, source, env: _run([PNPM, "--dir", "chat", "dev"]))

# Qualidade
_cmd("tests",      _action_tests)
_cmd("tests-full", lambda target, source, env: _action_tests(target, source, env, include_external=True))
_cmd("test",       _action_test_legacy)  # back-compat
_cmd("lint",       _action_lint)
_cmd("clean",      _action_clean)
_cmd("help",       _action_help)

# Default: exibe ajuda
Default(env.Command("_default", [], _action_help))
