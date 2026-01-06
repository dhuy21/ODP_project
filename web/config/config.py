import os
import secrets

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
