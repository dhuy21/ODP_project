from flask import Flask, render_template, request, jsonify, redirect, url_for
from flask_socketio import SocketIO, emit
import paramiko
import yaml
import subprocess
import os
import time

app = Flask(__name__)
socketio = SocketIO(app, async_mode='threading', cors_allowed_origins="*")

ssh_connections = {}

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/provision', methods=['POST'])
def provision():
    data = request.json
    
    # Generate a unique subnet and port range for this user
    username_hash = abs(hash(data['username'])) % 250
    subnet = f"172.28.{username_hash}.0/24"
    base_port = 2200 + (username_hash * 10)
    
    config = {
        'client_id': data['username'],
        'count': int(data['vm_count']),
        'subnet_cidr': subnet,
        'packages': data['packages'].split(','),
        'roles': ['base'],
        'username': data['username'],
        'password': data['password'],
        'base_port': base_port
    }
    
    try:
        current_dir = os.path.dirname(os.path.abspath(__file__))
        project_dir = os.path.dirname(current_dir)
        config_file = os.path.join(project_dir, 'requests', f"{config['client_id']}.yaml")
        script_path = os.path.join(project_dir, 'allocates.sh')
        
        # Clean up existing resources
        cleanup_cmds = [
            f"docker network rm internet-{config['client_id']} 2>/dev/null || true",
            f"docker rm -f $(docker ps -a -q --filter 'label=client={config['client_id']}') 2>/dev/null || true"
        ]
        for cmd in cleanup_cmds:
            subprocess.run(cmd, shell=True, cwd=project_dir)
        
        # Save configuration
        os.makedirs(os.path.dirname(config_file), exist_ok=True)
        with open(config_file, 'w') as f:
            yaml.dump(config, f)
        
        # Run allocates.sh to create containers
        print(f"Creating VMs with {script_path}")
        result = subprocess.run(
            ['/bin/bash', script_path, config_file],
            capture_output=True,
            text=True,
            cwd=project_dir
        )
        
        if result.returncode != 0:
            print(f"Error creating VMs: {result.stderr}")
            return jsonify({
                'status': 'error',
                'message': f"Failed to create VMs: {result.stderr}"
            })
        
        # Wait for containers to be ready
        time.sleep(5)
        
        # Create inventory file for this specific user
        inventory_file = os.path.join(project_dir, 'Ansible', f'inventory_{data["username"]}.ini')
        with open(inventory_file, 'w') as f:
            f.write(f"[{data['username']}]\n")
            for i in range(int(data['vm_count'])):
                port = base_port + i
                f.write(f"{data['username']}-node{i+1} ansible_host=127.0.0.1 ansible_port={port} ansible_user=vagrant ansible_ssh_private_key_file={os.path.expanduser('~/.vagrant.d/insecure_private_key')}\n")
            f.write(f"\n[{data['username']}:vars]\n")
            f.write(f"packages={','.join(config['packages'])}\n")
        
        # Run Ansible playbook
        ansible_cmd = [
            'ansible-playbook',
            '-i', inventory_file,
            os.path.join(project_dir, 'Ansible', 'playbook.yml'),
            '-e', f'username={config["username"]}',
            '-e', f'password={config["password"]}',
            '-e', f'packages={",".join(config["packages"])}',
            '-vv'  # Increase verbosity
        ]
        
        print(f"Running Ansible with command: {' '.join(ansible_cmd)}")
        ansible_result = subprocess.run(
            ansible_cmd,
            capture_output=True,
            text=True,
            cwd=project_dir
        )
        
        if ansible_result.returncode != 0:
            print(f"Ansible Error: {ansible_result.stderr}")
            # Don't fail here, just log the error
            print(f"Proceeding to dashboard despite Ansible error")
        
        # Redirect to dashboard even if Ansible had issues
        return jsonify({
            'status': 'success',
            'redirect': f"/dashboard/{data['username']}/{data['vm_count']}"
        })
        
    except Exception as e:
        print(f"Error in provision: {str(e)}")
        return jsonify({
            'status': 'error',
            'message': str(e)
        })

@app.route('/dashboard/<username>/<int:vm_count>')
def dashboard(username, vm_count):
    return render_template('dashboard.html', username=username, vm_count=vm_count)

@app.route('/terminal/<username>/<node_id>')
def terminal(username, node_id):
    return render_template('terminal.html', username=username, node_id=node_id)

@socketio.on('connect_ssh')
def handle_ssh_connection(data):
    try:
        print(f"SSH connection request received: {data}")
        ssh = paramiko.SSHClient()
        ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        
        username_hash = abs(hash(data['username'])) % 250
        base_port = 2200 + (username_hash * 10)
        port = base_port + int(data['node_id']) - 1
        
        print(f"Attempting SSH connection to 127.0.0.1:{port}")
        
        try:
            # First try with the provided user credentials
            ssh.connect(
                '127.0.0.1',
                port=port,
                username=data['username'],
                password=data['password'],
                look_for_keys=False,
                allow_agent=False,
                timeout=10
            )
            print(f"Connected as user {data['username']}")
        except Exception as user_auth_error:
            print(f"User auth failed: {str(user_auth_error)}")
            # Fall back to vagrant user
            try:
                ssh.connect(
                    '127.0.0.1',
                    port=port,
                    username='vagrant',
                    key_filename=os.path.expanduser('~/.vagrant.d/insecure_private_key'),
                    timeout=10
                )
                print("Connected as vagrant user")
            except Exception as vagrant_auth_error:
                print(f"Vagrant auth failed: {str(vagrant_auth_error)}")
                raise

        # Get interactive shell
        channel = ssh.invoke_shell(
            term='xterm',
            width=80,
            height=24
        )
        
        # Important: Set non-blocking mode
        channel.setblocking(0)
        
        # Store the connection
        session_id = request.sid
        ssh_connections[session_id] = {
            'client': ssh,
            'channel': channel
        }
        
        # Send initial newline to get prompt
        channel.send('\n')
        
        def read_output():
            while True:
                if session_id not in ssh_connections:
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
        
        socketio.start_background_task(read_output)
        print("SSH connection and shell established successfully")
        
    except Exception as e:
        print(f"SSH Connection Error: {str(e)}")
        emit('error', {'message': str(e)})

@socketio.on('input')
def handle_input(data):
    session_id = request.sid
    if session_id in ssh_connections:
        channel = ssh_connections[session_id]['channel']
        try:
            channel.send(data['data'])
        except Exception as e:
            print(f"Error sending input: {str(e)}")
            emit('error', {'message': str(e)})

@socketio.on('resize')
def handle_resize(data):
    session_id = request.sid
    if session_id in ssh_connections:
        channel = ssh_connections[session_id]['channel']
        try:
            channel.resize_pty(width=data['cols'], height=data['rows'])
        except Exception as e:
            emit('error', {'message': str(e)})

@socketio.on('disconnect')
def handle_disconnect():
    session_id = request.sid
    if session_id in ssh_connections:
        ssh_connections[session_id]['client'].close()
        del ssh_connections[session_id]

@app.template_filter('hash')
def hash_filter(s):
    return abs(hash(s)) % 250

if __name__ == '__main__':
    socketio.run(app, debug=True, host='0.0.0.0', port=5001)