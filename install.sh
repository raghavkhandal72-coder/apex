#!/usr/bin/env bash
# Apex Installer: Standalone zero-dependency Python program repair
# Usage: curl -fsSL https://raw.githubusercontent.com/YOUR_USER/apex/main/install.sh | bash

set -euo pipefail

REPO="YOUR_USER/apex"
INSTALL_DIR="${APEX_INSTALL_DIR:-$HOME/.local/bin}"
BIN_NAME="apex"
TARGET="$INSTALL_DIR/$BIN_NAME"

echo "=== Installing Apex (Zero-Dependency Program Repair) ==="

# Check Python 3.10+
if ! command -v python3 >/dev/null 2>&1; then
    echo "Error: python3 is required but was not found on PATH." >&2
    exit 1
fi

PY_VER=$(python3 -c "import sys; print(f'{sys.version_info.major}.{sys.version_info.minor}')")
PY_MAJOR=$(echo "$PY_VER" | cut -d. -f1)
PY_MINOR=$(echo "$PY_VER" | cut -d. -f2)

if [ "$PY_MAJOR" -lt 3 ] || ([ "$PY_MAJOR" -eq 3 ] && [ "$PY_MINOR" -lt 10 ]); then
    echo "Warning: Apex requires Python 3.10+ (found $PY_VER)." >&2
fi

mkdir -p "$INSTALL_DIR"

LATEST_URL="https://github.com/$REPO/releases/latest/download/apex.pyz"

echo "Downloading apex.pyz to $TARGET..."
if command -v curl >/dev/null 2>&1; then
    curl -fsSL "$LATEST_URL" -o "$TARGET" || {
        echo "Could not fetch release binary. If building from source, run: python scripts/build_pyz.py" >&2
        exit 1
    }
elif command -v wget >/dev/null 2>&1; then
    wget -qO "$TARGET" "$LATEST_URL" || {
        echo "Could not fetch release binary. If building from source, run: python scripts/build_pyz.py" >&2
        exit 1
    }
else
    echo "Error: curl or wget is required to download Apex." >&2
    exit 1
fi

chmod +x "$TARGET"

echo "Apex successfully installed to $TARGET!"

# PATH check
case ":$PATH:" in
    *":$INSTALL_DIR:"*) ;;
    *)
        echo ""
        echo "Note: $INSTALL_DIR is not in your PATH."
        echo "Add it by adding this to your ~/.bashrc or ~/.zshrc:"
        echo "  export PATH=\"\$PATH:$INSTALL_DIR\""
        ;;
esac

echo ""
echo "Verify installation with:"
echo "  $BIN_NAME --version"
