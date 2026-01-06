import paramiko
import time

class SSHSession:
    """SSH Session model"""
    
    def __init__(self, session_id, username, node_name, host='127.0.0.1', port=22):
        self.session_id = session_id
        self.username = username
        self.node_name = node_name
        self.host = host
        self.port = port
        self.client = None
        self.channel = None
        self.reservation_id = None
        self.expires_at = None
        self.connected = False
    
    def connect(self, password=None, default_user='vagrant', default_password='vagrant'):
        """Establish SSH connection"""
        try:
            self.client = paramiko.SSHClient()
            self.client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
            
            # Try user credentials first
            if password:
                try:
                    self.client.connect(
                        self.host,
                        port=self.port,
                        username=self.username,
                        password=password,
                        look_for_keys=False,
                        allow_agent=False,
                        timeout=10
                    )
                    self.connected = True
                    return True
                except Exception as e:
                    print(f"User auth failed: {e}")
            
            # Fall back to default vagrant credentials
            self.client.connect(
                self.host,
                port=self.port,
                username=default_user,
                password=default_password,
                look_for_keys=False,
                allow_agent=False,
                timeout=10
            )
            self.connected = True
            return True
            
        except Exception as e:
            print(f"SSH connection failed: {e}")
            return False
    
    def create_shell(self, term='xterm', width=80, height=24):
        """Create interactive shell"""
        if not self.connected or not self.client:
            return False
        
        try:
            self.channel = self.client.invoke_shell(term=term, width=width, height=height)
            self.channel.setblocking(0)
            
            # Send initial newline
            time.sleep(0.5)
            self.channel.send('\n')
            return True
        except Exception as e:
            print(f"Failed to create shell: {e}")
            return False
    
    def send_input(self, data):
        """Send input to SSH channel"""
        if self.channel:
            self.channel.send(data)
    
    def recv_output(self, buffer_size=4096):
        """Receive output from SSH channel"""
        if self.channel and self.channel.recv_ready():
            return self.channel.recv(buffer_size).decode('utf-8', 'ignore')
        return None
    
    def resize_terminal(self, width, height):
        """Resize terminal"""
        if self.channel:
            try:
                self.channel.resize_pty(width=width, height=height)
            except:
                pass
    
    def is_expired(self):
        """Check if session has expired"""
        if self.expires_at:
            return time.time() > self.expires_at
        return False
    
    def close(self):
        """Close SSH connection"""
        if self.channel:
            try:
                self.channel.close()
            except:
                pass
        
        if self.client:
            try:
                self.client.close()
            except:
                pass
        
        self.connected = False
