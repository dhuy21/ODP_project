"""
Service pour gérer les conteneurs Docker
"""
import subprocess
import os

class DockerService:
    """Service pour les opérations Docker"""
    
    @staticmethod
    def cleanup_resources(client_id: str, project_dir: str):
        """Nettoie les ressources Docker existantes pour un client"""
        cleanup_cmds = [
            f"docker network rm internet-{client_id} 2>/dev/null || true",
            f"docker rm -f $(docker ps -a -q --filter 'label=client={client_id}') 2>/dev/null || true"
        ]
        
        for cmd in cleanup_cmds:
            try:
                subprocess.run(cmd, shell=True, cwd=project_dir, check=False)
            except Exception as e:
                print(f"Warning during cleanup: {e}")
    
    @staticmethod
    def create_containers(script_path: str, config_file: str, project_dir: str) -> tuple[bool, str]:
        """
        Crée les conteneurs Docker via le script allocates.sh
        
        Returns:
            tuple: (success: bool, error_message: str)
        """
        print(f"Creating VMs with {script_path}")
        
        try:
            result = subprocess.run(
                [script_path, config_file],
                capture_output=True,
                text=True,
                cwd=project_dir,
                timeout=60  # Timeout de 60 secondes
            )
            
            if result.returncode != 0:
                error_msg = f"Failed to create VMs: {result.stderr}"
                print(f"Error creating VMs: {result.stderr}")
                return False, error_msg
            
            return True, ""
            
        except subprocess.TimeoutExpired:
            return False, "Container creation timed out"
        except Exception as e:
            return False, str(e)
