#!/usr/bin/env bash
set -euo pipefail

INSTALL_DIR="${HOME}/.local/bin"
DATA_DIR="${XDG_DATA_HOME:-${HOME}/.local/share}/cast-bullet-workshop-calculator"
PURGE=0

if [[ "${1:-}" == "--purge" ]]; then
    PURGE=1
elif [[ $# -gt 0 ]]; then
    echo "Usage: ./uninstall.sh [--purge]" >&2
    exit 2
fi

rm -f "${INSTALL_DIR}/cast-bullet-workshop" "${INSTALL_DIR}/cbwc"

LEGACY_LINK="${INSTALL_DIR}/bullet-lube"
if [[ -L "$LEGACY_LINK" && "$(readlink "$LEGACY_LINK" || true)" == "cast-bullet-workshop" ]]; then
    rm -f "$LEGACY_LINK"
fi

if [[ "$PURGE" -eq 1 ]]; then
    rm -rf "$DATA_DIR"
    echo "Removed program commands and workshop data."
else
    echo "Removed program commands. Saved recipes remain in:"
    echo "  $DATA_DIR"
fi
