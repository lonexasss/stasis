#!/usr/bin/env bash
# stasis installer: puts the launcher in PATH and adds it to the apps menu.
set -euo pipefail

HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PREFIX="${HOME}/.local"
BIN_DIR="$PREFIX/bin"
DESKTOP_DIR="$PREFIX/share/applications"

mkdir -p "$BIN_DIR" "$DESKTOP_DIR"

if [[ -f "$HERE/stasis-gui" ]]; then
    install -m 755 "$HERE/stasis-gui" "$BIN_DIR/"
    SOURCE="binary"
elif python3 -c "import stasis" 2>/dev/null || python3 -m pip show stasis-launcher >/dev/null 2>&1; then
    SOURCE="existing python package"
else
    echo "no prebuilt binary found — installing from source with pip..."
    python3 -m pip install --user "$HERE"
    SOURCE="pip (source)"
fi

sed "s|@BIN@|$BIN_DIR/stasis-gui|" "$HERE/stasis.desktop.in" \
    > "$DESKTOP_DIR/stasis.desktop"

echo
echo "installed   : $BIN_DIR/stasis-gui   ($SOURCE)"
echo "menu entry  : $DESKTOP_DIR/stasis.desktop"
echo "'Stasis' now appears in your applications menu — just click it."
