#!/bin/bash
# Apply litellm-config.yaml into the hermes-agent container and restart it.
# Run this on the VPS: bash hermes/deploy-litellm-config.sh

set -euo pipefail

CONTAINER="hermes-agent"
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
CONFIG_SRC="$SCRIPT_DIR/litellm-config.yaml"

if ! docker inspect "$CONTAINER" &>/dev/null; then
  echo "❌  Container '$CONTAINER' not found" >&2
  exit 1
fi

echo "=== Backing up existing config ==="
docker exec "$CONTAINER" cp /app/config.yaml /app/config.yaml.bak 2>/dev/null && echo "  backup saved" || echo "  (no existing config to back up)"

echo "=== Copying new config ==="
docker cp "$CONFIG_SRC" "$CONTAINER":/app/config.yaml
echo "  $CONFIG_SRC → $CONTAINER:/app/config.yaml"

echo "=== Restarting container ==="
docker restart "$CONTAINER"
echo "✅  $CONTAINER restarted"

sleep 5
echo "=== Model / provider lines in logs ==="
docker logs "$CONTAINER" 2>&1 | grep -i "model\|provider" | head -5 || true
