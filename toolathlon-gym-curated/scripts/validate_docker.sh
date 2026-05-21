#!/usr/bin/env bash
# Validate Docker build and MCP preflight in containerized environment

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
TOOLATHLON_DIR="$(cd "$SCRIPT_DIR/.." && pwd)"
IMAGE_NAME="${IMAGE_NAME:-toolathlon:repair}"
BASE_IMAGE_NAME="${BASE_IMAGE_NAME:-toolathlon:base}"
DOCKER_CONTEXT="${DOCKER_CONTEXT:-default}"
OUT_DIR="${OUT_DIR:-$TOOLATHLON_DIR/../.validation_logs}"
DOCKER_PROGRESS="${DOCKER_PROGRESS:-auto}"
DOCKER_INSTALL_PLAYWRIGHT="${DOCKER_INSTALL_PLAYWRIGHT:-0}"
REBUILD_BASE_IMAGE="${REBUILD_BASE_IMAGE:-0}"
DOCKER_SMOKE_SUMMARY_FILE="$OUT_DIR/docker_mcp_smoke_summary.json"

mkdir -p "$OUT_DIR"

build_base_image() {
  echo "Building reusable Docker base image: $BASE_IMAGE_NAME"
  docker --context="$DOCKER_CONTEXT" buildx build \
    --progress "$DOCKER_PROGRESS" \
    --build-arg "INSTALL_PLAYWRIGHT=$DOCKER_INSTALL_PLAYWRIGHT" \
    --load -t "$BASE_IMAGE_NAME" -f "$TOOLATHLON_DIR/Dockerfile.base" "$TOOLATHLON_DIR"
}

if [ "$REBUILD_BASE_IMAGE" = "1" ]; then
  if ! build_base_image; then
    echo "✗ Docker base image build failed"
    exit 1
  fi
elif ! docker --context="$DOCKER_CONTEXT" image inspect "$BASE_IMAGE_NAME" >/dev/null 2>&1; then
  if ! build_base_image; then
    echo "✗ Docker base image build failed"
    exit 1
  fi
else
  echo "✓ Reusing existing Docker base image: $BASE_IMAGE_NAME"
fi

echo "Building Docker image: $IMAGE_NAME"
if ! docker --context="$DOCKER_CONTEXT" buildx build \
  --progress "$DOCKER_PROGRESS" \
  --build-arg "BASE_IMAGE=$BASE_IMAGE_NAME" \
  --load -t "$IMAGE_NAME" "$TOOLATHLON_DIR"; then
  echo "✗ Docker build failed"
  exit 1
fi

echo "Running preflight in container..."
if ! docker --context="$DOCKER_CONTEXT" run --rm \
  -v "$OUT_DIR:/validation_logs" \
  "$IMAGE_NAME" \
  python scripts/smoke_mcp_servers.py \
  --json-output /validation_logs/docker_mcp_smoke_summary.json; then
  echo "✗ Docker container MCP smoke tests failed"
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
echo "Evidence: $DOCKER_SMOKE_SUMMARY_FILE"
echo "Docker context: $DOCKER_CONTEXT"
echo "Docker progress mode: $DOCKER_PROGRESS"
echo "Base image: $BASE_IMAGE_NAME"
echo "Install Playwright browser in base image: $DOCKER_INSTALL_PLAYWRIGHT"
