from flask import Blueprint, render_template, request, jsonify, redirect, url_for
from middlewares.auth import login_required
from controller.dashboard_controller import DashboardController

main_bp = Blueprint('main', __name__)

vms = [
    {"id": 1, "name": "VM Ubuntu", "status": "running"},
    {"id": 2, "name": "VM CentOS", "status": "stopped"},
    {"id": 3, "name": "VM Debian", "status": "running"},
    {"id": 4, "name": "VM Fedora", "status": "stopped"},
    {"id": 5, "name": "VM Arch Linux", "status": "stopped"},
    {"id": 6, "name": "VM Kali Linux", "status": "stopped"},
]


@main_bp.route('/aboutus')
def aboutus():
    return render_template('aboutus.html')

@main_bp.route('/')
@login_required
def dashboard():
    return render_template('dashboard.html', user_is_logged_in=True, vms=vms)

@main_bp.route('/acceuil')
def accueil():
    return render_template('accueil.html')

@main_bp.route('/user-dashboard')
@login_required
def user_dashboard():
    """Dashboard utilisateur - délègue au contrôleur"""
    return render_template('user-dashboard.html', user_is_logged_in=True, vms=vms)
@main_bp.route('/vm/<vm_id>', methods=['POST'])
@login_required
def get_vm(vm_id):
    vm_id = request.view_args['vm_id']
    vm = next((vm for vm in vms if str(vm['id']) == str(vm_id)), None)
    if vm:
        vm['status'] = 'running'
        return jsonify({"message": f"VM {vm['name']} is now running."}), 200
    else:
        return jsonify({"message": "VM not found."}), 404

@main_bp.route('/admin-dashboard')
@login_required
def admin_dashboard():
    """Dashboard administrateur - délègue au contrôleur"""
    return DashboardController.get_admin_dashboard()
    

