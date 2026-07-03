"""
Vectora — SConstruct (SCons build file)

Uso (PowerShell / cmd, a partir da raiz do monorepo):
    scons               → exibe ajuda
    scons release       → build completo + instalador para o SO atual
    scons release-win   → instalador Windows (.msi + .exe NSIS)
    scons release-mac   → instalador macOS (.dmg universal)
    scons release-linux → instaladores Linux (.AppImage + .deb + .rpm)
    scons up-version [bump=patch|minor|major] → bump de versão + tag git
    scons tests         → suíte completa: todos os subprojetos (sem cobertura)
    scons coverage      → mesma suíte com relatório de cobertura
    scons lint          → todos os subprojetos: ruff+ty+bandit+tsc+oxlint+eslint
    scons docker        → sobe PostgreSQL + Redis + Qdrant via docker compose
    scons clean         → remove outputs de build

Pré-requisitos: uv, pnpm, nuitka (incluído no uv.lock), Hugo (extended) no PATH
Instalar SCons: pip install scons (ou uv add --dev scons)

Subprojetos cobertos por lint e tests:
    vectora/        Python (ruff, ty, bandit) + TS frontend (tsc, oxlint, vitest)
    company/        TypeScript (eslint, tsc, vitest)
    electron/       TypeScript (vitest — cookie-utils e lifecycle puro)
    docs/           Hugo + Hextra (build check via `hugo --gc --minify`) — sem
                    testes; era Docusaurus, migrado pra Hugo
    services/       TypeScript (tsc, vitest) — relay + updates unificados
                    (era relay/ + update-server/, ver Fase A do plano de
                    unificação)
"""

import base64
import glob
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile

# ── Helpers ───────────────────────────────────────────────────────────────────

ROOT = Dir(".").abspath

# Subprojetos
VECTORA  = os.path.join(ROOT, "vectora")
COMPANY  = os.path.join(ROOT, "company")
DOCS     = os.path.join(ROOT, "docs")
SERVICES = os.path.join(ROOT, "services")

_ANSI_RE = re.compile(r"\x1b(?:[@-Z\\-_]|\[[0-?]*[ -/]*[@-~])")


def _find_pnpm() -> str:
    if sys.platform == "win32":
        for name in ("pnpm.cmd", "pnpm.exe", "pnpm"):
            found = shutil.which(name)
            if found:
                return found
    return shutil.which("pnpm") or "pnpm"


PNPM = _find_pnpm()


def _find_hugo() -> str:
    found = shutil.which("hugo") or shutil.which("hugo.exe")
    if found:
        return found
    # winget instala fora do PATH da sessão atual até reiniciar o shell —
    # cai no caminho padrão do pacote Hugo.Hugo.Extended no Windows.
    if sys.platform == "win32":
        packages = os.path.join(
            os.environ.get("LOCALAPPDATA", ""), "Microsoft", "WinGet", "Packages"
        )
        if os.path.isdir(packages):
            for name in os.listdir(packages):
                if name.startswith("Hugo.Hugo.Extended_"):
                    candidate = os.path.join(packages, name, "hugo.exe")
                    if os.path.isfile(candidate):
                        return candidate
    return "hugo"


HUGO = _find_hugo()


def _run(
    cmd: list[str],
    env: dict | None = None,
    cwd: str | None = None,
    log=None,
    discard_stderr: bool = False,
) -> None:
    """Executa um comando, falha se o código de retorno for ≠ 0.

    Com ``log`` (file handle), espelha stdout+stderr para o terminal E para o
    arquivo (tee). O pipe desliga cores ANSI, deixando o .txt limpo.

    ``discard_stderr=True`` roteia stderr para DEVNULL — útil para ferramentas
    que emitem avisos ruidosos em stderr mas reportam erros reais via código de
    retorno (ex: bandit com comentários em língua não-inglesa).
    """
    merged = {**os.environ, **(env or {})}
    run_cwd = cwd or ROOT
    header = f"\n>> [{os.path.relpath(run_cwd, ROOT)}] {' '.join(str(c) for c in cmd)}"
    print(header)
    stderr_dest = subprocess.DEVNULL if discard_stderr else None
    if log is None:
        result = subprocess.run(cmd, cwd=run_cwd, env=merged, stderr=stderr_dest)
        rc = result.returncode
    else:
        merged["PYTHONIOENCODING"] = "utf-8"
        log.write(header + "\n")
        log.flush()
        proc = subprocess.Popen(
            cmd,
            cwd=run_cwd,
            env=merged,
            stdout=subprocess.PIPE,
            stderr=subprocess.DEVNULL if discard_stderr else subprocess.STDOUT,
            text=True,
            encoding="utf-8",
            errors="replace",
            bufsize=1,
        )
        for line in proc.stdout:  # type: ignore[union-attr]
            sys.stdout.write(line)
            log.write(_ANSI_RE.sub("", line))
        proc.wait()
        rc = proc.returncode
    if rc != 0:
        raise SystemExit(rc)


def _open_log(name: str):
    logdir = os.path.join(ROOT, ".scons-logs")
    os.makedirs(logdir, exist_ok=True)
    return open(os.path.join(logdir, f"{name}.txt"), "w", encoding="utf-8")


# ── Ações de build ────────────────────────────────────────────────────────────


def _action_build_chat(target, source, env):
    frontend_dir = os.path.join(VECTORA, "frontend")
    node_env = {"NODE_NO_WARNINGS": "1"}
    _run([PNPM, "install", "--frozen-lockfile"], env=node_env, cwd=frontend_dir)
    _run([PNPM, "build"], env=node_env, cwd=frontend_dir)

    dist = os.path.join(VECTORA, "frontend", "dist")
    if not os.path.isdir(dist) or not os.path.isfile(os.path.join(dist, "index.html")):
        raise SystemExit(
            "ERRO: vectora/frontend/dist/index.html não foi gerado. "
            "Verifique a configuração do Vite em vectora/frontend/vite.config.ts."
        )
    print(f">> chat dist pronto em {dist}")


def _msvc_env() -> dict[str, str] | None:
    """Captura o ambiente do MSVC (x64) via vcvars64.bat, no Windows.

    O Nuitka ``--msvc=latest`` às vezes não configura o toolchain mesmo com MSVC +
    Windows SDK instalados (falha com "scons environment variable 'CC' is not
    set"). Pré-carregar o vcvars exporta INCLUDE/LIB/PATH e o Nuitka reaproveita o
    ambiente já ativo. O vcvars64.bat pode sair com código ≠ 0 por um aviso interno
    de vswhere mesmo tendo inicializado o ambiente — por isso validamos INCLUDE/LIB
    em vez do código de retorno. Retorna ``None`` (sem alterar o env) quando não há
    toolchain detectável, deixando o Nuitka tentar sua própria detecção.
    """
    if sys.platform != "win32":
        return None
    program_files_x86 = os.environ.get("ProgramFiles(x86)", r"C:\Program Files (x86)")
    vswhere = os.path.join(
        program_files_x86, "Microsoft Visual Studio", "Installer", "vswhere.exe"
    )
    if not os.path.isfile(vswhere):
        return None
    try:
        install_path = subprocess.run(
            [vswhere, "-latest", "-products", "*", "-property", "installationPath"],
            capture_output=True,
            text=True,
            check=True,
        ).stdout.strip()
    except (subprocess.SubprocessError, OSError):
        return None
    vcvars = os.path.join(install_path, "VC", "Auxiliary", "Build", "vcvars64.bat")
    if not install_path or not os.path.isfile(vcvars):
        return None
    # Forma string (não lista): o cmd precisa parsear o wrap externo de aspas
    # `cmd /c "..."` para lidar com o caminho do vcvars com espaços + o `&& set`.
    # A forma lista quebra o redirecionamento/aspas e não captura o ambiente.
    proc = subprocess.run(
        f'cmd /c ""{vcvars}" >nul 2>&1 && set"',
        capture_output=True,
        text=True,
    )
    env: dict[str, str] = {}
    for line in proc.stdout.splitlines():
        key, sep, value = line.partition("=")
        if sep:
            env[key] = value
    if "INCLUDE" not in env or "LIB" not in env:
        return None
    # Força a saída do MSVC em inglês: o clcache do Nuitka parseia o output do
    # cl, e mensagens localizadas (pt-BR) disparam o aviso de "language pack".
    env["VSLANG"] = "1033"
    return env


def _action_build_nuitka(target, source, env):
    # Build híbrido: Nuitka --mode=package compila SÓ o pacote backend em C
    # (backend.pyd), depois PyInstaller empacota launcher + backend.pyd + libs
    # Python num vectora.exe. Compilar só o backend (pequeno) evita o OOM (C1002)
    # de compilar libs gigantes (google.genai.types ~157k linhas, lance) para C.
    # Default de jobs conservador (2); quem tem muita RAM sobe via NUITKA_JOBS.
    jobs = int(os.environ.get("NUITKA_JOBS", "2"))
    _run(
        [sys.executable, "build-hybrid.py", "--jobs", str(jobs)],
        cwd=ROOT,
        env=_msvc_env(),
    )

    # build-hybrid.py já valida cada fase, mas reconferimos o artefato final:
    # sem ele, o release empacotaria um instalador sem o executável.
    binary_name = "vectora.exe" if sys.platform == "win32" else "vectora"
    # --onedir: o executável fica em dist/vectora/ (pasta com _internal/).
    binary = os.path.join(ROOT, "dist", "vectora", binary_name)
    if not os.path.isfile(binary):
        raise SystemExit(
            f"ERRO: build-hybrid.py não gerou {binary}. "
            "Cheque o toolchain C (MSVC + Windows SDK) e o passo do PyInstaller."
        )
    print(f">> executável híbrido pronto em {binary}")


def _find_signtool() -> str | None:
    if sys.platform != "win32":
        return None
    kits_root = r"C:\Program Files (x86)\Windows Kits\10\bin"
    if os.path.isdir(kits_root):
        for version_dir in sorted(os.listdir(kits_root), reverse=True):
            for arch in ("x64", "x86"):
                candidate = os.path.join(kits_root, version_dir, arch, "signtool.exe")
                if os.path.isfile(candidate):
                    return candidate
    return shutil.which("signtool.exe")


def _get_dev_cert_env() -> dict[str, str] | None:
    pfx_path = os.path.join(VECTORA, "electron", "build-resources", "dev-cert.pfx")
    if not os.path.isfile(pfx_path):
        return None
    password = os.environ.get("DEV_CSC_PASSWORD", "vectora-dev")
    with open(pfx_path, "rb") as f:
        pfx_b64 = base64.b64encode(f.read()).decode()
    return {"CSC_LINK": pfx_b64, "CSC_KEY_PASSWORD": password}


def _sign_binary(binary: str) -> None:
    pfx_path = os.path.join(VECTORA, "electron", "build-resources", "dev-cert.pfx")
    if not os.path.isfile(pfx_path) or not os.path.isfile(binary):
        return
    signtool = _find_signtool()
    if not signtool:
        print(">> signtool.exe nao encontrado — assinatura manual ignorada")
        return
    password = os.environ.get("DEV_CSC_PASSWORD", "vectora-dev")
    _run([signtool, "sign", "/f", pfx_path, "/p", password, "/fd", "SHA256", "/v", binary])
    print(f">> assinado: {os.path.basename(binary)}")


def _action_install_desktop(target, source, env):
    _run([PNPM, "--dir", "vectora/electron", "install", "--frozen-lockfile"])


def _action_build_desktop(target, source, env):
    _run([PNPM, "--dir", "vectora/electron", "build"])


def _free_desktop_dist() -> None:
    if sys.platform != "win32":
        return
    subprocess.run(
        ["taskkill", "/F", "/IM", "vectora.exe", "/T"],
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        check=False,
    )
    unpacked = os.path.join(VECTORA, "electron", "dist-electron", "win-unpacked")
    if os.path.isdir(unpacked):
        shutil.rmtree(unpacked, ignore_errors=True)
        print(">> limpou win-unpacked travado (lock prevention)")


def _action_package(target, source, env, platform=""):
    """Empaqueta com electron-builder escrevendo fora do repositório.

    O watcher de arquivos do editor/IDE trava o win-unpacked/resources/app.asar
    quando escrito dentro da árvore observada. Buildar num diretório externo
    elimina a corrida; ao final copiamos só os instaladores de volta.
    """
    _free_desktop_dist()
    out_dir = os.path.join(
        os.environ.get("LOCALAPPDATA") or tempfile.gettempdir(),
        "Vectora",
        "dist-electron",
    )
    shutil.rmtree(out_dir, ignore_errors=True)
    os.makedirs(out_dir, exist_ok=True)

    flag = {"win": "--win", "mac": "--mac", "linux": "--linux"}.get(platform)
    cmd = [PNPM, "--dir", "vectora/electron", "exec", "electron-builder"]
    if flag:
        cmd.append(flag)
    cmd.append(f"-c.directories.output={out_dir}")

    build_env: dict[str, str] = {}
    has_signing_creds = any(
        os.environ.get(k)
        for k in ("CSC_LINK", "WIN_CSC_LINK", "CSC_KEY_PASSWORD", "MAC_CSC_LINK")
    )
    if not has_signing_creds:
        dev_env = _get_dev_cert_env() if sys.platform == "win32" else None
        if dev_env:
            build_env.update(dev_env)
            nuitka_bin = os.path.join(ROOT, "dist", "vectora", "vectora.exe")
            if os.path.isfile(nuitka_bin):
                print(">> assinando binário híbrido (extraResource) com dev-cert.pfx...")
                _sign_binary(nuitka_bin)
            print(">> assinando instaladores com dev-cert.pfx")
        else:
            build_env["CSC_IDENTITY_AUTO_DISCOVERY"] = "false"
    _run(cmd, env=build_env or None)

    dest = os.path.join(VECTORA, "electron", "dist-electron")
    os.makedirs(dest, exist_ok=True)
    patterns = (
        "*.exe", "*.msi", "*.dmg", "*.AppImage", "*.deb", "*.rpm",
        "latest*.yml", "*.blockmap",
    )
    copied: list[str] = []
    for pat in patterns:
        for f in glob.glob(os.path.join(out_dir, pat)):
            shutil.copy2(f, dest)
            copied.append(os.path.basename(f))
    if copied:
        print(f">> instaladores em {dest}:")
        for name in copied:
            print(f"     {name}")
    else:
        print(f">> build concluído em {out_dir} (nenhum instalador encontrado)")


# ── Lint ──────────────────────────────────────────────────────────────────────


def _pnpm_install_if_needed(pkg_dir: str, log) -> None:
    """Instala deps do subprojeto se node_modules ausente ou desatualizado."""
    modules = os.path.join(ROOT, pkg_dir, "node_modules")
    lock = os.path.join(ROOT, pkg_dir, "pnpm-lock.yaml")
    stamp = os.path.join(modules, ".pnpm-install-stamp")
    if (
        not os.path.isdir(modules)
        or not os.path.isfile(stamp)
        or (os.path.isfile(lock) and os.path.getmtime(lock) > os.path.getmtime(stamp))
    ):
        _run([PNPM, "--dir", pkg_dir, "install", "--frozen-lockfile"], log=log)
        open(stamp, "w").close()  # noqa: PTH123 WPS515


def _action_lint(target, source, env):
    with _open_log("lint") as log:
        # ── vectora: Python ───────────────────────────────────────────────────
        _run(["uv", "run", "ruff", "check", "backend", "tests"], log=log, cwd=VECTORA)
        _run(["uv", "run", "ty", "check", "backend", "tests"], log=log, cwd=VECTORA)
        _run(
            [
                "uv", "run", "python", "-m", "bandit",
                "-q",
                "-s", "B110,B101",
                "-c", "pyproject.toml",
                "--exclude", "backend/services/context_graph",
                "-r", "backend",
            ],
            log=log,
            cwd=VECTORA,
            discard_stderr=True,
        )
        # ── vectora: TypeScript frontend ──────────────────────────────────────
        # `typecheck` = i18n:compile (paraglide) + tsr generate + tsc --noEmit
        _run([PNPM, "--dir", "vectora/frontend", "run", "typecheck"], log=log)
        _run([PNPM, "--dir", "vectora/frontend", "exec", "oxlint"], log=log)
        # ── company ───────────────────────────────────────────────────────────
        _pnpm_install_if_needed("company", log)
        _run([PNPM, "--dir", "company", "run", "lint"], log=log)
        _run([PNPM, "--dir", "company", "run", "typecheck"], log=log)
        # ── docs (Hugo + Hextra) ─────────────────────────────────────────────
        # Sem typecheck TS aqui — o gate é o próprio build do site. `hugo build`
        # já resolve o módulo Hextra pinado em go.mod sozinho — não rodar
        # `hugo mod get` aqui, que faz upgrade do pin como side-effect.
        _run([HUGO, "--gc", "--minify", "--destination", "public"], log=log, cwd=DOCS)
        # ── services (relay + updates unificados) ──────────────────────────────
        _pnpm_install_if_needed("services", log)
        _run([PNPM, "--dir", "services", "exec", "tsc", "--noEmit"], log=log)
    print("\n>> log completo (limpo) em .scons-logs/lint.txt")


# ── Tests ─────────────────────────────────────────────────────────────────────


def _action_tests_storage(target, source, env):
    """Testes de storage (Postgres, Redis, Qdrant, SQLite, LanceDB).

    Pulam automaticamente quando o serviço não está acessível.
    """
    with _open_log("tests-storage") as log:
        _run(
            [
                "uv", "run", "pytest", "tests/integration",
                "-q", "--tb=short",
                "-m", "storage",
            ],
            log=log,
            cwd=VECTORA,
        )
    print("\n>> log completo em .scons-logs/tests-storage.txt")


def _run_full_suite(log, *, coverage: bool):
    """Suíte completa: vectora (vitest + pytest) + company + electron
    + services (vitest — relay + updates unificados).

    docs não tem testes — coberto só pelo lint (typecheck).

    Com ``coverage=True``, ativa --coverage no vitest e --cov no pytest
    (relatórios em vectora/frontend/coverage/ e vectora/htmlcov/).
    """
    # ── vectora/frontend ──────────────────────────────────────────────────────
    # Paraglide deve compilar antes do vitest: lib/paraglide é gitignored e o
    # vitest importa os messages compilados. O plugin Vite só compila em dev/build.
    _run([PNPM, "--dir", "vectora/frontend", "run", "i18n:compile"], log=log)

    vitest_cmd = [PNPM, "--dir", "vectora/frontend", "exec", "vitest", "run"]
    if coverage:
        vitest_cmd.append("--coverage")
    _run(vitest_cmd, log=log)

    # ── vectora/backend ───────────────────────────────────────────────────────
    pytest_cmd = ["uv", "run", "pytest", "tests", "-q", "--tb=short"]
    if coverage:
        pytest_cmd += [
            "--cov=backend",
            "--cov-report=term:skip-covered",
            "--cov-report=html:htmlcov",
        ]
    _run(pytest_cmd, log=log, cwd=VECTORA)

    # ── company ───────────────────────────────────────────────────────────────
    _pnpm_install_if_needed("company", log)
    _run([PNPM, "--dir", "company", "run", "test"], log=log)

    # ── electron (cookie-utils e lifecycle puro) ───────────────────────────
    _pnpm_install_if_needed("vectora/electron", log)
    _run([PNPM, "--dir", "vectora/electron", "run", "test"], log=log)

    # ── services (relay + updates unificados; worker.ts + scripts/release.ts) ─
    _pnpm_install_if_needed("services", log)
    services_test_cmd = [PNPM, "--dir", "services", "exec", "vitest", "run"]
    if coverage:
        services_test_cmd.append("--coverage")
    _run(services_test_cmd, log=log)


def _action_tests(target, source, env):
    with _open_log("tests") as log:
        _run_full_suite(log, coverage=False)
    print("\n>> log completo (limpo) em .scons-logs/tests.txt")


def _action_coverage(target, source, env):
    with _open_log("coverage") as log:
        _run_full_suite(log, coverage=True)
    print("\n>> log completo (limpo) em .scons-logs/coverage.txt")
    print(
        ">> cobertura HTML: vectora/frontend/coverage/index.html, "
        "vectora/htmlcov/index.html e services/coverage/index.html"
    )


# ── Docker ────────────────────────────────────────────────────────────────────


def _action_docker(target, source, env):
    """Sobe a infraestrutura do Vectora (PostgreSQL, Redis, Qdrant).

    O Vectora em si NÃO roda como container. O backend roda no host.
    """
    probe = subprocess.run(  # noqa: S603 S607
        ["docker", "info"],
        stdout=subprocess.DEVNULL,
        stderr=subprocess.PIPE,
        cwd=ROOT,
        text=True,
        check=False,
    )
    daemon_error = (
        probe.returncode != 0
        or "failed to connect" in (probe.stderr or "").lower()
        or "cannot connect" in (probe.stderr or "").lower()
        or "is the docker daemon running" in (probe.stderr or "").lower()
    )
    if daemon_error:
        print(
            "\n[scons docker] Docker não está acessível.\n"
            "  Inicie o Docker Desktop e tente novamente.\n"
        )
        raise SystemExit(1)

    compose_env: dict[str, str] = {}
    dotenv = os.path.join(os.path.expanduser("~"), ".vectora", ".env")
    if os.path.isfile(dotenv):
        with open(dotenv, encoding="utf-8") as f:  # noqa: PTH123
            for line in f:
                stripped = line.strip()
                if stripped and not stripped.startswith("#") and "=" in stripped:
                    key, value = stripped.split("=", 1)
                    compose_env[key.strip()] = value.strip()

    _run(["docker", "compose", "up", "-d"], env=compose_env or None, cwd=VECTORA)
    print("\n>> Infraestrutura pronta. Configure ~/.vectora/.env:")
    print(">>   STORAGE_MODE=complete")
    print(">>   POSTGRES_DSN=postgresql+asyncpg://vectora:vectora@127.0.0.1:5432/vectora")
    print(">>   REDIS_URL=redis://127.0.0.1:6379/0")
    print(">>   QDRANT_URL=http://127.0.0.1:6333")
    print(">> Depois execute: vectora start")


# ── Clean ─────────────────────────────────────────────────────────────────────


def _action_clean(target, source, env):
    paths = [
        "vectora/dist-nuitka",
        "dist",
        "build/pyinstaller",
        "build/vectora.spec",
        "vectora/frontend/dist",
        "vectora/frontend/.next",
        "vectora/frontend/out",
        "vectora/electron/dist",
        "vectora/electron/dist-electron",
        "docs/public",
        "docs/resources",
    ]
    for path in paths:
        full = os.path.join(ROOT, path.replace("/", os.sep))
        if os.path.exists(full):
            shutil.rmtree(full)
            print(f">> removido: {path}")


# ── Up-version ────────────────────────────────────────────────────────────────
# `scons up-version [bump=patch|minor|major]` — sobe o semver em pyproject.toml
# (fonte única — backend/version.py lê de lá via importlib.metadata) e propaga
# pro package.json do electron/services. NÃO grava hash nenhum
# nesses arquivos: o `buildVersion` (semver + hash numérico do commit, pro
# recurso de versão do .exe/.msi) é só impresso aqui — quem usa é
# `scons release-<os>` na hora do build. company/ fica de fora (não tem
# version própria, é site separado do app).

def _read_pyproject_version(path: str) -> tuple[int, int, int]:
    text = open(path, encoding="utf-8").read()
    m = re.search(r'(?m)^version\s*=\s*"(\d+)\.(\d+)\.(\d+)"', text)
    if not m:
        raise RuntimeError(f"version não encontrada em {path}")
    return int(m.group(1)), int(m.group(2)), int(m.group(3))


def _write_pyproject_version(path: str, new_version: str) -> None:
    text = open(path, encoding="utf-8").read()
    new_text = re.sub(
        r'(?m)^version\s*=\s*"\d+\.\d+\.\d+"',
        f'version = "{new_version}"',
        text,
        count=1,
    )
    open(path, "w", encoding="utf-8").write(new_text)


def _write_package_json_version(path: str, new_version: str) -> None:
    with open(path, encoding="utf-8") as f:
        data = json.load(f)
    data["version"] = new_version
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)
        f.write("\n")


def _bump_semver(version: tuple[int, int, int], kind: str) -> tuple[int, int, int]:
    major, minor, patch = version
    if kind == "major":
        return (major + 1, 0, 0)
    if kind == "minor":
        return (major, minor + 1, 0)
    return (major, minor, patch + 1)


def _git_short_hash() -> str:
    return subprocess.check_output(
        ["git", "rev-parse", "--short", "HEAD"], cwd=ROOT, text=True
    ).strip()


def _numeric_build_hash(short_hash: str) -> int:
    # Windows limita o 4º campo de versão de arquivo (FileVersion/ProductVersion)
    # a 16 bits — mod 65536 garante que o .msi/.exe nunca recebam um valor
    # inválido, mesmo assim determinístico por commit.
    return int(short_hash, 16) % 65536


def _action_up_version(target, source, env):
    bump_kind = ARGUMENTS.get("bump", "patch")
    if bump_kind not in ("major", "minor", "patch"):
        print(f">> bump inválido: {bump_kind!r} — use bump=major|minor|patch")
        return 1

    pyproject_path = os.path.join(VECTORA, "pyproject.toml")
    package_json_paths = [
        os.path.join(VECTORA, "electron", "package.json"),
        os.path.join(SERVICES, "package.json"),
    ]

    old_version = _read_pyproject_version(pyproject_path)
    new_version = _bump_semver(old_version, bump_kind)
    new_version_str = ".".join(str(p) for p in new_version)

    _write_pyproject_version(pyproject_path, new_version_str)
    for pkg_path in package_json_paths:
        _write_package_json_version(pkg_path, new_version_str)

    subprocess.run(
        ["git", "add", pyproject_path, *package_json_paths], cwd=ROOT, check=True
    )
    subprocess.run(
        ["git", "commit", "-m", f"chore: bump version to v{new_version_str}"],
        cwd=ROOT,
        check=True,
    )
    subprocess.run(["git", "tag", f"v{new_version_str}"], cwd=ROOT, check=True)

    short_hash = _git_short_hash()
    hash_num = _numeric_build_hash(short_hash)
    build_version = f"{new_version_str}.{hash_num}"

    print(f">> versão {'.'.join(str(p) for p in old_version)} → {new_version_str}")
    print(f">> commit + tag v{new_version_str} criados (sem push — manual)")
    print(f">> buildVersion (p/ electron-builder --config.buildVersion=...): {build_version}")
    print(">> Próximos passos:")
    print(f">>   scons release-<os>")
    print(
        f">>   pnpm --dir services run release -- --version={new_version_str}"
    )


# ── Help ──────────────────────────────────────────────────────────────────────


def _action_help(target, source, env):
    sys.stdout.write("""
  Vectora — alvos SCons  (rodar da raiz do monorepo)

  Produto final
    scons release          build completo + instalador para o SO atual
    scons release-win      instalador Windows (.msi + .exe NSIS)
    scons release-mac      instalador macOS (.dmg universal)
    scons release-linux    instaladores Linux (.AppImage + .deb + .rpm)
    scons up-version [bump=patch|minor|major]
                           bump de versão (pyproject.toml + package.json) + tag git

  Build
    scons frontend         só o build do frontend (vectora/frontend/dist/)
    scons docker           sobe infraestrutura (PostgreSQL, Redis, Qdrant)

  Qualidade — cobrem todos os subprojetos
    scons tests            suíte completa: vectora + services + company (sem cobertura)
    scons coverage         a mesma suíte COM relatório de cobertura
    scons tests-storage    só testes de storage (Postgres, Redis, Qdrant, SQLite, LanceDB)
    scons lint             vectora (ruff+ty+bandit+tsc+oxlint) + company (eslint+tsc)
                           + docs (tsc) + services (tsc)
    scons clean            remove todos os outputs de build
""")
    sys.stdout.flush()


# ── Alvos SCons ───────────────────────────────────────────────────────────────

env = Environment(ENV=os.environ)
env.Decider("timestamp-match")


def _node(name: str, action, deps: list | None = None):
    t = env.Command(f"_{name}", deps or [], action)
    env.AlwaysBuild(t)
    return t


def _cmd(name: str, action, deps: list | None = None):
    t = env.Command(f"_{name}", deps or [], action)
    env.AlwaysBuild(t)
    env.Alias(name, t)
    return t


_cmd("frontend", _action_build_chat)

_build_chat    = _node("build-chat",      _action_build_chat)
_build_nuitka  = _node("build-nuitka",    _action_build_nuitka,   deps=[_build_chat])
_inst_desktop  = _node("install-desktop", _action_install_desktop)
_build_desktop = _node("build-desktop",   _action_build_desktop,  deps=[_inst_desktop])

_FULL_DEPS = [_build_chat, _build_nuitka, _build_desktop]

_cmd("release-win",   lambda target, source, env: _action_package(target, source, env, "win"),   deps=_FULL_DEPS)
_cmd("release-mac",   lambda target, source, env: _action_package(target, source, env, "mac"),   deps=_FULL_DEPS)
_cmd("release-linux", lambda target, source, env: _action_package(target, source, env, "linux"), deps=_FULL_DEPS)
_cmd("release",       lambda target, source, env: _action_package(target, source, env),          deps=_FULL_DEPS)

_cmd("up-version",    _action_up_version)

_cmd("tests",         _action_tests)
_cmd("coverage",      _action_coverage)
_cmd("tests-storage", _action_tests_storage)
_cmd("lint",          _action_lint)
_cmd("clean",         _action_clean)
_cmd("help",          _action_help)
_cmd("docker",        _action_docker)

Default(env.Command("_default", [], _action_help))
