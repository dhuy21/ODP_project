from flask import Blueprint, render_template
from middlewares.auth import login_required

main_bp = Blueprint('main', __name__)


@main_bp.route('/aboutus')
def aboutus():
    return render_template('aboutus.html')

@main_bp.route('/')
def accueil():
    return render_template('accueil.html')

@main_bp.route('/')
@login_required
def dashboard():
    return render_template('dashboard.html')
    

