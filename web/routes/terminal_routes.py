from flask import Blueprint
from controller.ssh_controller import SSHController
from middlewares.auth import login_required

# Create blueprint
terminal_bp = Blueprint('terminal', __name__)

# SSH controller will be initialized in app.py after socketio is created

@terminal_bp.route('/terminal/<username>/<node_name>')
@login_required
def terminal(username, node_name):
    from flask import current_app
    ssh_controller = current_app.config['SSH_CONTROLLER']
    return ssh_controller.show_terminal(username, node_name)
