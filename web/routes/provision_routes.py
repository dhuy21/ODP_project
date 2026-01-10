from flask import Blueprint
from controller.vm_controller import VMController
from middlewares.auth import login_required, user_only

# Create blueprint
provision_bp = Blueprint('provision', __name__)

# Initialize controller
vm_controller = VMController()

# Routes
@provision_bp.route('/pool/status', methods=['GET'])
@login_required
def pool_status():
    return vm_controller.get_pool_status()

@provision_bp.route('/provision', methods=['POST'])
@login_required
@user_only
def provision():
    return vm_controller.provision()

@provision_bp.route('/reservation/<reservation_id>')
@login_required
def view_reservation(reservation_id):
    return vm_controller.view_reservation(reservation_id)

@provision_bp.route('/release/<username>', methods=['POST'])
@login_required
def release_resources(username):
    return vm_controller.release_resources(username)

@provision_bp.route('/stats/<reservation_id>', methods=['GET'])
@login_required
def get_container_stats(reservation_id):
    """Get container statistics for a reservation"""
    return vm_controller.get_container_stats(reservation_id)
