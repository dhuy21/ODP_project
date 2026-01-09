from flask import session, render_template, request, jsonify, redirect, url_for
from models.user import UserDatabase

class AuthController:
    """Controller for authentication"""
    
    def __init__(self):
        self.user_db = UserDatabase()
    
    def show_login(self):
        """Show login page"""
        return render_template('login.html')
    
    def show_register(self):
        """Show registration page"""
        return render_template('register.html')
    
    def login(self):
        """Handle login"""
        data = request.json
        result = self.user_db.login_user(data['username'], data['password'])
        
        if result['status'] == 'success':
            session['username'] = result['user']
            session['role'] = result['role']
            session['logged_in'] = True
            
            return jsonify({
                'status': 'success',
                'redirect': url_for('main.home')
            })
        
        return jsonify(result)
    
    def register(self):
        """Handle registration"""
        data = request.json
        result = self.user_db.register_user(
            data['username'],
            data['email'],
            data['password'],
            role='user'
        )
        return jsonify(result)
    
    def logout(self):
        """Handle logout"""
        session.clear()
        return redirect(url_for('auth.login'))
