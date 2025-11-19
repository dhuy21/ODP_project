"""
Contrôleur pour la gestion des connexions SSH
"""
from flask import request
from flask_socketio import emit
from services.ssh_service import SSHService

# Instance globale du service SSH (singleton)
ssh_service = SSHService()


class SSHController:
    """Contrôleur pour les opérations SSH via WebSocket"""
    
    @staticmethod
    def handle_connect(data, socketio, session_id):
        """
        Gère la connexion SSH initiale
        
        Args:
            data: Données de connexion (username, password, node_id)
            socketio: Instance SocketIO pour les communications
            session_id: ID de la session WebSocket
        """
        try:
            print(f"SSH connection request received: {data}")
            
            # Créer la connexion SSH
            success, session, error_msg = ssh_service.create_connection(
                session_id=session_id,
                username=data['username'],
                password=data['password'],
                node_id=int(data['node_id'])
            )
            
            if not success:
                emit('error', {'message': error_msg})
                return
            
            # Démarrer la tâche de lecture de sortie
            def read_output():
                """Lit en continu la sortie du channel SSH"""
                channel = session.channel
                
                while True:
                    if session_id not in ssh_service.sessions:
                        print(f"Session {session_id} ended")
                        break
                    
                    try:
                        if channel.recv_ready():
                            output = channel.recv(1024).decode('utf-8', 'ignore')
                            print(f"Sending output to client: {len(output)} bytes")
                            socketio.emit('output', {'data': output}, room=session_id)
                    except Exception as e:
                        print(f"Error reading from channel: {e}")
                        break
                    
                    socketio.sleep(0.01)
            
            # Démarrer la tâche en arrière-plan
            socketio.start_background_task(read_output)
            print("SSH connection and shell established successfully")
            
        except Exception as e:
            print(f"SSH Connection Error: {str(e)}")
            emit('error', {'message': str(e)})
    
    @staticmethod
    def handle_input(data, session_id):
        """
        Gère l'envoi d'input vers le terminal SSH
        
        Args:
            data: Données contenant l'input à envoyer
            session_id: ID de la session WebSocket
        """
        success, error_msg = ssh_service.send_input(session_id, data['data'])
        
        if not success:
            print(f"Error sending input: {error_msg}")
            emit('error', {'message': error_msg})
    
    @staticmethod
    def handle_resize(data, session_id):
        """
        Gère le redimensionnement du terminal
        
        Args:
            data: Données contenant cols et rows
            session_id: ID de la session WebSocket
        """
        success, error_msg = ssh_service.resize_terminal(
            session_id,
            cols=data['cols'],
            rows=data['rows']
        )
        
        if not success:
            print(f"Error resizing terminal: {error_msg}")
            emit('error', {'message': error_msg})
    
    @staticmethod
    def handle_disconnect(session_id):
        """
        Gère la déconnexion d'une session SSH
        
        Args:
            session_id: ID de la session WebSocket à fermer
        """
        print(f"Closing SSH session: {session_id}")
        ssh_service.close_session(session_id)
