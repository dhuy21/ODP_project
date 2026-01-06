#!/usr/bin/env bash
# Kill and cleanup pool containers

set -euo pipefail

POOL_SIZE=30
POOL_NETWORK="pool-network"
STATE_FILE="/tmp/pool_state.json"

echo "==> Killing ODP Pool"

# Stop and remove all pool containers
echo "==> Stopping containers..."
for i in $(seq 1 ${POOL_SIZE}); do
    NAME="pool-node-${i}"
    if docker ps -aq -f name="^${NAME}$" | grep -q .; then
        echo "   - Removing ${NAME}"
        docker rm -f "${NAME}" 2>/dev/null || true
    fi
done

# Remove network
echo "==> Removing network..."
docker network rm "${POOL_NETWORK}" 2>/dev/null || true

# Remove state file
echo "==> Removing state file..."
rm -f "${STATE_FILE}"

# Optional: Remove any client containers/networks
echo "==> Checking for client containers..."
docker ps -a --filter "label=client" --format "{{.Names}}" | while read name; do
    if [ -n "$name" ]; then
        echo "   - Removing client container: ${name}"
        docker rm -f "${name}" 2>/dev/null || true
    fi
done

# Remove client networks (internet-*)
echo "==> Checking for client networks..."
docker network ls --filter "name=internet-" --format "{{.Name}}" | while read net; do
    if [ -n "$net" ]; then
        echo "   - Removing client network: ${net}"
        docker network rm "${net}" 2>/dev/null || true
    fi
done

echo ""
echo "✅ Pool cleanup complete!"
echo ""
echo "To reinitialize the pool, run:"
echo "  ./pool_manager.sh init"
