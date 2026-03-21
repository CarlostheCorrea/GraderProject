#!/usr/bin/env bash
set -euo pipefail

if ! command -v python3 >/dev/null 2>&1; then
  echo "python3 is required but was not found."
  exit 1
fi

if [ ! -d ".venv" ]; then
  echo "Creating virtual environment..."
  python3 -m venv .venv
fi

echo "Installing dependencies..."
.venv/bin/pip install -r requirements.txt

if [ -z "${OPENAI_API_KEY:-}" ]; then
  echo "OPENAI_API_KEY is not set."
  echo "Set it first, for example:"
  echo "export OPENAI_API_KEY='your_key_here'"
  exit 1
fi

echo "Starting app at http://127.0.0.1:8000"
exec .venv/bin/uvicorn main:app
