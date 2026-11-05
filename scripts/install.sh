#!/usr/bin/env bash
# Apex-Sovereign: Universal Unix Installer (Linux & macOS)
# Zero external dependencies | 100% Pure Python Standard Library
set -e

BOLD="\033[1m"
GREEN="\033[32m"
CYAN="\033[36m"
GOLD="\033[33m"
RESET="\033[0m"

echo -e "${GOLD}"
echo "   ▄██████▄      APEX-SOVEREIGN INSTALLER"
echo " ▟███▀▀██▀▀███▙    Autonomous Multi-LLM Software Engineering & Attestation Council"
echo " ▐███ █▗▖█ ▐███▌   100% Pure Python | Zero Dependencies"
echo "  ████▄▄▄▄████"
echo "  ▜██████████▛"
echo "    ▀██  ██▀"
echo -e "${RESET}"

# Check for python3
if ! command -v python3 >/dev/null 2>&1; then
    echo -e "[\033[31mERROR\033[0m] python3 is required to run Apex-Sovereign."
    exit 1
fi

PY_VER=$(python3 -c 'import sys; print(f"{sys.version_info.major}.{sys.version_info.minor}")')
echo -e "Detected Python ${CYAN}${PY_VER}${RESET}..."

INSTALL_DIR="${HOME}/.apex/bin"
mkdir -p "${INSTALL_DIR}"

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_DIR="$(dirname "${SCRIPT_DIR}")"
PYZ_SOURCE="${REPO_DIR}/dist/apex.pyz"

if [ -f "${PYZ_SOURCE}" ]; then
    cp "${PYZ_SOURCE}" "${INSTALL_DIR}/apex.pyz"
else
    # Build it fresh
    python3 "${REPO_DIR}/scripts/build_pyz.py"
    cp "${REPO_DIR}/dist/apex.pyz" "${INSTALL_DIR}/apex.pyz"
fi

# Create executable runner shim
cat <<'EOF' > "${INSTALL_DIR}/apex"
#!/usr/bin/env bash
exec python3 "${HOME}/.apex/bin/apex.pyz" "$@"
EOF
chmod +x "${INSTALL_DIR}/apex"
chmod +x "${INSTALL_DIR}/apex.pyz"

# Add to PATH if needed
SHELL_RC=""
case "${SHELL}" in
    */zsh) SHELL_RC="${HOME}/.zshrc" ;;
    */bash) SHELL_RC="${HOME}/.bashrc" ;;
    *) SHELL_RC="${HOME}/.profile" ;;
esac

if ! grep -q 'export PATH="${HOME}/.apex/bin:$PATH"' "${SHELL_RC}" 2>/dev/null; then
    echo 'export PATH="${HOME}/.apex/bin:$PATH"' >> "${SHELL_RC}"
    echo -e "Added ${CYAN}${INSTALL_DIR}${RESET} to ${SHELL_RC}."
fi

echo -e "\n${GREEN}[OK] Successfully installed Apex-Sovereign to ${INSTALL_DIR}/apex${RESET}"
echo -e "Run ${BOLD}apex console${RESET} or ${BOLD}apex omo${RESET} to start!\n"
