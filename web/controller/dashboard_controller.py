from flask import session, render_template, jsonify
from models.user import UserDatabase
from services.docker_service import DockerService
import time

class DashboardController:
    """Controller for dashboard views"""
    
    def __init__(self):
        self.user_db = UserDatabase()
        self.docker_service = DockerService()
    
    def home(self):
        """Main home page"""
        username = session['username']
        role = session.get('role', 'user')
        
        # Redirect admin to admin panel
        if role == 'admin':
            from flask import redirect, url_for
            return redirect(url_for('main.admin_panel'))
        
        # Get pool status
        pool_status = self.docker_service.get_pool_status()
        available = pool_status['free']
        
        # Get user's reservations
        reservations = self.user_db.get_user_reservations(username)
        
        # Filter active reservations - check both status and expires_at
        current_time = time.time()
        active_reservations = []
        for r in reservations:
            status = r.get('status')
            expires_at = r.get('expires_at', 0)
            
            # Only include if status is 'active' AND not expired
            if status == 'active' and current_time < expires_at:
                active_reservations.append(r)
            elif status == 'active' and current_time >= expires_at:
                # Reservation is expired but status hasn't been updated yet
                # This can happen due to race conditions - filter it out
                print(f"[DASHBOARD] Filtering out expired reservation {r.get('id', 'unknown')[:8]} that still has 'active' status")
        
        # Generate recent activity
        recent_activity = self._generate_recent_activity(reservations)
        
        return render_template('dashboard_home.html',
                             username=username,
                             role=role,
                             available_containers=available,
                             active_reservations=active_reservations,
                             total_reservations=len(reservations),
                             reservations=reservations,
                             recent_activity=recent_activity)
    
    def dashboard_home(self):
        """Dashboard page for users"""
        username = session['username']
        role = session.get('role', 'user')
        
        # Redirect admin to admin panel
        if role == 'admin':
            from flask import redirect, url_for
            return redirect(url_for('main.admin_panel'))
        
        # Run health check
        self.docker_service.health_check()
        
        # Get pool status
        pool_status = self.docker_service.get_pool_status()
        available = pool_status['free']
        
        # Get user's reservations
        reservations = self.user_db.get_user_reservations(username)
        
        # Check health of active reservations
        active_reservations = []
        for r in reservations:
            if r.get('status') == 'active':
                if not self._check_reservation_health(r):
                    # Save final stats before marking as deleted
                    from services.stats_service import StatsService
                    stats_service = StatsService()
                    final_stats = stats_service.get_reservation_stats(r.get('nodes', []))
                    if final_stats:
                        self.user_db.save_reservation_final_stats(username, r['id'], final_stats)
                    
                    self.user_db.update_reservation_status(username, r['id'], 'deleted')
                    r['status'] = 'deleted'
                else:
                    active_reservations.append(r)
        
        return render_template('dashboard_home.html',
                             username=username,
                             role=role,
                             available_containers=available,
                             reservations=reservations,
                             active_reservations=active_reservations)
    
    def admin_panel(self):
        """Admin panel"""
        username = session['username']
        
        # Get all users
        all_users = self.user_db.get_all_users()
        
        # Get all reservations
        all_reservations = self.user_db.get_all_reservations()
        
        # Get pool status
        pool_status = self.docker_service.get_pool_status()
        
        return render_template('admin_panel.html',
                             username=username,
                             users=all_users,
                             reservations=all_reservations,
                             pool_status=pool_status)
    
    def admin_get_users(self):
        """Get all users for admin"""
        users = self.user_db.get_all_users()
        return jsonify({'status': 'success', 'users': users})
    
    def admin_create_user(self):
        """Create user as admin"""
        from flask import request
        data = request.json
        
        # Validate role - only 'user' or 'admin' allowed
        role = data.get('role', 'user')
        if role not in ['user', 'admin']:
            return jsonify({
                'status': 'error',
                'message': f'Invalid role: {role}. Only "user" or "admin" are allowed.'
            })
        
        result = self.user_db.register_user(
            data['username'],
            data['email'],
            data['password'],
            role=role
        )
        return jsonify(result)
    
    def admin_delete_user(self, username):
        """Delete user as admin - Force release ALL reservations"""
        # Prevent deleting admin account
        if username == 'admin':
            return jsonify({
                'status': 'error',
                'message': 'Cannot delete the system admin account'
            })
        
        # Prevent admins from deleting other admins
        user_info = self.user_db.get_user(username)
        if user_info and user_info.get('role') == 'admin':
            return jsonify({
                'status': 'error',
                'message': 'Cannot delete admin users. Only regular users can be deleted.'
            })
        
        try:
            # 1. Get ALL reservations of this user (active and non-active)
            user_reservations = self.user_db.get_user_reservations(username)
            active_reservations = [r for r in user_reservations if r.get('status') == 'active']
            
            # 2. Force release ALL active reservations
            released_count = 0
            for reservation in active_reservations:
                reservation_id = reservation.get('id')
                nodes = reservation.get('nodes', [])
                
                if nodes:
                    # Save final stats before release
                    self._save_final_stats_before_status_change(username, reservation_id, 'deleted')
                    
                    # Release containers for this reservation
                    result = self.docker_service.release_containers_by_nodes(username, nodes)
                    if result.get('success'):
                        released_count += len(nodes)
                        print(f"[ADMIN DELETE] Released {len(nodes)} containers for reservation {reservation_id[:8]}")
                    
                    # Disconnect SSH sessions for this reservation
                    from services.ssh_service import SSHService
                    ssh_service = SSHService()
                    disconnected = ssh_service.disconnect_sessions_by_nodes(username, nodes)
                    if disconnected > 0:
                        print(f"[ADMIN DELETE] Disconnected {disconnected} SSH sessions")
                
                # Update reservation status to 'deleted'
                self.user_db.update_reservation_status(username, reservation_id, 'deleted')
            
            # 3. Delete user from database (will cascade delete reservations via FK)
            if self.user_db.delete_user(username):
                return jsonify({
                    'status': 'success',
                    'message': f'User {username} deleted. Released {released_count} containers and {len(active_reservations)} reservations.'
                })
            else:
                return jsonify({'status': 'error', 'message': 'Failed to delete user'})
                
        except Exception as e:
            print(f"[ADMIN DELETE ERROR] {e}")
            return jsonify({'status': 'error', 'message': f'Error deleting user: {str(e)}'})
    
    def admin_update_role(self, username):
        """Update user role"""
        from flask import request
        data = request.json
        role = data.get('role', 'user')
        
        # Validate role
        if role not in ['user', 'admin']:
            return jsonify({'status': 'error', 'message': 'Invalid role'})
        
        # Prevent changing admin account
        if username == 'admin':
            return jsonify({'status': 'error', 'message': 'Cannot change system admin role'})
        
        # Get current user info
        user_info = self.user_db.get_user(username)
        if not user_info:
            return jsonify({'status': 'error', 'message': 'User not found'})
        
        # Prevent demoting other admins
        if user_info.get('role') == 'admin' and role == 'user':
            return jsonify({'status': 'error', 'message': 'Cannot demote admin users. Only regular users can have their roles changed.'})
        
        if self.user_db.update_user_role(username, role):
            return jsonify({'status': 'success', 'message': f'Role updated to {role}'})
        
        return jsonify({'status': 'error', 'message': 'Failed to update role'})
    
    def admin_delete_reservation(self, reservation_id):
        """Delete reservation as admin"""
        admin = session['username']
        all_reservations = self.user_db.get_all_reservations()
        reservation = next((r for r in all_reservations if r['id'] == reservation_id), None)
        
        if not reservation:
            return jsonify({'status': 'error', 'message': 'Reservation not found'})
        
        owner = reservation['owner']
        nodes = reservation.get('nodes', [])
        
        # Release ONLY containers for THIS reservation (not all user containers)
        if nodes:
            self.docker_service.release_containers_by_nodes(owner, nodes)
        
        # Delete reservation from database
        if not self.user_db.delete_reservation(admin, reservation_id):
            return jsonify({'status': 'error', 'message': 'Permission denied'})
        
        return jsonify({'status': 'success', 'message': 'Reservation deleted'})
    
    def admin_recover_pool(self):
        """Recover pool"""
        result = self.docker_service.recover_pool()
        
        if result['success']:
            return jsonify({
                'status': 'success',
                'message': 'Pool recovery initiated',
                'output': result['output']
            })
        else:
            return jsonify({
                'status': 'error',
                'message': result.get('error', 'Unknown error')
            })
    
    def admin_overview(self):
        """Admin overview/dashboard page"""
        username = session['username']
        
        # Get all users (returns dict with username as key)
        all_users = self.user_db.get_all_users()
        
        # Count admins and regular users
        admin_count = len([user_data for user_data in all_users.values() if user_data.get('role') == 'admin'])
        user_count = len([user_data for user_data in all_users.values() if user_data.get('role') == 'user'])
        
        # Get all reservations
        all_reservations = self.user_db.get_all_reservations()
        active_reservations = [r for r in all_reservations if r.get('status') == 'active']
        
        # Get pool status
        pool_status = self.docker_service.get_pool_status()
        
        # Generate recent activity from all reservations
        recent_activity = self._generate_admin_recent_activity(all_reservations)
        
        stats = {
            'total_users': len(all_users),
            'admin_count': admin_count,
            'user_count': user_count,
            'active_reservations': len(active_reservations),
            'total_containers': pool_status.get('total', 30),
            'available_containers': pool_status.get('free', 0)
        }
        
        return render_template('admin_overview.html',
                             username=username,
                             stats=stats,
                             recent_activity=recent_activity)
    
    def admin_users(self):
        """Admin users management page"""
        username = session['username']
        all_users = self.user_db.get_all_users()
        
        # Format users for template
        users_list = []
        for username_key, user_data in all_users.items():
            users_list.append({
                'username': username_key,
                'email': user_data.get('email', ''),
                'role': user_data.get('role', 'user'),
                'created_at': user_data.get('created_at', ''),
                'reservation_count': user_data.get('reservation_count', 0),
                'is_active': True  # Assume all users are active for now
            })
        
        return render_template('admin_users.html',
                             username=username,
                             users=users_list)
    
    def admin_reservations(self):
        """Admin reservations management page"""
        username = session['username']
        all_reservations = self.user_db.get_all_reservations()
        
        # Sort by created_at descending
        all_reservations.sort(key=lambda x: x.get('created_at', 0), reverse=True)
        
        return render_template('admin_reservations.html',
                             username=username,
                             reservations=all_reservations)
    
    def admin_pool(self):
        """Admin pool management page"""
        username = session['username']
        pool_details = self.docker_service.get_pool_details()
        
        return render_template('admin_pool.html',
                             username=username,
                             pool_details=pool_details)
    
    def _generate_recent_activity(self, reservations):
        """Generate recent activity list"""
        from datetime import datetime
        
        recent_activity = []
        for reservation in sorted(reservations, key=lambda x: x.get('created_at', 0), reverse=True)[:5]:
            activity_type = reservation.get('status', 'unknown')
            created_time = reservation.get('created_at', 0)
            time_str = datetime.fromtimestamp(created_time).strftime('%Y-%m-%d %H:%M')
            
            if activity_type == 'active':
                recent_activity.append({
                    'type': 'created',
                    'title': f'Created reservation with {reservation.get("vm_count")} VMs',
                    'time': time_str
                })
            elif activity_type == 'expired':
                recent_activity.append({
                    'type': 'expired',
                    'title': f'Reservation expired ({reservation.get("vm_count")} VMs)',
                    'time': time_str
                })
            elif activity_type == 'released':
                recent_activity.append({
                    'type': 'released',
                    'title': f'Released {reservation.get("vm_count")} VMs',
                    'time': time_str
                })
        
        return recent_activity
    
    def reservation_history(self):
        """Reservation history page"""
        username = session['username']
        role = session.get('role', 'user')
        
        # Redirect admin to admin panel
        if role == 'admin':
            from flask import redirect, url_for
            return redirect(url_for('main.admin_panel'))
        
        # Get user's reservations
        reservations = self.user_db.get_user_reservations(username)
        
        # Sort by created_at descending (newest first)
        reservations.sort(key=lambda x: x.get('created_at', 0), reverse=True)
        
        return render_template('reservation_history.html',
                             username=username,
                             role=role,
                             reservations=reservations)
    
    def _check_reservation_health(self, reservation):
        """Check if reservation's containers are still running"""
        for node in reservation.get('nodes', []):
            if not self.docker_service.check_container_running(node['name']):
                return False
        return True
    
    def _generate_admin_recent_activity(self, all_reservations):
        """Generate recent activity list for admin from all reservations"""
        from datetime import datetime
        
        recent_activity = []
        for reservation in sorted(all_reservations, key=lambda x: x.get('created_at', 0), reverse=True)[:10]:
            activity_type = reservation.get('status', 'unknown')
            created_time = reservation.get('created_at', 0)
            owner = reservation.get('owner', 'unknown')
            time_str = datetime.fromtimestamp(created_time).strftime('%Y-%m-%d %H:%M:%S')
            
            if activity_type == 'active':
                recent_activity.append({
                    'timestamp': time_str,
                    'user': owner,
                    'action': 'Created',
                    'details': f'Reservation with {reservation.get("vm_count")} VMs'
                })
            elif activity_type == 'expired':
                recent_activity.append({
                    'timestamp': time_str,
                    'user': owner,
                    'action': 'Expired',
                    'details': f'Reservation expired ({reservation.get("vm_count")} VMs)'
                })
            elif activity_type == 'released':
                recent_activity.append({
                    'timestamp': time_str,
                    'user': owner,
                    'action': 'Released',
                    'details': f'Released {reservation.get("vm_count")} VMs'
                })
        
        return recent_activity

    def get_active_reservations(self):
        """API endpoint to get active reservations for current user"""
        username = session['username']
        
        # Get user's reservations
        reservations = self.user_db.get_user_reservations(username)
        
        # Filter active reservations - check both status and expires_at
        current_time = time.time()
        active_reservations = []
        for r in reservations:
            status = r.get('status')
            expires_at = r.get('expires_at', 0)
            
            # Only include if status is 'active' AND not expired
            if status == 'active' and current_time < expires_at:
                active_reservations.append(r)
            elif status == 'active' and current_time >= expires_at:
                # Reservation is expired but status hasn't been updated yet
                # Filter it out
                print(f"[API] Filtering out expired reservation {r.get('id', 'unknown')[:8]} that still has 'active' status")
        
        return jsonify({
            'status': 'success',
            'active_reservations': active_reservations,
            'count': len(active_reservations)
        })