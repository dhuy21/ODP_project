const term = new Terminal({
  cursorBlink: true,
  fontSize: 14,
  fontFamily: 'Menlo, Monaco, "Courier New", monospace',
  theme: {
    background: "#1e1e1e",
    foreground: "#ffffff",
  },
});

// FitAddon is loaded from CDN as window.FitAddon
const fitAddon = new window.FitAddon.FitAddon();
term.loadAddon(fitAddon);

const terminalElement = document.getElementById("terminal");
if (!terminalElement) {
  console.error("Terminal element not found!");
} else {
  term.open(terminalElement);
}

// Use existing socket from layout.html if available, otherwise create new one
const socket = window.socket || io();
if (!window.socket) {
  window.socket = socket;
}

socket.on("connect", () => {
  const pathParts = window.location.pathname.split("/");
  const username = pathParts[pathParts.length - 2];
  const node_name = pathParts[pathParts.length - 1];

  console.log(`Connecting to ${node_name} for user ${username}`);

  // First, request reservation info from server to get correct password
  // This is needed because user may have multiple reservations with different passwords
  socket.emit("request_reservation_info", {
    username: username,
    node_name: node_name
  });
  
  setTimeout(() => {
    fitAddon.fit();
  }, 100);
});

// Handle reservation info response and connect with password from server
socket.on("reservation_info", (data) => {
  if (data.error) {
    term.write("\r\n\x1b[31mError: " + data.error + "\x1b[0m\r\n");
    if (typeof Notification !== 'undefined') {
      Notification.error(data.error);
    }
    return;
  }

  const reservation_id = data.reservation_id;
  const username = data.username;
  const node_name = data.node_name;
  
  // Get password from server response (decrypted from database)
  // This is secure because password is encrypted in database and only sent over HTTPS
  let password = data.password;
  
  // Fallback to sessionStorage only if server doesn't provide password (backward compatibility)
  if (!password) {
    password = sessionStorage.getItem(`password_${reservation_id}`);
  }
  
  // Fallback to old global password
  if (!password) {
    password = sessionStorage.getItem("password");
  }
  
  // If still no password, try vagrant default
  if (!password) {
    password = "vagrant";
    term.write("\r\n\x1b[33mWarning: No password found, using default 'vagrant'\x1b[0m\r\n");
  }

  console.log(`Connecting with reservation ${reservation_id}`);
  
  socket.emit("connect_ssh", {
    username: username,
    node_name: node_name,
    password: password,
  });
});

term.onData((data) => {
  socket.emit("input", { data: data });
});

socket.on("output", (data) => {
  term.write(data.data);
});

socket.on("error", (data) => {
  term.write("\r\n\x1b[31mError: " + data.message + "\x1b[0m\r\n");
  if (typeof Notification !== 'undefined') {
    Notification.error('Terminal error: ' + data.message);
  }
});

socket.on("force_disconnect", (data) => {
  term.write("\r\n\x1b[33m" + data.message + "\x1b[0m\r\n");
  if (typeof Notification !== 'undefined') {
    Notification.warning(data.message, 3000);
  }
  setTimeout(() => {
    window.close();
  }, 3000);
});

window.addEventListener("resize", () => {
  fitAddon.fit();
  socket.emit("resize", {
    cols: term.cols,
    rows: term.rows,
  });
});
