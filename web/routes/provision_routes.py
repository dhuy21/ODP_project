"""
Routes pour le provisioning des VMs
"""
from flask import Blueprint, render_template, request
from controller.vm_controller import VMController

provision_bp = Blueprint('provision', __name__)


@provision_bp.route('/provision', methods=['POST'])
def provision():
    """Route pour provisionner des VMs"""
    return VMController.provision()

@provision_bp.route('/request-vm', methods=['GET'])
def request_vm():
    return render_template('requestVM.html')

