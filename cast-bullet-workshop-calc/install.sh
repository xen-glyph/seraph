#!/usr/bin/env bash
set -euo pipefail

APP_NAME="Cast Bullet Workshop Calculator"
SCRIPT_NAME="cast_bullet_workshop_calculator.py"
INSTALL_DIR="${HOME}/.local/bin"
PROGRAM_PATH="${INSTALL_DIR}/cast-bullet-workshop"
PRINTER_QUEUE=""
SET_PRINTER=0
COMPAT_BULLET_LUBE=0
UPDATE_PATH=1

usage() {
    cat <<'EOF'
Usage: ./install.sh [options]

Options:
  --printer QUEUE          Save a preferred CUPS printer queue.
  --compat-bullet-lube     Install a bullet-lube compatibility command.
  --no-path-update         Do not add ~/.local/bin to the shell PATH.
  -h, --help               Show this help.

Examples:
  ./install.sh
  ./install.sh --printer MyPrinter
  ./install.sh --printer MyPrinter --compat-bullet-lube
EOF
}

while [[ $# -gt 0 ]]; do
    case "$1" in
        --printer)
            [[ $# -ge 2 ]] || { echo "--printer requires a queue name." >&2; exit 2; }
            PRINTER_QUEUE="$2"
            SET_PRINTER=1
            shift 2
            ;;
        --compat-bullet-lube)
            COMPAT_BULLET_LUBE=1
            shift
            ;;
        --no-path-update)
            UPDATE_PATH=0
            shift
            ;;
        -h|--help)
            usage
            exit 0
            ;;
        *)
            echo "Unknown option: $1" >&2
            usage >&2
            exit 2
            ;;
    esac
done

SCRIPT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
SOURCE_PATH="${SCRIPT_DIR}/${SCRIPT_NAME}"

if [[ ! -f "$SOURCE_PATH" ]]; then
    echo "Cannot find ${SCRIPT_NAME} beside install.sh." >&2
    exit 1
fi

if ! command -v python3 >/dev/null 2>&1; then
    echo "Python 3 is required but was not found." >&2
    exit 1
fi

python3 - <<'PY'
import sys
if sys.version_info < (3, 8):
    raise SystemExit("Python 3.8 or newer is required.")
PY

mkdir -p "$INSTALL_DIR"
install -m 0755 "$SOURCE_PATH" "$PROGRAM_PATH"
ln -sfn "cast-bullet-workshop" "${INSTALL_DIR}/cbwc"

if [[ "$COMPAT_BULLET_LUBE" -eq 1 ]]; then
    LEGACY_PATH="${INSTALL_DIR}/bullet-lube"
    if [[ -e "$LEGACY_PATH" && ! -L "$LEGACY_PATH" ]]; then
        BACKUP="${LEGACY_PATH}.pre-cbwc.$(date +%Y%m%d-%H%M%S)"
        mv "$LEGACY_PATH" "$BACKUP"
        echo "Backed up the existing bullet-lube command to:"
        echo "  $BACKUP"
    elif [[ -L "$LEGACY_PATH" ]]; then
        CURRENT_TARGET="$(readlink "$LEGACY_PATH" || true)"
        if [[ "$CURRENT_TARGET" != "cast-bullet-workshop" ]]; then
            BACKUP="${LEGACY_PATH}.pre-cbwc.$(date +%Y%m%d-%H%M%S)"
            mv "$LEGACY_PATH" "$BACKUP"
            echo "Backed up the existing bullet-lube link to:"
            echo "  $BACKUP"
        fi
    fi
    ln -sfn "cast-bullet-workshop" "$LEGACY_PATH"
fi

if [[ "$SET_PRINTER" -eq 1 ]]; then
    "$PROGRAM_PATH" --no-color --set-printer "$PRINTER_QUEUE"
fi

if [[ "$UPDATE_PATH" -eq 1 && ":${PATH}:" != *":${INSTALL_DIR}:"* ]]; then
    SHELL_NAME="$(basename "${SHELL:-bash}")"
    case "$SHELL_NAME" in
        zsh) RC_FILE="${HOME}/.zshrc" ;;
        bash) RC_FILE="${HOME}/.bashrc" ;;
        *) RC_FILE="${HOME}/.profile" ;;
    esac
    PATH_LINE='export PATH="$HOME/.local/bin:$PATH"'
    if [[ ! -f "$RC_FILE" ]] || ! grep -Fqx "$PATH_LINE" "$RC_FILE"; then
        printf '\n# Local user commands\n%s\n' "$PATH_LINE" >> "$RC_FILE"
        echo "Added ~/.local/bin to PATH in $RC_FILE"
    fi
fi

cat <<EOF

${APP_NAME} ${VERSION:-2.0.0} installed.

Commands:
  cast-bullet-workshop
  cbwc
EOF

if [[ "$COMPAT_BULLET_LUBE" -eq 1 ]]; then
    echo "  bullet-lube  (opens the lube module)"
fi

cat <<EOF

Run this in the current shell if the command is not found yet:
  export PATH="\$HOME/.local/bin:\$PATH"

Saved recipes are kept outside the installation directory and survive updates.
EOF
