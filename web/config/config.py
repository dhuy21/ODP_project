import os
import secrets
from pathlib import Path
from dotenv import load_dotenv

# Load environment variables from .env file
# Look for .env in the web directory (parent of config)
env_path = Path(__file__).parent.parent / '.env'
if env_path.exists():
    load_dotenv(env_path)
    print(f"[CONFIG] Loaded environment variables from {env_path}")
else:
    # Also try in project root
    root_env_path = Path(__file__).parent.parent.parent / '.env'
    if root_env_path.exists():
        load_dotenv(root_env_path)
        print(f"[CONFIG] Loaded environment variables from {root_env_path}")
    else:
        print("[CONFIG] No .env file found, using environment variables or defaults")

class Config:
    """Application configuration"""
    
    # Flask Config
    SECRET_KEY = os.environ.get('SECRET_KEY') or secrets.token_hex(32)
    
    # Project paths
    BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    PROJECT_DIR = os.path.dirname(BASE_DIR)
    
    # Pool Configuration
    POOL_SIZE = 30
    POOL_NETWORK = "pool-network"
    POOL_SUBNET = "172.30.0.0/24"
    POOL_BASE_PORT = 3000
    
    # SSH Configuration
    SSH_TIMEOUT = 10
    SSH_DEFAULT_USER = 'vagrant'
    SSH_DEFAULT_PASSWORD = 'vagrant'
    
    # Session Configuration
    SESSION_TYPE = 'filesystem'
    PERMANENT_SESSION_LIFETIME = 3600  # 1 hour
    
    # SocketIO Configuration
    SOCKETIO_ASYNC_MODE = 'threading'
    SOCKETIO_CORS_ALLOWED_ORIGINS = "*"
    
    # Ansible Configuration
    ANSIBLE_DIR = os.path.join(PROJECT_DIR, 'Ansible')
    ANSIBLE_PLAYBOOK = os.path.join(ANSIBLE_DIR, 'playbook.yml')
    
    # Debug
    DEBUG = os.environ.get('FLASK_DEBUG', 'True').lower() == 'true'
    
    @staticmethod
    def init_app(app):
        """Initialize application with config"""
        pass
