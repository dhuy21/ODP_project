import subprocess
import os
from config.config import Config

class DockerService:
    """Service for Docker container management"""
    
    def __init__(self):
        self.project_dir = Config.PROJECT_DIR
    
    def get_pool_status(self):
        """Get current pool status"""
        try:
            result = subprocess.run(
                ['./pool_manager.sh', 'status'],
                capture_output=True,
                text=True,
                cwd=self.project_dir,
                timeout=10
            )
            
            free_count = 0
            allocated_count = 0
            
            for line in result.stdout.split('\n'):
                if 'pool-node-' in line:
                    if 'free' in line and 'allocated' not in line and 'error' not in line:
                        free_count += 1
                    elif 'allocated' in line:
                        allocated_count += 1
            
            return {
                'success': True,
                'total': Config.POOL_SIZE,
                'free': free_count,
                'allocated': allocated_count
            }
        except Exception as e:
            print(f"Error getting pool status: {e}")
            return {
                'success': False,
                'total': Config.POOL_SIZE,
                'free': 0,
                'allocated': 0,
                'error': str(e)
            }
    
    def check_expired_containers(self):
        """Check and cleanup expired containers"""
        try:
            result = subprocess.run(
                ['./pool_manager.sh', 'check-expired'],
                capture_output=True,
                text=True,
                cwd=self.project_dir,
                timeout=10
            )
            return result.returncode == 0
        except Exception as e:
            print(f"Error checking expired containers: {e}")
            return False
    
    def health_check(self):
        """Run health check on pool"""
        try:
            result = subprocess.run(
                ['./pool_manager.sh', 'health-check'],
                capture_output=True,
                text=True,
                cwd=self.project_dir,
                timeout=10
            )
            return result.returncode == 0
        except Exception as e:
            print(f"Error running health check: {e}")
            return False
    
    def allocate_containers(self, username, vm_count, password, duration):
        """Allocate containers for a user"""
        try:
            result = subprocess.run(
                ['./pool_manager.sh', 'allocate', username, str(vm_count), username, password, str(duration)],
                capture_output=True,
                text=True,
                cwd=self.project_dir,
                timeout=30
            )
            
            if result.returncode != 0:
                return {
                    'success': False,
                    'error': result.stderr or 'Failed to allocate containers'
                }
            
            # Parse allocated nodes
            allocated_nodes = []
            for line in result.stdout.split('\n'):
                if 'Allocated' in line and '(' in line:
                    try:
                        parts = line.strip().split()
                        node_name = parts[2]
                        ip_port = parts[3].strip('()')
                        
                        if ':' in ip_port:
                            ip, port = ip_port.split(':')
                            allocated_nodes.append({
                                'name': node_name,
                                'ip': ip,
                                'port': port
                            })
                    except Exception as e:
                        print(f"Failed to parse line: {line} - {e}")
                        continue
            
            if not allocated_nodes:
                return {
                    'success': False,
                    'error': 'Failed to parse allocated containers'
                }
            
            return {
                'success': True,
                'nodes': allocated_nodes
            }
            
        except subprocess.TimeoutExpired:
            return {
                'success': False,
                'error': 'Allocation timeout - system is busy'
            }
        except Exception as e:
            return {
                'success': False,
                'error': str(e)
            }
    
    def release_containers(self, username):
        """Release containers for a user"""
        try:
            result = subprocess.run(
                ['./pool_manager.sh', 'release', username],
                capture_output=True,
                text=True,
                cwd=self.project_dir,
                timeout=10
            )
            
            return {
                'success': result.returncode == 0,
                'output': result.stdout
            }
        except Exception as e:
            return {
                'success': False,
                'error': str(e)
            }
    
    def check_container_running(self, node_name):
        """Check if a container is running"""
        try:
            result = subprocess.run(
                ['docker', 'ps', '-q', '-f', f'name=^{node_name}$'],
                capture_output=True,
                text=True,
                cwd=self.project_dir
            )
            return bool(result.stdout.strip())
        except:
            return False
    
    def recover_pool(self):
        """Recover pool by restarting failed containers"""
        try:
            result = subprocess.run(
                ['./pool_manager.sh', 'recover'],
                capture_output=True,
                text=True,
                cwd=self.project_dir,
                timeout=30
            )
            
            return {
                'success': result.returncode == 0,
                'output': result.stdout
            }
        except Exception as e:
            return {
                'success': False,
                'error': str(e)
            }

    def get_pool_details(self):
        """Get detailed pool information with individual container details"""
        import json
        import time
        from datetime import datetime
        
        try:
            # Read state file directly
            state_file = '/tmp/pool_state.json'
            
            # Try to read state file
            state = {}
            try:
                with open(state_file, 'r') as f:
                    state = json.load(f)
            except:
                pass
            
            containers = []
            free_count = 0
            allocated_count = 0
            error_count = 0
            stopped_count = 0
            current_time = time.time()
            
            # Get docker container info
            result = subprocess.run(
                ['docker', 'ps', '-a', '--format', '{{.Names}}'],
                capture_output=True,
                text=True,
                cwd=self.project_dir,
                timeout=10
            )
            
            running_containers = set(result.stdout.strip().split('\n')) if result.stdout.strip() else set()
            
            for i in range(1, Config.POOL_SIZE + 1):
                name = f'pool-node-{i}'
                container_info = state.get(name, {})
                status = container_info.get('status', 'unknown')
                client = container_info.get('client', '')
                expiry = container_info.get('expiry', 0)
                
                # Get IP and port from docker
                ip = '-'
                port = '-'
                is_running = name in running_containers
                
                if is_running:
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
                else:
                    status = 'stopped'
                    stopped_count += 1
                
                # Format expiry time
                expires_str = None
                if status == 'allocated' and expiry > 0:
                    remaining = expiry - current_time
                    if remaining > 0:
                        minutes = int(remaining / 60)
                        expires_str = f'in {minutes} min'
                    else:
                        expires_str = 'EXPIRED'
                
                # Count by status
                if status == 'free':
                    free_count += 1
                elif status == 'allocated':
                    allocated_count += 1
                elif status == 'stopped':
                    stopped_count += 1
                elif status == 'error' or status == 'unknown':
                    error_count += 1
                
                containers.append({
                    'name': name,
                    'ip': ip,
                    'port': port,
                    'status': status,
                    'client': client,
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