// Validação client-side dos anexos de issue. Espelha os limites do worker
// (services/src/issues/routes.ts::ISSUE_FILE_LIMITS) — o worker é a
// autoridade; aqui é só feedback imediato antes do upload.

export const MAX_ISSUE_FILES = 3;
export const MAX_VIDEO_SECONDS = 30;

export const ISSUE_FILE_LIMITS: Record<string, number> = {
  "image/png": 5 * 1024 * 1024,
  "image/jpeg": 5 * 1024 * 1024,
  "image/webp": 5 * 1024 * 1024,
  "video/mp4": 50 * 1024 * 1024,
  "video/webm": 50 * 1024 * 1024,
};

export const ISSUE_FILE_ACCEPT = Object.keys(ISSUE_FILE_LIMITS).join(",");

export type IssueFileError =
  | "invalid_type"
  | "too_large"
  | "video_too_long"
  | "too_many";

export function isVideoType(type: string): boolean {
  return type.startsWith("video/");
}

/**
 * Valida um anexo. `durationSeconds` só é exigido para vídeo (lido da
 * metadata pelo caller — jsdom não decodifica mídia, então a leitura fica
 * fora daqui de propósito).
 */
export function validateIssueFile(
  file: { type: string; size: number },
  durationSeconds?: number,
): IssueFileError | null {
  if (!(file.type in ISSUE_FILE_LIMITS)) return "invalid_type";
  const limit = ISSUE_FILE_LIMITS[file.type];
  if (file.size > limit) return "too_large";
  if (isVideoType(file.type)) {
    if (durationSeconds === undefined || durationSeconds > MAX_VIDEO_SECONDS) {
      return "video_too_long";
    }
  }
  return null;
}

/** Duração de um vídeo em segundos, via metadata (browser real, não jsdom). */
export function readVideoDuration(file: File): Promise<number> {
  return new Promise((resolve, reject) => {
    const url = URL.createObjectURL(file);
    const video = document.createElement("video");
    video.preload = "metadata";
    video.onloadedmetadata = () => {
      URL.revokeObjectURL(url);
      resolve(video.duration);
    };
    video.onerror = () => {
      URL.revokeObjectURL(url);
      reject(new Error("video_metadata_unreadable"));
    };
    video.src = url;
  });
}
