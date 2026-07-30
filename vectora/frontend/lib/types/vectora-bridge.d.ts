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

export interface VectoraViewBounds {
  x: number;
  y: number;
  width: number;
  height: number;
}

export type VectoraBrowserViewEvent =
  | {
      type: "navigated";
      url: string;
      canGoBack: boolean;
      canGoForward: boolean;
    }
  | { type: "titleUpdated"; title: string }
  | { type: "faviconUpdated"; favicon: string }
  | { type: "loadingChanged"; isLoading: boolean }
  | {
      type: "loadFailed";
      errorCode: number;
      errorDescription: string;
      url: string;
    };

export interface VectoraDesktopBridge {
  readonly platform?: NodeJS.Platform;
  readonly appVersion?: string;
  openExternal?: (url: string) => Promise<void>;
  /** Seletor nativo de pasta. `null` = cancelado (distinto de pasta escolhida).
   * Opcional como o resto da bridge: no modo web `window.vectora` não existe. */
  pickDirectory?: () => Promise<string | null>;
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
  /** Browser real da aba Browser do workbench (WebContentsView com sessão
   * própria) — presente só no desktop; sem isso, a aba Browser cai no
   * `<iframe>` de fallback (sujeito a X-Frame-Options). */
  browserView?: {
    createView: () => Promise<number>;
    destroyView: (viewId: number) => void;
    navigate: (
      viewId: number,
      url: string,
    ) => Promise<{ ok: boolean; error?: string }>;
    goBack: (viewId: number) => void;
    goForward: (viewId: number) => void;
    reload: (viewId: number) => void;
    stop: (viewId: number) => void;
    setBounds: (viewId: number, bounds: VectoraViewBounds) => void;
    setVisible: (viewId: number, visible: boolean) => void;
    onEvent: (
      handler: (viewId: number, event: VectoraBrowserViewEvent) => void,
    ) => () => void;
  };
}

declare global {
  interface Window {
    vectora?: VectoraDesktopBridge;
  }
}
