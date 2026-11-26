#!/usr/bin/env bash
set -e

if ! command -v python3 >/dev/null 2>&1; then
    echo "Could not detect python3. Please install Python 3.8 or newer." >&2
    exit 1
fi

python3 -m pip install --user .

echo "Installed rmcm for the current user. Ensure the Python user bin directory is on PATH."
