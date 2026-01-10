from flask import Blueprint
from controller.auth_controller import AuthController

# Create blueprint
auth_bp = Blueprint('auth', __name__)

# Initialize controller
auth_controller = AuthController()

# Routes
@auth_bp.route('/login', methods=['GET'])
def show_login():
    return auth_controller.show_login()

@auth_bp.route('/login', methods=['POST'])
def login():
    return auth_controller.login()

@auth_bp.route('/register', methods=['GET'])
def show_register():
    return auth_controller.show_register()

@auth_bp.route('/register', methods=['POST'])
def register():
    return auth_controller.register()

@auth_bp.route('/logout')
def logout():
    return auth_controller.logout()
