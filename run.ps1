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

$Port = if ($env:PORT) { $env:PORT } else { "8017" }

if (Test-Path ".env") {
  Get-Content ".env" | ForEach-Object {
    $line = $_.Trim()
    if ($line -and -not $line.StartsWith("#") -and $line.Contains("=")) {
      $name, $value = $line -split "=", 2
      $name = $name.Trim()
      $value = $value.Trim().Trim('"').Trim("'")
      if ($name -and -not [Environment]::GetEnvironmentVariable($name, "Process")) {
        [Environment]::SetEnvironmentVariable($name, $value, "Process")
      }
    }
  }
}

if (-not $env:OPENAI_API_KEY) {
  Write-Host "OPENAI_API_KEY is not set."
  Write-Host "Set it in .env or set it first, for example:"
  Write-Host 'OPENAI_API_KEY="your_key_here"'
  exit 1
}

Write-Host "Starting Rubric Grader at http://127.0.0.1:$Port"
.\.venv\Scripts\python -m uvicorn main:app --host 127.0.0.1 --port $Port
