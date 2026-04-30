#!/usr/bin/env bash
set -euo pipefail

if ! command -v python3 >/dev/null 2>&1; then
  echo "python3 is missing. Install it with: sudo apt update && sudo apt install -y python3"
  exit 1
fi

python3 - <<'PY'
import curses
print('python3 and curses are available')
PY

chmod +x "$(dirname "$0")/run.sh" "$(dirname "$0")/centipede_terminal.py"
echo "Install check complete. Run: ./run.sh"
