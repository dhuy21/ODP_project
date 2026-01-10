import time
import uuid

class VM:
    """Virtual Machine model"""
    
    def __init__(self, name, ip, port, username):
        self.name = name
        self.ip = ip
        self.port = port
        self.username = username
    
    def to_dict(self):
        return {
            'name': self.name,
            'ip': self.ip,
            'port': self.port
        }

class Reservation:
    """Reservation model"""
    
    def __init__(self, username, vm_count, duration, packages=None):
        self.id = str(uuid.uuid4())
        self.username = username
        self.vm_count = vm_count
        self.duration = duration
        self.packages = packages or []
        self.nodes = []
        self.created_at = time.time()
        self.expires_at = time.time() + (duration * 60)
        self.status = 'active'
    
    def add_node(self, node):
        """Add a VM node to this reservation"""
        self.nodes.append(node)
    
    def is_expired(self):
        """Check if reservation has expired"""
        return time.time() > self.expires_at
    
    def mark_expired(self):
        """Mark reservation as expired"""
        self.status = 'expired'
    
    def mark_released(self):
        """Mark reservation as released"""
        self.status = 'released'
    
    def to_dict(self):
        """Convert to dictionary for JSON serialization"""
        return {
            'id': self.id,
            'username': self.username,
            'vm_count': self.vm_count,
            'duration': self.duration,
            'packages': self.packages,
            'nodes': [node.to_dict() if hasattr(node, 'to_dict') else node for node in self.nodes],
            'created_at': self.created_at,
            'expires_at': self.expires_at,
            'status': self.status
        }
    
    @staticmethod
    def from_dict(data):
        """Create Reservation from dictionary"""
        reservation = Reservation(
            username=data['username'],
            vm_count=data['vm_count'],
            duration=data['duration'],
            packages=data.get('packages', [])
        )
        reservation.id = data['id']
        reservation.nodes = data.get('nodes', [])
        reservation.created_at = data['created_at']
        reservation.expires_at = data['expires_at']
        reservation.status = data['status']
        return reservation
