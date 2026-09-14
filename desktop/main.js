const { app, BrowserWindow } = require("electron");
const { spawn } = require("child_process");
const path = require("path");

const DEV_PROJECT_ROOT = path.join(__dirname, "..");

// En dev, le projet Python est le dossier parent de desktop/. Une fois packagee,
// l'app embarque une copie du projet (src/, pyproject.toml, uv.lock) dans ses
// resources : c'est depuis la que "uv run jarvis-server" doit tourner.
function getBackendCwd() {
  return app.isPackaged ? path.join(process.resourcesPath, "backend") : DEV_PROJECT_ROOT;
}

let mainWindow;
let backendProcess;

function startBackend() {
  backendProcess = spawn("uv", ["run", "jarvis-server"], {
    cwd: getBackendCwd(),
    env: process.env,
    windowsHide: true,
  });

  backendProcess.stdout.on("data", (data) => process.stdout.write(`[jarvis-server] ${data}`));
  backendProcess.stderr.on("data", (data) => process.stderr.write(`[jarvis-server] ${data}`));
  backendProcess.on("error", (err) => console.error("Impossible de lancer le backend Jarvis:", err));
}

function createWindow() {
  mainWindow = new BrowserWindow({
    width: 1080,
    height: 720,
    minWidth: 760,
    minHeight: 480,
    backgroundColor: "#00000000",
    titleBarStyle: "hiddenInset",
    trafficLightPosition: { x: 18, y: 18 },
    vibrancy: "sidebar",
    webPreferences: {
      contextIsolation: true,
      nodeIntegration: false,
      sandbox: true,
    },
  });

  mainWindow.loadFile(path.join(__dirname, "renderer", "index.html"));
}

app.whenReady().then(() => {
  startBackend();
  createWindow();

  app.on("activate", () => {
    if (BrowserWindow.getAllWindows().length === 0) createWindow();
  });
});

app.on("window-all-closed", () => {
  if (process.platform !== "darwin") app.quit();
});

app.on("before-quit", () => {
  if (backendProcess) backendProcess.kill();
});
