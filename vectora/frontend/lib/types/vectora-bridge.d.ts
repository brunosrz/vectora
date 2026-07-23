/**
 * Tipos do bridge ``window.vectora`` exposto pelo preload do desktop
 * Electron (``desktop/src/preload.ts``). Centralizado para evitar
 * declarações divergentes em componentes diferentes.
 */

export interface VectoraUpdateStatus {
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

export interface VectoraDesktopBridge {
  readonly platform?: NodeJS.Platform;
  readonly appVersion?: string;
  openExternal?: (url: string) => Promise<void>;
  acknowledgeDeepLink?: (url: string) => void;
  onDeepLink?: (handler: (url: string) => void) => () => void;
  onUpdateStatus?: (
    handler: (status: VectoraUpdateStatus) => void,
  ) => () => void;
  quitAndInstallUpdate?: () => void;
  /** Dispara uma checagem manual de atualização — independente do toggle
   * de auto-update (que só gate os timers automáticos, ver main.ts). */
  checkForUpdate?: () => void;
  /** Origem `ws://127.0.0.1:{porta}` do backend — necessária porque o
   * renderer carrega de `vectora-app://`, scheme custom contra o qual uma
   * URL relativa de WebSocket não resolve pra `ws://` (só HTTP/fetch passa
   * pelo proxy de protocolo). `null` se o backend ainda não subiu porta. */
  getBackendWsOrigin?: () => Promise<string | null>;
  windowControls?: {
    minimize: () => void;
    maximizeToggle: () => void;
    close: () => void;
    isMaximized: () => Promise<boolean>;
    onStateChange: (
      handler: (state: { maximized: boolean }) => void,
    ) => () => void;
  };
}

declare global {
  interface Window {
    vectora?: VectoraDesktopBridge;
  }
}
