"""
Contrôleur pour la gestion des dashboards
"""
from flask import render_template, redirect, url_for, session
from models.user import User
from models.vm import VM


class DashboardController:
    """Contrôleur pour les opérations de dashboard"""

    
    @staticmethod
    def get_user_dashboard():
        """
        Affiche le dashboard utilisateur
        
        Returns:
            Template du dashboard utilisateur
        """
        return render_template('user-dashboard.html')
    
    @staticmethod
    def get_admin_dashboard():
        """
        Affiche le dashboard administrateur avec les informations des VMs
        
        Returns:
            Template du dashboard admin avec username et vm_count
        """
        user = User.query.get(session.get('user_id'))
        
        if not user:
            return redirect(url_for('auth.login'))
        
        # Compter le nombre de VMs pour cet utilisateur
        vm_count = VM.query.filter_by(username=user.username).count()
        
        return render_template('admin-dashboard.html', 
                             username=user.username, 
                             vm_count=vm_count, 
                             user_is_logged_in=True)

