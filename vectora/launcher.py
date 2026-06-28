"""Entry-point do executável Vectora (empacotado por PyInstaller).

Importa o pacote backend compilado (backend.pyd, gerado por Nuitka
--mode=package) e executa backend.launcher.main().
"""

import os
import sys

# backend.pyd fica ao lado deste arquivo no bundle do PyInstaller (sys._MEIPASS);
# em dev, fica em dist-nuitka/.
_here = os.path.dirname(os.path.abspath(__file__))
for _cand in (_here, os.path.join(_here, "dist-nuitka")):
    if os.path.isdir(_cand) and _cand not in sys.path:
        sys.path.insert(0, _cand)


def main() -> int:
    from backend.launcher import main as backend_main

    return backend_main()


if __name__ == "__main__":
    raise SystemExit(main())
