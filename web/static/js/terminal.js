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

const socket = io();

socket.on("connect", () => {
  const pathParts = window.location.pathname.split("/");
  const username = pathParts[pathParts.length - 2];
  const node_name = pathParts[pathParts.length - 1];

  console.log(`Connecting to ${node_name} for user ${username}`);

  // Get password from sessionStorage or use default vagrant password
  let password = sessionStorage.getItem("password");
  
  // If no password, try vagrant default
  if (!password) {
    password = "vagrant";  // Default vagrant password
  }

  socket.emit("connect_ssh", {
    username: username,
    node_name: node_name,
    password: password,
  });
  
  setTimeout(() => {
    fitAddon.fit();
  }, 100);
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
