"""Entry-point do executável Vectora (empacotado por PyInstaller)."""

from __future__ import annotations

import os
import sys

_here = os.path.dirname(os.path.abspath(__file__))
for _cand in (_here, os.path.join(_here, "dist-nuitka")):
    if os.path.isdir(_cand) and _cand not in sys.path:
        sys.path.insert(0, _cand)

if __name__ == "__main__":
    from backend.main import run

    run()
