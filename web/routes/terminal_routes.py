"""
Routes pour les terminaux SSH
"""
from flask import Blueprint, render_template

terminal_bp = Blueprint('terminal', __name__)


@terminal_bp.route('/terminal/<username>/<node_id>')
def terminal(username, node_id):
    """Route pour afficher le terminal SSH d'un node"""
    return render_template('terminal.html', username=username, node_id=node_id)

