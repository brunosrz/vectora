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
}

declare global {
  interface Window {
    vectora?: VectoraDesktopBridge;
  }
}

export {};
