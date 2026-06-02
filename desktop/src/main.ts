/**
 * Vectora Desktop — main process.
 *
 * Responsabilidades:
 * - Spawn do binário Nuitka (``vectora-core``) como sidecar com porta efêmera.
 * - Health-check com retry exponencial antes de carregar a janela.
 * - BrowserWindow apontando para ``http://127.0.0.1:<port>/``.
 * - Tray icon com menu (Open / Restart Backend / Quit).
 * - Deep-link ``vectora://`` (signin magic-link, deep-link de workspace).
 * - IPC tipado (``contextBridge``) exposto via ``preload.ts``.
 * - Auto-update via ``electron-updater`` repassando estado para o renderer.
 * - Crash handler com diálogo "Reiniciar" e relay para Sentry quando ligado.
 *
 * Não roda lógica de negócio — é casca nativa que orquestra o backend.
 */

import { spawn, ChildProcess } from "child_process";
import {
  app,
  BrowserWindow,
  Menu,
  Tray,
  dialog,
  ipcMain,
  nativeImage,
  shell,
} from "electron";
import { autoUpdater } from "electron-updater";
import * as net from "net";
import * as path from "path";
// tree-kill ships its own types — no @types/tree-kill needed.
import treeKill = require("tree-kill");

interface UpdateStatus {
  state:
    | "checking"
    | "available"
    | "downloading"
    | "downloaded"
    | "error"
    | "not-available";
  message?: string;
  progress?: number;
}

let backend: ChildProcess | null = null;
let backendPort: number | null = null;
let mainWindow: BrowserWindow | null = null;
let tray: Tray | null = null;
let pendingDeepLink: string | null = null;
let updateReady = false;

const PROTOCOL = "vectora";
const READINESS_TIMEOUT_MS = 30_000;
const HEALTH_BASE_DELAY_MS = 200;
const HEALTH_MAX_DELAY_MS = 2_000;

// ---------------------------------------------------------------------------
// Backend lifecycle
// ---------------------------------------------------------------------------

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

/**
 * Resolve o path do binário Nuitka. Em produção: ``resources/vectora-core/``
 * (electron-builder usa ``extraResources``). Em dev: override por env
 * ``VECTORA_CORE_PATH`` para apontar a um build local.
 */
function backendPath(): string {
  const override = process.env.VECTORA_CORE_PATH;
  if (override) {
    return path.join(
      override,
      process.platform === "win32" ? "src.exe" : "vectora",
    );
  }
  const resources = process.resourcesPath || path.join(__dirname, "..");
  const exe = process.platform === "win32" ? "vectora.exe" : "vectora";
  return path.join(resources, "vectora-core", exe);
}

async function startBackend(): Promise<void> {
  backendPort = await getFreePort();
  const env: NodeJS.ProcessEnv = {
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
  backend.on("exit", handleBackendExit);
}

function handleBackendExit(code: number | null, signal: NodeJS.Signals | null) {
  if ((app as unknown as { isQuitting: boolean }).isQuitting) return;
  const detail = `code=${code} signal=${signal ?? "none"}`;
  console.error(`[backend] saiu inesperadamente: ${detail}`);
  if (!mainWindow) return;
  const action = dialog.showMessageBoxSync(mainWindow, {
    type: "error",
    title: "Vectora encerrou inesperadamente",
    message: "O backend Vectora encerrou sem aviso.",
    detail,
    buttons: ["Reiniciar", "Sair"],
    defaultId: 0,
    cancelId: 1,
  });
  if (action === 0) {
    void restartBackend();
  } else {
    app.quit();
  }
}

async function restartBackend(): Promise<void> {
  if (backend?.pid) {
    treeKill(backend.pid);
    backend = null;
  }
  try {
    await startBackend();
    await waitForBackend(backendPort!);
    if (mainWindow && backendPort !== null) {
      void mainWindow.loadURL(`http://127.0.0.1:${backendPort}/`);
    }
  } catch (err) {
    dialog.showErrorBox(
      "Vectora",
      `Falha ao reiniciar backend: ${(err as Error).message}`,
    );
    app.exit(1);
  }
}

/**
 * Health-check com backoff exponencial. Cada falha dobra o delay até
 * ``HEALTH_MAX_DELAY_MS``, capado no ``READINESS_TIMEOUT_MS`` global.
 */
async function waitForBackend(port: number): Promise<void> {
  const deadline = Date.now() + READINESS_TIMEOUT_MS;
  let delay = HEALTH_BASE_DELAY_MS;
  while (Date.now() < deadline) {
    try {
      const ok = await fetch(`http://127.0.0.1:${port}/health`);
      if (ok.ok) return;
    } catch {
      // ignora — backend ainda subindo
    }
    await new Promise((r) => setTimeout(r, delay));
    delay = Math.min(delay * 2, HEALTH_MAX_DELAY_MS);
  }
  throw new Error(`Backend não respondeu em ${READINESS_TIMEOUT_MS}ms.`);
}

// ---------------------------------------------------------------------------
// Window
// ---------------------------------------------------------------------------

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
      preload: path.join(__dirname, "preload.js"),
    },
  });

  // Inject app version no preload sem precisar recompilar.
  process.env.VECTORA_APP_VERSION = app.getVersion();

  void mainWindow.loadURL(`http://127.0.0.1:${backendPort}/`);
  mainWindow.once("ready-to-show", () => {
    mainWindow?.show();
    if (pendingDeepLink) {
      mainWindow?.webContents.send("vectora:deep-link", pendingDeepLink);
      pendingDeepLink = null;
    }
  });
  mainWindow.on("closed", () => {
    mainWindow = null;
  });

  // Links externos abrem no navegador padrão (Stripe portal, dashboard).
  mainWindow.webContents.setWindowOpenHandler(({ url }) => {
    void shell.openExternal(url);
    return { action: "deny" };
  });

  // Bloqueia reload/devtools em prod. Permite com VECTORA_DEV=1.
  if (process.env.VECTORA_DEV !== "1") {
    mainWindow.webContents.on("before-input-event", (event, input) => {
      const isReload =
        (input.control || input.meta) && input.key.toLowerCase() === "r";
      const isDevTools =
        (input.control || input.meta) &&
        input.shift &&
        input.key.toLowerCase() === "i";
      if (isReload || isDevTools) event.preventDefault();
    });
  }
}

// ---------------------------------------------------------------------------
// Tray icon
// ---------------------------------------------------------------------------

function getTrayIcon(): Electron.NativeImage {
  // electron-builder copia ``build-resources/icon.png`` para ``resources/``;
  // em dev usa o favicon do chat como fallback.
  const candidates = [
    path.join(process.resourcesPath, "tray-icon.png"),
    path.join(__dirname, "..", "..", "chat", "public", "favicon-32x32.png"),
  ];
  for (const c of candidates) {
    const img = nativeImage.createFromPath(c);
    if (!img.isEmpty()) return img;
  }
  return nativeImage.createEmpty();
}

function createTray(): void {
  if (tray) return;
  tray = new Tray(getTrayIcon());
  tray.setToolTip("Vectora");
  refreshTrayMenu();
  tray.on("click", () => {
    if (mainWindow) {
      mainWindow.isVisible() ? mainWindow.focus() : mainWindow.show();
    }
  });
}

function refreshTrayMenu(): void {
  if (!tray) return;
  const menu = Menu.buildFromTemplate([
    {
      label: "Abrir Vectora",
      click: () => {
        if (mainWindow) {
          mainWindow.show();
          mainWindow.focus();
        }
      },
    },
    {
      label: "Reiniciar backend",
      click: () => void restartBackend(),
    },
    ...(updateReady
      ? [
          { type: "separator" as const },
          {
            label: "Aplicar atualização e reiniciar",
            click: () => autoUpdater.quitAndInstall(),
          },
        ]
      : []),
    { type: "separator" },
    {
      label: "Sair",
      click: () => app.quit(),
    },
  ]);
  tray.setContextMenu(menu);
}

// ---------------------------------------------------------------------------
// Deep-link (vectora://)
// ---------------------------------------------------------------------------

function registerDeepLinkProtocol(): void {
  if (process.defaultApp && process.argv.length >= 2) {
    app.setAsDefaultProtocolClient(PROTOCOL, process.execPath, [
      path.resolve(process.argv[1]),
    ]);
  } else {
    app.setAsDefaultProtocolClient(PROTOCOL);
  }
}

function deliverDeepLink(url: string): void {
  if (mainWindow && !mainWindow.webContents.isLoading()) {
    mainWindow.webContents.send("vectora:deep-link", url);
    mainWindow.show();
    mainWindow.focus();
  } else {
    pendingDeepLink = url;
  }
}

// ---------------------------------------------------------------------------
// Auto-updater
// ---------------------------------------------------------------------------

function setupAutoUpdater(): void {
  autoUpdater.autoDownload = true;
  autoUpdater.autoInstallOnAppQuit = true;

  const broadcast = (status: UpdateStatus) => {
    mainWindow?.webContents.send("vectora:update-status", status);
  };

  autoUpdater.on("checking-for-update", () => broadcast({ state: "checking" }));
  autoUpdater.on("update-available", (info) =>
    broadcast({ state: "available", message: info.version }),
  );
  autoUpdater.on("update-not-available", () =>
    broadcast({ state: "not-available" }),
  );
  autoUpdater.on("download-progress", (p) =>
    broadcast({ state: "downloading", progress: p.percent }),
  );
  autoUpdater.on("update-downloaded", () => {
    updateReady = true;
    refreshTrayMenu();
    broadcast({ state: "downloaded" });
  });
  autoUpdater.on("error", (err) =>
    broadcast({ state: "error", message: err.message }),
  );

  // Verifica updates 30s após boot (deixa o backend subir primeiro)
  // e depois a cada 6h.
  setTimeout(() => {
    autoUpdater.checkForUpdates().catch(() => undefined);
  }, 30_000);
  setInterval(
    () => autoUpdater.checkForUpdates().catch(() => undefined),
    6 * 60 * 60 * 1000,
  );
}

// ---------------------------------------------------------------------------
// IPC handlers (responde ao preload bridge)
// ---------------------------------------------------------------------------

function registerIpc(): void {
  ipcMain.handle("vectora:open-external", (_event, url: string) =>
    shell.openExternal(url),
  );
  ipcMain.on("vectora:deep-link-ack", (_event, url: string) => {
    console.log(`[deep-link] renderer ack: ${url}`);
  });
  ipcMain.on("vectora:quit-and-install", () => {
    if (updateReady) autoUpdater.quitAndInstall();
  });
}

// ---------------------------------------------------------------------------
// Single instance lock — necessário para deep-link no Windows/Linux
// ---------------------------------------------------------------------------

const gotLock = app.requestSingleInstanceLock();
if (!gotLock) {
  app.quit();
}

app.on("second-instance", (_event, argv) => {
  // Windows passa o deep-link como último argumento.
  const url = argv.find((a) => a.startsWith(`${PROTOCOL}://`));
  if (url) deliverDeepLink(url);
  if (mainWindow) {
    if (mainWindow.isMinimized()) mainWindow.restore();
    mainWindow.show();
    mainWindow.focus();
  }
});

// macOS entrega via "open-url".
app.on("open-url", (event, url) => {
  event.preventDefault();
  if (url.startsWith(`${PROTOCOL}://`)) deliverDeepLink(url);
});

// ---------------------------------------------------------------------------
// App lifecycle
// ---------------------------------------------------------------------------

(app as unknown as { isQuitting: boolean }).isQuitting = false;

app.whenReady().then(async () => {
  registerDeepLinkProtocol();
  registerIpc();
  try {
    await startBackend();
    await waitForBackend(backendPort!);
    createWindow();
    createTray();
    setupAutoUpdater();
  } catch (err) {
    dialog.showErrorBox(
      "Vectora",
      `Falha ao iniciar: ${(err as Error).message}`,
    );
    app.exit(1);
  }
});

app.on("window-all-closed", () => {
  // Mantém app vivo no tray em todas plataformas — usuário usa "Sair" no
  // menu ou Cmd+Q (macOS).
  if (process.platform !== "darwin") {
    // No Windows/Linux, sem tray seria zumbi; com tray, fica disponível.
    if (!tray) app.quit();
  }
});

app.on("before-quit", () => {
  (app as unknown as { isQuitting: boolean }).isQuitting = true;
  if (backend?.pid) {
    treeKill(backend.pid);
  }
});

app.on("activate", () => {
  // macOS: clicar no dock recria janela se fechada.
  if (BrowserWindow.getAllWindows().length === 0 && backendPort !== null) {
    createWindow();
  }
});
