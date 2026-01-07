from flask import Flask
from flask_socketio import SocketIO
import threading
import time

# Import configuration
from config.config import Config

# Import models
from models.user import UserDatabase

# Import controllers
from controller.ssh_controller import SSHController
from controller.vm_controller import VMController

# Import routes
from routes.auth_routes import auth_bp
from routes.main_routes import main_bp
from routes.provision_routes import provision_bp
from routes.terminal_routes import terminal_bp
from routes.socketio_handlers import register_socketio_handlers

# Import services
from services.docker_service import DockerService

def create_app(config_class=Config):
    """Application factory"""
    app = Flask(__name__)
    app.config.from_object(config_class)
    app.secret_key = config_class.SECRET_KEY
    
    # Initialize SocketIO
    socketio = SocketIO(
        app,
        async_mode=config_class.SOCKETIO_ASYNC_MODE,
        cors_allowed_origins=config_class.SOCKETIO_CORS_ALLOWED_ORIGINS
    )
    
    # Initialize controllers
    ssh_controller = SSHController(socketio)
    vm_controller = VMController()
    
    # Store SSH controller in app config for terminal routes
    app.config['SSH_CONTROLLER'] = ssh_controller
    
    # Register blueprints
    app.register_blueprint(auth_bp)
    app.register_blueprint(main_bp)
    app.register_blueprint(provision_bp)
    app.register_blueprint(terminal_bp)
    
    # Register SocketIO handlers
    register_socketio_handlers(socketio, ssh_controller, vm_controller)
    
    # Register template filters
    register_template_filters(app)
    
    # Start background tasks
    start_background_tasks(ssh_controller)
    
    return app, socketio

def register_template_filters(app):
    """Register custom template filters"""
    @app.template_filter('timestamp_to_date')
    def timestamp_to_date(timestamp):
        from datetime import datetime
        return datetime.fromtimestamp(timestamp).strftime('%Y-%m-%d %H:%M:%S')

def start_background_tasks(ssh_controller):
    """Start background tasks"""
    
    def check_expired_reservations_loop():
        """Background thread that checks for expired reservations every 30 seconds"""
        user_db = UserDatabase()
        docker_service = DockerService()
        
        while True:
            try:
                # Run check-expired command
                docker_service.check_expired_containers()
                
                # Update database for all expired reservations
                all_users = user_db.load_users()
                current_time = time.time()
                
                for username, user_data in all_users.items():
                    reservations = user_data.get('reservations', [])
                    for reservation in reservations:
                        if reservation.get('status') == 'active':
                            expires_at = reservation.get('expires_at', 0)
                            if current_time > expires_at:
                                print(f"[EXPIRY] Marking reservation {reservation['id'][:8]} as expired for {username}")
                                
                                # Save final stats before marking as expired
                                from services.stats_service import StatsService
                                stats_service = StatsService()
                                final_stats = stats_service.get_reservation_stats(reservation.get('nodes', []))
                                if final_stats:
                                    user_db.save_reservation_final_stats(username, reservation['id'], final_stats)
                                    print(f"[STATS] Saved final stats for expired reservation {reservation['id'][:8]}...")
                                
                                user_db.update_reservation_status(username, reservation['id'], 'expired')
                                
                                # Disconnect any active SSH sessions for this user
                                ssh_controller.disconnect_user_sessions(username)
                
                print(f"[EXPIRY CHECK] Completed at {time.strftime('%Y-%m-%d %H:%M:%S')}")
                
            except Exception as e:
                print(f"[EXPIRY CHECK ERROR] {e}")
            
            time.sleep(30)  # Check every 30 seconds
    
    # Start background thread
    expiry_checker_thread = threading.Thread(target=check_expired_reservations_loop, daemon=True)
    expiry_checker_thread.start()

# Create app instance
app, socketio = create_app()

if __name__ == '__main__':
    print("="*60)
    print("🚀 Starting ODP Platform (MVC Architecture)")
    print("="*60)
    print("📋 Architecture:")
    print("   - Models: User, VM, Reservation, SSH Session")
    print("   - Views: Templates in templates/")
    print("   - Controllers: Auth, Dashboard, VM, SSH")
    print("   - Services: Docker, SSH, Ansible")
    print("="*60)
    print("🌐 Server starting on http://0.0.0.0:5001")
    print("="*60)
    
    socketio.run(app, debug=Config.DEBUG, host='0.0.0.0', port=5001)
