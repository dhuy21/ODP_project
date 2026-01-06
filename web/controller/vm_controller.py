from flask import session, render_template, request, jsonify, redirect, url_for
from models.user import UserDatabase
from models.vm import Reservation, VM
from services.docker_service import DockerService
from services.ansible_service import AnsibleService
from services.stats_service import StatsService
import time
import uuid

class VMController:
    """Controller for VM provisioning and management"""
    
    def __init__(self):
        self.user_db = UserDatabase()
        self.docker_service = DockerService()
        self.ansible_service = AnsibleService()
        self.stats_service = StatsService()
        self.client_allocations = {}
    
    def get_pool_status(self):
        """Get pool status"""
        result = self.docker_service.get_pool_status()
        
        return jsonify({
            'status': 'success' if result['success'] else 'error',
            'total': result['total'],
            'free': result['free'],
            'allocated': result['allocated']
        })
    
    def provision(self):
        """Provision VMs for user"""
        data = request.json
        username = session['username']
        vm_password = data['password']
        vm_count = int(data['vm_count'])
        duration = int(data.get('duration', 60))
        packages = data.get('packages', '').strip()
        
        try:
            # Check and release expired containers
            self.docker_service.check_expired_containers()
            
            # Check available containers
            pool_status = self.docker_service.get_pool_status()
            free_count = pool_status['free']
            
            if free_count < vm_count:
                return jsonify({
                    'status': 'error',
                    'message': f'Not enough containers available. You need {vm_count} but only {free_count} are free.'
                })
            
            # Allocate containers
            allocation_result = self.docker_service.allocate_containers(
                username, vm_count, vm_password, duration
            )
            
            if not allocation_result['success']:
                return jsonify({
                    'status': 'error',
                    'message': allocation_result['error']
                })
            
            allocated_nodes = allocation_result['nodes']
            
            # Create reservation
            reservation = Reservation(username, vm_count, duration, packages.split(',') if packages else [])
            
            # Add nodes to reservation
            for node in allocated_nodes:
                vm = VM(node['name'], node['ip'], node['port'], username)
                reservation.add_node(vm)
            
            # Save reservation to database
            self.user_db.add_reservation(username, reservation.to_dict())
            
            # Store allocation info in memory
            self.client_allocations[username] = {
                'nodes': allocated_nodes,
                'username': username,
                'password': vm_password,
                'duration': duration,
                'reservation_id': reservation.id
            }
            
            # Install packages in background if specified
            if packages:
                self.ansible_service.install_packages_async(
                    username, allocated_nodes, vm_password, packages
                )
            
            return jsonify({
                'status': 'success',
                'redirect': f"/reservation/{reservation.id}"
            })
            
        except Exception as e:
            print(f"[ERROR] Provision failed: {str(e)}")
            import traceback
            traceback.print_exc()
            return jsonify({
                'status': 'error',
                'message': f'Internal error: {str(e)}'
            })
    
    def view_reservation(self, reservation_id):
        """View reservation details"""
        username = session['username']
        
        # Get reservation from database
        reservations = self.user_db.get_user_reservations(username)
        reservation = next((r for r in reservations if r['id'] == reservation_id), None)
        
        if not reservation:
            return redirect(url_for('main.dashboard_home'))
        
        return render_template('reservation_detail.html',
                             username=username,
                             reservation=reservation)
    
    def release_resources(self, username):
        """Release user resources"""
        if session['username'] != username:
            return jsonify({
                'status': 'error',
                'message': 'Unauthorized'
            })
        
        try:
            data = request.json
            reservation_id = data.get('reservation_id')
            
            # Release containers
            result = self.docker_service.release_containers(username)
            
            # Update reservation status
            if reservation_id:
                self.user_db.update_reservation_status(username, reservation_id, 'released')
            
            # Remove from memory
            if username in self.client_allocations:
                del self.client_allocations[username]
            
            return jsonify({
                'status': 'success',
                'message': 'Resources released'
            })
        except Exception as e:
            return jsonify({
                'status': 'error',
                'message': str(e)
            })
    
    def check_my_reservations(self):
        """Check if user has expired reservations"""
        username = session['username']
        reservations = self.user_db.get_user_reservations(username)
        current_time = time.time()
        
        has_expired = False
        
        for reservation in reservations:
            if reservation.get('status') == 'active':
                if current_time > reservation.get('expires_at', 0):
                    has_expired = True
                    self.user_db.update_reservation_status(username, reservation['id'], 'expired')
        
        return jsonify({
            'status': 'success',
            'has_expired': has_expired
        })
    
    def get_allocations(self):
        """Get current allocations (for backward compatibility)"""
        return self.client_allocations
    
    def get_container_stats(self, reservation_id):
        """Get container statistics for a reservation"""
        username = session['username']
        
        # Get reservation from database
        reservations = self.user_db.get_user_reservations(username)
        reservation = next((r for r in reservations if r['id'] == reservation_id), None)
        
        if not reservation:
            return jsonify({
                'status': 'error',
                'message': 'Reservation not found'
            })
        
        try:
            # Get stats for all nodes in the reservation
            stats = self.stats_service.get_reservation_stats(reservation.get('nodes', []))
            
            return jsonify({
                'status': 'success',
                'stats': stats
            })
        except Exception as e:
            print(f"[ERROR] Failed to get container stats: {e}")
            return jsonify({
                'status': 'error',
                'message': str(e)
            })
