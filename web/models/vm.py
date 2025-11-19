"""
Modèle pour la configuration des VMs
"""

from . import db
from datetime import datetime, timezone


class VM(db.Model):
    """Classe représentant la configuration d'une VM"""
    id = db.Column(db.Integer, primary_key=True)
    client_id = db.Column(db.String(80), nullable=False)
    username = db.Column(db.String(80), nullable=False)
    password = db.Column(db.String(200), nullable=False)
    count = db.Column(db.Integer, nullable=False)
    packages = db.Column(db.String(200), nullable=False)
    roles = db.Column(db.String(200), nullable=False, default='base')
    username_hash = db.Column(db.Integer, nullable=False)
    subnet_cidr = db.Column(db.String(200), nullable=False)
    base_port = db.Column(db.Integer, nullable=False)
    created_at = db.Column(db.DateTime, nullable=False, default=datetime.now(timezone.utc))
    
    def __init__(self, username, count, packages, password, **kwargs):
        """Initialise une VM avec calcul automatique des configurations réseau"""
        super(VM, self).__init__(**kwargs)
        
        self.username = username
        self.client_id = username
        self.password = password
        self.count = int(count)
        
        # Parser les packages
        if isinstance(packages, str):
            self.packages = packages
        elif isinstance(packages, list):
            self.packages = ','.join(packages)
        else:
            self.packages = str(packages)
        
        # Calcul automatique
        self.username_hash = abs(hash(username)) % 250
        self.subnet_cidr = self._generate_subnet()
        self.base_port = self._generate_base_port()
        self.roles = 'base'
    
    def _parse_packages(self):
        """Parse les packages depuis une string"""
        if self.packages:
            return [pkg.strip() for pkg in self.packages.split(',') if pkg.strip()]
        return []
    
    def _generate_subnet(self):
        """Génère un subnet unique basé sur le hash du username"""
        return f"172.28.{self.username_hash}.0/24"
    
    def _generate_base_port(self):
        """Génère un port de base unique pour ce user"""
        return 2200 + (self.username_hash * 10)
    
    def get_port_for_node(self, node_index):
        """Retourne le port SSH pour un node spécifique (0-indexed)"""
        return self.base_port + node_index
    
    def to_dict(self):
        """Convertit la configuration en dictionnaire pour YAML"""
        return {
            'client_id': self.client_id,
            'count': self.count,
            'subnet_cidr': self.subnet_cidr,
            'packages': self._parse_packages(),
            'roles': [self.roles] if isinstance(self.roles, str) else self.roles,
            'username': self.username,
            'password': self.password,
            'base_port': self.base_port
        }
