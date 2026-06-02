#!/bin/sh
# Pós-remoção .deb/.rpm — remove registro do protocolo vectora://.

set -e

if command -v xdg-mime >/dev/null 2>&1; then
    xdg-mime default firefox.desktop x-scheme-handler/vectora 2>/dev/null || true
fi

if command -v update-desktop-database >/dev/null 2>&1; then
    update-desktop-database -q /usr/share/applications || true
fi

exit 0
