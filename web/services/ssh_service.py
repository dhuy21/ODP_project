"""
Service pour gérer les connexions SSH
"""
import paramiko
import os
from typing import Optional, Dict
from models.ssh_session import SSHSession
from models.vm import VM

class SSHService:
    """Service pour gérer les connexions SSH"""
    
    def __init__(self):
        self.sessions: Dict[str, SSHSession] = {}
    
    def create_connection(self, session_id: str, username: str, password: str, node_id: int) -> tuple[bool, Optional[SSHSession], str]:
        """
        Crée une connexion SSH vers un node
        
        Returns:
            tuple: (success: bool, session: Optional[SSHSession], error_message: str)
        """
        try:
            print(f"SSH connection request for user {username}, node {node_id}")
            
            # Récupérer la configuration VM depuis la base de données
            vm = VM.query.filter_by(username=username).first()
            if not vm:
                return False, None, f"No VM configuration found for user {username}"
            
            # Utiliser le port depuis la configuration VM
            port = vm.get_port_for_node(node_id - 1)  # node_id est 1-indexed, mais la méthode attend 0-indexed
            
            print(f"Attempting SSH connection to 127.0.0.1:{port}")
            
            # Créer le client SSH
            ssh = paramiko.SSHClient()
            ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
            
            # Essayer de se connecter avec les credentials de l'utilisateur
            connected = False
            try:
                ssh.connect(
                    '127.0.0.1',
                    port=port,
                    username=username,
                    password=password,
                    look_for_keys=False,
                    allow_agent=False,
                    timeout=10
                )
                print(f"Connected as user {username}")
                connected = True
            except Exception as user_auth_error:
                print(f"User auth failed: {str(user_auth_error)}")
                # Fallback vers l'utilisateur vagrant
                try:
                    ssh.connect(
                        '127.0.0.1',
                        port=port,
                        username='vagrant',
                        key_filename=os.path.expanduser('~/.vagrant.d/insecure_private_key'),
                        timeout=10
                    )
                    print("Connected as vagrant user")
                    connected = True
                except Exception as vagrant_auth_error:
                    print(f"Vagrant auth failed: {str(vagrant_auth_error)}")
                    return False, None, f"Authentication failed: {str(vagrant_auth_error)}"
            
            if not connected:
                return False, None, "Failed to establish SSH connection"
            
            # Créer un shell interactif
            channel = ssh.invoke_shell(
                term='xterm',
                width=80,
                height=24
            )
            
            # Mode non-bloquant
            channel.setblocking(0)
            
            # Créer et stocker la session
            session = SSHSession(session_id, username, node_id)
            session.client = ssh
            session.channel = channel
            self.sessions[session_id] = session
            
            # Envoyer un newline initial pour obtenir le prompt
            channel.send('\n')
            
            print("SSH connection and shell established successfully")
            return True, session, ""
            
        except Exception as e:
            error_msg = f"SSH Connection Error: {str(e)}"
            print(error_msg)
            return False, None, error_msg
    
    def get_session(self, session_id: str) -> Optional[SSHSession]:
        """Récupère une session SSH par son ID"""
        return self.sessions.get(session_id)
    
    def send_input(self, session_id: str, data: str) -> tuple[bool, str]:
        """
        Envoie une commande à une session SSH
        
        Returns:
            tuple: (success: bool, error_message: str)
        """
        session = self.get_session(session_id)
        if not session or not session.channel:
            return False, "Session not found or not connected"
        
        try:
            session.channel.send(data)
            return True, ""
        except Exception as e:
            return False, str(e)
    
    def resize_terminal(self, session_id: str, cols: int, rows: int) -> tuple[bool, str]:
        """
        Redimensionne le terminal d'une session
        
        Returns:
            tuple: (success: bool, error_message: str)
        """
        session = self.get_session(session_id)
        if not session or not session.channel:
            return False, "Session not found or not connected"
        
        try:
            session.channel.resize_pty(width=cols, height=rows)
            return True, ""
        except Exception as e:
            return False, str(e)
    
    def close_session(self, session_id: str):
        """Ferme une session SSH"""
        session = self.sessions.pop(session_id, None)
        if session:
            session.close()
    
    def close_all_sessions(self):
        """Ferme toutes les sessions SSH"""
        for session_id in list(self.sessions.keys()):
            self.close_session(session_id)

