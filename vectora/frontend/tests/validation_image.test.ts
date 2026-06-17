/**
 * Tests para validateImageFile: limites de tamanho (10MB padrão, 50MB p/ .har)
 * e aceitação por mimetype OU extensão.
 */

import { describe, expect, it } from "vitest";
import { validateImageFile } from "@/lib/utils/chat/validation";

function file(name: string, size: number, type = ""): File {
  return { name, size, type } as unknown as File;
}

const MB = 1024 * 1024;

describe("validateImageFile", () => {
  it("aceita imagem pequena por mimetype", () => {
    expect(validateImageFile(file("foto.png", 1 * MB, "image/png"))).toEqual({
      valid: true,
    });
  });

  it("aceita por extensão quando o mimetype está vazio", () => {
    expect(validateImageFile(file("script.py", 1 * MB, "")).valid).toBe(true);
  });

  it("rejeita arquivo acima de 10MB (não-har)", () => {
    const res = validateImageFile(file("grande.png", 11 * MB, "image/png"));
    expect(res.valid).toBe(false);
    expect(res.error).toContain("10MB");
  });

  it("permite .har até 50MB", () => {
    expect(validateImageFile(file("captura.har", 40 * MB, "")).valid).toBe(
      true,
    );
  });

  it("rejeita .har acima de 50MB", () => {
    const res = validateImageFile(file("captura.har", 60 * MB, ""));
    expect(res.valid).toBe(false);
    expect(res.error).toContain("50MB");
  });

  it("rejeita tipo não suportado e informa a extensão", () => {
    const res = validateImageFile(file("malware.exe", 1 * MB, ""));
    expect(res.valid).toBe(false);
    expect(res.error).toContain(".exe");
  });
});
