$ErrorActionPreference = "Stop"

if (-not (Get-Command python -ErrorAction SilentlyContinue)) {
  Write-Host "Python is required but was not found."
  exit 1
}

if (-not (Test-Path ".venv")) {
  Write-Host "Creating virtual environment..."
  python -m venv .venv
}

Write-Host "Installing dependencies..."
.\.venv\Scripts\python -m pip install -r requirements.txt

if (-not $env:OPENAI_API_KEY) {
  Write-Host "OPENAI_API_KEY is not set."
  Write-Host "Set it first, for example:"
  Write-Host '$env:OPENAI_API_KEY="your_key_here"'
  exit 1
}

Write-Host "Starting app at http://127.0.0.1:8000"
.\.venv\Scripts\python -m uvicorn main:app
