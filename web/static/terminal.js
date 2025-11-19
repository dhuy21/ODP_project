const term = new Terminal({
    cursorBlink: true,
    fontSize: 14,
    fontFamily: 'Menlo, Monaco, "Courier New", monospace',
    theme: {
        background: '#1e1e1e',
        foreground: '#ffffff'
    },
    rows: 24,
    cols: 80
});

const fitAddon = new FitAddon.FitAddon();
term.loadAddon(fitAddon);

term.open(document.getElementById('terminal'));

const socket = io({
    transports: ['websocket'],
    upgrade: false
});

socket.on('connect', () => {
    const pathParts = window.location.pathname.split('/');
    const username = pathParts[pathParts.length - 2];
    const node_id = pathParts[pathParts.length - 1];
    
    console.log(`Attempting connection to ${username}-node${node_id}`);
    
    socket.emit('connect_ssh', {
        username: username,
        password: sessionStorage.getItem('password'),
        node_id: node_id
    });
    fitAddon.fit();
});

term.onData(data => {
    socket.emit('input', { data: data });
});

socket.on('output', (data) => {
    console.log('Received output:', data);
    term.write(data.data);
});

socket.on('error', (data) => {
    console.error('Terminal error:', data.message);
    term.write('\r\n\x1b[31mError: ' + data.message + '\x1b[0m\r\n');
});

window.addEventListener('resize', () => {
    fitAddon.fit();
    socket.emit('resize', {
        cols: term.cols,
        rows: term.rows
    });
});

// Debug connection issues
socket.on('connect_error', (error) => {
    console.error('Connection error:', error);
});

socket.on('disconnect', () => {
    console.log('Disconnected from server');
    term.write('\r\n\x1b[31mDisconnected. Attempting to reconnect...\x1b[0m\r\n');
});
