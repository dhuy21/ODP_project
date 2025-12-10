#!/usr/bin/env bash
# Run this script to auto-release expired containers and check health

while true; do
    echo "==> $(date '+%Y-%m-%d %H:%M:%S') - Running cleanup and health check"
    
    # Check for expired allocations
    ./pool_manager.sh check-expired
    
    # Perform health check
    if ! ./pool_manager.sh health-check >/dev/null 2>&1; then
        echo "!!! Health check failed - attempting recovery..."
        ./pool_manager.sh recover
    fi
    
    echo ""
    sleep 60
done