from models.ssh_session import SSHSession

class SSHService:
    """Service for managing SSH sessions"""
    
    def __init__(self):
        self.sessions = {}
    
    def create_session(self, session_id, username, node_name, host, port):
        """Create a new SSH session"""
        session = SSHSession(session_id, username, node_name, host, port)
        self.sessions[session_id] = session
        return session
    
    def get_session(self, session_id):
        """Get an existing SSH session"""
        return self.sessions.get(session_id)
    
    def remove_session(self, session_id):
        """Remove and close an SSH session"""
        if session_id in self.sessions:
            session = self.sessions[session_id]
            session.close()
            del self.sessions[session_id]
            return True
        return False
    
    def disconnect_sessions_by_nodes(self, username, nodes):
        """Disconnect SSH sessions for specific nodes (for specific reservation)"""
        sessions_to_close = []
        node_names = {node.get('name') for node in nodes if node.get('name')}
        
        for session_id, session in self.sessions.items():
            # Only disconnect sessions matching both username AND node_name
            if session.username == username and session.node_name in node_names:
                sessions_to_close.append(session_id)
        
        for session_id in sessions_to_close:
            self.remove_session(session_id)
        
        return len(sessions_to_close)
    
    def disconnect_user_sessions(self, username):
        """Disconnect ALL SSH sessions for a specific user (use disconnect_sessions_by_nodes for specific reservations)"""
        sessions_to_close = []
        
        for session_id, session in self.sessions.items():
            if session.username == username:
                sessions_to_close.append(session_id)
        
        for session_id in sessions_to_close:
            self.remove_session(session_id)
        
        return len(sessions_to_close)
    
    def check_expired_sessions(self):
        """Check and close expired sessions"""
        expired_sessions = []
        
        for session_id, session in self.sessions.items():
            if session.is_expired():
                expired_sessions.append(session_id)
        
        for session_id in expired_sessions:
            self.remove_session(session_id)
        
        return len(expired_sessions)
    
    def get_all_sessions(self):
        """Get all active sessions"""
        return self.sessions
