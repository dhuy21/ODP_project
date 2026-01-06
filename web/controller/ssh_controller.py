from flask import session, render_template, request
from flask_socketio import emit
from models.user import UserDatabase
from services.ssh_service import SSHService
import time

class SSHController:
    """Controller for SSH terminal connections"""
    
    def __init__(self, socketio):
        self.user_db = UserDatabase()
        self.ssh_service = SSHService()
        self.socketio = socketio
    
    def show_terminal(self, username, node_name):
        """Show terminal page"""
        if session['username'] != username:
            from flask import redirect, url_for
            return redirect(url_for('main.dashboard_home'))
        
        return render_template('terminal.html', username=username, node_name=node_name)
    
    def handle_connect(self, data, session_id, vm_controller):
        """Handle SSH connection"""
        try:
            username = data['username']
            node_name = data['node_name']
            
            # Check authorization
            if 'username' not in session or session['username'] != username:
                emit('error', {'message': 'Unauthorized'})
                return
            
            # Check if reservation is still active
            reservations = self.user_db.get_user_reservations(username)
            active_reservation = None
            
            for res in reservations:
                if res.get('status') == 'active':
                    # Check if not expired
                    if time.time() < res.get('expires_at', 0):
                        # Check if this node belongs to this reservation
                        for node in res.get('nodes', []):
                            if node['name'] == node_name:
                                active_reservation = res
                                break
                        if active_reservation:
                            break
            
            if not active_reservation:
                emit('error', {'message': 'No active reservation found for this container'})
                return
            
            # Find node port from reservation data
            node = next((n for n in active_reservation.get('nodes', []) if n['name'] == node_name), None)
            
            if not node:
                emit('error', {'message': 'Node not found in reservation'})
                return
            
            port = int(node['port'])
            
            # Create SSH session
            ssh_session = self.ssh_service.create_session(
                session_id, username, node_name, '127.0.0.1', port
            )
            
            # Connect
            password = data.get('password')
            if not ssh_session.connect(password=password):
                emit('error', {'message': 'Failed to connect to SSH'})
                return
            
            # Create shell
            if not ssh_session.create_shell():
                emit('error', {'message': 'Failed to create shell'})
                return
            
            # Store reservation info in session
            ssh_session.reservation_id = active_reservation['id']
            ssh_session.expires_at = active_reservation['expires_at']
            
            # Start output reader
            self._start_output_reader(session_id)
            
        except Exception as e:
            emit('error', {'message': str(e)})
    
    def handle_input(self, data, session_id):
        """Handle terminal input"""
        ssh_session = self.ssh_service.get_session(session_id)
        if ssh_session:
            try:
                ssh_session.send_input(data['data'])
            except Exception as e:
                emit('error', {'message': str(e)})
    
    def handle_resize(self, data, session_id):
        """Handle terminal resize"""
        ssh_session = self.ssh_service.get_session(session_id)
        if ssh_session:
            ssh_session.resize_terminal(data['cols'], data['rows'])
    
    def handle_disconnect(self, session_id):
        """Handle disconnect"""
        self.ssh_service.remove_session(session_id)
    
    def disconnect_user_sessions(self, username):
        """Disconnect all sessions for a user"""
        return self.ssh_service.disconnect_user_sessions(username)
    
    def _start_output_reader(self, session_id):
        """Start background task to read SSH output"""
        def read_output():
            while True:
                ssh_session = self.ssh_service.get_session(session_id)
                if not ssh_session:
                    break
                
                try:
                    # Check if session expired
                    if ssh_session.is_expired():
                        ssh_session.send_input('\r\n\r\n*** YOUR RESERVATION HAS EXPIRED ***\r\n')
                        ssh_session.send_input('*** This session will be disconnected in 5 seconds ***\r\n\r\n')
                        self.socketio.sleep(5)
                        
                        self.ssh_service.remove_session(session_id)
                        self.socketio.emit('force_disconnect',
                                          {'message': 'Reservation expired'},
                                          room=session_id)
                        break
                    
                    # Read output
                    output = ssh_session.recv_output()
                    if output:
                        self.socketio.emit('output', {'data': output}, room=session_id)
                    
                except Exception as e:
                    break
                
                self.socketio.sleep(0.01)
        
        self.socketio.start_background_task(read_output)
