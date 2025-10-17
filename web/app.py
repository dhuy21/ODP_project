from flask import Flask
from config import Config
from models import db
from routes.auth_routes import auth_bp
from routes.main_routes import main_bp

app = Flask(__name__)
app.config.from_object(Config)

# Initialiser la base de données
db.init_app(app)

# Enregistrer les blueprints
app.register_blueprint(auth_bp)
app.register_blueprint(main_bp)

# Créer les tables
with app.app_context():
    db.create_all()

if __name__ == '__main__':
    app.run(debug=True)