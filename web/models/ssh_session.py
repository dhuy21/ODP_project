"""
Modèle pour gérer les sessions SSH
"""
import paramiko
from typing import Optional

class SSHSession:
    """Classe représentant une session SSH active"""
    
    def __init__(self, session_id: str, username: str, node_id: int):
        self.session_id = session_id
        self.username = username
        self.node_id = node_id
        self.client: Optional[paramiko.SSHClient] = None
        self.channel: Optional[paramiko.Channel] = None
    
    def is_connected(self) -> bool:
        """Vérifie si la session est connectée"""
        return self.client is not None and self.channel is not None
    
    def close(self):
        """Ferme la connexion SSH"""
        if self.client:
            try:
                self.client.close()
            except:
                pass
        self.client = None
        self.channel = None
