#!/usr/bin/env bash
set -euo pipefail

POOL_SIZE=30
POOL_NETWORK="pool-network"
POOL_SUBNET="172.30.0.0/24"
POOL_BASE_PORT=3000
STATE_FILE="/tmp/pool_state.json"

# Try to use venv python if available, fallback to system python
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
if [ -f "${SCRIPT_DIR}/venv/bin/python3" ]; then
    PYTHON="${SCRIPT_DIR}/venv/bin/python3"
elif [ -f "${SCRIPT_DIR}/venv/bin/python" ]; then
    PYTHON="${SCRIPT_DIR}/venv/bin/python"
else
    PYTHON="python3"
fi

# --- State file updates must be serialized ---
# We run release/check-expired in parallel. Without locking, concurrent writes can corrupt JSON,
# causing `status` to show "unknown" for all containers.
update_state_locked() {
    local name="$1"
    local status="$2"
    local client="$3"
    local expiry="$4"

    # Serialize updates with a file lock. Also write atomically to avoid partial reads.
    (
        flock -x 200
        python3 - "${STATE_FILE}" "${name}" "${status}" "${client}" "${expiry}" <<'PY'
import sys, json, os, tempfile

state_file, name, status, client, expiry = sys.argv[1:6]
try:
    with open(state_file, 'r') as f:
        state = json.load(f)
except Exception:
    state = {}

state[name] = {"status": status, "client": client, "expiry": int(expiry)}

dir_name = os.path.dirname(state_file) or "."
fd, tmp_path = tempfile.mkstemp(prefix=".pool_state_", dir=dir_name, text=True)
try:
    with os.fdopen(fd, 'w') as f:
        json.dump(state, f)
    os.replace(tmp_path, state_file)
finally:
    try:
        if os.path.exists(tmp_path):
            os.remove(tmp_path)
    except Exception:
        pass
PY
    ) 200>"${STATE_FILE}.lock"
}
# --- Auto-detect platform architecture ---
ARCH="$(uname -m)"
case "${ARCH}" in
  x86_64|amd64)
    PLATFORM="linux/amd64"
    echo "==> Detected architecture: Intel/AMD (Windows/Linux)"
    ;;
  aarch64|arm64)
    PLATFORM="linux/arm64"
    echo "==> Detected architecture: Apple Silicon (Mac M1/M2/M3)"
    ;;
  *)
    echo "Warning: Unknown architecture ${ARCH}, defaulting to linux/amd64"
    PLATFORM="linux/amd64"
    ;;
esac

# Initialize pool
init_pool() {
    echo "==> Initializing resource pool"
    
    # Create network if not exists
    docker network inspect "${POOL_NETWORK}" >/dev/null 2>&1 || \
        docker network create --subnet "${POOL_SUBNET}" "${POOL_NETWORK}"
    
    # Build base image
    docker build -t pool-node:latest --platform="${PLATFORM}" -f ./Docker/ssh/Dockerfile ./Docker/ssh
    
    # Initialize state file
    echo "{}" > "${STATE_FILE}"
    
    # Start pool containers
    for i in $(seq 1 "${POOL_SIZE}"); do
        NAME="pool-node-${i}"
        PORT=$((POOL_BASE_PORT+i-1))
        
        # Remove existing container if any
        docker rm -f "${NAME}" 2>/dev/null || true
        
        echo "   - Starting ${NAME} on port ${PORT}"
        docker run -d --restart unless-stopped \
            --name "${NAME}" \
            --network "${POOL_NETWORK}" \
            -p "127.0.0.1:${PORT}:22" \
            pool-node:latest >/dev/null
        
        # Query actual IP from Docker (after creation)
        IP=$(docker inspect -f '{{range .NetworkSettings.Networks}}{{.IPAddress}}{{end}}' "${NAME}")
        
        # Mark as free in state file
        python3 - "${STATE_FILE}" "${NAME}" "free" "" "0" <<'PY'
import sys, json
state_file, name, status, client, expiry = sys.argv[1:6]
try:
    with open(state_file, 'r') as f:
        state = json.load(f)
except:
    state = {}
state[name] = {"status": status, "client": client, "expiry": int(expiry)}
with open(state_file, 'w') as f:
    json.dump(state, f)
PY
    done
    
    echo "==> Pool initialized with ${POOL_SIZE} containers"
}

# Allocate containers to client with duration
allocate_to_client() {
    local client_id=$1
    local count=$2
    local username=$3
    local password=$4
    local duration_minutes=${5:-60}  # Default 60 minutes
    
    echo "==> Allocating ${count} containers to ${client_id} for ${duration_minutes} minutes"
    
    # Calculate expiry timestamp
    local expiry=$(date -v+${duration_minutes}M +%s 2>/dev/null || date -d "+${duration_minutes} minutes" +%s)
    
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
        
        # Update state file with expiry
        python3 - "${STATE_FILE}" "${name}" "allocated" "${client_id}" "${expiry}" <<'PY'
import sys, json
state_file, name, status, client, expiry = sys.argv[1:6]
try:
    with open(state_file, 'r') as f:
        state = json.load(f)
except:
    state = {}
state[name] = {"status": status, "client": client, "expiry": int(expiry)}
with open(state_file, 'w') as f:
    json.dump(state, f)
PY
        
        echo "   - Allocated ${name} (${ip}:${port}) until $(date -r ${expiry} '+%Y-%m-%d %H:%M:%S' 2>/dev/null || date -d @${expiry} '+%Y-%m-%d %H:%M:%S')"
    done
}

# Check and release expired containers
check_expired() {
    echo "==> Checking for expired allocations"
    
    local current_time=$(date +%s)
    local expired_count=0
    local pids=()
    
    for i in $(seq 1 "${POOL_SIZE}"); do
        local name="pool-node-${i}"
        
        # Get expiry and status
        local expiry=$(python3 - "${STATE_FILE}" "${name}" <<'PY'
import sys, json
try:
    with open(sys.argv[1], 'r') as f:
        state = json.load(f)
    print(state.get(sys.argv[2], {}).get("expiry", 0))
except:
    print(0)
PY
)
        
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
        
        # Check if allocated and expired
        if [ "${status}" = "allocated" ] && [ "${expiry}" -gt 0 ] && [ "${current_time}" -gt "${expiry}" ]; then
            echo "   - Releasing expired ${name} (client: ${client})"
            
            # Process each expired container in parallel (background job)
            (
                docker restart "${name}" >/dev/null 2>&1
                
                if [ $? -eq 0 ]; then
                    sleep 3
                    
                    if docker ps -q -f name="^${name}$" | grep -q .; then
                        # Update state to free IMMEDIATELY (before deep clean)
                        update_state_locked "${name}" "free" "" "0"
                        
                        # DEEP CLEAN: Extra safety measure (runs after state update, non-blocking)
                        docker exec "${name}" /bin/bash -c "
                            for user in \$(ls /home 2>/dev/null | grep -v vagrant); do
                                userdel -r \$user 2>/dev/null || true
                            done
                            rm -rf /home/vagrant/* /home/vagrant/.* 2>/dev/null || true
                            mkdir -p /home/vagrant/.ssh
                            curl -fsSL https://raw.githubusercontent.com/hashicorp/vagrant/master/keys/vagrant.pub -o /home/vagrant/.ssh/authorized_keys 2>/dev/null || true
                            chmod 700 /home/vagrant/.ssh
                            chmod 600 /home/vagrant/.ssh/authorized_keys
                            chown -R vagrant:vagrant /home/vagrant/.ssh
                            rm -rf /tmp/* /tmp/.* 2>/dev/null || true
                            rm -rf /var/tmp/* 2>/dev/null || true
                            rm -rf /opt/* 2>/dev/null || true
                        " >/dev/null 2>&1 || true
                    fi
                fi
            ) &
            
            pids+=($!)
            expired_count=$((expired_count + 1))
        fi
    done
    
    # Wait for all background jobs to complete
    for pid in "${pids[@]}"; do
        wait "$pid" 2>/dev/null || true
    done
    
    if [ ${expired_count} -gt 0 ]; then
        echo "==> Released ${expired_count} expired container(s)"
    else
        echo "==> No expired containers found"
    fi
}

# Release containers from client
release_from_client() {
    local client_id=$1
    
    echo "==> Releasing containers from ${client_id}"
    
    local released_count=0
    local pids=()
    
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
            echo "   - Resetting ${name} (full clean)..."
            
            # Process each container in parallel (background job)
            (
                # Restart container to completely reset filesystem
                docker restart "${name}" >/dev/null 2>&1
                
                if [ $? -eq 0 ]; then
                    # Wait for container to be fully ready (SSH service started)
                    sleep 3
                    
                    # VERIFY: Check that container is actually running
                    if docker ps -q -f name="^${name}$" | grep -q .; then
                        # Update state file to free IMMEDIATELY (before deep clean)
                        update_state_locked "${name}" "free" "" "0"
                        
                        echo "   ✓ ${name} marked as free"
                        
                        # DEEP CLEAN: Extra safety measure (runs after state update, non-blocking)
                        docker exec "${name}" /bin/bash -c "
                            for user in \$(ls /home 2>/dev/null | grep -v vagrant); do
                                userdel -r \$user 2>/dev/null || true
                            done
                            rm -rf /home/vagrant/* /home/vagrant/.* 2>/dev/null || true
                            mkdir -p /home/vagrant/.ssh
                            curl -fsSL https://raw.githubusercontent.com/hashicorp/vagrant/master/keys/vagrant.pub -o /home/vagrant/.ssh/authorized_keys 2>/dev/null || true
                            chmod 700 /home/vagrant/.ssh
                            chmod 600 /home/vagrant/.ssh/authorized_keys
                            chown -R vagrant:vagrant /home/vagrant/.ssh
                            rm -rf /tmp/* /tmp/.* 2>/dev/null || true
                            rm -rf /var/tmp/* 2>/dev/null || true
                            rm -rf /opt/* 2>/dev/null || true
                        " >/dev/null 2>&1 || true
                    fi
                fi
            ) &
            
            pids+=($!)
            released_count=$((released_count + 1))
        fi
    done
    
    # Wait for all background jobs to complete
    for pid in "${pids[@]}"; do
        wait "$pid" 2>/dev/null || true
    done
    
    if [ ${released_count} -gt 0 ]; then
        echo "==> Successfully released and reset ${released_count} container(s)"
    else
        echo "==> No containers found for ${client_id}"
    fi
}

# Show pool status
show_status() {
    echo "==> Pool Status (from MySQL Database)"
    echo ""
    printf "%-20s %-15s %-10s %-20s %-25s\n" "Container" "IP" "Port" "Status" "Expires"
    echo "--------------------------------------------------------------------------------------------"
    
    local current_time=$(date +%s)
    
    for i in $(seq 1 "${POOL_SIZE}"); do
        name="pool-node-${i}"
        if docker ps -q -f name="^${name}$" | grep -q .; then
            ip=$(docker inspect --format='{{range .NetworkSettings.Networks}}{{.IPAddress}}{{end}}' "${name}" 2>/dev/null || echo "-")
            port=$(docker port "${name}" 22 2>/dev/null | cut -d: -f2 || echo "-")
            
            # Query MySQL database instead of JSON file
            read -r status client expiry <<< $("${PYTHON}" - "${name}" 2>/dev/null <<'PY'
import sys, os
try:
    import mysql.connector
    from dotenv import load_dotenv
    from pathlib import Path
    
    # Load .env file from web directory
    script_dir = os.path.dirname(os.path.abspath(__file__)) if '__file__' in dir() else os.getcwd()
    env_path = os.path.join(script_dir, 'web', '.env')
    if not os.path.exists(env_path):
        env_path = os.path.join(script_dir, '.env')
    if os.path.exists(env_path):
        load_dotenv(env_path)
    
    # Connect to MySQL
    conn = mysql.connector.connect(
        host=os.environ.get('MYSQL_HOST', 'localhost'),
        user=os.environ.get('MYSQL_USER', 'root'),
        password=os.environ.get('MYSQL_PASSWORD', ''),
        database=os.environ.get('MYSQL_DB', 'odp_platform')
    )
    cursor = conn.cursor()
    
    # Query node info
    cursor.execute("SELECT status, owner, expiry FROM pool_nodes WHERE name = %s", (sys.argv[1],))
    result = cursor.fetchone()
    
    cursor.close()
    conn.close()
    
    if result:
        status, owner, expiry = result
        owner = owner if owner else ""
        expiry = int(expiry) if expiry else 0
        print(f"{status} {owner} {expiry}")
    else:
        print("free  0")
except Exception:
    # Fallback to free if database query fails
    print("free  0")
PY
)
            
            if [ "${status}" = "allocated" ] && [ -n "${client}" ]; then
                status="allocated (${client})"
                
                if [ "${expiry}" -gt 0 ]; then
                    remaining=$((expiry - current_time))
                    if [ ${remaining} -gt 0 ]; then
                        minutes=$((remaining / 60))
                        expires="in ${minutes} min"
                    else
                        expires="EXPIRED"
                    fi
                else
                    expires="never"
                fi
            else
                expires="-"
            fi
            
            printf "%-20s %-15s %-10s %-20s %-25s\n" "${name}" "${ip}" "${port}" "${status}" "${expires}"
        else
            printf "%-20s %-15s %-10s %-20s %-25s\n" "${name}" "-" "-" "stopped" "-"
        fi
    done
}

# Health check - verify all containers are running
health_check() {
    echo "==> Performing health check"
    
    local missing_count=0
    local stopped_count=0
    
    for i in $(seq 1 "${POOL_SIZE}"); do
        local name="pool-node-${i}"
        
        # Check if container exists and is running
        if ! docker ps -q -f name="^${name}$" | grep -q .; then
            # Container is missing or stopped
            if docker ps -a -q -f name="^${name}$" | grep -q .; then
                echo "   - ${name}: STOPPED"
                stopped_count=$((stopped_count + 1))
            else
                echo "   - ${name}: MISSING"
                missing_count=$((missing_count + 1))
            fi
            
            # Get client from state file
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
            
            # If container was allocated, mark it as error
            if [ "${status}" = "allocated" ] && [ -n "${client}" ]; then
                echo "      WARNING: Container was allocated to ${client}"
                
                # Mark as error in state file
                python3 - "${STATE_FILE}" "${name}" "error" "${client}" "0" <<'PY'
import sys, json
state_file, name, status, client, expiry = sys.argv[1:6]
try:
    with open(state_file, 'r') as f:
        state = json.load(f)
except:
    state = {}
state[name] = {"status": status, "client": client, "expiry": 0}
with open(state_file, 'w') as f:
    json.dump(state, f)
PY
            fi
        fi
    done
    
    if [ $((missing_count + stopped_count)) -gt 0 ]; then
        echo ""
        echo "==> Health check FAILED:"
        echo "    - Missing containers: ${missing_count}"
        echo "    - Stopped containers: ${stopped_count}"
        echo ""
        echo "Run './pool_manager.sh recover' to attempt automatic recovery"
        return 1
    else
        echo "==> Health check PASSED: All ${POOL_SIZE} containers are running"
        return 0
    fi
}

# Recover missing or stopped containers
recover_pool() {
    echo "==> Attempting to recover pool"
    
    for i in $(seq 1 "${POOL_SIZE}"); do
        local name="pool-node-${i}"
        local ip="172.30.0.$((10+i))"
        local port=$((POOL_BASE_PORT+i-1))
        
        # Check if container is running
        if docker ps -q -f name="^${name}$" | grep -q .; then
            echo "   - ${name}: OK"
            continue
        fi
        
        # Check if container exists but stopped
        if docker ps -a -q -f name="^${name}$" | grep -q .; then
            echo "   - ${name}: Restarting..."
            docker start "${name}" >/dev/null
        else
            echo "   - ${name}: Recreating..."
            
            # Remove from state first
            docker rm -f "${name}" 2>/dev/null || true
            
            # Recreate container
            docker run -d --restart unless-stopped \
                --name "${name}" \
                --network "${POOL_NETWORK}" --ip "${ip}" \
                -p "127.0.0.1:${port}:22" \
                pool-node:latest >/dev/null
        fi
        
        # Reset to free state
        python3 - "${STATE_FILE}" "${name}" "free" "" "0" <<'PY'
import sys, json
state_file, name, status, client, expiry = sys.argv[1:6]
try:
    with open(state_file, 'r') as f:
        state = json.load(f)
except:
    state = {}
state[name] = {"status": status, "client": client, "expiry": int(expiry)}
with open(state_file, 'w') as f:
    json.dump(state, f)
PY
    done
    
    echo "==> Recovery complete"
}

# Main command handler
case "${1:-}" in
    init)
        init_pool
        ;;
    allocate)
        allocate_to_client "$2" "$3" "$4" "$5" "${6:-60}"
        ;;
    release)
        release_from_client "$2"
        ;;
    check-expired)
        check_expired
        ;;
    health-check)
        health_check
        ;;
    recover)
        recover_pool
        ;;
    status)
        show_status
        ;;
    *)
        echo "Usage: $0 {init|allocate|release|check-expired|health-check|recover|status}"
        echo ""
        echo "Commands:"
        echo "  init                                    - Initialize container pool"
        echo "  allocate <client> <count> <user> <pass> [duration] - Allocate containers"
        echo "  release <client>                        - Release client's containers"
        echo "  check-expired                           - Check and release expired allocations"
        echo "  health-check                            - Verify all containers are running"
        echo "  recover                                 - Recover missing/stopped containers"
        echo "  status                                  - Show pool status"
        exit 1
        ;;
esac