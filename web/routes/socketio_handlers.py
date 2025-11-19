"""
Gestionnaires d'événements SocketIO pour les connexions SSH
"""
from flask import request
from flask_socketio import emit
from controller.ssh_controller import SSHController


def register_socketio_handlers(socketio):
    """
    Enregistre tous les gestionnaires SocketIO
    
    Args:
        socketio: Instance Flask-SocketIO
    """
    
    @socketio.on('connect_ssh')
    def handle_ssh_connection(data):
        """Gère l'établissement d'une connexion SSH"""
        session_id = request.sid
        SSHController.handle_connect(data, socketio, session_id)
    
    @socketio.on('input')
    def handle_input(data):
        """Gère l'envoi d'input au terminal"""
        session_id = request.sid
        SSHController.handle_input(data, session_id)
    
    @socketio.on('resize')
    def handle_resize(data):
        """Gère le redimensionnement du terminal"""
        session_id = request.sid
        SSHController.handle_resize(data, session_id)
    
    @socketio.on('disconnect')
    def handle_disconnect():
        """Gère la déconnexion d'une session SSH"""
        session_id = request.sid
        SSHController.handle_disconnect(session_id)

