#!/usr/bin/env bash
set -euo pipefail

POOL_SIZE=10
POOL_NETWORK="pool-network"
POOL_SUBNET="172.30.0.0/24"
POOL_BASE_PORT=3000
STATE_FILE="/tmp/pool_state.json"

# Initialize pool
init_pool() {
    echo "==> Initializing resource pool"
    
    # Create network if not exists
    docker network inspect "${POOL_NETWORK}" >/dev/null 2>&1 || \
        docker network create --subnet "${POOL_SUBNET}" "${POOL_NETWORK}"
    
    # Build base image
    docker build -t pool-node:latest --platform=linux/arm64 -f ./Docker/ssh/Dockerfile ./Docker/ssh
    
    # Initialize state file
    echo "{}" > "${STATE_FILE}"
    
    # Start pool containers
    for i in $(seq 1 "${POOL_SIZE}"); do
        NAME="pool-node-${i}"
        IP="172.30.0.$((10+i))"
        PORT=$((POOL_BASE_PORT+i-1))
        
        # Remove existing container if any
        docker rm -f "${NAME}" 2>/dev/null || true
        
        echo "   - Starting ${NAME} on port ${PORT}"
        docker run -d --restart unless-stopped \
            --name "${NAME}" \
            --network "${POOL_NETWORK}" --ip "${IP}" \
            -p "127.0.0.1:${PORT}:22" \
            pool-node:latest >/dev/null
        
        # Mark as free in state file
        python3 - "${STATE_FILE}" "${NAME}" "free" "" <<'PY'
import sys, json
state_file, name, status, client = sys.argv[1:5]
try:
    with open(state_file, 'r') as f:
        state = json.load(f)
except:
    state = {}
state[name] = {"status": status, "client": client}
with open(state_file, 'w') as f:
    json.dump(state, f)
PY
    done
    
    echo "==> Pool initialized with ${POOL_SIZE} containers"
}

# Allocate containers to client
allocate_to_client() {
    local client_id=$1
    local count=$2
    local username=$3
    local password=$4
    
    echo "==> Allocating ${count} containers to ${client_id}"
    
    # Find free containers
    local free_containers=()
    for i in $(seq 1 "${POOL_SIZE}"); do
        local name="pool-node-${i}"
        
        # Check if container exists and is running
        if ! docker ps -q -f name="^${name}$" | grep -q .; then
            continue
        fi
        
        # Check status in state file
        local status=$(python3 - "${STATE_FILE}" "${name}" <<'PY'
import sys, json
try:
    with open(sys.argv[1], 'r') as f:
        state = json.load(f)
    print(state.get(sys.argv[2], {}).get("status", "free"))
except:
    print("free")
PY
)
        
        if [ "${status}" = "free" ]; then
            free_containers+=("${name}")
        fi
        
        if [ ${#free_containers[@]} -eq ${count} ]; then
            break
        fi
    done
    
    local available_count=${#free_containers[@]}
    
    if [ "${available_count}" -lt "${count}" ]; then
        echo "Error: Not enough free containers (need ${count}, have ${available_count})"
        return 1
    fi
    
    # Allocate containers
    for name in "${free_containers[@]}"; do
        local container_id=$(docker ps -q -f name="^${name}$")
        local port=$(docker port "${name}" 22 2>/dev/null | cut -d: -f2)
        local ip=$(docker inspect --format='{{range .NetworkSettings.Networks}}{{.IPAddress}}{{end}}' "${name}" 2>/dev/null)
        
        # Create user in container
        docker exec "${name}" /bin/bash -c "
            useradd -m -s /bin/bash ${username} 2>/dev/null || true
            echo '${username}:${password}' | chpasswd
            echo '${username} ALL=(ALL) NOPASSWD: ALL' > /etc/sudoers.d/${username}
            chmod 0440 /etc/sudoers.d/${username}
        " >/dev/null 2>&1
        
        # Update state file
        python3 - "${STATE_FILE}" "${name}" "allocated" "${client_id}" <<'PY'
import sys, json
state_file, name, status, client = sys.argv[1:5]
try:
    with open(state_file, 'r') as f:
        state = json.load(f)
except:
    state = {}
state[name] = {"status": status, "client": client}
with open(state_file, 'w') as f:
    json.dump(state, f)
PY
        
        echo "   - Allocated ${name} (${ip}:${port})"
    done
}

# Release containers from client
release_from_client() {
    local client_id=$1
    
    echo "==> Releasing containers from ${client_id}"
    
    for i in $(seq 1 "${POOL_SIZE}"); do
        local name="pool-node-${i}"
        
        # Check client in state file
        local client=$(python3 - "${STATE_FILE}" "${name}" <<'PY'
import sys, json
try:
    with open(sys.argv[1], 'r') as f:
        state = json.load(f)
    print(state.get(sys.argv[2], {}).get("client", ""))
except:
    print("")
PY
)
        
        if [ "${client}" = "${client_id}" ]; then
            # Reset container - remove custom users
            docker exec "${name}" /bin/bash -c "
                for user in \$(ls /home | grep -v vagrant); do
                    userdel -r \$user 2>/dev/null || true
                done
            " >/dev/null 2>&1 || true
            
            # Update state file
            python3 - "${STATE_FILE}" "${name}" "free" "" <<'PY'
import sys, json
state_file, name, status, client = sys.argv[1:5]
try:
    with open(state_file, 'r') as f:
        state = json.load(f)
except:
    state = {}
state[name] = {"status": status, "client": client}
with open(state_file, 'w') as f:
    json.dump(state, f)
PY
            
            echo "   - Released ${name}"
        fi
    done
}

# Show pool status
show_status() {
    echo "==> Pool Status"
    echo ""
    printf "%-20s %-15s %-10s %-15s\n" "Container" "IP" "Port" "Status"
    echo "----------------------------------------------------------------"
    
    for i in $(seq 1 "${POOL_SIZE}"); do
        name="pool-node-${i}"
        if docker ps -q -f name="^${name}$" | grep -q .; then
            ip=$(docker inspect --format='{{range .NetworkSettings.Networks}}{{.IPAddress}}{{end}}' "${name}" 2>/dev/null || echo "-")
            port=$(docker port "${name}" 22 2>/dev/null | cut -d: -f2 || echo "-")
            
            status=$(python3 - "${STATE_FILE}" "${name}" <<'PY'
import sys, json
try:
    with open(sys.argv[1], 'r') as f:
        state = json.load(f)
    print(state.get(sys.argv[2], {}).get("status", "unknown"))
except:
    print("unknown")
PY
)
            
            client=$(python3 - "${STATE_FILE}" "${name}" <<'PY'
import sys, json
try:
    with open(sys.argv[1], 'r') as f:
        state = json.load(f)
    print(state.get(sys.argv[2], {}).get("client", ""))
except:
    print("")
PY
)
            
            if [ "${status}" = "allocated" ] && [ -n "${client}" ]; then
                status="allocated (${client})"
            fi
            
            printf "%-20s %-15s %-10s %-15s\n" "${name}" "${ip}" "${port}" "${status}"
        else
            printf "%-20s %-15s %-10s %-15s\n" "${name}" "-" "-" "stopped"
        fi
    done
}

# Main command handler
case "${1:-}" in
    init)
        init_pool
        ;;
    allocate)
        allocate_to_client "$2" "$3" "$4" "$5"
        ;;
    release)
        release_from_client "$2"
        ;;
    status)
        show_status
        ;;
    *)
        echo "Usage: $0 {init|allocate|release|status}"
        echo ""
        echo "Commands:"
        echo "  init                           - Initialize container pool"
        echo "  allocate <client> <count> <user> <pass> - Allocate containers"
        echo "  release <client>               - Release client's containers"
        echo "  status                         - Show pool status"
        exit 1
        ;;
esac