#!/usr/bin/env bash
set -euo pipefail
#cd "$(dirname "$0")"
cd arcade
python3 arcade_launcher.py "$@"
