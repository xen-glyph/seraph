#!/usr/bin/env bash
set -euo pipefail

TARGET_FILE="$HOME/.local/bin/bullet-lube"
DATA_DIR="${XDG_DATA_HOME:-$HOME/.local/share}/bullet-lube-calculator"

rm -f "$TARGET_FILE"
echo "Removed: $TARGET_FILE"

if [[ "${1:-}" == "--purge" ]]; then
    rm -rf "$DATA_DIR"
    echo "Removed saved recipe data: $DATA_DIR"
else
    echo "Saved recipes were preserved in: $DATA_DIR"
    echo "Run ./uninstall.sh --purge to remove them too."
fi
