from flask import session, flash, redirect, url_for
from models import db
from models.user import User
from models.vm import VM

class AuthController:
    @staticmethod
    def login_user(username, password):
        user = User.query.filter_by(username=username).first()
        if user and user.check_password(password):
            session['user_id'] = user.id
            flash('Connexion reussie.')
            if user.is_admin:
                return redirect(url_for('main.admin_dashboard'))
            else:
                return redirect(url_for('main.user_dashboard'))
        else:
            flash('Nom d\'utilisateur ou mot de passe incorrect.')
            return redirect(url_for('auth.login'))

    @staticmethod
    def register_user(username, password, role):
        if User.query.filter_by(username=username).first():
            flash('Nom d\'utilisateur deja pris.')
            return redirect(url_for('auth.register'))
        
        user = User(username=username, role=role)
        user.set_password(password)
        db.session.add(user)
        db.session.commit()
        flash('Inscription reussie. Connectez-vous.')
        return redirect(url_for('auth.login'))

    @staticmethod
    def logout_user():
        session.pop('user_id', None)
        flash('Deconnexion reussie.')
        return redirect(url_for('auth.login'))

