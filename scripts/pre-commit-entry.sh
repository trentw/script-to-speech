#!/bin/sh
set -euo pipefail

FRONTEND_DIR="gui/frontend"
FRONTEND_PACKAGE_NAME="frontend"

# Check for pnpm
if ! command -v pnpm >/dev/null; then
  echo "Error: pnpm is not installed or not in your PATH."
  echo "Please install it: https://pnpm.io/installation"
  exit 1
fi

# Check dependencies installed
if [ ! -d "${FRONTEND_DIR}/node_modules" ]; then
  echo "Error: node_modules not found in '${FRONTEND_DIR}/'."
  echo "Please run 'pnpm install' from the repository root."
  exit 1
fi

# Get the command and shift it off
CMD="$1"
shift

# Transform file paths by removing the frontend directory prefix
TRANSFORMED_ARGS=()
for arg in "$@"; do
  # If the argument starts with gui/frontend/, remove that prefix
  if echo "$arg" | grep -q "^gui/frontend/"; then
    arg=$(echo "$arg" | sed 's|^gui/frontend/||')
  fi
  TRANSFORMED_ARGS+=("$arg")
done

# Execute using workspace filter with transformed arguments
exec pnpm --filter "${FRONTEND_PACKAGE_NAME}" exec -- "$CMD" "${TRANSFORMED_ARGS[@]}"