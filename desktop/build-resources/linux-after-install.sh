#!/bin/sh
# Pós-instalação .deb/.rpm — registra protocolo vectora:// no XDG.

set -e

if command -v update-desktop-database >/dev/null 2>&1; then
    update-desktop-database -q /usr/share/applications || true
fi

if command -v xdg-mime >/dev/null 2>&1; then
    xdg-mime default vectora.desktop x-scheme-handler/vectora || true
fi

# Garante que o binário Nuitka embutido em /opt/Vectora/resources/vectora-core/
# tem +x (electron-builder copia mas alguns FS perdem permissões).
chmod +x /opt/Vectora/resources/vectora-core/vectora 2>/dev/null || true

exit 0
