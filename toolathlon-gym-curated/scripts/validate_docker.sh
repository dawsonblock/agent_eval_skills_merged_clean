#!/usr/bin/env bash
# Validate Docker build and MCP preflight in containerized environment

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
TOOLATHLON_DIR="$(cd "$SCRIPT_DIR/.." && pwd)"
IMAGE_NAME="${IMAGE_NAME:-toolathlon:repair}"
DOCKER_CONTEXT="${DOCKER_CONTEXT:-default}"
OUT_DIR="${OUT_DIR:-$TOOLATHLON_DIR/../.validation_logs}"
DOCKER_PROGRESS="${DOCKER_PROGRESS:-auto}"
DOCKER_INSTALL_PLAYWRIGHT="${DOCKER_INSTALL_PLAYWRIGHT:-0}"

mkdir -p "$OUT_DIR"

echo "Building Docker image: $IMAGE_NAME"
if ! docker --context="$DOCKER_CONTEXT" buildx build \
  --progress "$DOCKER_PROGRESS" \
  --build-arg "INSTALL_PLAYWRIGHT=$DOCKER_INSTALL_PLAYWRIGHT" \
  --load -t "$IMAGE_NAME" "$TOOLATHLON_DIR"; then
  echo "✗ Docker build failed"
  exit 1
fi

echo "Running preflight in container..."
if ! docker --context="$DOCKER_CONTEXT" run --rm \
  -v "$OUT_DIR:/validation_logs" \
  "$IMAGE_NAME" \
  python scripts/preflight_mcp_paths.py \
  --json-output /validation_logs/docker_preflight_summary.json; then
  echo "✗ Docker container preflight failed"
  exit 1
fi

echo "✓ Docker validation passed"
echo "Evidence: $OUT_DIR/docker_preflight_summary.json"
echo "Docker context: $DOCKER_CONTEXT"
echo "Docker progress mode: $DOCKER_PROGRESS"
echo "Install Playwright browser in image: $DOCKER_INSTALL_PLAYWRIGHT"
