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
            with open(self.db_file, 'w') as f:
                json.dump({}, f)
    
    def hash_password(self, password):
        return hashlib.sha256(password.encode()).hexdigest()
    
    def register_user(self, username, email, password):
        users = self.load_users()
        
        if username in users:
            return {'status': 'error', 'message': 'Username already exists'}
        
        if any(u['email'] == email for u in users.values()):
            return {'status': 'error', 'message': 'Email already registered'}
        
        users[username] = {
            'email': email,
            'password': self.hash_password(password),
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
        
        return {'status': 'success', 'user': username}
    
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
    
    def load_users(self):
        with open(self.db_file, 'r') as f:
            return json.load(f)
    
    def save_users(self, users):
        with open(self.db_file, 'w') as f:
            json.dump(users, f, indent=2)