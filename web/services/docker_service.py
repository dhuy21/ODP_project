import docker
import time
import platform
import subprocess
from config.config import Config
from models.pool import PoolDatabase

class DockerService:
    """Service for Docker container management"""
    def __init__(self):
        self.project_dir = Config.PROJECT_DIR
        self.pool_db = PoolDatabase()
        try:
            self.client = docker.from_env()
        except Exception as e:
            print(f"Failed to connect to Docker Daemon: {e}")
            self.client = None
    
    def get_pool_status(self):
        """Get current pool status"""
        try:
            stats = self.pool_db.get_pool_status()
            return {
                'success': True,
                'total': stats.get('total', 0),
                'free': stats.get('free', 0),
                'allocated': stats.get('allocated', 0)
            }
        except Exception as e:
            print(f"Error getting pool status: {e}")
            return {'success': False, 'error': str(e)}
    
    def check_expired_containers(self):
        """Check and cleanup expired containers (backup cleanup for orphaned nodes)"""
        if not self.client:
            return False
        try:
            # Find expired nodes in pool_nodes table
            # This is a backup cleanup in case nodes are not released by main expiry logic
            current_time = time.time()
            conn = self.pool_db._get_connection()
            cursor = conn.cursor(dictionary=True)
            expired_nodes = []
            try:
                sql = "SELECT * FROM pool_nodes WHERE status = 'allocated' AND expiry > 0 AND expiry < %s"
                cursor.execute(sql, (current_time,))
                expired_nodes = cursor.fetchall()
            finally:
                cursor.close()
                conn.close()
            
            # Release ONLY the specific expired nodes (not all containers of owner)
            # This preserves other active reservations of the same user
            count = 0
            for node in expired_nodes:
                node_name = node['name']
                owner = node['owner']
                print(f"[BACKUP CLEANUP] Found orphaned expired node: {node_name} (Owner: {owner})")
                
                # Clean this specific node only
                cleanup_success = False
                try:
                    container = self.client.containers.get(node_name)
                    
                    # Force kill processes
                    result = container.exec_run(f"pkill -9 -u {owner}")
                    time.sleep(0.5)
                    
                    # Force remove user
                    result = container.exec_run(f"userdel -r -f {owner}")
                    if result.exit_code == 0 or b"does not exist" in result.output or result.exit_code == 6:
                        cleanup_success = True
                        print(f"[BACKUP CLEANUP] Cleaned user {owner} from {node_name}")
                    else:
                        print(f"[BACKUP CLEANUP] Warning cleaning {node_name}: {result.output.decode()}")
                        cleanup_success = True  # Continue anyway
                        
                except Exception as e:
                    print(f"[BACKUP CLEANUP] Error cleaning container {node_name}: {e}")
                    cleanup_success = True  # Continue anyway
                
                # Release this specific node in DB
                if cleanup_success:
                    self.pool_db.release_node(node_name)
                    print(f"[BACKUP CLEANUP] Released orphaned node: {node_name}")
                count += 1
            
            if count > 0:
                print(f"[BACKUP CLEANUP] Cleaned up {count} orphaned nodes.")
            return True
        except Exception as e:
            print(f"Error in backup cleanup: {e}")
            return False
    
    def health_check(self):
        """Run health check on pool"""
        if not self.client:
            return False
        try:
            self.client.ping()
            return True
        except Exception as e:
            print(f"Error running health check: {e}")
            return False

    def allocate_containers(self, username, vm_count, password, duration):
        """Allocate containers for a user"""
        if not self.client:
            return {'success': False, 'error': 'Docker daemon not connected'}
        allocated_nodes = []
        try:
            # 1. Find free nodes
            free_nodes = self.pool_db.find_free_nodes(int(vm_count))
            if len(free_nodes) < int(vm_count):
                return {'success': False, 'error': 'Not enough free containers available'}
            expiry_time = time.time() + (int(duration) * 60)
            # 2. Allocate and configure each node
            for node in free_nodes:
                node_name = node['name']
                # A. Update DB first to reserve
                if not self.pool_db.allocate_node(node_name, username, expiry_time):
                    # Skip if update fails (race condition)
                    continue
                # B. Configure Container (Equivalent to setup_container_user in bash)
                try:
                    container = self.client.containers.get(node_name)
                    
                    # 1. Check if user exists, create if not
                    check_result = container.exec_run(f"id -u {username}")
                    if check_result.exit_code != 0:
                        # User doesn't exist, create it
                        result = container.exec_run(f"useradd -m -s /bin/bash {username}")
                        if result.exit_code != 0:
                            raise Exception(f"Failed to create user: {result.output.decode()}")
                    else:
                        print(f"User {username} already exists in {node_name}, reusing...")
                    
                    # 2. Set/Reset password (works for both new and existing users)
                    result = container.exec_run(f"/bin/sh -c 'echo \"{username}:{password}\" | chpasswd'")
                    if result.exit_code != 0:
                        raise Exception(f"Failed to set password: {result.output.decode()}")
                    
                    # 3. Add to sudo (if needed, skip if already in group)
                    container.exec_run(f"usermod -aG sudo {username}")
                    
                    print(f"Allocated and Configured {node_name} for {username}")
                    allocated_nodes.append({
                        'name': node_name,
                        'ip': node['ip'],
                        'port': node['port']
                    })
                except Exception as e:
                    print(f"Failed to configure container {node_name}: {e}")
                    # Rollback DB if configuration fails
                    self.pool_db.release_node(node_name)
                    return {'success': False, 'error': f"Failed to configure {node_name}: {str(e)}"}
            return {
                'success': True,
                'nodes': allocated_nodes
            }
        except Exception as e:
            print(f"Allocation error: {e}")
            return {'success': False, 'error': str(e)}

    def release_containers_by_nodes(self, username, nodes):
        """Release specific containers by node list (for specific reservation)"""
        if not self.client:
            return {'success': False, 'error': 'No docker connection'}
        try:
            released_count = 0
            for node in nodes:
                node_name = node.get('name')
                if not node_name:
                    continue
                
                # A. Cleanup Container (Deep Clean)
                cleanup_success = False
                try:
                    container = self.client.containers.get(node_name)
                    
                    # 1. Kill user processes (force kill if needed)
                    result = container.exec_run(f"pkill -9 -u {username}")
                    # pkill returns 1 if no processes found, which is OK
                    if result.exit_code not in [0, 1]:
                        print(f"Warning: pkill returned {result.exit_code} for {node_name}")
                    
                    # 2. Wait a moment for processes to die
                    time.sleep(0.5)
                    
                    # 3. Remove user and home dir (force if needed)
                    result = container.exec_run(f"userdel -r -f {username}")
                    if result.exit_code == 0:
                        cleanup_success = True
                        print(f"Successfully cleaned user {username} from {node_name}")
                    else:
                        # User might not exist or already deleted
                        if b"does not exist" in result.output or result.exit_code == 6:
                            cleanup_success = True
                            print(f"User {username} already removed from {node_name}")
                        else:
                            print(f"Error removing user from {node_name}: {result.output.decode()}")
                            # Try to continue anyway
                            cleanup_success = True
                    
                except Exception as e:
                    print(f"Error cleaning container {node_name}: {e}")
                    # Continue anyway to release node in DB
                    cleanup_success = True
                
                # B. Update DB -> free (only if cleanup succeeded or user didn't exist)
                if cleanup_success:
                    self.pool_db.release_node(node_name)
                    print(f"Released {node_name} for user {username}")
                    released_count += 1
                else:
                    print(f"WARNING: Skipped releasing {node_name} due to cleanup failure")
            
            return {'success': True, 'message': f'Released {released_count} nodes'}
        except Exception as e:
            return {'success': False, 'error': str(e)}

    def release_containers(self, username):
        """Release ALL containers for a user (use release_containers_by_nodes for specific reservations)"""
        if not self.client:
            return {'success': False, 'error': 'No docker connection'}
        try:
            # 1. Get user nodes from DB
            user_nodes = self.pool_db.get_nodes_by_owner(username)
            released_count = 0
            for node in user_nodes:
                node_name = node['name']
                # A. Cleanup Container (Deep Clean)
                cleanup_success = False
                try:
                    container = self.client.containers.get(node_name)
                    
                    # Kill user processes (force)
                    result = container.exec_run(f"pkill -9 -u {username}")
                    time.sleep(0.5)
                    
                    # Remove user and home dir (force)
                    result = container.exec_run(f"userdel -r -f {username}")
                    if result.exit_code == 0 or b"does not exist" in result.output or result.exit_code == 6:
                        cleanup_success = True
                    else:
                        print(f"Warning cleaning {node_name}: {result.output.decode()}")
                        cleanup_success = True  # Continue anyway
                        
                except Exception as e:
                    print(f"Error cleaning container {node_name}: {e}")
                    cleanup_success = True  # Continue anyway
                
                # B. Update DB -> free
                if cleanup_success:
                    self.pool_db.release_node(node_name)
                    print(f"Released {node_name}")
                    released_count += 1
            
            return {'success': True, 'message': f'Released {released_count} nodes'}
        except Exception as e:
            return {'success': False, 'error': str(e)}

    def check_container_running(self, node_name):
        """Check if a container is running"""
        if not self.client:
            return False
        try:
            container = self.client.containers.get(node_name)
            return container.status == 'running'
        except docker.errors.NotFound:
            return False
        except Exception as e:
            print(f"Error checking container {node_name}: {e}")
            return False

    def recover_pool(self):
        """Recover pool (Restart stopped containers)"""
        # Restart stopped containers
        count = 0
        if not self.client:
            return {'success': False}
        try:
            # Get all pool-node-*
            containers = self.client.containers.list(all=True, filters={"name": "pool-node-"})
            for c in containers:
                if c.status != 'running':
                    c.start()
                    count += 1
            return {'success': True, 'output': f"Restarted {count} containers"}
        except Exception as e:
            return {'success': False, 'error': str(e)}

    def init_pool(self, pool_size=30):
        """
        Init Pool (Replaces pool_manager.sh init)
        1. Create Network
        2. Build Image
        3. Run Containers
        4. Sync to MySQL
        """
        if not self.client:
            return {'success': False, 'error': 'Docker daemon not connected'}
        print(f"==> Initializing pool with {pool_size} containers...")
        # 1. Create Network (172.30.0.0/24)
        pool_net_name = "pool-network"
        try:
            self.client.networks.get(pool_net_name)
        except docker.errors.NotFound:
            ipam_pool = docker.types.IPAMPool(subnet='172.30.0.0/24')
            ipam_config = docker.types.IPAMConfig(pool_configs=[ipam_pool])
            self.client.networks.create(pool_net_name, driver="bridge", ipam=ipam_config)
            print(f"Created network {pool_net_name}")
        # 2. Detect Architecture & Build Image
        arch = platform.machine()
        docker_platform = "linux/arm64" if arch in ['aarch64', 'arm64'] else "linux/amd64"
        print(f"Detected architecture: {arch} -> {docker_platform}")
        print("Building base image (pool-node:latest)... This may take a while.")
        try:
            # Note: Path must point to Dockerfile directory
            # Assuming script runs from project root
            self.client.images.build(
                path="./Docker/ssh",
                tag="pool-node:latest",
                platform=docker_platform,
                rm=True
            )
            print("Image built successfully.")
        except Exception as e:
            return {'success': False, 'error': f"Build failed: {e}"}
        # 3. Start Containers & Update MySQL
        for i in range(1, pool_size + 1):
            name = f"pool-node-{i}"
            port = 3000 + i - 1
            # Remove old container if exists
            try:
                old = self.client.containers.get(name)
                old.remove(force=True)
            except docker.errors.NotFound:
                pass
            # Run new container (let Docker auto-assign IP)
            try:
                container = self.client.containers.run(
                    "pool-node:latest",
                    name=name,
                    detach=True,
                    network=pool_net_name,
                    ports={'22/tcp': port}, # Map port 22 container -> port 3000+ host
                    restart_policy={"Name": "unless-stopped"}
                )
                # Query actual IP from Docker (after creation)
                container.reload()
                actual_ip = container.attrs['NetworkSettings']['Networks'][pool_net_name]['IPAddress']
                
                # 4. IMPORTANT: Write actual IP to MySQL
                self.pool_db.upsert_node(name, actual_ip, port, 'free')
                print(f"Started {name} at {actual_ip}:{port} -> DB Synced")
            except Exception as e:
                print(f"Failed to start {name}: {e}")
        return {'success': True, 'message': f"Initialized {pool_size} nodes"}

    def get_pool_details(self):
        """Get detailed pool information with individual container details"""
        try:
            containers = []
            free_count = 0
            allocated_count = 0
            error_count = 0
            stopped_count = 0
            current_time = time.time()
            
            # Get all nodes from MySQL database
            conn = self.pool_db._get_connection()
            cursor = conn.cursor(dictionary=True)
            try:
                cursor.execute("SELECT * FROM pool_nodes ORDER BY name")
                db_nodes = {row['name']: row for row in cursor.fetchall()}
            finally:
                cursor.close()
                conn.close()
            
            # Get docker container info to check if containers are running
            running_containers = set()
            try:
                result = subprocess.run(
                    ['docker', 'ps', '-a', '--format', '{{.Names}}'],
                    capture_output=True,
                    text=True,
                    cwd=self.project_dir,
                    timeout=10
                )
                if result.returncode == 0 and result.stdout.strip():
                    running_containers = set(result.stdout.strip().split('\n'))
            except:
                pass
            
            # Process each node
            for i in range(1, Config.POOL_SIZE + 1):
                name = f'pool-node-{i}'
                
                # Get info from database
                db_node = db_nodes.get(name, {})
                db_status = db_node.get('status', 'unknown')
                owner = db_node.get('owner', '')
                expiry = db_node.get('expiry', 0)
                db_ip = db_node.get('ip', '-')
                db_port = db_node.get('port', '-')
                
                # Check if container is actually running
                is_running = name in running_containers
                
                # Determine final status
                if not is_running:
                    status = 'stopped'
                    stopped_count += 1
                elif db_status == 'error':
                    status = 'error'
                    error_count += 1
                elif db_status == 'allocated':
                    status = 'allocated'
                    allocated_count += 1
                elif db_status == 'free':
                    status = 'free'
                    free_count += 1
                else:
                    status = db_status
                    if status == 'maintenance':
                        error_count += 1
                    else:
                        error_count += 1
                
                # Get IP and port (prefer database, fallback to docker inspect)
                ip = db_ip if db_ip != '-' else '-'
                port = str(db_port) if db_port != '-' else '-'
                
                if is_running and (ip == '-' or port == '-'):
                    try:
                        ip_result = subprocess.run(
                            ['docker', 'inspect', '--format', '{{range .NetworkSettings.Networks}}{{.IPAddress}}{{end}}', name],
                            capture_output=True,
                            text=True,
                            timeout=5
                        )
                        if ip_result.returncode == 0 and ip_result.stdout.strip():
                            ip = ip_result.stdout.strip()
                        
                        port_result = subprocess.run(
                            ['docker', 'port', name, '22'],
                            capture_output=True,
                            text=True,
                            timeout=5
                        )
                        if port_result.returncode == 0 and port_result.stdout.strip():
                            port = port_result.stdout.strip().split(':')[-1]
                    except:
                        pass
                
                # Format expiry time
                expires_str = None
                if status == 'allocated' and expiry > 0:
                    remaining = expiry - current_time
                    if remaining > 0:
                        minutes = int(remaining / 60)
                        expires_str = f'in {minutes} min'
                    else:
                        expires_str = 'EXPIRED'
                
                containers.append({
                    'name': name,
                    'ip': ip,
                    'port': port,
                    'status': status,
                    'client': owner if owner else '',
                    'expires': expires_str
                })
            
            return {
                'containers': containers,
                'free_count': free_count,
                'allocated_count': allocated_count,
                'error_count': error_count,
                'stopped_count': stopped_count,
                'total': Config.POOL_SIZE
            }
            
        except Exception as e:
            print(f"Error getting pool details: {e}")
            import traceback
            traceback.print_exc()
            return {
                'containers': [],
                'free_count': 0,
                'allocated_count': 0,
                'error_count': 0,
                'stopped_count': 0,
                'total': Config.POOL_SIZE,
                'error': str(e)
            }