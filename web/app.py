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
    start_background_tasks(ssh_controller, socketio)
    
    return app, socketio

def register_template_filters(app):
    """Register custom template filters"""
    @app.template_filter('timestamp_to_date')
    def timestamp_to_date(timestamp):
        from datetime import datetime
        return datetime.fromtimestamp(timestamp).strftime('%Y-%m-%d %H:%M:%S')

def start_background_tasks(ssh_controller, socketio):
    """Start background tasks"""
    
    def check_expired_reservations_loop():
        """Background thread with smart scheduling - checks when needed"""
        user_db = UserDatabase()
        docker_service = DockerService()
        
        while True:
            try:
                # Run check-expired command
                docker_service.check_expired_containers()
                
                # Get only active reservations (optimized)
                active_reservations = user_db.get_active_reservations()
                current_time = time.time()
                
                expired_batch = []
                
                # Collect expired reservations
                
                for reservation in active_reservations:
                    expires_at = reservation.get('expires_at', 0)
                    if current_time > expires_at:
                        username = reservation.get('owner')
                        reservation_id = reservation.get('id')
                        nodes = reservation.get('nodes', [])
                        
                        # Save final stats before marking as expired
                        from services.stats_service import StatsService
                        stats_service = StatsService()
                        final_stats = stats_service.get_reservation_stats(nodes)
                        if final_stats:
                            reservation['final_stats'] = final_stats
                            print(f"[STATS] Saved final stats for expired reservation {reservation_id[:8]}...")
                        
                        expired_batch.append(reservation)
                        
                        # Disconnect SSH sessions ONLY for nodes of this expired reservation
                        # This preserves SSH sessions for other active reservations of the same user
                        if nodes:
                            disconnected = ssh_controller.disconnect_sessions_by_nodes(username, nodes)
                            if disconnected > 0:
                                print(f"[SSH] Disconnected {disconnected} SSH sessions for expired reservation {reservation_id[:8]}")
                
                # Batch update all expired reservations (single write)
                if expired_batch:
                    user_db.batch_update_expired(expired_batch)
                    
                    # Release containers for EACH expired reservation (not all user containers)
                    # This ensures only nodes of expired reservations are released
                    for reservation in expired_batch:
                        username = reservation.get('owner')
                        reservation_id = reservation.get('id')
                        nodes = reservation.get('nodes', [])
                        
                        if nodes:
                            result = docker_service.release_containers_by_nodes(username, nodes)
                            if result.get('success'):
                                print(f"[RELEASE] Released {len(nodes)} containers for expired reservation {reservation_id[:8]}")
                            else:
                                print(f"[RELEASE ERROR] Failed to release containers for reservation {reservation_id[:8]}: {result.get('error', 'Unknown error')}")
                        else:
                            print(f"[RELEASE WARNING] No nodes found for reservation {reservation_id[:8]}")
                    
                    # Emit WebSocket events for each expired reservation
                    for reservation in expired_batch:
                        username = reservation.get('owner')
                        reservation_id = reservation.get('id')
                        print(f"[EXPIRY] Marking reservation {reservation_id[:8]} as expired for {username}")
                        
                        socketio.emit('reservation_expired', {
                            'reservation_id': reservation_id,
                            'expired_count': len(expired_batch)
                        }, room=username)
                
                print(f"[EXPIRY CHECK] Completed at {time.strftime('%Y-%m-%d %H:%M:%S')}")
                
            except Exception as e:
                print(f"[EXPIRY CHECK ERROR] {e}")
            
            # Smart scheduling: sleep until next expiry or max 30 seconds
            next_expiry = user_db.get_next_expiry_time()
            if next_expiry:
                current_time = time.time()
                sleep_time = next_expiry - current_time
                # Sleep between 1 and 30 seconds
                sleep_time = max(1, min(30, sleep_time))
            else:
                sleep_time = 30  # No active reservations, check again in 30s
            
            time.sleep(sleep_time)
    
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
    
    socketio.run(app, debug=Config.DEBUG, host='0.0.0.0', port=5001, allow_unsafe_werkzeug=True)
