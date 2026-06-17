/**
 * Tests para o `chat-input-store`: injeção cross-component (push/consume) e
 * rascunhos por thread persistidos.
 */

import { describe, expect, it, beforeEach } from "vitest";
import { useChatInputStore } from "../chat-input-store";

beforeEach(() => {
  useChatInputStore.setState({ draft: null, mention: null, drafts: {} });
  if (typeof localStorage !== "undefined") localStorage.clear();
});

describe("chat-input-store — injeção cross-component", () => {
  it("pushDraft/consumeDraft preenchem e limpam o draft volátil", () => {
    const s = useChatInputStore.getState();
    s.pushDraft("crie um plano");
    expect(useChatInputStore.getState().draft).toBe("crie um plano");
    useChatInputStore.getState().consumeDraft();
    expect(useChatInputStore.getState().draft).toBeNull();
  });

  it("pushMention/consumeMention preenchem e limpam a mention", () => {
    useChatInputStore.getState().pushMention("src/app.ts");
    expect(useChatInputStore.getState().mention).toBe("src/app.ts");
    useChatInputStore.getState().consumeMention();
    expect(useChatInputStore.getState().mention).toBeNull();
  });
});

describe("chat-input-store — rascunhos por thread", () => {
  it("getDraft devolve string vazia para thread sem rascunho", () => {
    expect(useChatInputStore.getState().getDraft("t1")).toBe("");
  });

  it("setDraft persiste por thread e isola threads diferentes", () => {
    const s = useChatInputStore.getState();
    s.setDraft("t1", "olá A");
    s.setDraft("t2", "olá B");
    expect(useChatInputStore.getState().getDraft("t1")).toBe("olá A");
    expect(useChatInputStore.getState().getDraft("t2")).toBe("olá B");
  });

  it("setDraft com texto vazio remove a entrada (não acumula vazios)", () => {
    const s = useChatInputStore.getState();
    s.setDraft("t1", "rascunho");
    s.setDraft("t1", "");
    expect("t1" in useChatInputStore.getState().drafts).toBe(false);
  });

  it("setDraft idempotente: mesmo valor não cria novo objeto de estado", () => {
    const s = useChatInputStore.getState();
    s.setDraft("t1", "x");
    const before = useChatInputStore.getState().drafts;
    s.setDraft("t1", "x");
    expect(useChatInputStore.getState().drafts).toBe(before);
  });

  it("clearDraft remove o rascunho da thread (envio)", () => {
    const s = useChatInputStore.getState();
    s.setDraft("t1", "vai ser enviada");
    s.clearDraft("t1");
    expect(useChatInputStore.getState().getDraft("t1")).toBe("");
  });

  it("clearDraft em thread inexistente é no-op", () => {
    const before = useChatInputStore.getState().drafts;
    useChatInputStore.getState().clearDraft("inexistente");
    expect(useChatInputStore.getState().drafts).toBe(before);
  });
});
