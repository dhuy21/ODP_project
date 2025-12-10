"""
Routes pour le provisionnement des VMs
"""

from flask import Blueprint, request
from controller.vm_controller import VMController

provision_bp = Blueprint('provision', __name__)


@provision_bp.route('/provision', methods=['POST'])
def provision():
    return VMController.provision()

