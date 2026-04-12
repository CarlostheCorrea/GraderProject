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

PORT="${PORT:-8017}"

if [ -f ".env" ]; then
  set -a
  # shellcheck disable=SC1091
  . ./.env
  set +a
fi

if [ -z "${OPENAI_API_KEY:-}" ]; then
  echo "OPENAI_API_KEY is not set."
  echo "Set it in .env or export it first, for example:"
  echo "OPENAI_API_KEY='your_key_here'"
  exit 1
fi

echo "Starting Rubric Grader at http://127.0.0.1:${PORT}"
exec .venv/bin/uvicorn main:app --host 127.0.0.1 --port "${PORT}"
