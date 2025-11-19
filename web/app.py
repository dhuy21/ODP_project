"""
Application Flask avec architecture MVC/OOP
Version refactorisée de app.py
"""
from flask import Flask
from flask_socketio import SocketIO

# Import de la base de données et configuration
from models import db
from config.config import Config

# Import des modèles pour créer les tables
from models.user import User
from models.vm import VM

# Import des blueprints
from routes.main_routes import main_bp
from routes.auth_routes import auth_bp
from routes.provision_routes import provision_bp
from routes.terminal_routes import terminal_bp
from routes.socketio_handlers import register_socketio_handlers

# Configuration de l'application
app = Flask(__name__)
app.config.from_object(Config)

# Initialisation de la base de données
db.init_app(app)

# Création des tables si elles n'existent pas
with app.app_context():
    db.create_all()

# Configuration SocketIO
socketio = SocketIO(app, async_mode='threading', cors_allowed_origins="*")

# Enregistrement des blueprints
app.register_blueprint(main_bp)
app.register_blueprint(auth_bp)
app.register_blueprint(provision_bp)
app.register_blueprint(terminal_bp)

# Enregistrement des gestionnaires SocketIO
register_socketio_handlers(socketio)

# Filtre de template pour le hash
@app.template_filter('hash')
def hash_filter(s):
    """Filtre Jinja2 pour calculer le hash d'une chaîne"""
    return abs(hash(s)) % 250

# Point d'entrée
if __name__ == '__main__':
    socketio.run(app, debug=True, host='0.0.0.0', port=5001)

