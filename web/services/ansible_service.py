"""
Service pour gérer Ansible
"""
import subprocess
import os
from models.vm import VM

class AnsibleService:
    """Service pour les opérations Ansible"""
    
    @staticmethod
    def create_inventory_file(config: VM, project_dir: str) -> str:
        """
        Crée le fichier d'inventaire Ansible
        
        Returns:
            str: Chemin vers le fichier d'inventaire créé
        """
        inventory_file = os.path.join(project_dir, 'Ansible', f'inventory_{config.username}.ini')
        
        with open(inventory_file, 'w') as f:
            f.write(f"[{config.username}]\n")
            
            for i in range(config.count):
                port = config.get_port_for_node(i)
                private_key = os.path.expanduser('~/.vagrant.d/insecure_private_key')
                f.write(
                    f"{config.username}-node{i+1} "
                    f"ansible_host=127.0.0.1 "
                    f"ansible_port={port} "
                    f"ansible_user=vagrant "
                    f"ansible_ssh_private_key_file={private_key}\n"
                )
            
            f.write(f"\n[{config.username}:vars]\n")
            f.write(f"packages={','.join(config.packages)}\n")
        
        return inventory_file
    
    @staticmethod
    def run_playbook(inventory_file: str, config: VM, project_dir: str) -> tuple[bool, str, str]:
        """
        Exécute le playbook Ansible
        
        Returns:
            tuple: (success: bool, stdout: str, stderr: str)
        """
        ansible_cmd = [
            'ansible-playbook',
            '-i', inventory_file,
            os.path.join(project_dir, 'Ansible', 'playbook.yml'),
            '-e', f'username={config.username}',
            '-e', f'password={config.password}',
            '-e', f'packages={",".join(config.packages)}',
            '-vv'
        ]
        
        env = os.environ.copy()
        env["ANSIBLE_HOST_KEY_CHECKING"] = "False"
        
        print(f"Running Ansible with command: {' '.join(ansible_cmd)}")
        
        try:
            result = subprocess.run(
                ansible_cmd,
                capture_output=True,
                text=True,
                cwd=project_dir,
                env=env,
                timeout=300  # Timeout de 5 minutes
            )
            
            if result.returncode != 0:
                print(f"Ansible Error: {result.stderr}")
                print(f"Ansible STDOUT: {result.stdout}")
                return False, result.stdout, result.stderr
            
            return True, result.stdout, result.stderr
            
        except subprocess.TimeoutExpired:
            return False, "", "Ansible playbook timed out"
        except Exception as e:
            return False, "", str(e)
