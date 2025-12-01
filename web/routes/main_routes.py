from flask import Blueprint, render_template
from middlewares.auth import login_required
from controller.dashboard_controller import DashboardController

main_bp = Blueprint('main', __name__)


@main_bp.route('/aboutus')
def aboutus():
    return render_template('aboutus.html')

@main_bp.route('/')
def accueil():
    return render_template('accueil.html')

@main_bp.route('/user-dashboard')
@login_required
def user_dashboard():
    """Dashboard utilisateur - délègue au contrôleur"""
    return DashboardController.get_user_dashboard()

@main_bp.route('/admin-dashboard')
@login_required
def admin_dashboard():
    """Dashboard administrateur - délègue au contrôleur"""
    return DashboardController.get_admin_dashboard()
    

