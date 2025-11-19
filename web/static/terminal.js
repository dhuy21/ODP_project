const term = new Terminal({
    cursorBlink: true,
    fontSize: 14,
    fontFamily: 'Menlo, Monaco, "Courier New", monospace',
    theme: {
        background: '#1e1e1e',
        foreground: '#ffffff'
    }
});

const fitAddon = new FitAddon.FitAddon();
term.loadAddon(fitAddon);

term.open(document.getElementById('terminal'));
fitAddon.fit();

const socket = io();

socket.on('connect', () => {
    const pathParts = window.location.pathname.split('/');
    const username = pathParts[pathParts.length - 2];
    const node_name = pathParts[pathParts.length - 1];
    
    console.log(`Connecting to ${node_name} for user ${username}`);
    
    socket.emit('connect_ssh', {
        username: username,
        node_name: node_name,
        password: sessionStorage.getItem('password')
    });
});

term.onData(data => {
    socket.emit('input', { data: data });
});

socket.on('output', (data) => {
    term.write(data.data);
});

socket.on('error', (data) => {
    term.write('\r\n\x1b[31m' + data.message + '\x1b[0m\r\n');
});

window.addEventListener('resize', () => {
    fitAddon.fit();
    socket.emit('resize', {
        cols: term.cols,
        rows: term.rows
    });
});
