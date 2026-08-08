// @vitest-environment jsdom
import { describe, it, expect } from "vitest";
import {
  fileToBase64,
  createImageAttachment,
  validateImageFile,
} from "../validation";

function makeFile(name: string, type: string, sizeBytes: number = 10): File {
  const content = new Uint8Array(sizeBytes);
  return new File([content], name, { type });
}

describe("fileToBase64", () => {
  it("converte um File pra base64 sem o prefixo de data URL", async () => {
    const file = makeFile("a.png", "image/png", 4);

    const base64 = await fileToBase64(file);

    expect(base64).not.toContain("data:");
    expect(typeof base64).toBe("string");
    expect(base64.length).toBeGreaterThan(0);
  });
});

describe("createImageAttachment", () => {
  it("monta um ImageAttachment completo a partir do File", async () => {
    const file = makeFile("foto.png", "image/png", 8);

    const att = await createImageAttachment(file);

    expect(att.name).toBe("foto.png");
    expect(att.mimeType).toBe("image/png");
    expect(att.size).toBe(8);
    expect(att.base64).toBeTruthy();
    expect(att.url).toBeTruthy();
    expect(att.id).toBeTruthy();
  });
});

describe("validateImageFile", () => {
  it("aceita imagem PNG dentro do limite de 10MB", () => {
    const result = validateImageFile(makeFile("a.png", "image/png", 1024));

    expect(result.valid).toBe(true);
  });

  it("rejeita arquivo maior que o limite (10MB para tipos comuns) — erro/borda", () => {
    const result = validateImageFile(
      makeFile("grande.png", "image/png", 11 * 1024 * 1024),
    );

    expect(result.valid).toBe(false);
    expect(result.error).toContain("10MB");
  });

  it("HAR aceita até 50MB (limite maior que o padrão)", () => {
    const okHar = validateImageFile(
      makeFile("captura.har", "application/octet-stream", 40 * 1024 * 1024),
    );
    const grandeDemais = validateImageFile(
      makeFile("captura.har", "application/octet-stream", 51 * 1024 * 1024),
    );

    expect(okHar.valid).toBe(true);
    expect(grandeDemais.valid).toBe(false);
    expect(grandeDemais.error).toContain("50MB");
  });

  it("áudio aceita até 25MB (limite intermediário)", () => {
    const ok = validateImageFile(
      makeFile("fala.mp3", "audio/mpeg", 20 * 1024 * 1024),
    );
    const grandeDemais = validateImageFile(
      makeFile("fala.mp3", "audio/mpeg", 26 * 1024 * 1024),
    );

    expect(ok.valid).toBe(true);
    expect(grandeDemais.valid).toBe(false);
    expect(grandeDemais.error).toContain("25MB");
  });

  it("aceita por extensão quando o mimetype não é reconhecido (fallback)", () => {
    const result = validateImageFile(
      makeFile("script.py", "application/octet-stream", 100),
    );

    expect(result.valid).toBe(true);
  });

  it("rejeita tipo de arquivo não suportado (nem mimetype nem extensão reconhecidos) — erro/borda", () => {
    const result = validateImageFile(
      makeFile("binario.exe", "application/octet-stream", 100),
    );

    expect(result.valid).toBe(false);
    expect(result.error).toContain(".exe");
  });
});
