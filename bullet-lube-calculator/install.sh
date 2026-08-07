#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
SOURCE_FILE="$SCRIPT_DIR/bullet_lube_calculator.py"
INSTALL_DIR="$HOME/.local/bin"
TARGET_FILE="$INSTALL_DIR/bullet-lube"

if [[ ! -f "$SOURCE_FILE" ]]; then
    echo "Error: bullet_lube_calculator.py was not found beside install.sh." >&2
    exit 1
fi

if ! command -v python3 >/dev/null 2>&1; then
    echo "Error: Python 3 is required but was not found." >&2
    exit 1
fi

if ! python3 - <<'PY'
import sys
raise SystemExit(0 if sys.version_info >= (3, 8) else 1)
PY
then
    echo "Error: Python 3.8 or newer is required." >&2
    exit 1
fi

mkdir -p "$INSTALL_DIR"
install -m 0755 "$SOURCE_FILE" "$TARGET_FILE"

echo
echo "Bullet Lube Calculator installed successfully:"
echo "  $TARGET_FILE"
echo

case ":$PATH:" in
    *":$INSTALL_DIR:"*)
        echo "Run it with:"
        echo "  bullet-lube"
        ;;
    *)
        echo "Your shell PATH does not currently include $INSTALL_DIR"
        echo
        echo "For Bash, add this line to ~/.bashrc:"
        echo '  export PATH="$HOME/.local/bin:$PATH"'
        echo
        echo "For Zsh, add the same line to ~/.zshrc."
        echo "Then open a new terminal or run: source ~/.bashrc"
        echo
        echo "You can launch it immediately with:"
        echo "  $TARGET_FILE"
        ;;
esac
