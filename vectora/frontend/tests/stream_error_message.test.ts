import { describe, it, expect } from "vitest";
import { streamErrorMessage } from "@/lib/hooks/chat/use-stream-handler";

// O backend classifica erros de stream em códigos tipados; o frontend mapeia
// para mensagens localizadas. Erros de provider (ex.: 429 do Gemini) viram um
// aviso limpo de limite, nunca o JSON cru como resposta da IA.
describe("streamErrorMessage", () => {
  it("RATE_LIMIT → mensagem de limite (não vaza JSON do provider)", () => {
    const msg = streamErrorMessage("RATE_LIMIT");
    expect(msg).toBeTruthy();
    expect(msg).not.toMatch(/RESOURCE_EXHAUSTED|429|gemini/i);
  });

  it("AUTH → mensagem de autenticação", () => {
    expect(streamErrorMessage("AUTH")).toBeTruthy();
  });

  it("código desconhecido → mensagem genérica", () => {
    expect(streamErrorMessage("STREAM_ERROR")).toBeTruthy();
    expect(streamErrorMessage(undefined)).toBeTruthy();
  });

  it("códigos distintos produzem mensagens distintas", () => {
    const rate = streamErrorMessage("RATE_LIMIT");
    const auth = streamErrorMessage("AUTH");
    const generic = streamErrorMessage("STREAM_ERROR");
    expect(new Set([rate, auth, generic]).size).toBe(3);
  });
});
