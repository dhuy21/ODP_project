from functools import wraps
from flask import session, redirect, url_for, jsonify

def login_required(f):
    """Decorator to require login for routes"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'username' not in session:
            return redirect(url_for('auth.login'))
        return f(*args, **kwargs)
    return decorated_function

def admin_required(f):
    """Decorator to require admin role"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'username' not in session:
            return redirect(url_for('auth.login'))
        
        from models.user import UserDatabase
        user_db = UserDatabase()
        
        if not user_db.is_admin(session['username']):
            return jsonify({
                'status': 'error',
                'message': 'Admin access required'
            }), 403
        
        return f(*args, **kwargs)
    return decorated_function

def user_only(f):
    """Decorator to allow only regular users (block admins)"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'username' not in session:
            return redirect(url_for('auth.login'))
        
        from models.user import UserDatabase
        user_db = UserDatabase()
        
        if user_db.is_admin(session['username']):
            return jsonify({
                'status': 'error',
                'message': 'Admin users cannot create reservations. Please use the admin panel to manage resources.'
            }), 403
        
        return f(*args, **kwargs)
    return decorated_function
