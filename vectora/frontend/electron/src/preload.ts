/**
 * Preload script — bridge tipada entre o renderer (chat web) e o main
 * process do Electron.
 *
 * Exposto no renderer como ``window.vectora`` (via ``contextBridge``).
 * Apenas APIs que precisam de capacidades nativas (deep-link, abrir URL
 * externa, info da plataforma) cruzam o bridge — toda a lógica de
 * negócio continua sendo HTTP/SSE contra o backend Vectora.
 */

import { contextBridge, ipcRenderer } from "electron";

export interface VectoraDesktopBridge {
  /** "win32" | "darwin" | "linux" — útil para shortcuts e UI condicional. */
  readonly platform: NodeJS.Platform;
  /** Versão do app Electron (lida do package.json no boot). */
  readonly appVersion: string;
  /** Abre uma URL no navegador padrão (Stripe portal, dashboard, docs). */
  openExternal: (url: string) => Promise<void>;
  /** Notifica o main que o renderer recebeu um deep-link e o processou. */
  acknowledgeDeepLink: (url: string) => void;
  /** Subscreve a deep-links (`vectora://...`) entregues ao app. */
  onDeepLink: (handler: (url: string) => void) => () => void;
  /** Subscreve ao estado do auto-updater (downloading, ready, error). */
  onUpdateStatus: (
    handler: (status: {
      state:
        | "checking"
        | "available"
        | "downloading"
        | "downloaded"
        | "error"
        | "not-available";
      message?: string;
      progress?: number;
    }) => void,
  ) => () => void;
  /** Aplica update baixado e reinicia. */
  quitAndInstallUpdate: () => void;
  /** Dispara uma checagem manual de atualização — independente do toggle
   * de auto-update (que só gate os timers automáticos, ver main.ts). */
  checkForUpdate: () => void;
  /** Origem `ws://127.0.0.1:{porta}` do backend — necessária porque o
   * renderer carrega de `vectora-app://`, scheme custom contra o qual uma
   * URL relativa de WebSocket não resolve pra `ws://` (só HTTP/fetch passa
   * pelo proxy de protocolo). `null` se o backend ainda não subiu porta. */
  getBackendWsOrigin: () => Promise<string | null>;
  /** Controles da titlebar customizada (frame: false — ver main.ts). */
  windowControls: {
    minimize: () => void;
    maximizeToggle: () => void;
    close: () => void;
    isMaximized: () => Promise<boolean>;
    /** Subscreve a mudanças de estado maximizado/restaurado da janela nativa
     * (ex.: duplo-clique na titlebar, resize manual) — mantém o ícone
     * maximizar/restaurar sincronizado sem polling. */
    onStateChange: (
      handler: (state: { maximized: boolean }) => void,
    ) => () => void;
  };
}

const bridge: VectoraDesktopBridge = {
  platform: process.platform,
  appVersion: process.env.VECTORA_APP_VERSION ?? "0.0.0",
  openExternal: (url) => ipcRenderer.invoke("vectora:open-external", url),
  acknowledgeDeepLink: (url) => ipcRenderer.send("vectora:deep-link-ack", url),
  onDeepLink: (handler) => {
    const listener = (_event: unknown, url: string) => handler(url);
    ipcRenderer.on("vectora:deep-link", listener);
    return () => {
      ipcRenderer.removeListener("vectora:deep-link", listener);
    };
  },
  onUpdateStatus: (handler) => {
    const listener = (_event: unknown, status: Parameters<typeof handler>[0]) =>
      handler(status);
    ipcRenderer.on("vectora:update-status", listener);
    return () => {
      ipcRenderer.removeListener("vectora:update-status", listener);
    };
  },
  quitAndInstallUpdate: () => ipcRenderer.send("vectora:quit-and-install"),
  checkForUpdate: () => ipcRenderer.send("vectora:check-for-update"),
  getBackendWsOrigin: () => ipcRenderer.invoke("vectora:get-backend-ws-origin"),
  windowControls: {
    minimize: () => ipcRenderer.send("vectora:window-minimize"),
    maximizeToggle: () => ipcRenderer.send("vectora:window-maximize-toggle"),
    close: () => ipcRenderer.send("vectora:window-close"),
    isMaximized: () => ipcRenderer.invoke("vectora:window-is-maximized"),
    onStateChange: (handler) => {
      const listener = (
        _event: unknown,
        state: Parameters<typeof handler>[0],
      ) => handler(state);
      ipcRenderer.on("vectora:window-state", listener);
      return () => {
        ipcRenderer.removeListener("vectora:window-state", listener);
      };
    },
  },
};

contextBridge.exposeInMainWorld("vectora", bridge);
