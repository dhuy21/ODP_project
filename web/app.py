from flask import Flask, render_template, request, jsonify, session, redirect, url_for
from flask_socketio import SocketIO, emit
import paramiko
import yaml
import subprocess
import os
import time
import uuid
from functools import wraps

# Import user database
import sys
sys.path.append(os.path.dirname(__file__))
from models.user import UserDatabase

app = Flask(__name__)
app.secret_key = 'your-secret-key-change-this-in-production' # a faire après 
socketio = SocketIO(app, async_mode='threading', cors_allowed_origins="*")

ssh_connections = {}
client_allocations = {}
user_db = UserDatabase()

# Login required decorator
def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'username' not in session:
            return redirect(url_for('login'))
        return f(*args, **kwargs)
    return decorated_function

@app.route('/')
def index():
    if 'username' in session:
        return redirect(url_for('dashboard_home'))
    return redirect(url_for('login'))

@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'GET':
        return render_template('register.html')
    
    data = request.json
    result = user_db.register_user(
        data['username'],
        data['email'],
        data['password']
    )
    
    return jsonify(result)

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'GET':
        return render_template('login.html')
    
    data = request.json
    result = user_db.login_user(data['username'], data['password'])
    
    if result['status'] == 'success':
        session['username'] = result['user']
        session['logged_in'] = True
    
    return jsonify(result)

@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('login'))

@app.route('/dashboard')
@login_required
def dashboard_home():
    username = session['username']
    
    # Get pool status
    try:
        project_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        
        # Run health check
        subprocess.run(
            ['./pool_manager.sh', 'health-check'],
            capture_output=True,
            text=True,
            cwd=project_dir
        )
        
        result = subprocess.run(
            ['./pool_manager.sh', 'status'],
            capture_output=True,
            text=True,
            cwd=project_dir
        )
        
        free_count = 0
        for line in result.stdout.split('\n'):
            if 'free' in line and 'pool-node-' in line and 'allocated' not in line and 'error' not in line:
                free_count += 1
        
        available = free_count
    except Exception as e:
        print(f"Error getting pool status: {e}")
        available = 0
    
    # Get user's reservations
    reservations = user_db.get_user_reservations(username)
    
    # Check health of active reservations
    active_reservations = []
    for r in reservations:
        if r.get('status') == 'active':
            # Check if containers still exist
            if not check_reservation_health(username, r):
                # Mark as deleted
                user_db.update_reservation_status(username, r['id'], 'deleted')
                r['status'] = 'deleted'
            else:
                active_reservations.append(r)
    
    return render_template('dashboard_home.html', 
                         username=username,
                         available_containers=available,
                         reservations=reservations,
                         active_reservations=active_reservations)

@app.route('/pool/status', methods=['GET'])
@login_required
def pool_status():
    try:
        project_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        result = subprocess.run(
            ['./pool_manager.sh', 'status'],
            capture_output=True,
            text=True,
            cwd=project_dir
        )
        
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
        return jsonify({'status': 'error', 'message': str(e)})

@app.route('/provision', methods=['POST'])
@login_required
def provision():
    data = request.json
    username = session['username']
    vm_password = data['password']
    vm_count = int(data['vm_count'])
    duration = int(data.get('duration', 60))
    packages = data.get('packages', '').strip()
    
    try:
        project_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        
        # Check and release expired containers first
        subprocess.run(
            ['./pool_manager.sh', 'check-expired'],
            capture_output=True,
            text=True,
            cwd=project_dir,
            timeout=5
        )
        
        # Check available containers
        status_result = subprocess.run(
            ['./pool_manager.sh', 'status'],
            capture_output=True,
            text=True,
            cwd=project_dir,
            timeout=5
        )
        
        free_count = sum(1 for line in status_result.stdout.split('\n') 
                        if 'free' in line and 'pool-node-' in line and 'allocated' not in line)
        
        if free_count < vm_count:
            return jsonify({
                'status': 'error',
                'message': f'Not enough containers available. You need {vm_count} but only {free_count} are free.'
            })
        
        # Generate unique reservation ID
        reservation_id = str(uuid.uuid4())
        
        print(f"[DEBUG] Allocating {vm_count} containers for {username}")
        
        # Allocate containers (pool_manager.sh creates the user)
        result = subprocess.run(
            ['./pool_manager.sh', 'allocate', username, str(vm_count), username, vm_password, str(duration)],
            capture_output=True,
            text=True,
            cwd=project_dir,
            timeout=30
        )
        
        print(f"[DEBUG] Allocation stdout: {result.stdout}")
        if result.stderr:
            print(f"[DEBUG] Allocation stderr: {result.stderr}")
        
        if result.returncode != 0:
            return jsonify({
                'status': 'error',
                'message': f'Failed to allocate containers: {result.stderr}'
            })
        
        # Parse allocated nodes
        allocated_nodes = []
        
        for line in result.stdout.split('\n'):
            if 'Allocated' in line and '(' in line:
                try:
                    parts = line.strip().split()
                    node_name = parts[2]  # pool-node-X
                    ip_port = parts[3].strip('()')  # 172.30.0.11:3000
                    
                    if ':' in ip_port:
                        ip, port = ip_port.split(':')
                        allocated_nodes.append({
                            'name': node_name,
                            'port': port,
                            'ip': ip
                        })
                        print(f"[DEBUG] Parsed node: {node_name} at {ip}:{port}")
                except Exception as e:
                    print(f"[DEBUG] Failed to parse line: {line} - {e}")
                    continue
        
        if not allocated_nodes:
            return jsonify({
                'status': 'error',
                'message': 'Failed to parse allocated containers. Check server logs.'
            })
        
        print(f"[DEBUG] Successfully allocated {len(allocated_nodes)} nodes")
        
        # Install packages in background ONLY if packages specified
        if packages:
            package_list = [p.strip() for p in packages.split(',') if p.strip()]
            
            if package_list:
                print(f"[DEBUG] Will install packages: {package_list}")
                
                # Create inventory for Ansible
                inventory_file = os.path.join(project_dir, 'Ansible', f'inventory_{username}.ini')
                with open(inventory_file, 'w') as f:
                    f.write(f"[{username}]\n")
                    for node in allocated_nodes:
                        f.write(f"{node['name']} ansible_host=127.0.0.1 ansible_port={node['port']} ")
                        f.write(f"ansible_user={username} ansible_ssh_pass={vm_password} ")
                        f.write(f"ansible_become_pass={vm_password}\n")
                    f.write(f"\n[{username}:vars]\n")
                    f.write(f"ansible_ssh_common_args='-o StrictHostKeyChecking=no'\n")
                    f.write(f"packages={','.join(package_list)}\n")
                
                # Run Ansible in background (completely non-blocking)
                def run_ansible_background():
                    try:
                        print(f"[ANSIBLE] Starting package installation for {username}")
                        ansible_result = subprocess.run(
                            ['ansible-playbook', '-i', inventory_file, 'Ansible/playbook.yml'],
                            capture_output=True,
                            text=True,
                            cwd=project_dir,
                            timeout=300  # 5 minutes max
                        )
                        if ansible_result.returncode == 0:
                            print(f"[ANSIBLE] Successfully installed packages for {username}")
                        else:
                            print(f"[ANSIBLE] Failed to install packages: {ansible_result.stderr}")
                    except Exception as e:
                        print(f"[ANSIBLE] Error: {e}")
                
                import threading
                threading.Thread(target=run_ansible_background, daemon=True).start()
        
        # Save reservation to database
        reservation_data = {
            'id': reservation_id,
            'created_at': time.time(),
            'expires_at': time.time() + (duration * 60),
            'duration': duration,
            'vm_count': vm_count,
            'nodes': allocated_nodes,
            'packages': package_list if packages else [],
            'status': 'active'
        }
        
        user_db.add_reservation(username, reservation_data)
        
        # Store allocation info in memory
        client_allocations[username] = {
            'nodes': allocated_nodes,
            'username': username,
            'password': vm_password,
            'duration': duration,
            'reservation_id': reservation_id
        }
        
        print(f"[DEBUG] Reservation {reservation_id} created successfully")
        
        return jsonify({
            'status': 'success',
            'redirect': f"/reservation/{reservation_id}"
        })
        
    except subprocess.TimeoutExpired:
        print("[ERROR] Allocation timeout")
        return jsonify({
            'status': 'error',
            'message': 'Allocation timeout - the system is busy, please try again'
        })
    except Exception as e:
        print(f"[ERROR] Provision failed: {str(e)}")
        import traceback
        traceback.print_exc()
        return jsonify({
            'status': 'error',
            'message': f'Internal error: {str(e)}'
        })

@app.route('/reservation/<reservation_id>')
@login_required
def view_reservation(reservation_id):
    username = session['username']
    reservations = user_db.get_user_reservations(username)
    
    reservation = next((r for r in reservations if r['id'] == reservation_id), None)
    
    if not reservation:
        return redirect(url_for('dashboard_home'))
    
    return render_template('reservation_detail.html',
                         username=username,
                         reservation=reservation)

@app.route('/release/<username>', methods=['POST'])
@login_required
def release_resources(username):
    if session['username'] != username:
        return jsonify({
            'status': 'error',
            'message': 'Unauthorized'
        })
    
    try:
        data = request.json
        reservation_id = data.get('reservation_id')
        
        project_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        
        result = subprocess.run(
            ['./pool_manager.sh', 'release', username],
            capture_output=True,
            text=True,
            cwd=project_dir
        )
        
        # Update reservation status
        if reservation_id:
            user_db.update_reservation_status(username, reservation_id, 'released')
        
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
@login_required
def terminal(username, node_name):
    if session['username'] != username:
        return redirect(url_for('dashboard_home'))
    
    return render_template('terminal.html', username=username, node_name=node_name)

@socketio.on('connect_ssh')
def handle_ssh_connection(data):
    try:
        ssh = paramiko.SSHClient()
        ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        
        username = data['username']
        node_name = data['node_name']
        
        # Check if user is authorized
        if 'username' not in session or session['username'] != username:
            emit('error', {'message': 'Unauthorized'})
            return
        
        # Find node port
        allocation = client_allocations.get(username, {})
        node = next((n for n in allocation.get('nodes', []) if n['name'] == node_name), None)
        
        if not node:
            emit('error', {'message': 'Node not found'})
            return
        
        port = int(node['port'])
        
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
            except Exception as e:
                print(f"User auth failed: {e}")
        
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
                    break
                socketio.sleep(0.01)
        
        socketio.start_background_task(read_output)
        
    except Exception as e:
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
        except:
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

@app.template_filter('timestamp_to_date')
def timestamp_to_date(timestamp):
    from datetime import datetime
    return datetime.fromtimestamp(timestamp).strftime('%Y-%m-%d %H:%M:%S')

def check_reservation_health(username, reservation):
    """Check if reservation's containers are still running"""
    try:
        project_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        
        for node in reservation.get('nodes', []):
            node_name = node['name']
            
            # Check if container is running
            result = subprocess.run(
                ['docker', 'ps', '-q', '-f', f'name=^{node_name}$'],
                capture_output=True,
                text=True,
                cwd=project_dir
            )
            
            if not result.stdout.strip():
                # Container not running - mark reservation as error
                return False
        
        return True
    except:
        return False

if __name__ == '__main__':
    socketio.run(app, debug=True, host='0.0.0.0', port=5001)