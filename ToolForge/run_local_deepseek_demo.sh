#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$ROOT_DIR"

if [[ -f ".env" ]]; then
  echo "Loading .env"
else
  echo "No .env found. Copy .env.example to .env and set DEEPSEEK_API_KEY if needed."
fi

if [[ -z "${DEEPSEEK_MODEL:-}" ]]; then
  export DEEPSEEK_MODEL="deepseek-chat"
fi

export PYTHONPATH="${ROOT_DIR}:${PYTHONPATH:-}"

echo "Starting Local DeepSeek Tool UI Demo on http://127.0.0.1:8080"
python -m uvicorn apps.local_deepseek_demo.server:app --host 127.0.0.1 --port 8080 --reload
