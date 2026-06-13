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
};

contextBridge.exposeInMainWorld("vectora", bridge);
