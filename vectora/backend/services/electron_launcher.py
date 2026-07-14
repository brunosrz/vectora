"""Resolve o launch do Electron em dev — o backend Python (`vectora start`
rodado direto, fora do Electron) passa a spawnar o Electron sozinho, ao
invés do caminho de produção onde é o Electron quem spawna o backend
compilado. Mesmo espírito de resolução defensiva que
`backend/scheduling/nats_sidecar.py::_resolve_binary` já usa: nunca lança,
retorna ``None`` quando qualquer peça não existir — o caller cai no
fallback antigo (bandeja/servidor puro).

Resolução (só dev — produção nunca passa por aqui, ver `_run_start`). O
Electron não tem pacote npm próprio — está fundido em
`vectora/frontend/package.json` (sem `electron/package.json` separado), só o
`tsconfig.json` de compilação (Node/NodeNext, incompatível com o tsconfig
browser/Vite do frontend) segue num subdiretório próprio. Por isso a
resolução consulta dois diretórios distintos:
  - binário Electron: `vectora/frontend/node_modules/electron/path.txt`
    (convenção do pacote npm `electron` — arquivo texto com o nome do
    executável da plataforma, relativo a `node_modules/electron/dist/`;
    instalado no node_modules do pacote frontend, não num subpacote).
  - entrypoint: `vectora/frontend/electron/dist/main.js`, compilado por
    `pnpm --dir frontend run electron:build` (`tsc -p electron/tsconfig.json`).
"""

from __future__ import annotations

import logging
from pathlib import Path

logger = logging.getLogger(__name__)


def _frontend_dir() -> Path:
    """`<repo>/vectora/frontend` — onde `pnpm install` escreve
    `node_modules/electron/` (pacote único, sem subpacote pro Electron)."""
    return Path(__file__).resolve().parent.parent.parent / "frontend"


def _electron_dir() -> Path:
    """`<repo>/vectora/frontend/electron` — onde `tsc` (tsconfig próprio)
    compila `src/main.ts` para `dist/main.js`."""
    return _frontend_dir() / "electron"


def resolve_electron_launch() -> tuple[str, list[str]] | None:
    """Retorna ``(executável, [main.js])`` prontos para
    ``asyncio.create_subprocess_exec``, ou ``None`` se o build de dev do
    Electron não estiver disponível (não instalado, não buildado).
    """
    main_js = _electron_dir() / "dist" / "main.js"
    if not main_js.is_file():
        return None

    path_txt = _frontend_dir() / "node_modules" / "electron" / "path.txt"
    if not path_txt.is_file():
        return None

    try:
        exe_name = path_txt.read_text(encoding="utf-8").strip()
    except OSError:
        logger.exception("electron_launcher: falha ao ler path.txt")
        return None
    if not exe_name:
        return None

    exe_path = path_txt.parent / "dist" / exe_name
    if not exe_path.is_file():
        return None

    return str(exe_path), [str(main_js)]
