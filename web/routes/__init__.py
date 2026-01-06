# Routes package
from .auth_routes import auth_bp
from .main_routes import main_bp
from .provision_routes import provision_bp
from .terminal_routes import terminal_bp

__all__ = ['auth_bp', 'main_bp', 'provision_bp', 'terminal_bp']
