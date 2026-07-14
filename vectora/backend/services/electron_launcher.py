"""Resolve o launch do Electron em dev — o backend Python (`vectora start`
rodado direto, fora do Electron) passa a spawnar o Electron sozinho, ao
invés do caminho de produção onde é o Electron quem spawna o backend
compilado. Mesmo espírito de resolução defensiva que
`backend/scheduling/nats_sidecar.py::_resolve_binary` já usa: nunca lança,
retorna ``None`` quando qualquer peça não existir — o caller cai no
fallback antigo (bandeja/servidor puro).

Resolução (só dev — produção nunca passa por aqui, ver `_run_start`):
  - binário Electron: `vectora/electron/node_modules/electron/path.txt`
    (convenção do pacote npm `electron` — arquivo texto com o nome do
    executável da plataforma, relativo a `node_modules/electron/dist/`).
  - entrypoint: `vectora/electron/dist/main.js`, compilado por
    `pnpm --dir electron build` (`tsc`).
"""

from __future__ import annotations

import logging
from pathlib import Path

logger = logging.getLogger(__name__)

_ELECTRON_DIR_NAME = "electron"


def _electron_dir() -> Path:
    """`<repo>/vectora/electron` — dois níveis acima deste arquivo."""
    return Path(__file__).resolve().parent.parent.parent / _ELECTRON_DIR_NAME


def resolve_electron_launch() -> tuple[str, list[str]] | None:
    """Retorna ``(executável, [main.js])`` prontos para
    ``asyncio.create_subprocess_exec``, ou ``None`` se o build de dev do
    Electron não estiver disponível (não instalado, não buildado).
    """
    electron_dir = _electron_dir()
    main_js = electron_dir / "dist" / "main.js"
    if not main_js.is_file():
        return None

    path_txt = electron_dir / "node_modules" / "electron" / "path.txt"
    if not path_txt.is_file():
        return None

    try:
        exe_name = path_txt.read_text(encoding="utf-8").strip()
    except OSError:
        logger.exception("electron_launcher: falha ao ler path.txt")
        return None
    if not exe_name:
        return None

    exe_path = electron_dir / "node_modules" / "electron" / "dist" / exe_name
    if not exe_path.is_file():
        return None

    return str(exe_path), [str(main_js)]
