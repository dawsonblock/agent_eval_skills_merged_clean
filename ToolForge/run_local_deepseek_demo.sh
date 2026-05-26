#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$ROOT_DIR"

HOST="127.0.0.1"
PORT="8080"
RELOAD="true"
DRY_RUN="false"

usage() {
  cat <<'EOF'
Usage: ./run_local_deepseek_demo.sh [options]

Options:
  --lan              Bind to 0.0.0.0 so other devices on your LAN can connect
  --host <host>      Bind host (default: 127.0.0.1)
  --port <port>      Bind port (default: 8080)
  --no-reload        Disable uvicorn autoreload
  --dry-run          Print launch settings and exit
  -h, --help         Show this help

Examples:
  ./run_local_deepseek_demo.sh
  ./run_local_deepseek_demo.sh --lan
  ./run_local_deepseek_demo.sh --lan --port 8090
EOF
}

while [[ $# -gt 0 ]]; do
  case "$1" in
    --lan)
      HOST="0.0.0.0"
      shift
      ;;
    --host)
      HOST="${2:-}"
      shift 2
      ;;
    --port)
      PORT="${2:-}"
      shift 2
      ;;
    --no-reload)
      RELOAD="false"
      shift
      ;;
    --dry-run)
      DRY_RUN="true"
      shift
      ;;
    -h|--help)
      usage
      exit 0
      ;;
    *)
      echo "Unknown option: $1"
      usage
      exit 1
      ;;
  esac
done

if [[ -f ".env" ]]; then
  echo "Loading .env"
else
  echo "No .env found. Copy .env.example to .env and set DEEPSEEK_API_KEY if needed."
fi

if [[ -z "${DEEPSEEK_MODEL:-}" ]]; then
  export DEEPSEEK_MODEL="deepseek-chat"
fi

export PYTHONPATH="${ROOT_DIR}:${PYTHONPATH:-}"

if [[ "$HOST" == "0.0.0.0" ]]; then
  LAN_IP="$(ipconfig getifaddr en0 2>/dev/null || true)"
  if [[ -z "$LAN_IP" ]]; then
    LAN_IP="$(ipconfig getifaddr en1 2>/dev/null || true)"
  fi

  if [[ -n "$LAN_IP" ]]; then
    echo "LAN mode enabled. Open from iPhone Safari: http://${LAN_IP}:${PORT}"
  else
    echo "LAN mode enabled. Could not auto-detect LAN IP."
    echo "Find your Mac IP in System Settings > Network, then open http://<your-ip>:${PORT}"
  fi
fi

echo "Starting Local DeepSeek Tool UI Demo on http://${HOST}:${PORT}"

if [[ "$DRY_RUN" == "true" ]]; then
  echo "Dry run only. Exiting without starting server."
  exit 0
fi

if [[ "$RELOAD" == "true" ]]; then
  python -m uvicorn apps.local_deepseek_demo.server:app --host "$HOST" --port "$PORT" --reload
else
  python -m uvicorn apps.local_deepseek_demo.server:app --host "$HOST" --port "$PORT"
fi
