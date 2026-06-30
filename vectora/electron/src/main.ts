/**
 * Vectora Desktop — main process.
 *
 * Responsabilidades:
 * - Spawn do binário Nuitka (``vectora-core``) como sidecar (VECTORA_DESKTOP=1).
 * - Transporte IPC: unix socket (Linux/macOS) / TCP loopback (Windows). A SPA
 *   carrega de ``vectora-app://app/`` e o main encaminha tudo ao backend, sem
 *   expor porta TCP no desktop (em Linux/macOS).
 * - Health-check com retry exponencial antes de carregar a janela.
 * - Tray icon com menu (Open / Restart Backend / Quit).
 * - Deep-link ``vectora://`` (signin magic-link, deep-link de workspace).
 * - IPC tipado (``contextBridge``) exposto via ``preload.ts``.
 * - Auto-update via ``electron-updater`` repassando estado para o renderer.
 * - Crash handler com diálogo "Reiniciar" e relay para Sentry quando ligado.
 *
 * Não roda lógica de negócio — é casca nativa que orquestra o backend.
 */

import { spawn, spawnSync, ChildProcess } from "child_process";
import * as fs from "fs";
import {
  app,
  BrowserWindow,
  Menu,
  Tray,
  dialog,
  ipcMain,
  nativeImage,
  protocol,
  session,
  shell,
} from "electron";
import { autoUpdater } from "electron-updater";
import * as http from "http";
import * as net from "net";
import * as os from "os";
import * as path from "path";
import { Readable } from "stream";
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
let backendPipePath: string | null = null; // Windows named pipe path (\\.\pipe\vectora-<pid>)
let mainWindow: BrowserWindow | null = null;
let tray: Tray | null = null;
let pendingDeepLink: string | null = null;
let updateReady = false;

const PROTOCOL = "vectora";
const APP_SCHEME = "vectora-app"; // origem da SPA no desktop (IPC, sem TCP)
// 90s: cobre extração do Nuitka onefile no primeiro boot (100-200 MB → %TEMP%)
// e scan do Windows Defender em binário novo não reconhecido.
const READINESS_TIMEOUT_MS = 90_000;
const HEALTH_BASE_DELAY_MS = 200;
const HEALTH_MAX_DELAY_MS = 2_000;

// Últimas linhas de stdout/stderr do backend — exibidas no dialog de erro.
const _backendLog: string[] = [];
const _MAX_LOG_LINES = 60;

// Arquivo que persiste o PID do sidecar backend entre sessões. Permite matar
// processo órfão deixado por crash do Electron sem disparar before-quit.
const _BACKEND_PID_FILE = path.join(os.homedir(), ".vectora", "backend.pid");

async function killStaleBackend(): Promise<void> {
  try {
    const raw = await fs.promises.readFile(_BACKEND_PID_FILE, "utf-8");
    const stalePid = parseInt(raw.trim(), 10);
    if (isNaN(stalePid)) return;
    treeKill(stalePid);
    await new Promise((r) => setTimeout(r, 400));
  } catch {
    // Arquivo não existe ou processo já morreu — normal.
  }
}

// O scheme da SPA precisa ser registrado ANTES de app.whenReady(). Habilita
// fetch/SSE e trata a origem como segura (Secure Context: crypto.randomUUID).
protocol.registerSchemesAsPrivileged([
  {
    scheme: APP_SCHEME,
    privileges: {
      standard: true,
      secure: true,
      supportFetchAPI: true,
      stream: true,
      corsEnabled: true,
    },
  },
]);

/**
 * Transporte do backend:
 * - Linux/macOS: unix socket (~/.vectora/vectora.sock)
 * - Windows: named pipe (\\.\pipe\vectora-<pid>) lido de stdout via VECTORA_IPC_PIPE
 * - Fallback Windows (sem pipe ainda pronto): TCP loopback
 */
function backendTransport(): http.RequestOptions {
  if (process.platform !== "win32") {
    return { socketPath: path.join(os.homedir(), ".vectora", "vectora.sock") };
  }
  if (backendPipePath) {
    return { socketPath: backendPipePath };
  }
  return { host: "127.0.0.1", port: backendPort ?? undefined };
}

const _HOP_BY_HOP = new Set([
  "transfer-encoding",
  "connection",
  "content-encoding",
  "content-length",
  "keep-alive",
]);

// Store in-memory de cookies do backend: injetado manualmente em toda request
// via forwardToBackend porque Chromium não inclui automaticamente cookies de
// session.defaultSession no Cookie header para schemes customizados (vectora-app://).
const _cookieStore = new Map<string, string>();

async function storeSetCookie(cookieStr: string): Promise<void> {
  const [nameValuePart, ...attrParts] = cookieStr
    .split(";")
    .map((s) => s.trim());
  const eqIdx = nameValuePart.indexOf("=");
  if (eqIdx === -1) return;
  const name = nameValuePart.slice(0, eqIdx).trim();
  const value = nameValuePart.slice(eqIdx + 1).trim();

  let httpOnly = false;
  const attrs: Record<string, string> = {};
  for (const part of attrParts) {
    if (part.toLowerCase() === "httponly") {
      httpOnly = true;
      continue;
    }
    const eq = part.indexOf("=");
    if (eq !== -1) {
      attrs[part.slice(0, eq).toLowerCase().trim()] = part.slice(eq + 1).trim();
    }
  }

  // Max-Age=0 → deletar o cookie (logout / expiração forçada).
  if (attrs["max-age"] !== undefined && parseInt(attrs["max-age"], 10) <= 0) {
    _cookieStore.delete(name);
    try {
      await session.defaultSession.cookies.remove(`${APP_SCHEME}://app`, name);
    } catch {}
    return;
  }

  _cookieStore.set(name, value);

  const details: Electron.CookiesSetDetails = {
    url: `${APP_SCHEME}://app`,
    name,
    value,
    httpOnly,
    secure: false,
    path: attrs["path"] ?? "/",
    sameSite:
      attrs["samesite"] === "strict"
        ? "strict"
        : attrs["samesite"] === "none"
          ? "no_restriction"
          : "lax",
  };
  if (attrs["max-age"] !== undefined) {
    details.expirationDate =
      Math.floor(Date.now() / 1000) + parseInt(attrs["max-age"], 10);
  }

  try {
    await session.defaultSession.cookies.set(details);
  } catch (err) {
    console.error(`[auth] falha ao armazenar cookie "${name}":`, err);
  }
}

/**
 * Encaminha um request do scheme ``vectora-app://`` para o backend pelo
 * transporte IPC, fazendo streaming da resposta (incl. SSE). ``vectora-app://
 * app/<path>`` → backend ``/<path>``.
 */
async function forwardToBackend(request: Request): Promise<Response> {
  const url = new URL(request.url);
  const headers: Record<string, string> = {};
  request.headers.forEach((value, key) => {
    if (!_HOP_BY_HOP.has(key.toLowerCase())) headers[key] = value;
  });

  // Injeta cookies do store in-memory no header Cookie. Necessário porque
  // Chromium não inclui automaticamente cookies de session.defaultSession
  // nas requests interceptadas por protocol.handle para schemes customizados.
  if (_cookieStore.size > 0) {
    headers["cookie"] = Array.from(_cookieStore.entries())
      .map(([k, v]) => `${k}=${v}`)
      .join("; ");
  }

  const body =
    request.method !== "GET" && request.method !== "HEAD"
      ? Buffer.from(await request.arrayBuffer())
      : undefined;

  return new Promise<Response>((resolve) => {
    const req = http.request(
      {
        ...backendTransport(),
        method: request.method,
        path: url.pathname + url.search,
        headers,
      },
      (res) => {
        void (async () => {
          const respHeaders = new Headers();
          for (const [key, value] of Object.entries(res.headers)) {
            if (value == null || _HOP_BY_HOP.has(key.toLowerCase())) continue;
            if (key.toLowerCase() === "set-cookie" && Array.isArray(value)) {
              for (const cookie of value) respHeaders.append(key, cookie);
            } else {
              respHeaders.set(
                key,
                Array.isArray(value) ? value.join(", ") : value,
              );
            }
          }
          // Armazena cookies explicitamente no session antes de resolver
          // para que estejam disponíveis na próxima request.
          const setCookies = res.headers["set-cookie"];
          if (Array.isArray(setCookies) && setCookies.length > 0) {
            await Promise.all(setCookies.map(storeSetCookie));
          }
          const stream = Readable.toWeb(res) as unknown as ReadableStream;
          resolve(
            new Response(stream, {
              status: res.statusCode ?? 502,
              headers: respHeaders,
            }),
          );
        })().catch((err) => {
          resolve(
            new Response(`Erro interno: ${(err as Error).message}`, {
              status: 500,
            }),
          );
        });
      },
    );
    req.on("error", (err) =>
      resolve(
        new Response(`Backend indisponível: ${err.message}`, { status: 502 }),
      ),
    );
    if (body) req.write(body);
    req.end();
  });
}

/** Health-check do backend pelo transporte IPC (UDS ou TCP). */
function pingBackend(): Promise<boolean> {
  return new Promise((resolve) => {
    const req = http.request(
      { ...backendTransport(), method: "GET", path: "/health" },
      (res) => {
        res.resume();
        resolve((res.statusCode ?? 500) < 400);
      },
    );
    req.on("error", () => resolve(false));
    req.end();
  });
}

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
      process.platform === "win32" ? "vectora.exe" : "vectora",
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
  backend = spawn(backendPath(), ["start"], {
    env,
    stdio: ["ignore", "pipe", "pipe"],
  });
  if (backend.pid) {
    fs.promises
      .writeFile(_BACKEND_PID_FILE, String(backend.pid), "utf-8")
      .catch(() => {});
  }
  backend.stdout?.on("data", (b: Buffer) => {
    const text = b.toString();
    // Lê VECTORA_IPC_PIPE=<path> do stdout para usar named pipe no Windows.
    const match = /VECTORA_IPC_PIPE=(.+)/.exec(text);
    if (match) backendPipePath = match[1].trim();
    _backendLog.push(text);
    if (_backendLog.length > _MAX_LOG_LINES) _backendLog.shift();
    process.stdout.write(`[backend] ${text}`);
  });
  backend.stderr?.on("data", (b: Buffer) => {
    const text = b.toString();
    _backendLog.push(text);
    if (_backendLog.length > _MAX_LOG_LINES) _backendLog.shift();
    process.stderr.write(`[backend] ${text}`);
  });
  backend.on("exit", handleBackendExit);
}

function handleBackendExit(code: number | null, signal: NodeJS.Signals | null) {
  if ((app as unknown as { isQuitting: boolean }).isQuitting) return;
  const logs = _backendLog.slice(-15).join("").trim();
  const detail = `code=${code} signal=${signal ?? "none"}${logs ? `\n\n${logs}` : ""}`;
  console.error(`[backend] saiu inesperadamente: ${detail}`);
  const opts = {
    type: "error" as const,
    title: "Vectora encerrou inesperadamente",
    message: "O backend Vectora encerrou sem aviso.",
    detail,
    buttons: ["Reiniciar", "Sair"],
    defaultId: 0,
    cancelId: 1,
  };
  const action = mainWindow
    ? dialog.showMessageBoxSync(mainWindow, opts)
    : dialog.showMessageBoxSync(opts);
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
  backendPipePath = null;
  try {
    await startBackend();
    await waitForBackend();
    if (mainWindow) {
      void mainWindow.loadURL(`${APP_SCHEME}://app/`);
    } else {
      createWindow();
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
 * Falha imediatamente se o processo backend já terminou (crash no startup).
 */
async function waitForBackend(): Promise<void> {
  const deadline = Date.now() + READINESS_TIMEOUT_MS;
  let delay = HEALTH_BASE_DELAY_MS;
  while (Date.now() < deadline) {
    // Detecta crash de startup sem esperar o timeout completo.
    if (backend !== null && backend.exitCode !== null) {
      const logs = _backendLog.slice(-20).join("").trim();
      throw new Error(
        `Backend encerrou inesperadamente (code=${backend.exitCode}).` +
          (logs ? `\n\nÚltimos logs:\n${logs}` : ""),
      );
    }
    if (await pingBackend()) return;
    await new Promise((r) => setTimeout(r, delay));
    delay = Math.min(delay * 2, HEALTH_MAX_DELAY_MS);
  }
  const logs = _backendLog.slice(-20).join("").trim();
  throw new Error(
    `Backend não respondeu em ${READINESS_TIMEOUT_MS / 1000}s.` +
      (logs ? `\n\nÚltimos logs:\n${logs}` : ""),
  );
}

// ---------------------------------------------------------------------------
// Window
// ---------------------------------------------------------------------------

function createWindow(): void {
  if (mainWindow) {
    mainWindow.show();
    mainWindow.focus();
    return;
  }
  if (backendPort === null && !backendPipePath)
    throw new Error("Backend não iniciado.");
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

  // Carrega a SPA pela origem IPC — zero porta TCP exposta (UDS em Linux/macOS).
  void mainWindow.loadURL(`${APP_SCHEME}://app/`);
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
    } else {
      createWindow();
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
        } else {
          createWindow();
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
  } else {
    createWindow();
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
  // Ponte IPC: serve a SPA e encaminha /auth, /vectora.*, /mcp, SSE… ao backend
  // pelo unix socket (Linux/macOS) ou TCP loopback (Windows).
  protocol.handle(APP_SCHEME, (req) => forwardToBackend(req));
  try {
    await killStaleBackend();
    await startBackend();
    await waitForBackend();
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
    const pid = backend.pid;
    backend = null;
    // spawnSync bloqueia até o taskkill terminar — garante que o backend
    // está morto antes do processo Electron sair (treeKill é async e o
    // Electron saía antes, deixando o backend órfão).
    if (process.platform === "win32") {
      spawnSync("taskkill", ["/T", "/F", "/PID", String(pid)], {
        stdio: "ignore",
      });
    } else {
      treeKill(pid);
    }
  }
  try {
    fs.unlinkSync(_BACKEND_PID_FILE);
  } catch {}
});

app.on("activate", () => {
  // macOS: clicar no dock recria janela se fechada.
  if (BrowserWindow.getAllWindows().length === 0 && backendPort !== null) {
    createWindow();
  }
});
