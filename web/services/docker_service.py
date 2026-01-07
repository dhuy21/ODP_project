import docker
import time
import platform
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
        """Check and cleanup expired containers"""
        if not self.client:
            return False
        try:
            # Find expired nodes
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
            count = 0
            for node in expired_nodes:
                print(f"Found expired node: {node['name']} (Owner: {node['owner']})")
                # Call release to clean container and update DB
                self.release_containers(node['owner'])
                count += 1
            if count > 0:
                print(f"Cleaned up {count} expired users.")
            return True
        except Exception as e:
            print(f"Error checking expired containers: {e}")
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
                    # 1. Create user if not exists
                    container.exec_run(f"useradd -m -s /bin/bash {username}")
                    # 2. Set password (chpasswd takes input from stdin)
                    container.exec_run(f"/bin/sh -c 'echo \"{username}:{password}\" | chpasswd'")
                    # 3. Add to sudo (if needed)
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
                    return {'success': False, 'error': f"Failed to configure {node_name}"}
            return {
                'success': True,
                'nodes': allocated_nodes
            }
        except Exception as e:
            print(f"Allocation error: {e}")
            return {'success': False, 'error': str(e)}

    def release_containers(self, username):
        """Release containers for a user"""
        if not self.client:
            return {'success': False, 'error': 'No docker connection'}
        try:
            # 1. Get user nodes from DB
            user_nodes = self.pool_db.get_nodes_by_owner(username)
            for node in user_nodes:
                node_name = node['name']
                # A. Cleanup Container (Deep Clean)
                try:
                    container = self.client.containers.get(node_name)
                    # Kill user processes
                    container.exec_run(f"pkill -u {username}")
                    # Remove user and home dir
                    container.exec_run(f"userdel -r {username}")
                    # (Optional) Restart container for full clean
                    # container.restart()
                except Exception as e:
                    print(f"Error cleaning container {node_name}: {e}")
                # B. Update DB -> free
                self.pool_db.release_node(node_name)
                print(f"Released {node_name}")
            return {'success': True, 'message': f'Released {len(user_nodes)} nodes'}
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
            ip = f"172.30.0.{10 + i}"
            port = 3000 + i - 1
            # Remove old container if exists
            try:
                old = self.client.containers.get(name)
                old.remove(force=True)
            except docker.errors.NotFound:
                pass
            # Run new container
            try:
                self.client.containers.run(
                    "pool-node:latest",
                    name=name,
                    detach=True,
                    network=pool_net_name,
                    ports={'22/tcp': port}, # Map port 22 container -> port 3000+ host
                    restart_policy={"Name": "unless-stopped"},
                    # Manually assign static IP
                    networking_config=self.client.api.create_networking_config({
                        pool_net_name: self.client.api.create_endpoint_config(ipv4_address=ip)
                    })
                )
                # 4. IMPORTANT: Write to MySQL
                self.pool_db.upsert_node(name, ip, port, 'free')
                print(f"Started {name} at {ip}:{port} -> DB Synced")
            except Exception as e:
                print(f"Failed to start {name}: {e}")
        return {'success': True, 'message': f"Initialized {pool_size} nodes"}
