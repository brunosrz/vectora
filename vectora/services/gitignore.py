"""Utilitários de filtragem baseada em .gitignore via pathspec.

Módulo compartilhado entre fs.py (grep, list_dir) e rag.py (ingest_docs)
para garantir que nenhuma tool do Vectora indexe ou varra arquivos que
estejam no .gitignore do projeto.

Usa a lib pathspec com suporte a gitwildmatch — o mesmo formato do git.
"""

from pathlib import Path

import pathspec

# Diretórios e extensões sempre ignorados, independente de .gitignore
ALWAYS_SKIP_SUFFIXES: frozenset[str] = frozenset(
    {".pyc", ".pyo", ".o", ".exe", ".dll", ".so", ".class", ".pyd", ".whl"}
)

ALWAYS_SKIP_DIRS: frozenset[str] = frozenset(
    {
        "__pycache__",
        ".git",
        ".venv",
        "venv",
        "node_modules",
        ".mypy_cache",
        ".ruff_cache",
        ".pytest_cache",
        ".egg-info",
        "dist",
        "build",
        ".build",
        ".tox",
        # AI assistant config dirs — never index for RAG
        ".claude",
        ".anthropic",
    }
)


def load_gitignore_spec(base_dir: Path) -> pathspec.PathSpec | None:
    """Carrega o .gitignore mais próximo e retorna um PathSpec gitwildmatch.

    Sobe a árvore de diretórios a partir de ``base_dir`` até encontrar um
    ``.gitignore``. Para na raiz do filesystem se não encontrar nenhum.

    Args:
        base_dir: Diretório de partida para a busca (geralmente o dir do projeto).

    Returns:
        PathSpec pronto para uso em ``match_file()``, ou None se não houver
        nenhum ``.gitignore`` acessível.
    """
    for parent in [base_dir.resolve(), *base_dir.resolve().parents]:
        gitignore = parent / ".gitignore"
        if gitignore.is_file():
            try:
                patterns = gitignore.read_text(encoding="utf-8", errors="ignore")
                return pathspec.PathSpec.from_lines(
                    "gitwildmatch", patterns.splitlines()
                )
            except Exception:
                return None
    return None


def is_ignored(path: Path, base_dir: Path, spec: pathspec.PathSpec | None) -> bool:
    """Retorna True se ``path`` deve ser ignorado.

    Três camadas de verificação, em ordem crescente de custo:

    1. Algum componente do path está em ALWAYS_SKIP_DIRS
       (ex: ``__pycache__``, ``.git``, ``node_modules``)
    2. A extensão do arquivo está em ALWAYS_SKIP_SUFFIXES
       (ex: ``.pyc``, ``.exe``)
    3. O path relativo ao ``base_dir`` bate com um padrão do ``.gitignore``
       carregado no PathSpec (ex: ``*.log``, ``dist/``, ``.env``)

    Args:
        path: Caminho absoluto ou relativo a verificar.
        base_dir: Diretório raiz usado para calcular o caminho relativo
                  ao avaliar o PathSpec.
        spec: PathSpec retornado por ``load_gitignore_spec()``.
              Pode ser None se não houver .gitignore.

    Returns:
        True se o arquivo deve ser ignorado, False caso contrário.
    """
    # Camada 1 — dirs hardcoded (mais rápido, sem I/O)
    for part in path.parts:
        if part in ALWAYS_SKIP_DIRS:
            return True

    # Camada 2 — extensões binárias/compiladas
    if path.suffix in ALWAYS_SKIP_SUFFIXES:
        return True

    # Camada 3 — regras do .gitignore via pathspec
    if spec is not None:
        try:
            rel = path.relative_to(base_dir)
            # pathspec espera separador POSIX em qualquer plataforma
            if spec.match_file(str(rel).replace("\\", "/")):
                return True
        except ValueError:
            pass

    return False


def iter_files(
    base_dir: Path,
    glob_pattern: str = "**/*",
    spec: pathspec.PathSpec | None = None,
) -> list[Path]:
    """Lista arquivos em ``base_dir`` respeitando .gitignore.

    Substitui ``Path.rglob()`` puro em contextos que precisam de filtragem.

    Args:
        base_dir: Diretório raiz da varredura.
        glob_pattern: Padrão glob (ex: ``**/*.md``, ``**/*.py``).
        spec: PathSpec do .gitignore (None → sem filtragem por gitignore,
              mas ALWAYS_SKIP ainda se aplica).

    Returns:
        Lista de Paths de arquivos que passaram em todos os filtros.
    """
    # Remove leading "**/" prefix so rglob receives a plain pattern (e.g. "*.md")
    stripped = glob_pattern
    while stripped.startswith("**/"):
        stripped = stripped[3:]

    return [
        path
        for path in sorted(base_dir.rglob(stripped))
        if path.is_file() and not is_ignored(path, base_dir, spec)
    ]
