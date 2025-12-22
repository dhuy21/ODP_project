import json
import os
from datetime import datetime
import hashlib

class UserDatabase:
    def __init__(self, db_file='data/users.json'):
        self.db_file = db_file
        self.ensure_db_exists()
    
    def ensure_db_exists(self):
        os.makedirs(os.path.dirname(self.db_file), exist_ok=True)
        if not os.path.exists(self.db_file):
            # Create default admin user
            default_users = {
                'admin': {
                    'email': 'admin@iaas.local',
                    'password': self.hash_password('admin123'),  # Change this!
                    'role': 'admin',
                    'created_at': datetime.now().isoformat(),
                    'reservations': []
                }
            }
            with open(self.db_file, 'w') as f:
                json.dump(default_users, f, indent=2)
    
    def hash_password(self, password):
        return hashlib.sha256(password.encode()).hexdigest()
    
    def register_user(self, username, email, password, role='user'):
        users = self.load_users()
        
        if username in users:
            return {'status': 'error', 'message': 'Username already exists'}
        
        if any(u['email'] == email for u in users.values()):
            return {'status': 'error', 'message': 'Email already registered'}
        
        users[username] = {
            'email': email,
            'password': self.hash_password(password),
            'role': role,
            'created_at': datetime.now().isoformat(),
            'reservations': []
        }
        
        self.save_users(users)
        return {'status': 'success', 'message': 'User registered successfully'}
    
    def login_user(self, username, password):
        users = self.load_users()
        
        if username not in users:
            return {'status': 'error', 'message': 'Invalid username or password'}
        
        if users[username]['password'] != self.hash_password(password):
            return {'status': 'error', 'message': 'Invalid username or password'}
        
        return {
            'status': 'success', 
            'user': username,
            'role': users[username].get('role', 'user')
        }
    
    def get_user_role(self, username):
        users = self.load_users()
        if username not in users:
            return 'user'
        return users[username].get('role', 'user')
    
    def is_admin(self, username):
        return self.get_user_role(username) == 'admin'
    
    def get_all_users(self):
        users = self.load_users()
        # Don't return passwords
        return {
            username: {
                'email': data['email'],
                'role': data.get('role', 'user'),
                'created_at': data.get('created_at', ''),
                'reservation_count': len(data.get('reservations', []))
            }
            for username, data in users.items()
        }
    
    def delete_user(self, username):
        users = self.load_users()
        if username in users:
            del users[username]
            self.save_users(users)
            return True
        return False
    
    def update_user_role(self, username, role):
        users = self.load_users()
        if username in users:
            users[username]['role'] = role
            self.save_users(users)
            return True
        return False
    
    def add_reservation(self, username, reservation_data):
        users = self.load_users()
        
        if username not in users:
            return False
        
        users[username]['reservations'].append(reservation_data)
        self.save_users(users)
        return True
    
    def get_user_reservations(self, username):
        users = self.load_users()
        
        if username not in users:
            return []
        
        return users[username]['reservations']
    
    def get_all_reservations(self):
        """Get all reservations from all users (admin only)"""
        users = self.load_users()
        all_reservations = []
        
        for username, data in users.items():
            for reservation in data.get('reservations', []):
                reservation['owner'] = username
                all_reservations.append(reservation)
        
        return all_reservations
    
    def update_reservation_status(self, username, reservation_id, status):
        users = self.load_users()
        
        if username not in users:
            return False
        
        for reservation in users[username]['reservations']:
            if reservation['id'] == reservation_id:
                reservation['status'] = status
                self.save_users(users)
                return True
        
        return False
    
    def delete_reservation(self, username, reservation_id):
        """Delete a specific reservation"""
        users = self.load_users()
        
        if username not in users:
            return False
        
        reservations = users[username]['reservations']
        users[username]['reservations'] = [
            r for r in reservations if r['id'] != reservation_id
        ]
        
        self.save_users(users)
        return True
    
    def load_users(self):
        with open(self.db_file, 'r') as f:
            return json.load(f)
    
    def save_users(self, users):
        with open(self.db_file, 'w') as f:
            json.dump(users, f, indent=2)