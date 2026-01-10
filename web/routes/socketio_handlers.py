from flask_socketio import emit, join_room
from flask import request, session

def register_socketio_handlers(socketio, ssh_controller, vm_controller):
    """Register SocketIO event handlers"""
    
    @socketio.on('connect')
    def handle_connect():
        """Handle client connection and join user room for notifications"""
        if 'username' in session:
            username = session['username']
            join_room(username)
    
    @socketio.on('request_reservation_info')
    def handle_request_reservation_info(data):
        """Handle request for reservation info to get correct password"""
        ssh_controller.handle_request_reservation_info(data)
    
    @socketio.on('connect_ssh')
    def handle_ssh_connection(data):
        session_id = request.sid
        ssh_controller.handle_connect(data, session_id, vm_controller)
    
    @socketio.on('input')
    def handle_input(data):
        session_id = request.sid
        ssh_controller.handle_input(data, session_id)
    
    @socketio.on('resize')
    def handle_resize(data):
        session_id = request.sid
        ssh_controller.handle_resize(data, session_id)
    
    @socketio.on('disconnect')
    def handle_disconnect():
        session_id = request.sid
        ssh_controller.handle_disconnect(session_id)
