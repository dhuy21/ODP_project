#!/usr/bin/env bash
set -euo pipefail

echo "==> Starting IaC Platform"

# Check if pool is initialized
if ! docker network inspect pool-network >/dev/null 2>&1; then
    echo "==> Initializing container pool..."
    ./pool_manager.sh init
else
    echo "==> Pool already initialized"
    ./pool_manager.sh status
fi

echo ""
echo "==> Starting Flask application..."
cd web
python3 app.py