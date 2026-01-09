import subprocess
import os
import threading
from config.config import Config

class AnsibleService:
    """Service for Ansible automation"""
    
    def __init__(self):
        self.project_dir = Config.PROJECT_DIR
        self.ansible_dir = Config.ANSIBLE_DIR
        self.playbook = Config.ANSIBLE_PLAYBOOK
    
    def create_inventory(self, username, nodes, password, packages):
        """Create Ansible inventory file for user"""
        inventory_file = os.path.join(self.ansible_dir, f'inventory_{username}.ini')
        
        try:
            with open(inventory_file, 'w') as f:
                f.write(f"[{username}]\n")
                for node in nodes:
                    f.write(f"{node['name']} ansible_host=127.0.0.1 ansible_port={node['port']} ")
                    f.write(f"ansible_user={username} ansible_ssh_pass={password} ")
                    f.write(f"ansible_become_pass={password}\n")
                
                f.write(f"\n[{username}:vars]\n")
                f.write(f"ansible_ssh_common_args='-o StrictHostKeyChecking=no'\n")
                
                if packages:
                    package_str = ','.join(packages) if isinstance(packages, list) else packages
                    f.write(f"packages={package_str}\n")
            
            return {
                'success': True,
                'inventory_file': inventory_file
            }
        except Exception as e:
            return {
                'success': False,
                'error': str(e)
            }
    
    def run_playbook(self, inventory_file, callback=None):
        """Run Ansible playbook"""
        try:
            result = subprocess.run(
                ['ansible-playbook', '-i', inventory_file, self.playbook],
                capture_output=True,
                text=True,
                cwd=self.project_dir,
                timeout=300  # 5 minutes max
            )
            
            success = result.returncode == 0
            
            if callback:
                callback(success, result.stdout, result.stderr)
            
            return {
                'success': success,
                'stdout': result.stdout,
                'stderr': result.stderr
            }
        except subprocess.TimeoutExpired:
            return {
                'success': False,
                'error': 'Ansible playbook timeout'
            }
        except Exception as e:
            return {
                'success': False,
                'error': str(e)
            }
    
    def install_packages_async(self, username, nodes, password, packages):
        """Install packages asynchronously"""
        if not packages:
            return {'success': True, 'message': 'No packages to install'}
        
        # Create package list
        package_list = [p.strip() for p in packages.split(',') if p.strip()] if isinstance(packages, str) else packages
        
        if not package_list:
            return {'success': True, 'message': 'No packages to install'}
        
        # Create inventory
        inventory_result = self.create_inventory(username, nodes, password, package_list)
        if not inventory_result['success']:
            return inventory_result
        
        # Run Ansible in background thread
        def run_ansible_background():
            try:
                print(f"[ANSIBLE] Starting package installation for {username}")
                result = self.run_playbook(inventory_result['inventory_file'])
                
                if result['success']:
                    print(f"[ANSIBLE] Successfully installed packages for {username}")
                else:
                    print(f"[ANSIBLE] Failed to install packages: {result.get('stderr', 'Unknown error')}")
            except Exception as e:
                print(f"[ANSIBLE] Error: {e}")
        
        thread = threading.Thread(target=run_ansible_background, daemon=True)
        thread.start()
        
        return {
            'success': True,
            'message': 'Package installation started in background'
        }
