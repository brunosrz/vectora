/**
 * Vectora Desktop — main process (T.12.5).
 *
 * Spawn do binário Nuitka (`vectora-core`) como sidecar com porta efêmera,
 * carrega o frontend embutido via `BrowserWindow.loadURL("http://127.0.0.1:<port>")`
 * e gerencia o ciclo de vida (mata o backend quando a última janela fecha).
 *
 * Não roda lógica de negócio — é só a casca nativa.
 */

import { spawn, ChildProcess } from "child_process";
import { app, BrowserWindow, dialog, shell } from "electron";
import { autoUpdater } from "electron-updater";
import * as net from "net";
import * as path from "path";
import treeKill from "tree-kill";

let backend: ChildProcess | null = null;
let backendPort: number | null = null;
let mainWindow: BrowserWindow | null = null;

/** Pega uma porta TCP livre — backend Vectora também faz isso, mas precisamos
 *  saber qual porta passar para o BrowserWindow. */
function getFreePort(): Promise<number> {
  return new Promise((resolve, reject) => {
    const srv = net.createServer();
    srv.listen(0, "127.0.0.1", () => {
      const address = srv.address();
      if (address && typeof address === "object") {
        const port = address.port;
        srv.close(() => resolve(port));
      } else {
        srv.close();
        reject(new Error("Sem porta livre."));
      }
    });
  });
}

/** Path do binário Nuitka empacotado dentro do .app/.exe. */
function backendPath(): string {
  // electron-builder coloca extraResources em `resources/`.
  const resources = process.resourcesPath || path.join(__dirname, "..");
  const exe = process.platform === "win32" ? "vectora.exe" : "vectora";
  return path.join(resources, "vectora-core", exe);
}

async function startBackend(): Promise<void> {
  backendPort = await getFreePort();
  const env = {
    ...process.env,
    VECTORA_PORT: String(backendPort),
    VECTORA_DESKTOP: "1",
  };
  backend = spawn(backendPath(), ["server", "chat"], {
    env,
    stdio: ["ignore", "pipe", "pipe"],
  });
  backend.stdout?.on("data", (b) => process.stdout.write(`[backend] ${b}`));
  backend.stderr?.on("data", (b) => process.stderr.write(`[backend] ${b}`));
  backend.on("exit", (code) => {
    if (code !== 0 && mainWindow) {
      dialog.showErrorBox(
        "Vectora encerrou inesperadamente",
        `Backend retornou código ${code}. Reinicie o app.`,
      );
    }
  });
}

async function waitForBackend(port: number, timeoutMs = 30_000): Promise<void> {
  const deadline = Date.now() + timeoutMs;
  while (Date.now() < deadline) {
    try {
      const ok = await fetch(`http://127.0.0.1:${port}/health`);
      if (ok.ok) return;
    } catch {
      // ignora — backend ainda subindo
    }
    await new Promise((r) => setTimeout(r, 300));
  }
  throw new Error("Backend não respondeu em 30s.");
}

function createWindow(): void {
  if (backendPort === null) throw new Error("Backend não iniciado.");
  mainWindow = new BrowserWindow({
    width: 1400,
    height: 900,
    minWidth: 800,
    minHeight: 600,
    show: false,
    autoHideMenuBar: true,
    backgroundColor: "#0a0e1a",
    webPreferences: {
      contextIsolation: true,
      nodeIntegration: false,
      sandbox: true,
    },
  });
  void mainWindow.loadURL(`http://127.0.0.1:${backendPort}/`);
  mainWindow.once("ready-to-show", () => mainWindow?.show());
  mainWindow.on("closed", () => {
    mainWindow = null;
  });
  // Links externos abrem no navegador padrão (Stripe portal, dashboard).
  mainWindow.webContents.setWindowOpenHandler(({ url }) => {
    void shell.openExternal(url);
    return { action: "deny" };
  });
}

app.whenReady().then(async () => {
  try {
    await startBackend();
    await waitForBackend(backendPort!);
    createWindow();
    // Auto-update aponta para o manifesto privado (T.12.3).
    autoUpdater.checkForUpdatesAndNotify().catch(() => undefined);
  } catch (err) {
    dialog.showErrorBox(
      "Vectora",
      `Falha ao iniciar: ${(err as Error).message}`,
    );
    app.exit(1);
  }
});

app.on("window-all-closed", () => {
  if (process.platform !== "darwin") app.quit();
});

app.on("before-quit", () => {
  if (backend?.pid) {
    treeKill(backend.pid);
  }
});
