from flask import Blueprint, render_template
from middlewares.auth import login_required

main_bp = Blueprint('main', __name__)


@main_bp.route('/aboutus')
def aboutus():
    return render_template('aboutus.html')

@main_bp.route('/')
@login_required
def dashboard():
    return render_template('dashboard.html', user_is_logged_in=True)

@main_bp.route('/acceuil')
def accueil():
    return render_template('accueil.html')

@main_bp.route('/vm/<vm_id>')
@login_required
def get_vm(vm_id):
    # Logique pour fournir la VM demandée
    return {"status": "success", "vm_id": vm_id, "message": f"Fourniture de la VM avec l'ID: {vm_id}"}, 200
    

