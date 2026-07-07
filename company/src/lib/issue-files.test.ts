// @vitest-environment jsdom
import { describe, it, expect } from "vitest";

import {
  MAX_ISSUE_FILES,
  MAX_VIDEO_SECONDS,
  ISSUE_FILE_LIMITS,
  validateIssueFile,
  isVideoType,
} from "./issue-files";

describe("validateIssueFile", () => {
  it("aceita imagem dentro do limite e recusa tipo desconhecido (par de erro)", () => {
    expect(validateIssueFile({ type: "image/png", size: 1024 })).toBeNull();
    expect(validateIssueFile({ type: "image/webp", size: 1024 })).toBeNull();
    expect(
      validateIssueFile({ type: "application/x-msdownload", size: 16 }),
    ).toBe("invalid_type");
    expect(validateIssueFile({ type: "", size: 0 })).toBe("invalid_type");
  });

  it("recusa arquivo acima do teto do próprio tipo (edge: exatamente no limite passa)", () => {
    const pngLimit = ISSUE_FILE_LIMITS["image/png"] ?? 0;
    expect(pngLimit).toBeGreaterThan(0);
    expect(validateIssueFile({ type: "image/png", size: pngLimit })).toBeNull();
    expect(validateIssueFile({ type: "image/png", size: pngLimit + 1 })).toBe(
      "too_large",
    );
  });

  it("vídeo até 30s passa; acima ou sem duração legível é recusado (par de erro)", () => {
    expect(
      validateIssueFile({ type: "video/mp4", size: 1024 }, MAX_VIDEO_SECONDS),
    ).toBeNull();
    expect(
      validateIssueFile(
        { type: "video/mp4", size: 1024 },
        MAX_VIDEO_SECONDS + 0.5,
      ),
    ).toBe("video_too_long");
    expect(validateIssueFile({ type: "video/webm", size: 1024 })).toBe(
      "video_too_long",
    );
  });

  it("constantes espelham o contrato do worker", () => {
    expect(MAX_ISSUE_FILES).toBe(3);
    expect(MAX_VIDEO_SECONDS).toBe(30);
    expect(isVideoType("video/mp4")).toBe(true);
    expect(isVideoType("image/png")).toBe(false);
  });
});
