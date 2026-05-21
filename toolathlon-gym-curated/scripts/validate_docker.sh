#!/usr/bin/env bash
# Validate Docker build and MCP preflight in containerized environment

set -euo pipefail

IMAGE_NAME="${IMAGE_NAME:-toolathlon:repair}"
DOCKER_CONTEXT="${DOCKER_CONTEXT:-default}"
OUT_DIR="${OUT_DIR:-$(cd "$(dirname "${BASH_SOURCE[0]}")" && cd .. && pwd)/../.validation_logs}"

mkdir -p "$OUT_DIR"

echo "Building Docker image: $IMAGE_NAME"
if ! docker --context="$DOCKER_CONTEXT" buildx build --load -t "$IMAGE_NAME" .; then
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
