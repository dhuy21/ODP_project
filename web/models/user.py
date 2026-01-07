import mysql.connector
import json
import os
import hashlib
from datetime import datetime
from config.config import Config

class UserDatabase:
    def __init__(self):
        # Database connection configuration
        self.db_config = {
            'host': os.environ.get('MYSQL_HOST', 'localhost'),
            'user': os.environ.get('MYSQL_USER', 'root'),
            'password': os.environ.get('MYSQL_PASSWORD', 'root'),  # Change your password
            'database': os.environ.get('MYSQL_DB', 'odp_platform')
        }

    def _get_connection(self):
        """Create a new MySQL connection"""
        return mysql.connector.connect(**self.db_config)
    
    def _create_default_users(self):
        """Create default admin user"""
        conn = None
        cursor = None
        try:
            conn = self._get_connection()
            cursor = conn.cursor()
            # Check if admin user already exists
            cursor.execute("SELECT id FROM users WHERE username = 'admin'")
            if cursor.fetchone():
                return  # Admin already exists
            # Create default admin user (password: admin)
            password = self._hash_password('admin')
            sql = """
                INSERT INTO users (username, email, password_hash, role, created_at)
                VALUES (%s, %s, %s, %s, NOW())
            """
            cursor.execute(sql, ('admin', 'admin@iac.com', password, 'admin'))
            conn.commit()
        except Exception as e:
            print(f"Error creating default users: {e}")
        finally:
            if cursor: cursor.close()
            if conn: conn.close()

    def _hash_password(self, password):
        """Hash password using SHA256"""
        return hashlib.sha256(password.encode()).hexdigest()
    
    def load_users(self):
        """Load all users and their reservations"""
        conn = self._get_connection()
        cursor = conn.cursor(dictionary=True)
        users_dict = {}
        try:
            # Load users
            cursor.execute("SELECT * FROM users")
            users_rows = cursor.fetchall()
            
            for row in users_rows:
                username = row['username']
                users_dict[username] = {
                    'email': row['email'],
                    'password': row['password_hash'],
                    'role': row['role'],
                    'created_at': row['created_at'].isoformat() if row['created_at'] else '',
                    'reservations': []
                }

            # Load reservations and attach to users
            cursor.execute(
                "SELECT r.*, u.username FROM reservations r JOIN users u ON r.user_id = u.id"
            )
            res_rows = cursor.fetchall()
            
            for row in res_rows:
                username = row['username']
                if username in users_dict:
                    users_dict[username]['reservations'].append({
                        'id': row['id'],
                        'username': username,
                        'vm_count': row['vm_count'],
                        'duration': row['duration_minutes'],
                        'status': row['status'],
                        'created_at': row['created_at'],
                        'expires_at': row['expires_at'],
                        'nodes': json.loads(row['nodes']) if row['nodes'] else [],
                        'final_stats': json.loads(row['final_stats']) if row['final_stats'] else {},
                        'packages': json.loads(row['packages']) if row['packages'] else []
                    })

            return users_dict
        except Exception as e:
            print(f"Error loading users: {e}")
            return {}
        finally:
            if cursor: cursor.close()
            if conn: conn.close()

    def register_user(self, username, email, password, role='user'):
        """Register a new user"""
        conn = None
        cursor = None
        try:
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
            conn = self._get_connection()
            cursor = conn.cursor()

            cursor.execute("SELECT id FROM users WHERE username = %s", (username,))
            if cursor.fetchone():
                return {'status': 'error', 'message': 'Username already exists'}

            sql = """
                INSERT INTO users (username, email, password_hash, role, created_at)
                VALUES (%s, %s, %s, %s, NOW())
            """
            cursor.execute(sql, (username, email, self._hash_password(password), role))
            conn.commit()
            return {'status': 'success', 'message': 'User registered successfully'}
        except Exception as e:
            return {'status': 'error', 'message': str(e)}
        finally:
            if cursor: cursor.close()
            if conn: conn.close()

    def login_user(self, username, password):
        """Authenticate user"""
        conn = None
        cursor = None
        try:
            conn = self._get_connection()
            cursor = conn.cursor(dictionary=True)
            cursor.execute(
                "SELECT username, password_hash, role FROM users WHERE username = %s",
                (username,)
            )
            user = cursor.fetchone()

            if not user or user['password_hash'] != self._hash_password(password):
                return {'status': 'error', 'message': 'Invalid credentials'}

            return {
                'status': 'success',
                'user': username,
                'role': user.get('role', 'user')
            }
        finally:
            if cursor: cursor.close()
            if conn: conn.close()

    def is_admin(self, username):
        """Check if user is admin"""
        conn = None
        cursor = None
        try:
            conn = self._get_connection()
            cursor = conn.cursor()
            cursor.execute("SELECT role FROM users WHERE username = %s", (username,))
            res = cursor.fetchone()
            return res[0] == 'admin' if res else False
        finally:
            if cursor: cursor.close()
            if conn: conn.close()

    def get_user_reservations(self, username):
        """Get all reservations for a user"""
        conn = None
        cursor = None
        try:
            conn = self._get_connection()
            cursor = conn.cursor(dictionary=True)
            cursor.execute(
                "SELECT r.* FROM reservations r "
                "JOIN users u ON r.user_id = u.id WHERE u.username = %s",
                (username,)
            )
            rows = cursor.fetchall()

            results = []
            for row in rows:
                row['nodes'] = json.loads(row['nodes']) if row['nodes'] else []
                row['final_stats'] = json.loads(row['final_stats']) if row['final_stats'] else {}
                row['packages'] = json.loads(row['packages']) if row['packages'] else []
                row['duration'] = row['duration_minutes']
                row['username'] = username
                results.append(row)
            return results
        finally:
            if cursor: cursor.close()
            if conn: conn.close()

    def add_reservation(self, username, reservation_data):
        """Add a reservation to user"""
        conn = None
        cursor = None
        try:
            conn = self._get_connection()
            cursor = conn.cursor()
            cursor.execute("SELECT id FROM users WHERE username = %s", (username,))
            user_res = cursor.fetchone()
            if not user_res:
                return False

            sql = """
                INSERT INTO reservations
                (id, user_id, vm_count, duration_minutes, status,
                 created_at, expires_at, nodes, final_stats, packages)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            """
            cursor.execute(sql, (
                reservation_data['id'],
                user_res[0],
                reservation_data.get('vm_count', 1),
                reservation_data.get('duration', 60),
                reservation_data.get('status', 'active'),
                reservation_data.get('created_at'),
                reservation_data.get('expires_at'),
                json.dumps(reservation_data.get('nodes', [])),
                json.dumps(reservation_data.get('final_stats', {})),
                json.dumps(reservation_data.get('packages', []))
            ))
            conn.commit()
            return True
        except Exception as e:
            print(f"Add reservation error: {e}")
            return False
        finally:
            if cursor: cursor.close()
            if conn: conn.close()

    def save_reservation_final_stats(self, username, reservation_id, final_stats):
        """Save final statistics when reservation expires or is released"""
        conn = None
        cursor = None
        try:
            conn = self._get_connection()
            cursor = conn.cursor()
            cursor.execute(
                "UPDATE reservations r JOIN users u ON r.user_id = u.id "
                "SET r.final_stats = %s WHERE u.username = %s AND r.id = %s",
                (json.dumps(final_stats), username, reservation_id)
            )
            conn.commit()
            return True
        finally:
            if cursor: cursor.close()
            if conn: conn.close()

    def update_reservation_status(self, username, reservation_id, new_status):
        """Update reservation status"""
        conn = None
        cursor = None
        try:
            conn = self._get_connection()
            cursor = conn.cursor()
            cursor.execute(
                "UPDATE reservations r JOIN users u ON r.user_id = u.id "
                "SET r.status = %s WHERE u.username = %s AND r.id = %s",
                (new_status, username, reservation_id)
            )
            conn.commit()
            return True
        finally:
            if cursor: cursor.close()
            if conn: conn.close()
    
    def delete_reservation(self, username, reservation_id):
        """Delete a reservation"""
        conn = cursor = None
        try:
            conn = self._get_connection()
            cursor = conn.cursor()
            # Check admin role
            cursor.execute(
                "SELECT role FROM users WHERE username = %s",
                (username,)
            )
            row = cursor.fetchone()
            if not row or row[0] != 'admin':
                return False
            # Soft delete reservation
            cursor.execute(
                "UPDATE reservations SET status = 'deleted' WHERE id = %s",
                (reservation_id,)
            )
            conn.commit()
            return cursor.rowcount > 0
        finally:
            if cursor:
                cursor.close()
            if conn:
                conn.close()

    def get_all_users(self):
        """Get all users with reservation count"""
        conn = None
        cursor = None
        result = {}
        try:
            conn = self._get_connection()
            cursor = conn.cursor(dictionary=True)
            cursor.execute(
                "SELECT u.username, u.email, u.role, u.created_at, "
                "COUNT(r.id) AS reservation_count "
                "FROM users u LEFT JOIN reservations r ON u.id = r.user_id "
                "GROUP BY u.id"
            )
            for row in cursor.fetchall():
                result[row['username']] = {
                    'email': row['email'],
                    'role': row['role'],
                    'created_at': row['created_at'].isoformat() if row['created_at'] else '',
                    'reservation_count': row['reservation_count']
                }
            return result
        finally:
            if cursor: cursor.close()
            if conn: conn.close()

    def get_all_reservations(self):
        """Get all reservations from all users"""
        conn = None
        cursor = None
        all_reservations = []
        try:
            conn = self._get_connection()
            cursor = conn.cursor(dictionary=True)
            cursor.execute(
                "SELECT r.*, u.username AS owner "
                "FROM reservations r JOIN users u ON r.user_id = u.id "
                "ORDER BY r.created_at DESC"
            )
            for row in cursor.fetchall():
                row['nodes'] = json.loads(row['nodes']) if row['nodes'] else []
                row['final_stats'] = json.loads(row['final_stats']) if row['final_stats'] else {}
                row['packages'] = json.loads(row['packages']) if row['packages'] else []
                row['duration'] = row['duration_minutes']
                all_reservations.append(row)
            return all_reservations
        finally:
            if cursor: cursor.close()
            if conn: conn.close()
    
    def delete_user(self, username):
        """Delete a user"""
        if username == 'admin':
            return False
        conn = cursor = None
        try:
            conn = self._get_connection()
            cursor = conn.cursor()
            cursor.execute("DELETE FROM users WHERE username=%s", (username,))
            conn.commit()
            return cursor.rowcount > 0
        finally:
            if cursor: cursor.close()
            if conn: conn.close()

    def update_user_role(self, username, new_role):
        """Update user role"""
        if username == 'admin':
            return False
        conn = cursor = None
        try:
            conn = self._get_connection()
            cursor = conn.cursor()
            cursor.execute(
                "UPDATE users SET role=%s WHERE username=%s",
                (new_role, username)
            )
            conn.commit()
            return True
        finally:
            if cursor: cursor.close()
            if conn: conn.close()
