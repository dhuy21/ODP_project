from flask import Flask, render_template, request, jsonify
from flask_socketio import SocketIO, emit
import paramiko
import yaml
import subprocess
import os
import time

app = Flask(__name__)
socketio = SocketIO(app, async_mode='threading', cors_allowed_origins="*")

ssh_connections = {}
client_allocations = {}  # Track client allocations

@app.route('/')
def index():
    # Get pool status
    try:
        project_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        result = subprocess.run(
            ['./pool_manager.sh', 'status'],
            capture_output=True,
            text=True,
            cwd=project_dir
        )
        
        # Count containers with status=free
        free_count = 0
        for line in result.stdout.split('\n'):
            if 'free' in line and 'pool-node-' in line:
                free_count += 1
        
        available = free_count
    except Exception as e:
        print(f"Error getting pool status: {e}")
        available = 0
    
    return render_template('index.html', available_containers=available)

@app.route('/pool/status', methods=['GET'])
def pool_status():
    """Get current pool status"""
    try:
        project_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        result = subprocess.run(
            ['./pool_manager.sh', 'status'],
            capture_output=True,
            text=True,
            cwd=project_dir
        )
        
        # Count containers more accurately
        free_count = 0
        allocated_count = 0
        
        for line in result.stdout.split('\n'):
            if 'pool-node-' in line:
                if 'free' in line and 'allocated' not in line:
                    free_count += 1
                elif 'allocated' in line:
                    allocated_count += 1
        
        return jsonify({
            'status': 'success',
            'total': 10,
            'free': free_count,
            'allocated': allocated_count
        })
    except Exception as e:
        print(f"Error: {e}")
        return jsonify({'status': 'error', 'message': str(e)})

@app.route('/provision', methods=['POST'])
def provision():
    data = request.json
    username = data['username']
    password = data['password']
    vm_count = int(data['vm_count'])
    packages = data['packages'].split(',') if data['packages'] else []
    
    try:
        project_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        
        # Check available containers first
        status_result = subprocess.run(
            ['./pool_manager.sh', 'status'],
            capture_output=True,
            text=True,
            cwd=project_dir
        )
        
        free_count = sum(1 for line in status_result.stdout.split('\n') 
                        if 'free' in line and 'pool-node-' in line and 'allocated' not in line)
        
        if free_count < vm_count:
            return jsonify({
                'status': 'error',
                'message': f'Not enough containers available. You need {vm_count} but only {free_count} are free.'
            })
        
        # Allocate containers from pool
        result = subprocess.run(
            ['./pool_manager.sh', 'allocate', username, str(vm_count), username, password],
            capture_output=True,
            text=True,
            cwd=project_dir
        )
        
        print(f"Allocation output: {result.stdout}")
        print(f"Allocation errors: {result.stderr}")
        
        if result.returncode != 0:
            return jsonify({
                'status': 'error',
                'message': 'Failed to allocate containers'
            })
        
        # Parse allocated nodes
        allocated_nodes = []
        for line in result.stdout.split('\n'):
            if 'Allocated' in line:
                # Parse: "   - Allocated pool-node-1 (172.30.0.11:3000)"
                parts = line.strip().split()
                if len(parts) >= 4:
                    node_name = parts[2]  # pool-node-1
                    ip_port = parts[3].strip('()')  # 172.30.0.11:3000
                    if ':' in ip_port:
                        ip, port = ip_port.split(':')
                        
                        allocated_nodes.append({
                            'name': node_name,
                            'port': port,
                            'ip': ip
                        })
        
        if not allocated_nodes:
            return jsonify({
                'status': 'error',
                'message': 'Failed to parse allocated containers'
            })
        
        # Wait for containers to be ready
        time.sleep(2)
        
        # Create inventory for Ansible
        inventory_file = os.path.join(project_dir, 'Ansible', f'inventory_{username}.ini')
        with open(inventory_file, 'w') as f:
            f.write(f"[{username}]\n")
            for node in allocated_nodes:
                f.write(f"{node['name']} ansible_host=127.0.0.1 ansible_port={node['port']} ")
                f.write(f"ansible_user=vagrant ansible_ssh_private_key_file={os.path.expanduser('~/.vagrant.d/insecure_private_key')}\n")
            f.write(f"\n[{username}:vars]\n")
            f.write(f"username={username}\n")
            f.write(f"password={password}\n")
            if packages:
                f.write(f"packages={','.join(packages)}\n")
        
        # Run Ansible to configure if packages or user requested
        if packages or username or password:
            ansible_cmd = [
                'ansible-playbook',
                '-i', inventory_file,
                'Ansible/playbook.yml'
            ]
            
            ansible_result = subprocess.run(
                ansible_cmd,
                capture_output=True,
                text=True,
                cwd=project_dir
            )
            
            if ansible_result.returncode != 0:
                print(f"Ansible warning: {ansible_result.stderr}")
        
        # Store allocation info
        client_allocations[username] = {
            'nodes': allocated_nodes,
            'username': username,
            'password': password
        }
        
        return jsonify({
            'status': 'success',
            'redirect': f"/dashboard/{username}/{vm_count}"
        })
        
    except Exception as e:
        print(f"Error in provision: {str(e)}")
        import traceback
        traceback.print_exc()
        return jsonify({
            'status': 'error',
            'message': str(e)
        })

@app.route('/dashboard/<username>/<int:vm_count>')
def dashboard(username, vm_count):
    allocation = client_allocations.get(username, {})
    nodes = allocation.get('nodes', [])
    
    return render_template('dashboard.html', 
                         username=username, 
                         vm_count=vm_count,
                         nodes=nodes)

@app.route('/release/<username>', methods=['POST'])
def release_resources(username):
    """Release client's resources back to pool"""
    try:
        project_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        
        result = subprocess.run(
            ['./pool_manager.sh', 'release', username],
            capture_output=True,
            text=True,
            cwd=project_dir
        )
        
        if username in client_allocations:
            del client_allocations[username]
        
        return jsonify({
            'status': 'success',
            'message': 'Resources released'
        })
    except Exception as e:
        return jsonify({
            'status': 'error',
            'message': str(e)
        })

@app.route('/terminal/<username>/<node_name>')
def terminal(username, node_name):
    return render_template('terminal.html', username=username, node_name=node_name)

@socketio.on('connect_ssh')
def handle_ssh_connection(data):
    try:
        ssh = paramiko.SSHClient()
        ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        
        username = data['username']
        node_name = data['node_name']
        
        # Find node port
        allocation = client_allocations.get(username, {})
        node = next((n for n in allocation.get('nodes', []) if n['name'] == node_name), None)
        
        if not node:
            emit('error', {'message': 'Node not found'})
            return
        
        port = int(node['port'])
        
        print(f"Connecting to {node_name} on port {port}")
        
        # Try with user credentials
        connected = False
        if data.get('password'):
            try:
                ssh.connect(
                    '127.0.0.1',
                    port=port,
                    username=username,
                    password=data['password'],
                    look_for_keys=False,
                    allow_agent=False,
                    timeout=10
                )
                connected = True
                print(f"Connected as {username}")
            except Exception as e:
                print(f"User auth failed: {e}")
        
        # Fallback to vagrant
        if not connected:
            ssh.connect(
                '127.0.0.1',
                port=port,
                username='vagrant',
                password='vagrant',
                look_for_keys=False,
                allow_agent=False,
                timeout=10
            )
            print("Connected as vagrant")
        
        channel = ssh.invoke_shell(term='xterm', width=80, height=24)
        channel.setblocking(0)
        
        session_id = request.sid
        ssh_connections[session_id] = {
            'client': ssh,
            'channel': channel
        }
        
        time.sleep(0.5)
        channel.send('\n')
        
        def read_output():
            while True:
                if session_id not in ssh_connections:
                    break
                try:
                    if channel.recv_ready():
                        output = channel.recv(4096).decode('utf-8', 'ignore')
                        socketio.emit('output', {'data': output}, room=session_id)
                except Exception as e:
                    print(f"Read error: {e}")
                    break
                socketio.sleep(0.01)
        
        socketio.start_background_task(read_output)
        
    except Exception as e:
        print(f"SSH Error: {e}")
        emit('error', {'message': str(e)})

@socketio.on('input')
def handle_input(data):
    session_id = request.sid
    if session_id in ssh_connections:
        try:
            ssh_connections[session_id]['channel'].send(data['data'])
        except Exception as e:
            emit('error', {'message': str(e)})

@socketio.on('resize')
def handle_resize(data):
    session_id = request.sid
    if session_id in ssh_connections:
        try:
            ssh_connections[session_id]['channel'].resize_pty(
                width=data['cols'], 
                height=data['rows']
            )
        except Exception as e:
            pass

@socketio.on('disconnect')
def handle_disconnect():
    session_id = request.sid
    if session_id in ssh_connections:
        try:
            ssh_connections[session_id]['client'].close()
        except:
            pass
        del ssh_connections[session_id]

if __name__ == '__main__':
    socketio.run(app, debug=True, host='0.0.0.0', port=5001)
