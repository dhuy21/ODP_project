from flask import Blueprint, render_template, session, redirect, url_for
from controller.dashboard_controller import DashboardController
from controller.vm_controller import VMController
from middlewares.auth import login_required, admin_required

# Create blueprint
main_bp = Blueprint('main', __name__)

# Initialize controllers
dashboard_controller = DashboardController()
vm_controller = VMController()

# ============ Public Routes ============

@main_bp.route('/')
def index():
    """Root route - show landing page (accueil)"""
    return render_template('accueil.html')



# ============ User Routes ============

@main_bp.route('/home')
@login_required
def home():
    return dashboard_controller.home()

@main_bp.route('/dashboard')
@login_required
def dashboard_home():
    return dashboard_controller.dashboard_home()

@main_bp.route('/my-reservations')
@login_required
def my_reservations():
    """Page showing all user reservations - redirect to reservation history"""
    return redirect(url_for('main.reservation_history'))

@main_bp.route('/reservation-history')
@login_required
def reservation_history():
    """Reservation history page"""
    return dashboard_controller.reservation_history()



# ============ Admin Routes ============

@main_bp.route('/admin')
@login_required
@admin_required
def admin_panel():
    return dashboard_controller.admin_panel()

@main_bp.route('/admin/users', methods=['GET'])
@login_required
@admin_required
def admin_get_users():
    return dashboard_controller.admin_get_users()

@main_bp.route('/admin/user/create', methods=['POST'])
@login_required
@admin_required
def admin_create_user():
    return dashboard_controller.admin_create_user()

@main_bp.route('/admin/user/<username>/delete', methods=['DELETE'])
@login_required
@admin_required
def admin_delete_user(username):
    return dashboard_controller.admin_delete_user(username)

@main_bp.route('/admin/user/<username>/role', methods=['PUT'])
@login_required
@admin_required
def admin_update_role(username):
    return dashboard_controller.admin_update_role(username)

@main_bp.route('/admin/reservation/<reservation_id>/delete', methods=['DELETE'])
@login_required
@admin_required
def admin_delete_reservation(reservation_id):
    return dashboard_controller.admin_delete_reservation(reservation_id)

@main_bp.route('/admin/pool/recover', methods=['POST'])
@login_required
@admin_required
def admin_recover_pool():
    return dashboard_controller.admin_recover_pool()
