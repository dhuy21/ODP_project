import json
import os
import hashlib
from datetime import datetime

class UserDatabase:
    def __init__(self, db_file='data/users.json'):
        self.db_file = os.path.join(os.path.dirname(__file__), '..', db_file)
        os.makedirs(os.path.dirname(self.db_file), exist_ok=True)
        
        if not os.path.exists(self.db_file):
            self._create_default_users()
    
    def _create_default_users(self):
        """Create default admin user"""
        default_users = {
            'admin': {
                'email': 'admin@iaas.com',
                'password': self._hash_password('admin'),
                'role': 'admin',
                'created_at': datetime.now().isoformat(),
                'reservations': []
            }
        }
        self.save_users(default_users)
    
    def _hash_password(self, password):
        """Hash password using SHA256"""
        return hashlib.sha256(password.encode()).hexdigest()
    
    def load_users(self):
        """Load users from JSON file"""
        try:
            with open(self.db_file, 'r') as f:
                return json.load(f)
        except:
            return {}
    
    def save_users(self, users):
        """Save users to JSON file"""
        with open(self.db_file, 'w') as f:
            json.dump(users, f, indent=2)
    
    def register_user(self, username, email, password, role='user'):
        """Register a new user"""
        users = self.load_users()
        
        # SECURITY: Block reserved system usernames
        RESERVED_USERNAMES = [
            'root', 'admin', 'vagrant', 'ubuntu', 'daemon', 'bin', 'sys', 
            'sync', 'games', 'man', 'lp', 'mail', 'news', 'uucp', 'proxy',
            'www-data', 'backup', 'list', 'irc', 'gnats', 'nobody', 
            'systemd-network', 'systemd-resolve', 'messagebus', 'syslog',
            'docker', 'sudo', 'wheel', 'operator', 'adm'
        ]
        
        if username.lower() in RESERVED_USERNAMES:
            return {
                'status': 'error', 
                'message': f'Username "{username}" is reserved and cannot be used. Please choose another username.'
            }
        
        if username in users:
            return {'status': 'error', 'message': 'Username already exists'}
        
        # Validate username format
        if not username.replace('_', '').replace('-', '').isalnum():
            return {
                'status': 'error',
                'message': 'Username can only contain letters, numbers, hyphens, and underscores'
            }
        
        if len(username) < 3 or len(username) > 32:
            return {
                'status': 'error',
                'message': 'Username must be between 3 and 32 characters'
            }
        
        users[username] = {
            'email': email,
            'password': self._hash_password(password),
            'role': role,
            'created_at': datetime.now().isoformat(),
            'reservations': []
        }
        
        self.save_users(users)
        return {'status': 'success', 'message': 'User registered successfully'}
    
    def login_user(self, username, password):
        """Authenticate user"""
        users = self.load_users()
        
        if username not in users:
            return {'status': 'error', 'message': 'Invalid credentials'}
        
        user = users[username]
        
        if user['password'] != self._hash_password(password):
            return {'status': 'error', 'message': 'Invalid credentials'}
        
        return {
            'status': 'success',
            'user': username,
            'role': user.get('role', 'user')
        }
    
    def is_admin(self, username):
        """Check if user is admin"""
        users = self.load_users()
        return users.get(username, {}).get('role') == 'admin'
    
    def get_user_reservations(self, username):
        """Get all reservations for a user"""
        users = self.load_users()
        return users.get(username, {}).get('reservations', [])
    
    def add_reservation(self, username, reservation_data):
        """Add a reservation to user"""
        users = self.load_users()
        
        if username not in users:
            return False
        
        users[username]['reservations'].append(reservation_data)
        self.save_users(users)
        return True
    
    def update_reservation_status(self, username, reservation_id, new_status):
        """Update reservation status"""
        users = self.load_users()
        
        if username not in users:
            return False
        
        for reservation in users[username]['reservations']:
            if reservation['id'] == reservation_id:
                reservation['status'] = new_status
                self.save_users(users)
                return True
        
        return False
    
    def delete_reservation(self, username, reservation_id):
        """Delete a reservation"""
        users = self.load_users()
        
        if username not in users:
            return False
        
        users[username]['reservations'] = [
            r for r in users[username]['reservations'] 
            if r['id'] != reservation_id
        ]
        
        self.save_users(users)
        return True
    
    def get_all_users(self):
        """Get all users with their reservation count - FIXED"""
        users = self.load_users()
        result = {}
        
        for username, user_data in users.items():
            result[username] = {
                'email': user_data.get('email', ''),
                'role': user_data.get('role', 'user'),
                'created_at': user_data.get('created_at', ''),
                'reservation_count': len(user_data.get('reservations', []))  # FIX: Added this
            }
        
        return result
    
    def get_all_reservations(self):
        """Get all reservations from all users"""
        users = self.load_users()
        all_reservations = []
        
        for username, user_data in users.items():
            for reservation in user_data.get('reservations', []):
                reservation_copy = reservation.copy()
                reservation_copy['owner'] = username
                all_reservations.append(reservation_copy)
        
        return all_reservations
    
    def delete_user(self, username):
        """Delete a user"""
        if username == 'admin':
            return False
        
        users = self.load_users()
        
        if username in users:
            del users[username]
            self.save_users(users)
            return True
        
        return False
    
    def update_user_role(self, username, new_role):
        """Update user role"""
        if username == 'admin':
            return False
        
        users = self.load_users()
        
        if username in users:
            users[username]['role'] = new_role
            self.save_users(users)
            return True
        
        return False