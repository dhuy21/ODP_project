"""
Encryption utilities for secure password storage
Uses Fernet (symmetric encryption) from cryptography library
"""
from cryptography.fernet import Fernet
import os
import base64
import hashlib

class PasswordEncryption:
    """Handle password encryption/decryption for VM passwords"""
    
    def __init__(self):
        # Get encryption key from environment or generate one
        # In production, this should be stored securely (env variable, secrets manager)
        key = os.environ.get('ENCRYPTION_KEY')
        
        if not key:
            # Generate key from SECRET_KEY for consistency
            secret_key = os.environ.get('SECRET_KEY', 'default-secret-key-change-in-production')
            # Derive a valid Fernet key from SECRET_KEY
            key_material = hashlib.sha256(secret_key.encode()).digest()
            key = base64.urlsafe_b64encode(key_material)
        else:
            key = key.encode()
        
        self.cipher = Fernet(key)
    
    def encrypt(self, plaintext):
        """
        Encrypt plaintext password
        
        Args:
            plaintext (str): Plain password
            
        Returns:
            str: Encrypted password (base64 encoded)
        """
        if not plaintext:
            return None
        
        encrypted_bytes = self.cipher.encrypt(plaintext.encode())
        return encrypted_bytes.decode('utf-8')
    
    def decrypt(self, encrypted_text):
        """
        Decrypt encrypted password
        
        Args:
            encrypted_text (str): Encrypted password
            
        Returns:
            str: Decrypted password
        """
        if not encrypted_text:
            return None
        
        try:
            decrypted_bytes = self.cipher.decrypt(encrypted_text.encode())
            return decrypted_bytes.decode('utf-8')
        except Exception as e:
            print(f"Error decrypting password: {e}")
            return None

