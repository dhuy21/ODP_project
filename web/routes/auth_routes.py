from flask import Blueprint, render_template, request
from controller.auth_controller import AuthController
from middlewares.auth import login_required

auth_bp = Blueprint('auth', __name__)

@auth_bp.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        return AuthController.login_user(username, password)
    return render_template('login.html')

@auth_bp.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        role = request.form['role']
        return AuthController.register_user(username, password, role)
    return render_template('register.html')

@auth_bp.route('/logout')
@login_required
def logout():
    return AuthController.logout_user()

