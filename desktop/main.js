const { app, BrowserWindow } = require("electron");
const { spawn } = require("child_process");
const path = require("path");
const fs = require("fs");

// Sans productName au niveau racine du package.json, Electron nommerait le
// dossier userData d'apres le champ "name" ("jarvis-desktop") plutot que
// "Jarvis" -- on le fixe explicitement pour que le chemin soit previsible.
app.setName("Jarvis");

const DEV_PROJECT_ROOT = path.join(__dirname, "..");

// En dev, le projet Python est le dossier parent de desktop/. Une fois packagee,
// l'app embarque une copie du projet (src/, pyproject.toml, uv.lock) dans ses
// resources : c'est depuis la que "uv run jarvis-server" doit tourner.
function getBackendCwd() {
  return app.isPackaged ? path.join(process.resourcesPath, "backend") : DEV_PROJECT_ROOT;
}

let mainWindow;
let backendProcess;

// La fenetre du backend est cachee (windowsHide), donc c'est le seul endroit
// ou une erreur au demarrage (ex: cle API manquante) reste consultable.
function getBackendLogPath() {
  return path.join(app.getPath("userData"), "backend.log");
}

function startBackend() {
  const logStream = fs.createWriteStream(getBackendLogPath(), { flags: "a" });
  const backendCwd = getBackendCwd();
  // L'app peut etre installee dans un dossier protege (ex: Program Files),
  // ou uv n'a pas le droit de creer son venv. On force l'environnement
  // virtuel dans userData, qui est toujours accessible en ecriture pour
  // l'utilisateur courant, quel que soit le dossier d'installation.
  const venvDir = path.join(app.getPath("userData"), "venv");
  logStream.write(`\n--- demarrage ${new Date().toISOString()} (cwd=${backendCwd}, venv=${venvDir}) ---\n`);

  backendProcess = spawn("uv", ["run", "jarvis-server"], {
    cwd: backendCwd,
    env: { ...process.env, UV_PROJECT_ENVIRONMENT: venvDir },
    windowsHide: true,
  });

  backendProcess.stdout.on("data", (data) => { process.stdout.write(`[jarvis-server] ${data}`); logStream.write(data); });
  backendProcess.stderr.on("data", (data) => { process.stderr.write(`[jarvis-server] ${data}`); logStream.write(data); });
  backendProcess.on("error", (err) => { console.error("Impossible de lancer le backend Jarvis:", err); logStream.write(`ERREUR: ${err}\n`); });
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
